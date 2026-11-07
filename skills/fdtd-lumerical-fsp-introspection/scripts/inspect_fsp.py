#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""inspect_fsp.py — reverse-engineer existing Lumerical .fsp projects into JSON evidence.

Consumes : a config JSON listing .fsp paths (and optionally a reference spec_<id>.json)
Produces : manifest.json (object tree / materials / settings / layoutmode),
           spectra.json  (R/T spectra already stored in the project + derived A/peak),
           diff.json     (FSP layer positions & solver settings vs the reference spec),
           summary.json  (machine-readable one-screen summary)

Paths in the config and in --out are resolved RELATIVE TO THE REPOSITORY ROOT
(the workspace directory three levels above this file), never relative to cwd.

CLI     : --config <json> --out <dir> [--dry-run] [--json]
Exit    : 0 = all projects inspected; 1 = one or more projects failed; 2 = usage/config error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_API_PATH = os.environ.get(
    "LUMERICAL_API_PATH", r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
DEFAULT_LICENSE = os.environ.get("ANSYSLMD_LICENSE_FILE", "1055@localhost")

_EXPR_OK = re.compile(r"[0-9a-zA-Z_.+\-*/() ]+")

CORE_PROPS = [
    "x", "y", "z", "x span", "y span", "z span",
    "x min", "x max", "y min", "y max", "z min", "z max",
    "radius", "inner radius", "outer radius", "height",
    "material", "mesh order", "index", "enabled",
    "dimension", "x min bc", "x max bc", "y min bc", "y max bc",
    "z min bc", "z max bc", "mesh accuracy", "auto shutoff min",
    "simulation time", "dt stability factor", "background material",
    "injection axis", "direction", "polarization angle", "amplitude",
    "wavelength start", "wavelength stop", "override global source settings",
    "monitor type", "wavelength center", "wavelength span", "frequency points",
    "use wavelength spacing", "override global monitor settings", "use source limits",
    "dx", "dy", "dz",
]

MATERIAL_PROPS = [
    "name", "Plasma resonance", "Plasma collision", "Refractive Index",
    "Imaginary Refractive Index", "Permittivity", "mesh order",
]

GEOM_TYPES = {"Rectangle", "Polygon", "Circle", "Sphere", "Ring"}
# Layers above this z (nm) are "functional" (ground plane / spacer / resonator).
# The substrate below an opaque ground plane is optically irrelevant, so a different
# substrate thickness must not invalidate the spacer-thickness verdict.
FUNCTIONAL_Z_MIN_NM = -500.0


class UsageError(Exception):
    """Config / CLI problem -> exit code 2."""


def ev(expr, params):
    if isinstance(expr, (int, float)):
        return float(expr)
    if not isinstance(expr, str) or not _EXPR_OK.fullmatch(expr):
        raise UsageError("unsupported spec expression: %r" % (expr,))
    return float(eval(expr, {"__builtins__": {}}, params))  # noqa: S307 - whitelisted charset


def jsonable(v):
    if isinstance(v, (np.ndarray, np.generic)):
        a = np.asarray(v)
        return "<array shape=%s>" % (a.shape,) if a.size > 200 else a.tolist()
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v[:200]]
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return repr(v)


def resolve_repo(p):
    q = Path(str(p))
    return q.resolve() if q.is_absolute() else (REPO_ROOT / q).resolve()


def ascii_gate(p):
    try:
        str(p).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def load_config(path):
    p = resolve_repo(path)
    if not p.is_file():
        raise UsageError("config not found: %s" % p)
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise UsageError("config is not valid JSON: %r" % (e,))
    if not isinstance(cfg, dict):
        raise UsageError("config must be a JSON object")
    fsp = cfg.get("fsp")
    if not isinstance(fsp, list) or not fsp or not all(isinstance(x, str) for x in fsp):
        raise UsageError("config.fsp must be a non-empty list of path strings")
    mode = cfg.get("mode", "both")
    if mode not in ("structure", "spectra", "both"):
        raise UsageError("config.mode must be structure | spectra | both")
    for raw in fsp:
        if not resolve_repo(raw).is_file():
            raise UsageError("fsp not found: %s" % resolve_repo(raw))
        if not ascii_gate(resolve_repo(raw)):
            raise UsageError("non-ASCII path (GPU error 1113): %s" % resolve_repo(raw))
    if cfg.get("reference_spec"):
        if not resolve_repo(cfg["reference_spec"]).is_file():
            raise UsageError("reference_spec not found: %s" % cfg["reference_spec"])
    return cfg


