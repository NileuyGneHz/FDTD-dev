#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_phase_sweep.py — extract the transmitted field phase of a unit cell, per polarization.

Why separate from run_fdtd_sweep.py: power and phase are different experiments. Power needs a
normalised flux monitor; phase needs a complex field monitor, a plane average to isolate the
zeroth order, and a differential method to cancel the propagation phase. Mixing them into one script
makes both harder to reason about.

Method
------
1. Build the model exactly as `fdtd-lumerical-unitcell-simulation` does (same spec, same builder).
2. Add a 2D DFT field monitor on the T-monitor plane.
3. Run once per polarization angle.
4. For each run take the **plane-averaged** co-polarised E — at normal incidence every non-zero
   diffraction order is evanescent, so the plane average is the zeroth-order transmitted amplitude.
5. Phase difference between two polarisations: `arg(E_x) - arg(E_y)` at the same plane. The common
   propagation phase cancels, so **no bare-substrate reference run is needed**.

Dependency: the model builder lives in the `fdtd-lumerical-unitcell-simulation` skill. This script imports
it rather than duplicating it — one implementation, one place to fix.

Usage
-----
    python run_phase_sweep.py --spec spec_p02.json --pol 0 90
    python run_phase_sweep.py --spec spec_p02.json --pol 0 90 --out results/phase

Output: `phase.csv` with `lam_um, phase_deg_<pol>..., dphi_deg, T_<pol>...`
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

UNITCELL_SCRIPTS = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "fdtd-lumerical-unitcell-simulation", "scripts"))
if UNITCELL_SCRIPTS not in sys.path:
    sys.path.insert(0, UNITCELL_SCRIPTS)

from run_fdtd_sweep import (  # noqa: E402
    DEFAULT_ENV, build_materials, build_objects, build_simulation, ev, open_session, read_power,
)

MONITOR = "Efield"


def add_field_monitor(f, sim, params, z_T, period):
    """Add a 2D DFT monitor that records E on the transmission plane."""
    src = sim["source"]
    f.addprofile(name=MONITOR)
    for k, v in [("monitor type", "2D Z-normal"),
                 ("x", 0), ("y", 0), ("z", z_T),
                 ("x span", period), ("y span", period),
                 ("spatial interpolation", "specified position"),
                 ("output Ex", 1), ("output Ey", 1), ("output Ez", 1),
                 ("override global monitor settings", 1),
                 ("use source limits", 0),
                 ("use wavelength spacing", 1),
                 ("wavelength center", sum(src["wavelength_range"]) / 2.0),
                 ("wavelength span", src["wavelength_range"][1] - src["wavelength_range"][0]),
                 ("frequency points", src.get("npts", 101))]:
        f.setnamed(MONITOR, k, v)


def read_field(f, name=MONITOR):
    """Return (lambda, complex E array shaped (nx, ny, nf, 3))."""
    raw = f.getresult(name, "E")
    item = raw[0] if isinstance(raw, (list, tuple)) else raw
    if not isinstance(item, dict) or "E" not in item:
        raise RuntimeError("monitor %r returned no 'E' result" % name)
    e = np.asarray(item["E"])
    lam = np.asarray(item["lambda"]).flatten() * 1e6      # m -> um
    while e.ndim > 4:                      # collapse the singleton z axis
        if e.shape[2] == 1:
            e = np.squeeze(e, axis=2)
        else:
            break
    if e.ndim != 4 or e.shape[-1] != 3:
        raise RuntimeError("unexpected E shape %r, expected (nx, ny, nf, 3)" % (e.shape,))
    return lam, e


def run_polarization(spec, params, pol_deg, env, save_path):
    f = open_session(env)
    try:
        build_materials(f, spec)
        z_bot, z_top = build_objects(f, spec, params)
        geo = build_simulation(f, spec, params, z_bot, z_top)
        f.setnamed("source", "polarization angle", float(pol_deg))
        period = ev(spec["lattice"]["period_x"], params)
        add_field_monitor(f, spec["simulation"], params, geo["z_T"], period)
        f.save(save_path)                  # ALWAYS before close: an unsaved session prompts a dialog
        f.run()
        lam, e = read_field(f)
        _, T = read_power(f, "T")
        return lam, e, np.asarray(T).flatten()
    finally:
        try:
            f.close()
        except Exception:  # noqa: BLE001
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--pol", nargs="+", type=float, default=[0.0, 90.0],
                    help="polarization angles in degrees (use two for a phase difference)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    params = dict(spec["parameters"])
    env = dict(DEFAULT_ENV, **(spec.get("env") or {}))
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)), "phase_out")
    os.makedirs(out_dir, exist_ok=True)

    print("spec: %s" % args.spec)
    print("pol : %s" % args.pol)
    print("out : %s\n" % out_dir)

    results = {}
    for pol in args.pol:
        tag = "pol_%g" % pol
        print("=== %s ===" % tag)
        lam, e, T = run_polarization(spec, params, pol, env,
                                     os.path.join(out_dir, "%s.fsp" % tag))
        comp = 0 if (pol % 180.0) < 45.0 or (pol % 180.0) > 135.0 else 1
        eco = e[..., comp].mean(axis=(0, 1))       # plane average = zeroth order
        phase = np.angle(eco)
        results[pol] = dict(lam=lam, phase=phase, amp=np.abs(eco), T=T)
        print("   |E_z0| mean = %.4f   phase range = [%.1f, %.1f] deg"
              % (results[pol]["amp"].mean(),
                 np.degrees(phase.min()), np.degrees(phase.max())))

    lams = results[args.pol[0]]["lam"]
    cols = [lams]
    header = ["lam_um"]
    for pol in args.pol:
        cols.append(np.degrees(results[pol]["phase"]))
        cols.append(results[pol]["T"])
        header += ["phase_deg_%g" % pol, "T_%g" % pol]

    d_mod = None
    if len(args.pol) == 2:
        # A half-wave plate sits at exactly 180 deg, i.e. on the wrap branch cut, where the sign
        # flips sample to sample. Report the signed value AND the value modulo 360 so the mean is
        # not destroyed by that artefact.
        dphi = results[args.pol[0]]["phase"] - results[args.pol[1]]["phase"]
        dphi = (dphi + np.pi) % (2 * np.pi) - np.pi      # (-pi, pi]
        d_mod = np.degrees(dphi) % 360.0                 # [0, 360)
        cols.append(np.degrees(dphi))
        cols.append(d_mod)
        cols.append(np.cos(dphi))
        header += ["dphi_deg", "dphi_deg_mod360", "cos_dphi"]

    data = np.column_stack(cols)
    path = os.path.join(out_dir, "phase.csv")
    np.savetxt(path, data, delimiter=",", header=",".join(header), comments="")

    if d_mod is not None:
        print("\ndphi (mod 360) = %.1f deg   [%.1f, %.1f]   target half-wave = 180 deg"
              % (d_mod.mean(), d_mod.min(), d_mod.max()))
        print("cos(dphi) mean = %+.3f   (half-wave target = -1.000)" % np.cos(np.radians(d_mod)).mean())
        print("note: a signed mean near 0 deg usually means the value sits ON the 180 deg branch cut;")
        print("      read dphi_deg_mod360, not dphi_deg.")
    print("\nphase -> %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
