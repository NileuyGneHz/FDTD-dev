#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_fdtd_sweep.py — build a periodic unit cell from a model spec, run it, and export R/T/A.

The spec is the JSON contract defined in the `fdtd-paper-parameter-extraction` skill
(`references/model-spec-schema.md`). Geometry is expressed as objects with named types; every
dimension is an expression over `parameters`, so one sweep changes one number everywhere at once.

Usage
-----
    python run_fdtd_sweep.py --spec spec_p01.json --dry-run
    python run_fdtd_sweep.py --spec spec_p01.json --out results/repro_p01
    python run_fdtd_sweep.py --spec spec_p01.json --sweep-json '{"ts": [1.2e-7, 1.85e-7]}'

Supported object types: box, polygon, cylinder, sphere, ring.
Supported material kinds: drude, constant_nk, constant_eps, builtin, sampled_nk.

Units: metres everywhere; drude wp/wc in rad/s.
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import os
import pathlib
import re
import sys
import time

import numpy as np

# Builder lives in library/py/fsp_build.py (single implementation, EXP-38).
# 2026-11-11: moved from _shared/ per workspace-layout.md §10.
# Do NOT copy it back here: D-005 / D-006 / EXP-02 were all "two divergent copies".
for _cand in (pathlib.Path(__file__).resolve().parents[3] / "library" / "py",
              pathlib.Path(__file__).resolve().parents[5] / "library" / "py"):
    if (_cand / "fsp_build.py").is_file():
        if str(_cand) not in sys.path:
            sys.path.insert(0, str(_cand))
        break
else:
    raise ImportError("library/py/fsp_build.py not found; expected at <repo>/library/py/")

from fsp_build import (  # noqa: E402
    C0, MIN_MONITOR_GAP, PHYS_TOL,
    build_materials, build_objects, build_simulation,
    check_monitor_gap, ev, resolve_axes, resolve_material,
)

DEFAULT_ENV = dict(
    license="1055@localhost",
    api_path=r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python",
)

# EXP-75 deviation (PLAN-2026-11-13 §11): an opaque metal ground plane makes T physically
# zero, but the DFT power monitor below it returns a small NEGATIVE noise floor. Measured on
# v251: our P08 theta=0 gave T in [-0.00305, -0.00007], mean -0.00106; the course's own
# finished wd.fsp / wd_BFASK.fsp gave [-0.00420, -0.00009] / [-0.00365, -0.00007].
# Two A/B controls (T monitor 4x further from the boundary; pml layers 8->4) changed |T| by
# <1e-5, so this is NOT a monitor-in-PML error. 5e-3 is a HARD bound on that noise: a real
# broken monitor (e.g. T=-0.80, the P07 event) is still rejected.
OPAQUE_T_NOISE_MAX = 5e-3


def open_session(env, retries=4):
    os.environ.setdefault("ANSYSLMD_LICENSE_FILE", env["license"])
    if env["api_path"] not in sys.path:
        sys.path.insert(0, env["api_path"])
    import lumapi

    last = None
    for i in range(retries):
        try:
            return lumapi.FDTD(hide=True)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2.0 * (i + 1))
    raise RuntimeError("could not open an FDTD session: %r" % (last,))

# ----------------------------------------------------------------------------- run
def read_power(f, name):
    """`getresult(name, 'T')` returns a list of dicts carrying lambda / f / T on v251."""
    raw = f.getresult(name, "T")
    item = raw[0] if isinstance(raw, (list, tuple)) else raw
    if isinstance(item, dict):
        lam = item.get("lambda", item.get("f"))
        return np.asarray(lam).flatten(), np.asarray(item["T"]).flatten()
    arr = np.asarray(item)
    if arr.ndim == 2 and arr.shape[1] >= 2:
        return arr[:, 0].flatten(), arr[:, 1].flatten()
    raise ValueError("unexpected getresult layout for %s: %r" % (name, type(item)))


