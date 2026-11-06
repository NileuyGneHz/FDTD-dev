#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""validate_spec.py — structural and physical sanity check for a model spec.

Catches the mistakes that are invisible in the JSON but fatal in the solver: a 185 m thick layer,
a plasma frequency in Hz where rad/s was expected, an object naming a material that does not exist,
a PML boundary on a periodic array.

Usage
-----
    python validate_spec.py spec.json
    python validate_spec.py spec.json --strict      # warnings become errors

Exit code: 0 = no errors, 1 = at least one error (or a warning under --strict).
"""

from __future__ import annotations

import argparse
import json
import re
import sys

REQUIRED_TOP = ["schema_version", "meta", "parameters", "lattice", "materials",
                "objects", "simulation", "targets"]
MATERIAL_KINDS = {"drude", "constant_nk", "constant_eps", "builtin", "sampled_nk"}
OBJECT_REQUIRED = {
    "box": ["center", "span"],
    "polygon": ["vertices", "z", "z_span"],
    "cylinder": ["center", "radius", "height"],
    "ellipse": ["center", "axes", "height"],
    "sphere": ["center", "radius"],
    "ring": ["center", "radius", "inner_radius", "height"],
}
BC_ALLOWED = {"Periodic", "Bloch", "PML", "Metal", "Symmetric", "Anti-Symmetric"}

issues = []


def err(msg):
    issues.append(("ERROR", msg))


def warn(msg):
    issues.append(("WARN", msg))


def evaluate(expr, params, where):
    """Evaluate a spec expression against the parameter table. Numbers pass through."""
    if isinstance(expr, (int, float)):
        return float(expr)
    if not isinstance(expr, str):
        err("%s: expected a number or an expression string, got %r" % (where, type(expr).__name__))
        return None
    if not re.fullmatch(r"[0-9a-zA-Z_.+\-*/() ]+", expr):
        err("%s: expression contains unsupported characters: %r" % (where, expr))
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, params))  # noqa: S307 - whitelisted charset
    except Exception as exc:  # noqa: BLE001
        err("%s: cannot evaluate %r (%s)" % (where, expr, exc))
        return None


def check_length(value, where, lo=1e-9, hi=1e-3):
    if value is None:
        return
    if not (lo <= value <= hi):
        err("%s = %.3g m is outside the plausible range [%.0e, %.0e]" % (where, value, lo, hi))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    for key in REQUIRED_TOP:
        if key not in spec:
            err("missing top-level key: %s" % key)
    if spec.get("schema_version") != "1.0":
        warn("schema_version is %r, expected '1.0'" % spec.get("schema_version"))

    params = spec.get("parameters") or {}
    for k, v in params.items():
        if not isinstance(v, (int, float)):
            err("parameters.%s must be a number (expressions belong on the object, not here)" % k)

    lat = spec.get("lattice") or {}
    for axis in ("period_x", "period_y"):
        check_length(evaluate(lat.get(axis), params, "lattice.%s" % axis), "lattice.%s" % axis)

    mats = spec.get("materials") or {}
    for name, m in mats.items():
        kind = m.get("kind")
        if kind not in MATERIAL_KINDS:
            err("materials.%s: unknown kind %r (allowed: %s)" % (name, kind, ", ".join(sorted(MATERIAL_KINDS))))
            continue
        if not m.get("cite"):
            warn("materials.%s: no cite — record where these numbers came from" % name)
        if kind == "drude":
            wp, wc = m.get("wp"), m.get("wc")
            if not isinstance(wp, (int, float)) or not isinstance(wc, (int, float)):
                err("materials.%s: drude needs numeric wp and wc" % name)
            else:
                if not (1e12 <= wp <= 1e18):
                    err("materials.%s.wp = %.3g rad/s is implausible (1e12..1e18); "
                        "a value near 2e15 is probably Hz, not rad/s" % (name, wp))
                if wc >= wp:
                    err("materials.%s: wc (%.3g) must be smaller than wp (%.3g)" % (name, wc, wp))
        if kind == "constant_nk" and m.get("k") is None:
            warn("materials.%s: no k given — treating as lossless; state this explicitly" % name)
        if kind in ("constant_nk", "constant_eps") and "n" not in m and "eps_real" not in m:
            err("materials.%s: constant_nk needs n, constant_eps needs eps_real" % name)

    objs = spec.get("objects") or []
    if not objs:
        err("objects is empty")
    seen_ids = set()
    for i, o in enumerate(objs):
        oid = o.get("id", "#%d" % i)
        where = "objects[%s]" % oid
        if oid in seen_ids:
            err("%s: duplicate id" % where)
        seen_ids.add(oid)
        typ = o.get("type")
        if typ not in OBJECT_REQUIRED:
            err("%s: unknown type %r (allowed: %s)" % (where, typ, ", ".join(sorted(OBJECT_REQUIRED))))
            continue
        for f in OBJECT_REQUIRED[typ]:
            if f not in o:
                err("%s: %s requires field %r" % (where, typ, f))
        mat = o.get("material")
        if mat and mat not in mats:
            err("%s: material %r is not defined in materials" % (where, mat))
        if typ == "box":
            for f in ("center", "span"):
                vals = o.get(f) or []
                if len(vals) != 3:
                    err("%s.%s must have 3 components" % (where, f))
                    continue
                for j, v in enumerate(vals):
                    got = evaluate(v, params, "%s.%s[%d]" % (where, f, j))
                    if f == "span":
                        check_length(got, "%s.span[%d]" % (where, j))
                    if f == "span" and got is not None and got <= 0:
                        err("%s.span[%d] must be positive" % (where, j))

    sim = spec.get("simulation") or {}
    bc = sim.get("bc") or {}
    for axis in ("x", "y", "z"):
        val = bc.get(axis)
        if val not in BC_ALLOWED:
            err("simulation.bc.%s = %r is not a valid boundary condition" % (axis, val))
    if bc.get("x") == "PML" and bc.get("y") == "PML" and lat.get("period_x"):
        warn("bc.x and bc.y are both PML while the spec defines a lattice period — "
             "PML simulates one isolated element. For a periodic array use Periodic, or add "
             "'isolated_element' to assumptions to record that this is deliberate.")

    targets = spec.get("targets") or []
    if not targets:
        err("targets is empty — without a target there is nothing to reproduce")
    for t in targets:
        if "quantity" not in t or "value" not in t:
            err("targets entry needs at least quantity and value: %r" % (t,))

    if not spec.get("assumptions"):
        warn("assumptions is empty — every spec has some; if truly none, write 'none'")

    errors = [m for lvl, m in issues if lvl == "ERROR"]
    warns = [m for lvl, m in issues if lvl == "WARN"]
    for lvl, msg in issues:
        print("[%s] %s" % (lvl, msg))
    print("\n%d error(s), %d warning(s)" % (len(errors), len(warns)))
    if not issues:
        print("spec is structurally valid")
    return 1 if errors or (args.strict and warns) else 0


if __name__ == "__main__":
    raise SystemExit(main())
