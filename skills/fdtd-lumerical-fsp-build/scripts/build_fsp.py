#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a Lumerical .fsp from a spec WITHOUT running it.

Why this exists: `run_fdtd_sweep.py` only saves the .fsp *after* a full solve, so asking for a
deliverable model cost a complete run first (P06: 876 s per point).  Building and solving are two
different jobs; this script does the first one in seconds.

    python build_fsp.py --spec <spec.json> --out <dir> [--tag name] [--check] [--dry-run] [--json]

Exit codes: 0 ok / 1 --check found a mismatch / 2 argument or config error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "library" / "py" / "fsp_build.py").is_file():
            return parent
        if parent.name == "skills":
            return parent.parent
    raise RuntimeError("找不到仓库根（应包含 library/py/fsp_build.py）")


ROOT = repo_root()
# 2026-11-11：唯一实现从 _shared/ 迁到 library/py/（workspace-layout.md §10）。
if str(ROOT / "library" / "py") not in sys.path:
    sys.path.insert(0, str(ROOT / "library" / "py"))

from fsp_build import (  # noqa: E402
    _MAX_CELLS_OBJECTS, array_cells, array_element_center, array_plan, build_materials,
    build_objects, build_simulation, ev, incidence_expected, resolve_axes,
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
        except Exception as exc:                   # noqa: BLE001
            last = exc
            time.sleep(2.0 * (i + 1))
    raise RuntimeError("could not open an FDTD session: %r" % (last,))


def expected_properties(spec: dict) -> list:
    """(object, property, value) triples the spec says must be true after building.

    Kept deliberately small: the point of `--check` is to catch "the file does not match the spec",
    not to re-implement the builder.  Anything the builder *derives* (region extent along the
    propagation axis, monitor positions) is checked against the in-memory build instead — see
    :func:`derived_properties`.

    ``array`` objects are expanded with **the builder's own** :func:`array_cells`, so cell names
    and per-cell scopes cannot drift between build and check (EXP-61).
    """
    params = spec.get("parameters") or {}
    _, _p, _lateral, _inv = resolve_axes(spec.get("simulation") or {})
    want = []
    for o in spec.get("objects") or []:
        if o.get("type") == "array":
            want.extend(array_expected(o, params, _p))
            continue
        oid = o["id"]
        if o.get("center") and len(o["center"]) == 3:
            for ax, v in zip(("x", "y", "z"), o["center"]):
                want.append((oid, ax, ev(v, params)))
        spans = o.get("span") or []
        if spans and o.get("type") == "2drect":
            # 面对象的两个 span 落在「法向之外」的轴上：法向 z -> (x,y)，法向 y -> (x,z)
            normal = str(o.get("surface_normal") or "z").lower()
            plane = [a for a in ("x", "y", "z") if a != normal]
            for ax, v in zip(plane, spans):
                want.append((oid, "%s span" % ax, ev(v, params)))
        elif len(spans) == 2:
            for ax, v in zip(("x span", "y span"), spans):
                want.append((oid, ax, ev(v, params)))
        elif len(spans) == 3:
            for ax, v in zip(("x span", "y span", "z span"), spans):
                want.append((oid, ax, ev(v, params)))
        if o.get("radius") is not None:
            want.append((oid, "radius", ev(o["radius"], params)))
        if o.get("height") is not None:
            want.append((oid, "z span", ev(o["height"], params)))
    sim = spec.get("simulation") or {}
    lat = spec.get("lattice") or {}
    _, p, lateral, _inv = resolve_axes(sim)
    sc = lat.get("supercell") or {}
    # 横向轴由晶格定；传播轴的范围是推导量，不在这里断言
    if "x" in lateral and lat.get("period_x") is not None:
        want.append(("FDTD", "x span", ev(lat["period_x"], params) * int(sc.get("nx", 1))))
    if "y" in lateral and lat.get("period_y") is not None:
        want.append(("FDTD", "y span", ev(lat["period_y"], params) * int(sc.get("ny", 1))))
    if sim.get("mesh_accuracy") is not None:
        want.append(("FDTD", "mesh accuracy", float(sim["mesh_accuracy"])))
    # EXP-75: high-angle BFAST stability is a declared, checkable property.
    if sim.get("dt_stability_factor") is not None:
        want.append(("FDTD", "dt stability factor", float(sim["dt_stability_factor"])))
    # EXP-72: angles / BCs / plane wave type are the properties a legacy check was blind to.
    # Values may be strings — run_check() compares those verbatim instead of float()-ing them.
    want.extend(incidence_expected(spec, params))
    return want


def array_expected(arr: dict, params: dict, p: str = "z") -> list:
    """Per-cell assertions for one ``array`` object.

    Only properties that are directly readable and directly determined by the spec are
    asserted.  ``ellipse`` / ``polygon`` cells are asserted by **centre** and, for polygons,
    ``x span`` / ``y span`` read back off the analytic vertex list — the engine stores
    vertices, so asserting a "radius" that does not exist on a polygon would report a false
    mismatch (the K11 mistake: judging B with A's property).
    """
    out = []
    tpl = arr.get("element") or {}
    etype = tpl.get("type")
    for i, j, scope in array_cells(arr, params):
        name = "%s_r%dc%d" % (arr["id"], i, j)
        cdx, cdy = array_element_center(arr, i, j, scope)
        if etype == "polygon":
            # 顶点已烘进格子偏移；读回的是引擎侧 vertices，这里断言包围盒
            verts = [[ev(v, scope) + (cdx if k == 0 else cdy) for k, v in enumerate(pair)]
                     for pair in tpl["vertices"]]
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            out.append((name, "x", (min(xs) + max(xs)) / 2))
            out.append((name, "y", (min(ys) + max(ys)) / 2))
            out.append((name, "x span", max(xs) - min(xs)))
            out.append((name, "y span", max(ys) - min(ys)))
            out.append((name, "z", ev(tpl.get("z", "0"), scope)))
            out.append((name, "z span", ev(tpl.get("z_span", "0"), scope)))
            continue
        base = tpl.get("center") or ["0", "0", "0"]
        bx, by, bz = [ev(v, scope) for v in base]
        # x/y 属性只有"几何由 center 决定"的类型才有意义；polygon/ellipse 的位置
        # 烘在 vertices 里，引擎侧 x/y 恒为 0——断言它必然全红（假 mismatch）。
        if etype not in ("polygon", "ellipse"):
            out.append((name, "x", bx + cdx))
            out.append((name, "y", by + cdy))
        if p not in ("x", "y"):
            out.append((name, "z", bz))
        if etype == "box":
            # 尺寸是 per-cell 的主战场：没有这一条，改一格的 d1 不会红（EXP-61 抓到过）。
            for ax, v in zip(("x span", "y span", "z span"), tpl["span"]):
                out.append((name, ax, ev(v, scope)))
        elif etype in ("cylinder", "ring"):
            out.append((name, "radius", ev(tpl["radius"], scope)))
            if etype == "ring":
                out.append((name, "inner radius", ev(tpl["inner_radius"], scope)))
            out.append((name, "z span", ev(tpl["height"], scope)))
        elif etype == "ellipse":
            # ellipse 建成 48 点离散多边形：check 用与 build_one **完全相同**的顶点公式
            # 重推包围盒（同公式同浮点，逐位可比）。旋转是逐格表达式（EXP-64），
            # 所以不能用未旋转的解析 bbox。
            import math as _math
            ax_, ay_ = ev(tpl["axes"][0], scope), ev(tpl["axes"][1], scope)
            rot = _math.radians(float(ev(tpl.get("rotation_deg", 0), scope)))
            n = int(tpl.get("n_vertices", 48))
            th = [2 * _math.pi * k / n for k in range(n)]
            u = [(ax_ / 2) * _math.cos(t) for t in th]
            v = [(ay_ / 2) * _math.sin(t) for t in th]
            # ellipse 建成 polygon 后，引擎侧没有可读的 x/y/x span/y span 属性
            # （几何在 vertices 里，getnamed 读不到）。诚实的降级：ellipse 单元只断言
            # 可读的 z / z span；逐格旋转的正确性由 build 侧 cell_params 的 i/j 标注
            # 校验 + 装配端双向检查覆盖。缺什么写什么，不假装全查（SKILL.md §6 同款）。
            out.append((name, "z", bz))
            out.append((name, "z span", ev(tpl["height"], scope)))
        elif etype == "2drect":
            normal = str(tpl.get("surface_normal") or "z").lower()
            plane = [a for a in ("x", "y", "z") if a != normal]
            for ax, v in zip(plane, tpl["span"]):
                out.append((name, "%s span" % ax, ev(v, scope)))
    return out


def derived_properties(built: dict) -> list:
    """(object, property, value) triples that must survive save/reload of *this* build.

    These numbers come from ``build_simulation``, so they do not re-derive the physics — they
    prove the .fsp on disk still carries what was built (a wrong monitor position or a region
    that silently fell back to its default would show up here).
    """
    p = built.get("axis")
    if not p:
        return []
    want = [("FDTD", p, (built["p_max"] + built["p_min"]) / 2),
            ("FDTD", "%s span" % p, built["p_max"] - built["p_min"]),
            ("source", p, built["pos_src"])]
    for m in built.get("monitors") or []:
        want.append((m["name"], p, m["pos"]))
    return want


def run_check(fsp: Path, spec: dict, tol: float = 1e-9, built: dict = None) -> dict:
    """Read the built file back and compare with the spec. Numbers on both sides, always."""
    env = dict(DEFAULT_ENV, **(spec.get("env") or {}))
    f = open_session(env)
    rows, bad = [], []
    want_all = expected_properties(spec)
    if built:
        want_all = want_all + derived_properties(built)
    try:
        f.load(str(fsp.resolve()))
        for obj, prop, want in want_all:
            if isinstance(want, str):
                # BC / plane wave type are enumerated strings, not numbers. float() would
                # raise and get filed as "missing" — a false mismatch (the K11 mistake).
                try:
                    got_s = str(f.getnamed(obj, prop)).strip()
                    ok = got_s == want
                    row = {"object": obj, "property": prop, "expected": want,
                           "actual": got_s, "status": "ok" if ok else "mismatch"}
                except Exception as e:                 # noqa: BLE001
                    ok = False
                    row = {"object": obj, "property": prop, "expected": want,
                           "actual": None,
                           "status": "missing: %s" % str(e).splitlines()[0][:60]}
                rows.append(row)
                if not ok:
                    bad.append(row)
                continue
            try:
                got = float(f.getnamed(obj, prop))
            except Exception as e:                 # noqa: BLE001
                rows.append({"object": obj, "property": prop, "expected": want,
                             "actual": None, "status": "missing: %s" % str(e).splitlines()[0][:60]})
                bad.append(rows[-1])
                continue
            ok = abs(got - want) <= max(tol, abs(want) * 1e-9)
            row = {"object": obj, "property": prop, "expected": want, "actual": got,
                   "status": "ok" if ok else "mismatch"}
            rows.append(row)
            if not ok:
                bad.append(row)
        try:
            f.eval("dim_check = getnamed('FDTD', 'dimension');")
            dim = str(f.getv("dim_check"))
        except Exception:                          # noqa: BLE001
            dim = "?"
        want_dim = str((spec.get("simulation") or {}).get("dimension", "3D"))
        rows.append({"object": "FDTD", "property": "dimension",
                     "expected": want_dim, "actual": dim,
                     "status": "ok" if dim == want_dim else "mismatch"})
        if dim != want_dim:
            bad.append(rows[-1])
    finally:
        f.close()
    return {"checked": len(rows), "mismatches": len(bad), "rows": rows, "bad": bad}


def array_summary(spec: dict) -> list:
    """Engine-free array report for ``--dry-run``: cell count, pitch, and the size warning.

    Printed *before* a session is opened, so "this spec will create 65k objects" is visible in
    0.2 s instead of after minutes of lumapi calls.
    """
    params = spec.get("parameters") or {}
    out = []
    for o in spec.get("objects") or []:
        if o.get("type") != "array":
            continue
        info = array_plan(o, params)
        info["element"] = (o.get("element") or {}).get("type")
        info["note"] = ("超过 objects 引擎建议上限 %d（脚本引擎尚未实现）"
                        % _MAX_CELLS_OBJECTS) if info["over_objects_limit"] else ""
        out.append(info)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build a Lumerical .fsp from a spec (no solve)")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", help="output directory (required unless --only-check)")
    ap.add_argument("--tag", default="model", help=".fsp basename")
    ap.add_argument("--check", action="store_true",
                    help="after building, read the file back and diff every property against the spec")
    ap.add_argument("--only-check", metavar="FSP",
                    help="skip building; check an existing .fsp against this spec")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; open no session")
    ap.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    args = ap.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print("ERROR spec not found: %s" % spec_path)
        return 2
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    if not (args.only_check or args.dry_run) and not args.out:
        ap.error("--out is required unless --only-check / --dry-run is given")

    out = Path(args.out) if args.out else None
    if out is not None:
        out = out if out.is_absolute() else (ROOT / out)
    fsp = (out / (args.tag + ".fsp")) if out is not None else None

    def emit(obj: dict) -> None:
        print(json.dumps(obj, ensure_ascii=False, indent=2) if args.json
              else "\n".join("%-16s %s" % (k, v) for k, v in obj.items()))

    if args.only_check:
        target = Path(args.only_check)
        target = target if target.is_absolute() else (ROOT / target)
        res = run_check(target, spec)
        print(json.dumps({k: res[k] for k in ("checked", "mismatches")}, ensure_ascii=False)
              if args.json else "checked=%d mismatches=%d" % (res["checked"], res["mismatches"]))
        for row in res["bad"][:20]:
            print("  %-14s %-12s expected=%r actual=%r (%s)"
                  % (row["object"], row["property"], row["expected"], row["actual"], row["status"]))
        return 0 if res["mismatches"] == 0 else 1

    params = spec.get("parameters") or {}
    plan = {
        "spec": str(spec_path),
        "out": str(fsp) if fsp is not None else None,
        "materials": len(spec.get("materials") or {}),
        "objects": len(spec.get("objects") or []),
        "dimension": (spec.get("simulation") or {}).get("dimension", "3D"),
        "monitors": list(((spec.get("simulation") or {}).get("monitors") or {}).keys())
        if isinstance((spec.get("simulation") or {}).get("monitors"), dict) else
        [m.get("name") for m in ((spec.get("simulation") or {}).get("monitors") or [])],
        "solves": 0,
    }
    if args.dry_run:
        plan["dry_run"] = True
        plan["arrays"] = array_summary(spec)
        emit(plan)
        return 0

    out.mkdir(parents=True, exist_ok=True)
    env = dict(DEFAULT_ENV, **(spec.get("env") or {}))
    t0 = time.time()
    f = open_session(env)
    try:
        axes = resolve_axes(spec["simulation"])
        build_materials(f, spec)
        p_bottom, p_top = build_objects(f, spec, params, axes)
        sim_info = build_simulation(f, spec, params, p_bottom, p_top, axes)
        f.save(str(fsp.resolve()))
        f.eval("lm_build = layoutmode;")
        layoutmode = float(f.getv("lm_build"))
    finally:
        f.close()

    log = fsp.with_name(fsp.stem + "_p0.log")
    manifest = {
        "ok": True, "fsp": str(fsp), "bytes": fsp.stat().st_size,
        "wall_s": round(time.time() - t0, 2),
        "layoutmode": layoutmode,
        "p0_log": log.is_file(),
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest()[:16],
        "monitors": sim_info.get("monitors"),
        "wavelength_range": sim_info.get("wavelength_range"),
        "axis": sim_info.get("axis"),
        "span_range": [sim_info["p_min"], sim_info["p_max"]],
        "solves": 0,
    }
    (out / (args.tag + "_build.json")).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    rc = 0
    if args.check:
        res = run_check(fsp, spec, built=sim_info)
        manifest["check"] = {"checked": res["checked"], "mismatches": res["mismatches"]}
        (out / (args.tag + "_build.json")).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if res["mismatches"]:
            rc = 1
            print("CHECK FAILED: %d mismatch(es)" % res["mismatches"])
            for row in res["bad"][:20]:
                print("  %-14s %-12s expected=%r actual=%r (%s)"
                      % (row["object"], row["property"], row["expected"], row["actual"],
                         row["status"]))
        elif not args.json:
            print("check: %d properties, 0 mismatches" % res["checked"])
    emit(manifest)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
