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
import re
import sys
import time

import numpy as np

C0 = 299792458.0

DEFAULT_ENV = dict(
    license="1055@localhost",
    api_path=r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python",
)

_EXPR_OK = re.compile(r"[0-9a-zA-Z_.+\-*/() ]+")


# ----------------------------------------------------------------------------- helpers
def ev(expr, params):
    """Evaluate a spec expression against the parameter table."""
    if isinstance(expr, (int, float)):
        return float(expr)
    if not isinstance(expr, str):
        raise TypeError("expected number or expression, got %r" % type(expr).__name__)
    if not _EXPR_OK.fullmatch(expr):
        raise ValueError("unsupported characters in expression %r" % expr)
    return float(eval(expr, {"__builtins__": {}}, params))  # noqa: S307 - whitelisted charset


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


# ----------------------------------------------------------------------------- materials
def build_materials(f, spec):
    for name, m in spec["materials"].items():
        kind = m["kind"]
        if kind == "builtin":
            continue                                  # assigned by name on the object
        if kind == "drude":
            t = f.addmaterial("Plasma")
            f.setmaterial(t, "name", name)
            f.setmaterial(name, {"Plasma resonance": m["wp"], "Plasma collision": m["wc"]})
        elif kind == "constant_nk":
            t = f.addmaterial("(n,k) Material")
            f.setmaterial(t, "name", name)
            f.setmaterial(name, {"Refractive Index": m["n"],
                                 "Imaginary Refractive Index": m.get("k", 0.0)})
        elif kind == "constant_eps":
            eps = complex(m["eps_real"], m.get("eps_imag", 0.0))
            n = np.sqrt(eps)
            t = f.addmaterial("(n,k) Material")
            f.setmaterial(t, "name", name)
            f.setmaterial(name, {"Refractive Index": float(n.real),
                                 "Imaginary Refractive Index": float(n.imag)})
        elif kind == "sampled_nk":
            data = np.asarray(m["data"], dtype=float)
            lam, n, k = data[:, 0], data[:, 1], data[:, 2]
            t = f.addmaterial("Sampled data")
            f.setmaterial(t, "name", name)
            f.setmaterial(name, "max coefficients", 6)
            f.setmaterial(name, "sampled data", np.column_stack([C0 / lam, n + 1j * k]))
        else:
            raise ValueError("unsupported material kind: %s" % kind)


def resolve_material(spec, key):
    """Map a spec material key to the name Lumerical actually knows.

    `builtin` entries are looked up in the database by their `name`; every other kind is created by
    us and keeps the key. Never name a custom material 'Au' or 'Al2O3' — those collide with database
    entries and the assignment silently picks the wrong one (or fails outright).
    """
    m = spec["materials"][key]
    return m["name"] if m["kind"] == "builtin" else key