def check_engine_log(save_path):
    """Reject a solve whose engine log says the fields diverged.

    v251 prints ``Simulation completed successfully`` even after
    ``ERROR: ... the electromagnetic fields are diverging`` (measured EXP-75 at theta=60 BFAST:
    R stayed in [0,1] yet Auto Shutoff had blown up to 8966). So `completed` alone is NOT a
    convergence criterion; the literal `diverging` must be checked.

    A log older than the .fsp is stale (left over from an earlier run) and is reported as
    N/A rather than being silently read as "converged".
    """
    if not save_path:
        return {"found": False, "reason": "no save_path, engine log location unknown"}
    fsp = pathlib.Path(save_path)
    log = fsp.with_name(fsp.stem + "_p0.log")
    if not log.is_file() or (fsp.is_file() and log.stat().st_mtime < fsp.stat().st_mtime):
        return {"found": False, "reason": "no fresh _p0.log beside the saved .fsp"}
    text = log.read_text(encoding="utf-8", errors="ignore")
    if "diverging" in text.lower():
        raise RuntimeError(
            "引擎在 %s 报 'fields are diverging'：本点不算结果。"
            "别把 R/T 仍在 [0,1] 当成收敛，先查 BFAST 角度 / dt stability factor / PML"
            % log.name)
    return {"found": True, "diverging": False,
            "completed": "simulation completed successfully" in text.lower()}


def run_point(spec, params, env, save_path=None):
    f = open_session(env)
    try:
        axes = resolve_axes(spec["simulation"])
        build_materials(f, spec)
        p_bottom, p_top = build_objects(f, spec, params, axes)
        build_simulation(f, spec, params, p_bottom, p_top, axes)
        if save_path:
            f.save(save_path)
        f.run()
        check_engine_log(save_path)
        lam, R = read_power(f, "R")
        _, T = read_power(f, "T")
        lam = np.asarray(lam).flatten() * 1e6
        R = np.asarray(R).flatten()
        T = np.asarray(T).flatten()
        if (spec.get("simulation") or {}).get("mode", "reflection") == "transmission":
            # The R monitor sits BELOW the source, so the reflected wave travels in -z and the
            # monitor's net flux is negative. Its magnitude is the reflectance.
            R = -R
        return apply_opaque_ground_plane(dict(lam=lam, R=R, T=T, A=1.0 - R - T), spec)
    finally:
        try:
            f.close()
        except Exception:  # noqa: BLE001
            pass


def check_physical_range(name, arr, tol=None):
    """R/T must sit in [0,1] up to numerical noise; return (min, max).

    Pure function on purpose: the tolerance can be calibrated offline (EXP-26) instead of
    by burning an FDTD run.  See PHYS_TOL for why 1e-3 and not 1e-6.
    """
    tol = PHYS_TOL if tol is None else float(tol)
    a = np.asarray(arr, dtype=float)
    if not a.size:
        return float("nan"), float("nan")
    lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
    if lo < -tol or hi > 1 + tol:
        raise ValueError(
            "%s 越界 [%.3f, %.3f]（容差 %.0e）：物理上必须落在 0..1。先查监视器是否压进 PML，"
            "不要把这个数当结果写进台账" % (name, lo, hi, tol))
    return lo, hi


def apply_opaque_ground_plane(res, spec):
    """Reflection device on an opaque metal backplane: use T == 0, but keep the raw evidence.

    Opt-in via ``simulation.opaque_ground_plane: true``. Legacy specs take the unchanged path,
    so the A/B call-sequence equivalence (EXP-71) is preserved bit-for-bit.

    The raw monitor trace is NOT discarded: it is kept in ``res["T_raw"]`` and its peak is
    checked against ``OPAQUE_T_NOISE_MAX``. A truly misplaced / broken monitor therefore still
    fails here instead of being hidden by the zero substitution.
    """
    if not (spec.get("simulation") or {}).get("opaque_ground_plane"):
        return res
    raw = np.asarray(res["T"], dtype=float)
    peak = float(np.nanmax(np.abs(raw))) if raw.size else 0.0
    if peak > OPAQUE_T_NOISE_MAX:
        raise ValueError(
            "opaque_ground_plane 声明下 T 监视器噪声 |T|max=%.5f > 上界 %.0e："
            "这不是不透明背板的 DFT 零点，检查监视器/几何/源归一化。"
            "原始 T 范围 [%.5f, %.5f]" %
            (peak, OPAQUE_T_NOISE_MAX, float(np.nanmin(raw)), float(np.nanmax(raw))))
    out = dict(res)
    out["T_raw"] = raw
    out["T_raw_abs_max"] = peak
    out["T"] = np.zeros_like(raw)
    out["A"] = 1.0 - np.asarray(out["R"]) - out["T"]
    return out


