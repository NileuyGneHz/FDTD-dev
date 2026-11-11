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
        lam, R = read_power(f, "R")
        _, T = read_power(f, "T")
        lam = np.asarray(lam).flatten() * 1e6
        R = np.asarray(R).flatten()
        T = np.asarray(T).flatten()
        if (spec.get("simulation") or {}).get("mode", "reflection") == "transmission":
            # The R monitor sits BELOW the source, so the reflected wave travels in -z and the
            # monitor's net flux is negative. Its magnitude is the reflectance.
            R = -R
        return dict(lam=lam, R=R, T=T, A=1.0 - R - T)
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


def metrics(res, mode="reflection", quantity=None):
    """Peak metric chosen by the declared quantity, not by the device type.

    P07 事件：反射式器件被写死成 ``A``，输出 ``peak A = 1.5956``（>1），
    而 spec 里明明写着 ``peak_reflectance``。这里按 ``target.quantity`` 选键，
    并对 R/T 做物理区间校验 —— 越界多半是监视器压进 PML，不是物理。
    """
    key = {"peak_transmittance": "T", "transmittance": "T",
           "peak_reflectance": "R", "reflectance": "R"}.get(
               str(quantity or ""), "T" if mode == "transmission" else "A")
    for name in ("R", "T"):
        check_physical_range(name, res[name])
    lam = res["lam"]
    arr = res[key]
    i = int(np.argmax(arr))
    half = arr >= arr[i] / 2.0
    return dict(metric=key,
                peak_value=float(arr[i]), peak_lam_um=float(lam[i]),
                R_at_peak=float(res["R"][i]), T_at_peak=float(res["T"][i]),
                fwhm_um=float(lam[half].max() - lam[half].min()) if half.sum() > 1 else float("nan"))


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
        np.savetxt(os.path.join(out_dir, "point_%02d_%s.csv" % (i, tag)),
                   np.column_stack([res["lam"], res["R"], res["T"], res["A"]]),
                   delimiter=",", header="lam_um,R,T,A", comments="")
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