# ----------------------------------------------------------------------------- geometry
def build_objects(f, spec, params):
    """Create every object; return the stack extent in z."""
    z_lo, z_hi = [], []
    for o in spec["objects"]:
        oid, typ = o["id"], o["type"]
        mat = o.get("material")

        if typ == "box":
            cx, cy, cz = [ev(v, params) for v in o["center"]]
            sx, sy, sz = [ev(v, params) for v in o["span"]]
            f.addrect(name=oid, x=cx, y=cy, z=cz, x_span=sx, y_span=sy, z_span=sz)
            z_lo.append(cz - sz / 2)
            z_hi.append(cz + sz / 2)

        elif typ == "polygon":
            verts = np.array([[ev(v, params) for v in pair] for pair in o["vertices"]], dtype=float)
            verts = np.vstack([verts, verts[0]])
            z, zs = ev(o["z"], params), ev(o["z_span"], params)
            f.addpoly(name=oid)
            f.setnamed(oid, "vertices", verts)
            f.setnamed(oid, "z", z)
            f.setnamed(oid, "z span", zs)
            z_lo.append(z - zs / 2)
            z_hi.append(z + zs / 2)

        elif typ == "cylinder":
            cx, cy, cz = [ev(v, params) for v in o["center"]]
            r, h = ev(o["radius"], params), ev(o["height"], params)
            f.addcircle(name=oid, x=cx, y=cy, z=cz, radius=r, z_span=h)
            z_lo.append(cz - h / 2)
            z_hi.append(cz + h / 2)

        elif typ == "sphere":
            cx, cy, cz = [ev(v, params) for v in o["center"]]
            r = ev(o["radius"], params)
            f.addsphere(name=oid, x=cx, y=cy, z=cz, radius=r)
            z_lo.append(cz - r)
            z_hi.append(cz + r)

        elif typ == "ellipse":
            # Elliptical pillar: a polygon with an analytic vertex list. `axes` are FULL diameters,
            # matching how papers quote "a = 285 nm, b = 450 nm" for an elliptical cross-section.
            cx, cy, cz = [ev(v, params) for v in o["center"]]
            ax, ay = ev(o["axes"][0], params), ev(o["axes"][1], params)
            h = ev(o["height"], params)
            n = int(o.get("n_vertices", 48))
            rot = np.deg2rad(float(o.get("rotation_deg", 0)))
            th = np.linspace(0, 2 * np.pi, n, endpoint=False)
            u, v = (ax / 2) * np.cos(th), (ay / 2) * np.sin(th)
            verts = np.column_stack([u * np.cos(rot) - v * np.sin(rot),
                                     u * np.sin(rot) + v * np.cos(rot)])
            verts = np.vstack([verts, verts[0]])
            f.addpoly(name=oid)
            f.setnamed(oid, "vertices", verts)
            f.setnamed(oid, "z", cz)
            f.setnamed(oid, "z span", h)
            z_lo.append(cz - h / 2)
            z_hi.append(cz + h / 2)

        elif typ == "ring":
            cx, cy, cz = [ev(v, params) for v in o["center"]]
            r, ri, h = ev(o["radius"], params), ev(o["inner_radius"], params), ev(o["height"], params)
            f.addring(name=oid, x=cx, y=cy, z=cz,
                      inner_radius=ri, outer_radius=r, z_span=h)
            z_lo.append(cz - h / 2)
            z_hi.append(cz + h / 2)

        else:
            raise ValueError("unsupported object type: %s" % typ)

        if mat:
            f.setnamed(oid, "material", resolve_material(spec, mat))
            f.setnamed(oid, "override mesh order from material database", 1)
            f.setnamed(oid, "mesh order", o.get("mesh_order", 1))

    return min(z_lo), max(z_hi)


