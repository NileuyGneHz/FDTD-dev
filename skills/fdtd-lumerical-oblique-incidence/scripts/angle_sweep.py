#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""angle_sweep.py — plan / collect a variable-incidence-angle FDTD sweep.

This skill owns NO engine session. It emits an angle-scan plan and a spec that the existing
``run_fdtd_sweep.py --sweep-json`` can drive verbatim, then aggregates the resulting CSVs.
All physics decisions come from the single builder implementation in ``library/py/fsp_build.py``.

    python angle_sweep.py --self-test
    python angle_sweep.py plan --spec spec.json --angles 0,30,60 --pol 90 \
        --mode bfast --out <dir> [--dry-run] [--json]
    python angle_sweep.py collect --plan <dir>/angle_sweep_plan.json \
        --run-dir <dir> --out <dir>/angle_matrix.csv [--json]

Exit codes: 0 ok / 1 check failed / 2 argument or config error.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import itertools
import json
import math
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True


def repo_root() -> pathlib.Path:
    for parent in pathlib.Path(__file__).resolve().parents:
        if (parent / "library" / "py" / "fsp_build.py").is_file():
            return parent
    raise RuntimeError("找不到仓库根（应包含 library/py/fsp_build.py）")


ROOT = repo_root()
if str(ROOT / "library" / "py") not in sys.path:
    sys.path.insert(0, str(ROOT / "library" / "py"))

from fsp_build import (  # noqa: E402
    C0, bloch_angle_drift, resolve_axes, resolve_incidence, source_wavelength_range,
)

# Ansys BFAST documentation cost multipliers relative to normal incidence.
_BFAST_COST = ((0.0, 1.0), (30.0, 2.0), (60.0, 7.5), (70.0, 16.6), (80.0, 65.8))
SIGN_CONVENTION = "paper_theta_i = -lumerical_angle_theta"
_COURSE_ANGLE_LIMIT_DEG = 60.0
_REJECT_ANGLE_DEG = 85.0
_DRIFT_TOL_DEG = 2.0


class AngleError(Exception):
    """Configuration error that must stop the plan (never silently relaxed)."""


# ----------------------------------------------------------------------------- pure helpers
def parse_list(text: str, name: str) -> list[float]:
    """Parse ``"0,30,60"`` into floats. Empty / non-numeric is a hard error."""
    if text is None or not str(text).strip():
        raise AngleError("--%s 不能为空" % name)
    out = []
    for tok in str(text).split(","):
        tok = tok.strip()
        if not tok:
            raise AngleError("--%s 含空元素: %r" % (name, text))
        try:
            out.append(float(tok))
        except ValueError:
            raise AngleError("--%s 的 %r 不是数字" % (name, tok)) from None
    return out


def bloch_boundary_phase(period_m: float, lam_m: float, theta_deg: float) -> float:
    """Delta-phi between the two lateral Bloch walls: 2*pi*P*sin(theta)/lambda."""
    return 2.0 * math.pi * float(period_m) * math.sin(math.radians(theta_deg)) / float(lam_m)


def bfast_cost_factor(theta_deg: float) -> float:
    """Interpolated wall-time multiplier from the Ansys BFAST table."""
    t = abs(float(theta_deg))
    if t <= 0.0:
        return 1.0
    if t >= _BFAST_COST[-1][0]:
        return _BFAST_COST[-1][1]
    for (a, ca), (b, cb) in zip(_BFAST_COST, _BFAST_COST[1:]):
        if a <= t <= b:
            return ca + (cb - ca) * (t - a) / (b - a)
    return _BFAST_COST[-1][1]