def metrics(res, mode="reflection", quantity=None):
    """Peak metric chosen by the declared quantity, not by the device type.

    P07 事件：反射式器件被写死成 ``A``，输出 ``peak A = 1.5956``（>1），
    而 spec 里明明写着 ``peak_reflectance``。这里按 ``target.quantity`` 选键，
    并对 R/T 做物理区间校验 —— 越界多半是监视器压进 PML，不是物理。
    """
    key = {"peak_transmittance": "T", "transmittance": "T",
           "peak_reflectance": "R", "reflectance": "R"}.get(
               str(quantity or ""), "T" if mode == "transmission" else "A")
    # EXP-73: the course's Bloch+broadband run produced A<0 near 700 nm while R and T
    # both stayed inside [0,1]. Checking only R/T let a wrong result through silently.
    # A = 1 - R - T is a physical quantity too and must pass the same range gate.
    for name in ("R", "T", "A"):
        check_physical_range(name, res[name])
    lam = res["lam"]
    arr = res[key]
    i = int(np.argmax(arr))
    half = arr >= arr[i] / 2.0
    m = dict(metric=key,
             peak_value=float(arr[i]), peak_lam_um=float(lam[i]),
             R_at_peak=float(res["R"][i]), T_at_peak=float(res["T"][i]),
             fwhm_um=float(lam[half].max() - lam[half].min()) if half.sum() > 1 else float("nan"))
    # Evidence for the opaque-backplane substitution travels with the row (EXP-75 §11).
    if "T_raw_abs_max" in res:
        m["T_raw_abs_max"] = round(float(res["T_raw_abs_max"]), 6)
    return m


def expand(sweep):
    if not sweep:
        return [{}]
    keys = list(sweep.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*[sweep[k] for k in keys])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--sweep-json", default=None,
                    help='override the spec sweep, e.g. \'{"ts": [1.2e-7, 1.85e-7]}\'')
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable result on stdout; human progress lines are suppressed")
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    sweep = json.loads(args.sweep_json) if args.sweep_json else spec.get("sweep") or {}
    points = expand(sweep)
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)),
                                       (spec.get("meta", {}).get("package", "spec") + "_out"))
    env = dict(DEFAULT_ENV, **(spec.get("env") or {}))
    # --json 时 stdout 只留 JSON，人读的行全部压掉（调用方 parse 不会被污染）
    say = (lambda *a, **k: None) if args.json else print
    payload = {
        "spec": args.spec,
        "target": spec.get("meta", {}).get("target_figure"),
        "n_points": len(points),
        "points": points,
        "out_dir": out_dir,
        "dry_run": bool(args.dry_run),
        "results": None,
        "summary_csv": None,
    }

    def emit(code=0):
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code

    say("spec     : %s" % args.spec)
    say("target   : %s" % spec.get("meta", {}).get("target_figure"))
    say("points   : %d" % len(points))
    say("out_dir  : %s" % out_dir)
    for i, p in enumerate(points):
        say("  [%02d] %s" % (i, p if p else "(base parameters)"))
    if args.dry_run:
        say("dry-run: nothing was simulated.")
        return emit(0)

    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for i, over in enumerate(points):
        params = copy.deepcopy(spec["parameters"])
        params.update(over)
        tag = "_".join("%s_%g" % (k, v) for k, v in over.items()) or "base"
        say("\n=== point %d/%d  %s ===" % (i + 1, len(points), over or "base"))
        res = run_point(spec, params, env,
                        save_path=os.path.join(out_dir, "point_%02d_%s.fsp" % (i, tag)))
        m = metrics(res, (spec.get("simulation") or {}).get("mode", "reflection"),
                    (spec.get("target") or {}).get("quantity"))
        cols = [res["lam"], res["R"], res["T"], res["A"]]
        header = "lam_um,R,T,A"
        if "T_raw" in res:
            cols.append(res["T_raw"])
            header += ",T_raw"
        np.savetxt(os.path.join(out_dir, "point_%02d_%s.csv" % (i, tag)),
                   np.column_stack(cols), delimiter=",", header=header, comments="")
        rows.append(dict(point=i, **over, **m))
        say("   peak %s = %.4f @ %.3f um   FWHM = %.3f um"
            % (m["metric"], m["peak_value"], m["peak_lam_um"], m["fwhm_um"]))

    keys = list(rows[0].keys())
    summary_csv = os.path.join(out_dir, "summary.csv")
    with open(summary_csv, "w", encoding="utf-8") as fh:
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in keys) + "\n")
    say("\nsummary -> %s" % summary_csv)

    payload["results"] = [{k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}
                          for r in rows]
    payload["summary_csv"] = summary_csv
    if args.json:
        with open(os.path.join(out_dir, "sweep_result.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    return emit(0)


if __name__ == "__main__":
    raise SystemExit(main())