def build_simulation(f, spec, params, z_bottom, z_top):
    sim = spec["simulation"]
    lat = spec["lattice"]
    sx = ev(lat["period_x"], params)
    sy = ev(lat["period_y"], params)
    nx = int((lat.get("supercell") or {}).get("nx", 1))
    ny = int((lat.get("supercell") or {}).get("ny", 1))

    air = sim.get("air_above", 2.5e-6)
    below = sim.get("below_structure", 1.0e-6)
    z_max, z_min = z_top + air, z_bottom - below

    f.addfdtd(dimension=sim.get("dimension", "3D"), x=0, y=0,
              z=(z_max + z_min) / 2,
              x_span=sx * nx, y_span=sy * ny, z_span=z_max - z_min)
    bc = sim["bc"]
    for axis in ("x", "y"):
        f.setnamed("FDTD", "%s min bc" % axis, bc[axis])
        f.setnamed("FDTD", "%s max bc" % axis, bc[axis])
    f.setnamed("FDTD", "z min bc", bc["z"])
    f.setnamed("FDTD", "z max bc", bc["z"])
    f.setnamed("FDTD", "mesh accuracy", sim.get("mesh_accuracy", 4))
    f.setnamed("FDTD", "auto shutoff min", sim.get("auto_shutoff", 1e-4))
    if sim.get("simulation_time"):
        f.setnamed("FDTD", "simulation time", sim["simulation_time"])

    mo = sim.get("mesh_override")
    if mo:
        zr = mo.get("z_range")
        if zr:
            z0, z1 = ev(zr[0], params), ev(zr[1], params)
        else:
            z0, z1 = z_bottom, z_top
        f.addmesh(name="mesh_fine", x=0, y=0, z=(z0 + z1) / 2,
                  x_span=sx * nx, y_span=sy * ny, z_span=abs(z1 - z0))
        for k in ("dx", "dy", "dz"):
            if mo.get(k):
                f.setnamed("mesh_fine", k, mo[k])

    src = sim["source"]
    mode = sim.get("mode", "reflection")
    if mode == "transmission":
        # light enters through the substrate (bottom) and is collected in air (top)
        z_src = z_bottom - 0.60 * below
        z_R = z_bottom - 0.85 * below      # below the source: only the reflected wave crosses it
        z_T = z_top + 0.60 * air
        default_dir = "Forward"
    else:
        # light enters from above (air) and reflects off the stack
        z_src = z_top + 0.60 * air
        z_R = z_top + 0.85 * air
        z_T = z_bottom - 0.60 * below
        default_dir = "Backward"

    f.addplane(name="source")
    for k, v in [("injection axis", "z"), ("direction", src.get("direction", default_dir)),
                 ("x", 0), ("y", 0), ("z", z_src),
                 ("x span", sx * nx), ("y span", sy * ny),
                 ("polarization angle", ev(src.get("polarization_deg", 0), params)),
                 ("amplitude", 1), ("override global source settings", 1),
                 ("wavelength start", src["wavelength_range"][0]),
                 ("wavelength stop", src["wavelength_range"][1])]:
        f.setnamed("source", k, v)

    npts = src.get("npts", 101)
    lam0 = sum(src["wavelength_range"]) / 2.0
    for nm, z in (("R", z_R), ("T", z_T)):
        f.addpower(name=nm, x=0, y=0, z=z, x_span=sx * nx, y_span=sy * ny)
        f.setnamed(nm, "monitor type", "2D Z-normal")
        for k, v in [("override global monitor settings", 1),
                     ("use source limits", 0),
                     ("wavelength center", lam0),
                     ("wavelength span", src["wavelength_range"][1] - src["wavelength_range"][0]),
                     ("frequency points", npts),
                     ("use wavelength spacing", 1)]:
            f.setnamed(nm, k, v)

    return dict(z_src=z_src, z_R=z_R, z_T=z_T, z_min=z_min, z_max=z_max)


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
        build_materials(f, spec)
        z_bottom, z_top = build_objects(f, spec, params)
        build_simulation(f, spec, params, z_bottom, z_top)
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


def metrics(res, mode="reflection"):
    """Peak metric appropriate to the device: absorption for a reflector, transmission for a window."""
    lam = res["lam"]
    key = "T" if mode == "transmission" else "A"
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
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    sweep = json.loads(args.sweep_json) if args.sweep_json else spec.get("sweep") or {}
    points = expand(sweep)
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)),
                                       (spec.get("meta", {}).get("package", "spec") + "_out"))
    env = dict(DEFAULT_ENV, **(spec.get("env") or {}))

    print("spec     : %s" % args.spec)
    print("target   : %s" % spec.get("meta", {}).get("target_figure"))
    print("points   : %d" % len(points))
    print("out_dir  : %s" % out_dir)
    for i, p in enumerate(points):
        print("  [%02d] %s" % (i, p if p else "(base parameters)"))
    if args.dry_run:
        print("dry-run: nothing was simulated.")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for i, over in enumerate(points):
        params = copy.deepcopy(spec["parameters"])
        params.update(over)
        tag = "_".join("%s_%g" % (k, v) for k, v in over.items()) or "base"
        print("\n=== point %d/%d  %s ===" % (i + 1, len(points), over or "base"))
        res = run_point(spec, params, env,
                        save_path=os.path.join(out_dir, "point_%02d_%s.fsp" % (i, tag)))
        m = metrics(res, (spec.get("simulation") or {}).get("mode", "reflection"))
        np.savetxt(os.path.join(out_dir, "point_%02d_%s.csv" % (i, tag)),
                   np.column_stack([res["lam"], res["R"], res["T"], res["A"]]),
                   delimiter=",", header="lam_um,R,T,A", comments="")
        rows.append(dict(point=i, **over, **m))
        print("   peak %s = %.4f @ %.3f um   FWHM = %.3f um"
              % (m["metric"], m["peak_value"], m["peak_lam_um"], m["fwhm_um"]))

    keys = list(rows[0].keys())
    with open(os.path.join(out_dir, "summary.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in keys) + "\n")
    print("\nsummary -> %s" % os.path.join(out_dir, "summary.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