# ---------------------------------------------------------------- lumapi helpers
def prop_names(f, obj, name):
    """getnamed(name) returns a newline-separated PROPERTY LIST STRING, not a dict.
    Mesh / PlaneSource / DFTMonitor throw on that call -> fall back to dir(obj)."""
    try:
        s = f.getnamed(name)
        if isinstance(s, str) and s.strip():
            return [x.strip() for x in s.split("\n") if x.strip()]
    except Exception:
        pass
    return [a.replace("_", " ") for a in dir(obj)
            if not a.startswith("_") and a not in ("getChildren", "results", "type", "name")]


def read_obj(f, obj, full=False):
    name, typ = getattr(obj, "name", "?"), getattr(obj, "type", "?")
    names = prop_names(f, obj, name)
    wanted = names if full else [p for p in CORE_PROPS if p in names]
    props = {}
    for p in wanted:
        try:
            props[p] = jsonable(f.getnamed(name, p))
        except Exception:
            try:
                props[p] = jsonable(getattr(obj, p.replace(" ", "_")))
            except Exception:
                pass
    entry = {"name": name, "type": typ, "props": props}
    if full:
        entry["all_property_names"] = names
    try:
        kids = obj.getChildren()
    except Exception:
        kids = []
    if kids:
        entry["children"] = [read_obj(f, k, full) for k in kids]
    return entry


def walk_material_names(node, acc):
    m = node.get("props", {}).get("material")
    if isinstance(m, str) and m:
        acc.append(m)
    for c in node.get("children", []):
        walk_material_names(c, acc)
    return acc


def material_dump(f, names):
    out = {}
    for nm in sorted(set(n for n in names if isinstance(n, str))):
        rec = {}
        for p in MATERIAL_PROPS:
            try:
                rec[p] = jsonable(f.getmaterial(nm, p))
            except Exception:
                pass
        if rec:
            out[nm] = rec
    return out


def read_power(f, name):
    raw = f.getresult(name, "T")
    item = raw[0] if isinstance(raw, (list, tuple)) else raw
    if isinstance(item, dict):
        return np.asarray(item.get("lambda", item.get("f"))).ravel(), np.asarray(item["T"]).ravel()
    a = np.asarray(item)
    if a.ndim == 2 and a.shape[1] >= 2:
        return a[:, 0].ravel(), a[:, 1].ravel()
    raise ValueError("unexpected getresult layout: %r" % (type(item),))


def inspect_structure(f, full):
    root = f.getObjectById("::model")
    tree = read_obj(f, root, full)
    try:
        f.eval("lm = layoutmode;")
        layoutmode = jsonable(f.getv("lm"))
    except Exception as e:
        layoutmode = "unreadable: %r" % (e,)
    try:
        results = [n for n in dir(root.results) if not n.startswith("_") and n]
    except Exception:
        results = []
    return {
        "layoutmode": layoutmode,
        "tree": tree,
        "materials": material_dump(f, walk_material_names(tree, [])),
        "root_results": results,
    }


def inspect_spectra(f):
    out = {}
    for nm in ("R", "T"):
        try:
            lam, p = read_power(f, nm)
            out[nm] = {"lambda": lam.tolist(), "power": p.tolist()}
        except Exception as e:
            out[nm] = {"error": repr(e)}
    if "lambda" in out.get("R", {}) and "lambda" in out.get("T", {}):
        lam = np.asarray(out["R"]["lambda"])
        R = np.asarray(out["R"]["power"])
        T = np.asarray(out["T"]["power"])
        if lam.size == R.size == T.size:
            A = 1.0 - R - T
            i = int(np.argmax(A))
            j = int(np.argmin(abs(lam - 6e-6)))
            out["derived"] = {
                "peak_A": float(A[i]), "peak_lambda_um": float(lam[i] * 1e6),
                "R_at_peak": float(R[i]), "T_at_peak": float(T[i]),
                "A_at_6um": float(A[j]), "npts": int(lam.size),
                "lambda_range_um": [float(lam.min() * 1e6), float(lam.max() * 1e6)],
            }
            out["spectrum"] = [[float(x * 1e6), float(r), float(t), float(a)]
                               for x, r, t, a in zip(lam, R, T, A)]
    return out


# ---------------------------------------------------------------- FSP <-> spec diff
def fsp_layers(manifest):
    out = []
    for o in manifest.get("tree", {}).get("children", []):
        if o.get("type") not in GEOM_TYPES:
            continue
        p = o.get("props", {})
        if not all(k in p for k in ("z min", "z max")):
            continue
        lo, hi = float(p["z min"]) * 1e9, float(p["z max"]) * 1e9
        out.append({"name": o["name"], "z_min_nm": round(lo, 2), "z_max_nm": round(hi, 2),
                    "span_nm": round(hi - lo, 2), "material": p.get("material")})
    return sorted(out, key=lambda x: x["z_min_nm"])