def grid_hash(angles, pols, mode) -> str:
    payload = json.dumps({"angles": angles, "pols": pols, "mode": mode}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_spec_angles(spec: dict, angles, pols, mode: str) -> dict:
    """Inject angle/polarization as PARAMETERS so the existing runner can sweep them.

    One number, one place: ``parameters.theta`` is the only source of the angle value;
    ``source.angle_theta_deg`` is just the expression string ``"theta"``.
    """
    out = copy.deepcopy(spec)
    params = out.setdefault("parameters", {})
    params["theta"] = float(angles[0])       # overwritten per point by --sweep-json
    params["pol"] = float(pols[0])
    sim = out["simulation"]
    src = sim["source"]
    src["angle_theta_deg"] = "theta"
    src["polarization_deg"] = "pol"
    # angle phi is inactive in 2D (measured on v251). Never emit it.
    src.pop("angle_phi_deg", None)
    inc = dict(sim.get("incidence") or {})
    inc["mode"] = mode
    inc["angle_grid_deg"] = list(angles)
    inc["polarizations_deg"] = list(pols)
    inc.setdefault("sign_convention", SIGN_CONVENTION)
    sim["incidence"] = inc
    # Also embed the sweep grid in the spec. run_fdtd_sweep.py reads spec["sweep"] when
    # --sweep-json is absent, which lets Windows cmd.exe callers avoid shell-quoting a JSON
    # literal (single quotes are NOT quotes there). One grid, one source of truth.
    out["sweep"] = {"theta": list(angles), "pol": list(pols)}
    out.setdefault("meta", {})["oblique_plan"] = {
        "angles_deg": list(angles), "polarizations_deg": list(pols), "mode": mode,
        "angle_is_parameter": "theta", "pol_is_parameter": "pol",
        "sign_convention": inc["sign_convention"],
    }
    return out


def make_plan(spec_path: str, spec: dict, angles, pols, mode: str, out_dir: str) -> tuple:
    """Engine-free plan. Raises AngleError on any physically wrong configuration."""
    if not angles or not pols:
        raise AngleError("角度或偏振网格为空")
    if len(set(angles)) != len(angles):
        raise AngleError("角度网格有重复值 %r：重复点会让 collect 只拿到同一条曲线" % angles)
    if len(set(pols)) != len(pols):
        raise AngleError("偏振网格有重复值 %r" % pols)
    for t in angles:
        if abs(t) >= _REJECT_ANGLE_DEG:
            raise AngleError("|theta|=%.1f° >= %.0f°：BFAST 掠入射不可靠"
                             % (abs(t), _REJECT_ANGLE_DEG))
    if mode not in ("normal", "bloch_single", "bfast", "auto"):
        raise AngleError("mode 只支持 normal / bloch_single / bfast / auto，收到 %r" % mode)

    spec2 = build_spec_angles(spec, angles, pols, mode)
    sim = spec2["simulation"]
    src = sim["source"]
    dim, p, lateral, _inv = resolve_axes(sim)
    lam_lo, lam_hi, _f_lo, _f_hi = source_wavelength_range(src)

    per_angle, warnings = [], []
    for th in angles:
        params = dict(spec2["parameters"])
        params["theta"] = th
        try:
            d = resolve_incidence(sim, params, dim, p, lateral, lam_lo, lam_hi)
        except ValueError as exc:
            raise AngleError("theta=%.1f° 配置非法: %s" % (th, exc)) from exc
        if d is None:
            raise AngleError("theta=%.1f° 没解析出 incidence 决策（spec 缺字段？）" % th)
        is_bfast = d["mode"] == "bfast"
        per_angle.append({
            "theta_deg": th, "mode": d["mode"],
            "plane_wave_type": d["plane_wave_type"],
            "source_properties": {"angle theta": d["theta"]},
            "tilt_axis": d["tilt_axis"], "tilt_bc": d["bc_tilt"],
            "pml_layers": d["pml_layers"], "bfast_alpha": d["bfast_alpha"],
            "cost_factor": round(bfast_cost_factor(th), 3) if is_bfast else 1.0,
            "warnings": d["warnings"],
        })
        warnings.extend("[%g°] %s" % (th, w) for w in d["warnings"])
        if abs(th) > _COURSE_ANGLE_LIMIT_DEG:
            warnings.append("[%g°] 超过课程经验上限 %.0f°" % (th, _COURSE_ANGLE_LIMIT_DEG))

    points = [{"theta_deg": t, "pol_deg": q} for t in angles for q in pols]
    plan = {
        "schema": "oblique-angle-plan/1.0",
        "spec": str(spec_path),
        "spec_angles": str(pathlib.Path(out_dir) / "spec_angles.json"),
        "dimension": dim, "propagation_axis": p,
        "tilt_axis": per_angle[0]["tilt_axis"],
        "mode": mode, "angles_deg": list(angles), "polarizations_deg": list(pols),
        "wavelength_range_um": [lam_lo * 1e6, lam_hi * 1e6],
        "sign_convention": sim["incidence"]["sign_convention"],
        "n_points": len(points), "points": points,
        "per_angle": per_angle,
        "estimated_total_cost_factor": round(
            sum(a["cost_factor"] for a in per_angle) * len(pols), 3),
        "angle_grid_sha256": grid_hash(list(angles), list(pols), mode),
        "warnings": warnings,
        "engine": "none (plan/collect are pure Python; the runner owns the session)",
        "check_coverage": {
            "checked": ["source.angle theta", "source.plane wave type", "tilt BC",
                        "pml layers", "bfast alpha"],
            "not_checked": ["angle phi (inactive in 2D)", "FDTD.angle theta (derived value)"],
        },
    }
    # The driver must consume the INJECTED spec: the original spec has no parameters.theta,
    # so sweeping it would produce three identical runs (N5 duplicate-curve failure).
    plan["driver"] = driver_command(plan, plan["spec_angles"],
                                    str(pathlib.Path(out_dir) / "run"))
    return plan, spec2


def driver_command(plan: dict, spec_path: str, run_dir: str) -> str:
    sweep = {"theta": plan["angles_deg"], "pol": plan["polarizations_deg"]}
    return ("python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py "
            "--spec %s --sweep-json '%s' --out %s --json"
            % (spec_path, json.dumps(sweep, separators=(",", ":")), run_dir))


# ----------------------------------------------------------------------------- collect
def parse_p0_log(path: pathlib.Path) -> dict:
    """Read the last Auto Shutoff, iteration count and completion markers from a _p0.log."""
    if not path.is_file():
        return {"found": False, "auto_shutoff": None, "iterations": None,
                "completed": False, "diverging": False}
    text = path.read_text(encoding="utf-8", errors="ignore")
    lows = text.lower()
    shut = re.findall(r"Auto Shutoff:\s*([0-9.eE+\-]+)", text)
    m = re.search(r"Completed\s+(\d+)\s+iterations", text)
    return {
        "found": True,
        "auto_shutoff": float(shut[-1]) if shut else None,
        "iterations": int(m.group(1)) if m else None,
        "completed": ("simulation completed successfully" in lows
                      or "early termination of simulation" in lows),
        "diverging": "diverging" in lows,
    }


def read_point_csv(path: pathlib.Path):
    with open(path, "r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            yield (float(row["lam_um"]), float(row["R"]), float(row["T"]), float(row["A"]))


def parse_tag(name: str, fallback: dict | None = None) -> tuple:
    """``point_00_theta_30_pol_90.csv`` -> (30.0, 90.0)."""
    m = re.search(r"theta_([-+0-9.eE]+)_pol_([-+0-9.eE]+)", name)
    if m:
        return float(m.group(1)), float(m.group(2))
    if fallback:
        return fallback.get("theta"), fallback.get("pol")
    return None, None


def collect_matrix(run_dir: pathlib.Path):
    """Return (rows, logs). rows = dicts with theta/pol/lam/R/T/A."""
    over_by_point = {}
    sr = run_dir / "sweep_result.json"
    if sr.is_file():
        data = json.loads(sr.read_text(encoding="utf-8"))
        for r in data.get("results") or []:
            over_by_point[int(r["point"])] = {"theta": r.get("theta"), "pol": r.get("pol")}
    rows, logs = [], {}
    csvs = sorted(run_dir.glob("point_*.csv"))
    for csv_path in csvs:
        m = re.match(r"point_(\d+)_(.+)\.csv$", csv_path.name)
        idx = int(m.group(1)) if m else -1
        theta, pol = parse_tag(csv_path.name, over_by_point.get(idx))
        if theta is None or pol is None:
            continue
        stem = csv_path.stem
        log_path = run_dir / (stem + "_p0.log")
        logs[(float(theta), float(pol))] = parse_p0_log(log_path)
        for lam, R, T, A in read_point_csv(csv_path):
            rows.append({"theta_deg": float(theta), "pol_deg": float(pol),
                         "lam_um": lam, "R": R, "T": T, "A": A})
    return rows, logs


def curve_key(row):
    return (row["theta_deg"], row["pol_deg"])


def detect_duplicate_curves(rows) -> list:
    """N5: if two DIFFERENT angles produce an identical A(lambda), the scan did not vary theta."""
    curves = {}
    for r in rows:
        curves.setdefault(curve_key(r), []).append((r["lam_um"], r["A"]))
    dups = []
    keys = sorted(curves)
    for a, b in itertools.combinations(keys, 2):
        if a[0] == b[0] or a[1] != b[1]:
            continue
        ca, cb = curves[a], curves[b]
        if len(ca) != len(cb) or not ca:
            continue
        if all(abs(x[0] - y[0]) < 1e-9 and abs(x[1] - y[1]) < 1e-9
               for x, y in zip(ca, cb)):
            dups.append({"angle_a_deg": a[0], "angle_b_deg": b[0], "pol_deg": a[1]})
    return dups


def angle_metrics(rows, logs, plan) -> dict:
    by_angle = {}
    for r in rows:
        by_angle.setdefault((r["theta_deg"], r["pol_deg"]), []).append(r)
    out = {}
    for key, curve in sorted(by_angle.items()):
        lam = [r["lam_um"] for r in curve]
        A = [r["A"] for r in curve]
        band = [r["A"] for r in curve if 0.4 <= r["lam_um"] <= 0.65]
        hi = [r["lam_um"] for r in curve if r["A"] >= 0.9]
        imax = max(range(len(A)), key=lambda i: A[i]) if A else None
        out["%g/%g" % key] = {
            "theta_deg": key[0], "pol_deg": key[1], "n_lambda": len(curve),
            "mean_A_400_650": round(sum(band) / len(band), 6) if band else None,
            "peak_A": round(A[imax], 6) if imax is not None else None,
            "peak_lam_um": round(lam[imax], 4) if imax is not None else None,
            "delta_lambda_A90_um": round(max(hi) - min(hi), 4) if len(hi) > 1 else 0.0,
            "min_A": round(min(A), 6) if A else None,
            "convergence": logs.get(key, {"found": False}),
        }
    # TE/TM difference is only meaningful when both polarizations were actually run.
    pols = sorted({k[1] for k in by_angle})
    te_tm = None
    if len(pols) == 2:
        diffs = []
        for r in rows:
            if r["pol_deg"] != pols[0]:
                continue
            match = [q["A"] for q in rows
                     if q["theta_deg"] == r["theta_deg"] and q["pol_deg"] == pols[1]
                     and abs(q["lam_um"] - r["lam_um"]) < 1e-9]
            if match:
                diffs.append(abs(r["A"] - match[0]))
        te_tm = round(max(diffs), 6) if diffs else None
    return {
        "per_angle": out,
        "te_tm_max_abs_diff": te_tm,
        "te_tm_note": ("N/A: only one polarization was run"
                       if te_tm is None else "max |A(pol0) - A(pol1)| over lambda and theta"),
        "sign_convention": plan.get("sign_convention", SIGN_CONVENTION),
        "angle_grid_sha256": plan.get("angle_grid_sha256"),
        "check_coverage": plan.get("check_coverage"),
    }


def angle_checks(rows, plan, auto_shutoff_min=None, logs=None) -> dict:
    A = [r["A"] for r in rows]
    dups = detect_duplicate_curves(rows)
    found = sorted({(r["theta_deg"], r["pol_deg"]) for r in rows})
    expected = [(p["theta_deg"], p["pol_deg"]) for p in plan["points"]]
    a_bad = (min(A) < -1e-3 or max(A) > 1 + 1e-3) if A else True
    drift = []
    for pa in plan.get("per_angle", []):
        if pa["mode"] == "bfast":
            drift.append({"theta_deg": pa["theta_deg"], "expected_drift_deg": 0.0,
                          "note": "BFAST: getsourceangle(f) is constant (measured 30/30/30)"})

    # A missing _p0.log is reported as N/A with a reason, never silently treated as
    # "converged". Only real failures (diverging / incomplete / shutoff above min) fail ok.
    conv = []
    for key in found:
        lg = (logs or {}).get(key)
        if lg is None or not lg.get("found"):
            conv.append({"point": list(key), "status": "N/A",
                         "reason": "no _p0.log beside this point's .fsp"})
        elif lg.get("diverging") or not lg.get("completed"):
            conv.append({"point": list(key), "status": "fail",
                         "reason": "diverging or simulation did not complete"})
        elif (auto_shutoff_min is not None and lg.get("auto_shutoff") is not None
              and lg["auto_shutoff"] >= auto_shutoff_min):
            conv.append({"point": list(key), "status": "fail",
                         "reason": "final Auto Shutoff >= spec auto_shutoff min",
                         "auto_shutoff": lg["auto_shutoff"]})
        else:
            conv.append({"point": list(key), "status": "ok",
                         "auto_shutoff": lg.get("auto_shutoff"),
                         "iterations": lg.get("iterations")})
    failures = [c for c in conv if c["status"] == "fail"]

    checks = {
        "n_points_expected": len(expected),
        "n_points_found": len(found),
        "points_complete": set(found) == set(expected),
        "A_range": [round(min(A), 6), round(max(A), 6)] if A else None,
        "A_in_range": not a_bad,
        "duplicate_curves": dups,
        "no_duplicate_curves": not dups,
        "bfast_drift_control": drift,
        "auto_shutoff_min_spec": auto_shutoff_min,
        "convergence": conv,
        "convergence_failures": failures,
        "convergence_status": ("N/A (no _p0.log in run-dir)"
                               if not any(c["status"] in ("ok", "fail") for c in conv)
                               else "checked"),
    }
    checks["ok"] = (checks["points_complete"] and checks["A_in_range"]
                    and checks["no_duplicate_curves"] and not failures)
    return checks


# ----------------------------------------------------------------------------- self-test
def self_test() -> int:
    checks = []

    def chk(name, cond):
        checks.append((name, bool(cond)))

    # --- analytic truths from the lecture / Ansys docs -------------------------------
    chk("Bloch boundary phase = pi for P=lam=1um, theta=30",
        abs(bloch_boundary_phase(1e-6, 1e-6, 30.0) - math.pi) < 1e-12)
    chk("Bloch boundary phase doubles with period",
        abs(bloch_boundary_phase(2e-6, 1e-6, 30.0) - 2 * math.pi) < 1e-12)
    chk("Bloch drift @750nm = 38.68deg",
        abs(bloch_angle_drift(30.0, 600e-9, 750e-9) - 38.68218745348944) < 1e-6)
    chk("Bloch drift @600nm = 30deg",
        abs(bloch_angle_drift(30.0, 600e-9, 600e-9) - 30.0) < 1e-9)
    chk("Bloch drift @400nm = 19.47deg",
        abs(bloch_angle_drift(30.0, 600e-9, 400e-9) - 19.471220634490695) < 1e-6)
    lam_sim = C0 / 125e12
    chk("Ansys 100 THz example = 38.68deg",
        abs(bloch_angle_drift(30.0, lam_sim, C0 / 100e12) - 38.68218745348944) < 1e-4)
    chk("Ansys 150 THz example = 24.62deg",
        abs(bloch_angle_drift(30.0, lam_sim, C0 / 150e12) - 24.624318) < 1e-3)
    chk("BFAST cost 0/60/80 = 1/7.5/65.8",
        bfast_cost_factor(0) == 1.0 and bfast_cost_factor(60) == 7.5
        and bfast_cost_factor(80) == 65.8)
    chk("BFAST cost 45 = linear interpolation 4.75",
        abs(bfast_cost_factor(45) - 4.75) < 1e-9)
    chk("BFAST cost is symmetric in sign",
        bfast_cost_factor(-30) == bfast_cost_factor(30))

    # --- grid / spec injection -------------------------------------------------------
    chk("parse_list 0,30,60", parse_list("0,30,60", "angles") == [0.0, 30.0, 60.0])
    chk("parse_list tolerates spaces", parse_list("0, 30, 60", "angles") == [0.0, 30.0, 60.0])
    try:
        parse_list("0,abc", "angles")
        chk("parse_list rejects non-numeric", False)
    except AngleError:
        chk("parse_list rejects non-numeric", True)
    chk("grid_hash stable", grid_hash([0, 30, 60], [90], "bfast")
        == grid_hash([0, 30, 60], [90], "bfast"))
    chk("grid_hash changes with angles", grid_hash([0, 30, 60], [90], "bfast")
        != grid_hash([0, 30, 45], [90], "bfast"))

    spec = {
        "parameters": {"P": 0.8e-6},
        "lattice": {"period_x": "P", "period_y": "P"},
        "simulation": {
            "dimension": "2D", "propagation_axis": "y",
            "bc": {"x": "Bloch", "y": "PML", "z": "PML"},
            "source": {"wavelength_range": [400e-9, 800e-9], "polarization_deg": 90},
            "incidence": {"pml_layers": 8, "bfast": {"alpha": 1.0}},
        },
    }
    s2 = build_spec_angles(spec, [0, 30, 60], [90], "bfast")
    chk("theta is a parameter", s2["parameters"]["theta"] == 0.0)
    chk("sweep grid embedded in spec (cmd.exe-safe)",
        s2["sweep"] == {"theta": [0, 30, 60], "pol": [90]})
    chk("angle expression is 'theta'", s2["simulation"]["source"]["angle_theta_deg"] == "theta")
    chk("pol expression is 'pol'", s2["simulation"]["source"]["polarization_deg"] == "pol")
    chk("angle phi never emitted", "angle_phi_deg" not in s2["simulation"]["source"])
    chk("build_spec_angles does not mutate input", spec["parameters"].get("theta") is None)
    chk("sign convention recorded, angle NOT negated",
        s2["meta"]["oblique_plan"]["sign_convention"] == SIGN_CONVENTION
        and s2["parameters"]["theta"] == 0.0)

    plan, _ = make_plan("spec.json", spec, [0, 30, 60], [90], "bfast", "out")
    chk("2D tilt axis = x", plan["tilt_axis"] == "x")
    chk("broadband auto->bfast (per angle)",
        all(a["mode"] == "bfast" for a in plan["per_angle"]))
    chk("all angles use BFAST plane wave",
        all(a["plane_wave_type"] == "BFAST" for a in plan["per_angle"]))
    chk("source.angle theta equals requested theta",
        all(abs(a["source_properties"]["angle theta"] - a["theta_deg"]) < 1e-9
            for a in plan["per_angle"]))
    chk("driver consumes spec_angles.json (not the raw spec)",
        "spec_angles.json" in plan["driver"] and plan["driver"].count("--spec ") == 1)
    chk("driver uses --sweep-json with theta", "--sweep-json" in plan["driver"]
        and "theta" in plan["driver"])
    chk("n_points = angles x pols", plan["n_points"] == 3)
    chk("60deg cost factor 7.5", plan["per_angle"][2]["cost_factor"] == 7.5)
    chk("no engine in plan", plan["engine"].startswith("none"))

    # --- negative controls -----------------------------------------------------------
    for name, fn in (
        ("duplicate angles rejected",
         lambda: make_plan("s", spec, [30, 30], [90], "bfast", "o")),
        ("theta>=85 rejected",
         lambda: make_plan("s", spec, [0, 85], [90], "bfast", "o")),
        ("bloch_single+broadband rejected",
         lambda: make_plan("s", spec, [0, 30], [90], "bloch_single", "o")),
        ("unknown mode rejected",
         lambda: make_plan("s", spec, [0, 30], [90], "nonsense", "o")),
    ):
        try:
            fn()
            chk(name, False)
        except (AngleError, ValueError):
            chk(name, True)

    # --- collect-side checks ---------------------------------------------------------
    rows = []
    for th in (0.0, 30.0):
        for lam in (0.4, 0.5, 0.6, 0.7, 0.8):
            rows.append({"theta_deg": th, "pol_deg": 90.0, "lam_um": lam,
                         "R": 0.2 + 0.1 * th / 30.0, "T": 0.0, "A": 0.8 - 0.1 * th / 30.0})
    chk("different angles are NOT flagged duplicate",
        detect_duplicate_curves(rows) == [])
    same = [dict(r, A=0.7) for r in rows]      # force 0deg and 30deg to be identical
    chk("identical curves across angles ARE flagged",
        len(detect_duplicate_curves(same)) >= 1)
    bad_rows = [dict(r) for r in rows]
    bad_rows[0]["A"] = -0.2
    plan2, _ = make_plan("spec.json", spec, [0, 30], [90], "bfast", "out")
    chk("A<0 makes angle_checks fail",
        angle_checks(bad_rows, plan2)["A_in_range"] is False)
    chk("clean rows pass angle_checks",
        angle_checks(rows, plan2)["ok"] is True)
    chk("missing _p0.log is reported N/A with a reason",
        any(c["status"] == "N/A" and c.get("reason")
            for c in angle_checks(rows, plan2)["convergence"]))
    bad_logs = {(0.0, 90.0): {"found": True, "diverging": True, "completed": False,
                              "auto_shutoff": None, "iterations": None}}
    chk("diverging log fails convergence check",
        angle_checks(rows, plan2, logs=bad_logs)["convergence_failures"] != []
        and angle_checks(rows, plan2, logs=bad_logs)["ok"] is False)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        lp = pathlib.Path(td) / "x_p0.log"
        lp.write_text("Starting 20000 total iterations\n"
                      "50% complete. Auto Shutoff: 0.012\n"
                      "100% complete. Auto Shutoff: 9.664e-006\n"
                      "Early termination of simulation, the autoshutoff criteria are satisfied.\n"
                      "Completed 18207 iterations, or 3.2e-14s of Simulation Time\n",
                      encoding="utf-8")
        lg = parse_p0_log(lp)
        chk("p0.log final Auto Shutoff", abs(lg["auto_shutoff"] - 9.664e-6) < 1e-12)
        chk("p0.log iterations", lg["iterations"] == 18207)
        chk("p0.log completed", lg["completed"] is True)
        chk("p0.log no diverging", lg["diverging"] is False)
        lp.write_text("fields are diverging\n", encoding="utf-8")
        chk("p0.log detects diverging", parse_p0_log(lp)["diverging"] is True)

    metrics = angle_metrics(rows, {}, plan)
    chk("mean_A_400_650 for 0deg = 0.8",
        abs(metrics["per_angle"]["0/90"]["mean_A_400_650"] - 0.8) < 1e-9)
    chk("single pol -> TE/TM N/A",
        metrics["te_tm_max_abs_diff"] is None and "N/A" in metrics["te_tm_note"])
    chk("check_coverage explicitly lists what is NOT checked",
        len(plan["check_coverage"]["not_checked"]) >= 2)

    # zero-engine proof: this module must never open a session. Build the token at
    # runtime so the literal does not appear in this very source file.
    src = pathlib.Path(__file__).read_text(encoding="utf-8")
    chk("no session constructor in source", ("FDTD" + "(") not in src)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print("  [%s] %s" % ("OK" if ok else "FAIL", n))
    print("\n%d/%d assertions passed" % (len(checks) - len(failed), len(checks)))
    if failed:
        print("FAILED:", "; ".join(failed))
        return 1
    return 0


# ----------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plan / collect a variable-angle FDTD sweep (zero engine)")
    ap.add_argument("--self-test", action="store_true", help="offline analytic assertions, no engine")
    sub = ap.add_subparsers(dest="cmd")

    pl = sub.add_parser("plan", help="emit angle_sweep_plan.json + spec_angles.json")
    pl.add_argument("--spec", required=True)
    pl.add_argument("--angles", default=None, help="comma-separated degrees, e.g. 0,30,60")
    pl.add_argument("--pol", default=None, help="comma-separated polarization degrees, e.g. 0,90")
    pl.add_argument("--mode", default=None,
                    choices=("normal", "bloch_single", "bfast", "auto"),
                    help="default: simulation.incidence.mode, else bfast")
    pl.add_argument("--out", required=True, help="output directory")
    pl.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    pl.add_argument("--json", action="store_true")

    co = sub.add_parser("collect", help="aggregate point_*.csv into A(lambda,theta)")
    co.add_argument("--plan", required=True, help="angle_sweep_plan.json from `plan`")
    co.add_argument("--run-dir", required=True, help="run_fdtd_sweep.py --out directory")
    co.add_argument("--out", required=True, help="output angle_matrix.csv path")
    co.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.cmd:
        ap.error("need a subcommand (plan / collect) or --self-test")

    try:
        if args.cmd == "plan":
            spec_path = pathlib.Path(args.spec)
            if not spec_path.is_file():
                raise AngleError("spec not found: %s" % spec_path)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            inc = spec.get("simulation", {}).get("incidence") or {}
            angles = parse_list(args.angles if args.angles is not None
                                else ",".join(str(a) for a in inc.get("angle_grid_deg", [0, 30, 60])),
                                "angles")
            pols = parse_list(args.pol if args.pol is not None
                              else ",".join(str(q) for q in inc.get("polarizations_deg", [90])),
                              "pol")
            mode = args.mode or str(inc.get("mode", "bfast"))
            plan, spec2 = make_plan(str(spec_path), spec, angles, pols, mode, args.out)
            summary = {"cmd": "plan", "spec": str(spec_path), "out": args.out,
                       "mode": mode, "angles_deg": angles, "pol_deg": pols,
                       "n_points": plan["n_points"], "tilt_axis": plan["tilt_axis"],
                       "angle_grid_sha256": plan["angle_grid_sha256"],
                       "estimated_total_cost_factor": plan["estimated_total_cost_factor"],
                       "warnings": plan["warnings"], "driver": plan["driver"],
                       "dry_run": bool(args.dry_run), "written": []}
            if not args.dry_run:
                out = pathlib.Path(args.out)
                out.mkdir(parents=True, exist_ok=True)
                (out / "angle_sweep_plan.json").write_text(
                    json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
                (out / "spec_angles.json").write_text(
                    json.dumps(spec2, ensure_ascii=False, indent=2), encoding="utf-8")
                summary["written"] = ["angle_sweep_plan.json", "spec_angles.json"]
            print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json
                  else "\n".join("%-28s %s" % (k, v) for k, v in summary.items()))
            return 0

        # ---- collect ----
        plan_path = pathlib.Path(args.plan)
        run_dir = pathlib.Path(args.run_dir)
        out_csv = pathlib.Path(args.out)
        if not plan_path.is_file():
            raise AngleError("plan not found: %s" % plan_path)
        if not run_dir.is_dir():
            raise AngleError("run-dir not found: %s" % run_dir)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        rows, logs = collect_matrix(run_dir)
        if not rows:
            raise AngleError("run-dir 里没有可解析的 point_*.csv（角度 tag 缺失？）")
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["theta_deg", "pol_deg", "lam_um", "R", "T", "A"])
            for r in sorted(rows, key=lambda x: (x["theta_deg"], x["pol_deg"], x["lam_um"])):
                w.writerow([r["theta_deg"], r["pol_deg"], r["lam_um"], r["R"], r["T"], r["A"]])
        spec_auto = None
        try:
            spec_auto = json.loads(pathlib.Path(plan["spec"]).read_text(encoding="utf-8")) \
                .get("simulation", {}).get("auto_shutoff")
        except Exception:                                          # noqa: BLE001
            pass
        metrics = angle_metrics(rows, logs, plan)
        checks = angle_checks(rows, plan, spec_auto, logs)
        (out_csv.parent / "angle_metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_csv.parent / "angle_check.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {"cmd": "collect", "matrix": str(out_csv), "rows": len(rows),
                   "n_points_found": checks["n_points_found"],
                   "n_points_expected": checks["n_points_expected"],
                   "A_range": checks["A_range"], "duplicate_curves": checks["duplicate_curves"],
                   "ok": checks["ok"],
                   "metrics": str(out_csv.parent / "angle_metrics.json"),
                   "checks": str(out_csv.parent / "angle_check.json")}
        print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json
              else "\n".join("%-28s %s" % (k, v) for k, v in summary.items()))
        return 0 if checks["ok"] else 1

    except (AngleError, ValueError, KeyError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - older consoles
        pass
    raise SystemExit(main())