def spec_layers(spec):
    params = {k: float(v) for k, v in spec.get("parameters", {}).items()}
    out = []
    for o in spec.get("objects", []):
        try:
            cz = ev(o["center"][2], params)
            sz = ev(o["span"][2], params)
        except (KeyError, IndexError, UsageError):
            continue
        lo, hi = (cz - sz / 2) * 1e9, (cz + sz / 2) * 1e9
        out.append({"name": o.get("id"), "z_min_nm": round(lo, 2), "z_max_nm": round(hi, 2),
                    "span_nm": round(hi - lo, 2), "material": o.get("material")})
    return sorted(out, key=lambda x: x["z_min_nm"])


def build_diff(manifest, spec):
    fl, sl = fsp_layers(manifest), spec_layers(spec)
    used, pairs = set(), []
    for f in fl:
        hit = next((s for i, s in enumerate(sl)
                    if i not in used and abs(s["z_min_nm"] - f["z_min_nm"]) <= 1.0
                    and abs(s["z_max_nm"] - f["z_max_nm"]) <= 1.0), None)
        if hit:
            used.add(sl.index(hit))
        pairs.append({"fsp": f, "spec": hit, "match": hit is not None})
    unmatched = [s for i, s in enumerate(sl) if i not in used]

    props = {}
    for o in manifest.get("tree", {}).get("children", []):
        if o.get("name") == "FDTD":
            props = o.get("props", {})
            break
    src, mon = {}, {}
    for o in manifest.get("tree", {}).get("children", []):
        if o.get("type") == "PlaneSource" and not src:
            src = o.get("props", {})
        if o.get("type") == "DFTMonitor" and not mon:
            mon = o.get("props", {})
    sim = spec.get("simulation", {})
    ssim = sim.get("source", {})
    bc = sim.get("bc", {})

    def row(field, fv, sv, note=""):
        # SI quantities here are tiny (1e-12 s, 1e-6 m). A fixed 1e-9 absolute floor
        # would silently call 1 ps == 5 ps. Use a relative tolerance with a tiny floor.
        try:
            match = abs(float(fv) - float(sv)) <= max(1e-18, abs(float(sv)) * 1e-6)
        except (TypeError, ValueError):
            match = str(fv) == str(sv)
        return {"field": field, "fsp": fv, "spec": sv, "match": bool(match), "note": note}

    settings = [
        row("mesh_accuracy", props.get("mesh accuracy"), sim.get("mesh_accuracy")),
        row("auto_shutoff", props.get("auto shutoff min"), sim.get("auto_shutoff")),
        row("simulation_time", props.get("simulation time"), sim.get("simulation_time")),
        row("lambda_start", src.get("wavelength start"), (ssim.get("wavelength_range") or [None])[0]),
        row("lambda_stop", src.get("wavelength stop"), (ssim.get("wavelength_range") or [None, None])[1]),
        row("npts", mon.get("frequency points"), ssim.get("npts"),
            "frequency points live on the DFT monitor, not on the plane source"),
        row("polarization_deg", src.get("polarization angle"), ssim.get("polarization_deg", 0)),
        row("direction", src.get("direction"), ssim.get("direction")),
        row("bc_x", props.get("x min bc"), bc.get("x")),
        row("bc_y", props.get("y min bc"), bc.get("y")),
        row("bc_z", props.get("z min bc"), bc.get("z")),
    ]

    # Material parameters are matched BY VALUE because custom material names differ
    # between the course project (user_Au) and our spec (Au_paper).
    fvals = []
    for m in manifest.get("materials", {}).values():
        for k, v in m.items():
            if isinstance(v, (int, float)):
                fvals.append((k, float(v)))
    materials = []
    for key, m in spec.get("materials", {}).items():
        for k in ("wp", "wc"):
            if k not in m:
                continue
            target = float(m[k])
            key_name = "Plasma resonance" if k == "wp" else "Plasma collision"
            hit = any(pk == key_name and abs(pv - target) <= abs(target) * 1e-4
                      for pk, pv in fvals)
            materials.append({"field": "%s.%s" % (key, k), "spec": target,
                              "fsp_property": key_name, "match": hit})
        if m.get("kind") == "constant_nk":
            n = float(m["n"])
            hit = any(abs(pv - n) <= 0.01 for pk, pv in fvals if pk == "Refractive Index")
            materials.append({"field": "%s.n" % key, "spec": n,
                              "fsp_property": "Refractive Index", "match": hit})

    functional = [p for p in pairs if p["fsp"]["z_min_nm"] > FUNCTIONAL_Z_MIN_NM]
    substrate = [
        {"fsp": p["fsp"], "spec": (p["spec"] or {}).get("name")}
        for p in pairs if p["fsp"]["z_min_nm"] <= FUNCTIONAL_Z_MIN_NM and not p["match"]
    ]
    return {
        "layers": pairs, "spec_layers_without_fsp_match": unmatched,
        "settings": settings, "materials": materials,
        "functional_layers": functional,
        "functional_layers_match": bool(functional) and all(p["match"] for p in functional),
        "substrate_mismatch": substrate,
        "substrate_note": ("substrate thickness differs; optically irrelevant when the metallic "
                           "ground plane is thicker than the IR skin depth (T is ~0)"),
        "all_layers_match": all(p["match"] for p in pairs) and not unmatched,
        "settings_mismatches": [r["field"] for r in settings if not r["match"]],
        "all_settings_match": all(r["match"] for r in settings),
        "all_materials_match": all(r["match"] for r in materials),
    }


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Inspect existing Lumerical .fsp projects")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        cfg = load_config(args.config)
    except UsageError as e:
        print("config error: %s" % e, file=sys.stderr)
        return 2

    fsp_paths = [resolve_repo(x) for x in cfg["fsp"]]
    out_dir = resolve_repo(args.out)
    plan = {
        "repo_root": str(REPO_ROOT), "mode": cfg.get("mode", "both"),
        "fsp": [str(p) for p in fsp_paths], "out": str(out_dir),
        "reference_spec": str(resolve_repo(cfg["reference_spec"])) if cfg.get("reference_spec") else None,
        "full_props": bool(cfg.get("full_props", False)),
    }
    if args.dry_run:
        if args.json:
            print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False, indent=2))
        else:
            print("dry-run plan:\n" + json.dumps(plan, ensure_ascii=False, indent=2))
            print("dry-run: no Lumerical session was opened.")
        return 0

    os.environ.setdefault("ANSYSLMD_LICENSE_FILE", cfg.get("env", {}).get("license", DEFAULT_LICENSE))
    api_path = cfg.get("env", {}).get("api_path", DEFAULT_API_PATH)
    if api_path not in sys.path:
        sys.path.insert(0, api_path)
    try:
        import lumapi
    except Exception as e:
        print("runtime error: import lumapi failed: %r" % (e,), file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    spec = None
    if plan["reference_spec"]:
        spec = json.loads(Path(plan["reference_spec"]).read_text(encoding="utf-8"))

    manifests, spectra_all, diffs, errors = [], {}, {}, []
    for p in fsp_paths:
        key = p.name
        f = None
        try:
            for i in range(4):
                try:
                    f = lumapi.FDTD(hide=True)
                    break
                except Exception:
                    if i == 3:
                        raise
                    time.sleep(2.0 * (i + 1))
            t0 = time.time()
            f.load(str(p))
            m = {"fsp": str(p), "bytes": p.stat().st_size}
            # ORDER MATTERS: walking the object tree (getObjectById/getChildren) changes
            # Lumerical's group scope, after which getresult("R","T") by global name fails
            # with "Can not find object 'R'". Read stored spectra FIRST, then the tree.
            if plan["mode"] in ("spectra", "both"):
                spectra_all[key] = inspect_spectra(f)
            if plan["mode"] in ("structure", "both"):
                m.update(inspect_structure(f, plan["full_props"]))
            m["probe_seconds"] = round(time.time() - t0, 1)
            manifests.append(m)
            if spec and plan["mode"] in ("structure", "both"):
                diffs[key] = build_diff(m, spec)
            if not args.json:
                d = (spectra_all.get(key) or {}).get("derived", {})
                print("%s: layoutmode=%s objects=%d derived=%s (%.1fs)"
                      % (key, m.get("layoutmode"), len(m.get("tree", {}).get("children", [])),
                         json.dumps(d), m["probe_seconds"]))
        except Exception as e:
            errors.append({"fsp": str(p), "error": repr(e)})
            print("%s FAILED: %r" % (key, e), file=sys.stderr)
        finally:
            if f is not None:
                try:
                    f.close()
                except Exception:
                    pass

    (out_dir / "manifest.json").write_text(
        json.dumps(manifests, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "spectra.json").write_text(
        json.dumps(spectra_all, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "diff.json").write_text(
        json.dumps(diffs, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        "plan": {"mode": plan["mode"], "out": plan["out"]},
        "projects": [{
            "name": Path(m["fsp"]).name,
            "layoutmode": m.get("layoutmode"),
            "n_objects": len(m.get("tree", {}).get("children", [])),
            "root_results": m.get("root_results"),
            "derived": (spectra_all.get(Path(m["fsp"]).name) or {}).get("derived"),
            "diff": ({k: diffs.get(Path(m["fsp"]).name, {}).get(k)
                      for k in ("functional_layers_match", "all_layers_match",
                                "all_settings_match", "settings_mismatches",
                                "all_materials_match", "substrate_mismatch")}
                     if diffs.get(Path(m["fsp"]).name) else None),
        } for m in manifests],
        "errors": errors,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("outputs -> %s (manifest.json / spectra.json / diff.json / summary.json)" % out_dir)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
