"""Spec -> Lumerical FDTD model builder (single implementation).

Extracted from ``run_fdtd_sweep.py`` on 2026-11-09 (EXP-38) so that
``fdtd-lumerical-fsp-build`` can build a ``.fsp`` without running it, while
``run_fdtd_sweep.py`` keeps importing the *same* code instead of carrying a copy.

Owners:
  * build_materials / resolve_material   material database entries
  * build_objects                        geometry + stack extent along the propagation axis
  * resolve_axes / check_monitor_gap / build_simulation
                                         FDTD region, BCs, source, monitors

Nothing here touches the session lifecycle: the caller owns ``lumapi.FDTD()``.

Axis model (EXP-46): a 3D model propagates along z with x/y transverse; a 2D model is
invariant along z and propagates inside the x-y plane (default y).  ``resolve_axes`` is the
only place that decides this, and every geometry/BC/source/monitor placement asks it.
"""
from __future__ import annotations

import re
import sys

import numpy as np

C0 = 299792458.0
PHYS_TOL = 1e-3          # R/T 的数值噪声容差（不是物理判据）
# 为什么不是 1e-6：不透明堆栈本应 T≡0，但 FDTD 的 DFT 通量在 0 附近有 ~1e-5 的噪声。
# 三个独立运行实测 T_at_peak = -1.4e-05 / -2.1e-05 / -2.2e-05（EXP-26 与 2026-11-03 的历史产物），
# 1e-6 容差会把一次完全正常的 P01 运行判成「监视器压进 PML」。真正的越界（P07: T=-0.80, A=1.60）
# 比噪声大 4 个数量级，1e-3 仍能拦住。
MIN_MONITOR_GAP = 0.3e-6  # 监视器到 PML 的最小间距（SKILL.md 一直这么写，但代码从没校验）

_AXES = ("x", "y", "z")
_VEC_INDEX = {a: i for i, a in enumerate(_AXES)}

_EXPR_OK = re.compile(r"[0-9a-zA-Z_.+\-*/() ]+")


# ----------------------------------------------------------------------------- helpers
def ev(expr, params):
    """Evaluate a spec expression against the parameter table.

    Parameter values may be numbers or numeric strings — a hand-written spec often
    quotes them (`"d": "4.7e-6"`), and `d/2` must still work instead of raising
    `TypeError: unsupported operand type(s) for /: 'str' and 'int'` (EXP-46).
    """
    if isinstance(expr, (int, float)):
        return float(expr)
    if not isinstance(expr, str):
        raise TypeError("expected number or expression, got %r" % type(expr).__name__)
    if not _EXPR_OK.fullmatch(expr):
        raise ValueError("unsupported characters in expression %r" % expr)
    scope = {}
    for k, v in params.items():
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise ValueError("参数 %r 的值 %r 不是数字；参数表只能放数字或数字字符串"
                                 % (k, v)) from None
        scope[k] = v
    return float(eval(expr, {"__builtins__": {}}, scope))  # noqa: S307 - whitelisted charset


# ----------------------------------------------------------------------------- axes
def resolve_axes(sim):
    """Decide the propagation axis and what that leaves transverse.

    Returns ``(dimension, propagation_axis, lateral_axes, invariant_axis)``.

    Lumerical's 2D solver is invariant along **z** (it meshes the x-y plane only), so
    ``z min bc`` / ``z max bc`` exist but are *inactive* — writing them raises
    ``LumApiError: ... 'z min bc' is inactive`` (D-008).  Hence z may be neither the
    propagation axis nor a boundary in a 2D model, and the invariant axis is dropped from
    every span/position list.
    """
    dim = str(sim.get("dimension", "3D")).strip().upper()
    if dim not in ("2D", "3D"):
        raise ValueError("dimension 只支持 '2D' / '3D'，收到 %r" % (sim.get("dimension"),))
    default_p = "y" if dim == "2D" else "z"
    p = str(sim.get("propagation_axis", default_p)).strip().lower()
    if p not in _AXES:
        raise ValueError("propagation_axis 只支持 x/y/z，收到 %r" % (sim.get("propagation_axis"),))
    if dim == "2D" and p == "z":
        raise ValueError(
            "2D 仿真的 z 是不变轴（引擎只在 x-y 面内网格化），propagation_axis 不能取 z。\n"
            "  请改 propagation_axis='y'（或 'x'），并把堆栈沿该轴排布。")
    invariant = "z" if dim == "2D" else None
    lateral = [a for a in _AXES if a != p and a != invariant]
    return dim, p, lateral, invariant


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
            f.setmaterial(name, "sampled data",
                          np.column_stack([C0 / lam, (n + 1j * k) ** 2]))
        elif kind == "conductive_3d":
            # P09: the paper states Au as a bulk conductivity (σ = 4e7 S/m), not a Drude fit.
            t = f.addmaterial("Conductive 3D")
            f.setmaterial(t, "name", name)
            f.setmaterial(name, "conductivity", float(m["conductivity"]))
        elif kind == "graphene_kubo_1nm":
            lam = np.linspace(float(m["wavelength_start_um"]),
                              float(m["wavelength_stop_um"]),
                              int(m.get("points", 200))) * 1e-6
            freq = C0 / lam
            eps = graphene_eps(freq, float(m["mu_c_ev"]), float(m["gamma_ev"]),
                               float(m.get("thickness_nm", 1.0)) * 1e-9,
                               float(m.get("temp_k", 300.0)))
            t = f.addmaterial("Sampled data")
            f.setmaterial(t, "name", name)
            f.setmaterial(name, "max coefficients", 6)
            f.setmaterial(name, "sampled data", np.column_stack([freq, eps]))
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


# ----------------------------------------------------------------------------- graphene
# 1 nm box is the project's only graphene path (D-2, 2026-11-09): the paper does the same and it
# keeps a single spec shape.  ε(ω) = 1 + iσ(ω)/(ε0 ω Δ).
E_CHARGE = 1.602176634e-19
H_BAR = 1.054571817e-34
K_B = 1.380649e-23
EPS0 = 8.8541878128e-12


def kubo_sigma(freq_hz, mu_c_ev: float, gamma_ev: float, temp_k: float = 300.0):
    """Sheet conductivity of graphene (S), Kubo in the Falkovsky/Alaee form.

    Two terms, both kept: interband matters above ~2|µc|/ħ (the P09 paper's 2nd mode lives there).
    ``gamma_ev`` is the scattering RATE as an energy (2Γ in the paper's notation); passing
    Γ_energy/ħ instead halves it and shifts every peak.
    """
    w = 2.0 * np.pi * np.asarray(freq_hz, dtype=float)
    mu = mu_c_ev * E_CHARGE
    gam = gamma_ev * E_CHARGE
    kt = K_B * temp_k
    intra = 1j * E_CHARGE ** 2 * kt / (np.pi * H_BAR ** 2 * (w + 1j * gam)) * (
        mu / kt + 2.0 * np.log(1.0 + np.exp(-mu / kt)))
    inter = 1j * E_CHARGE ** 2 / (4.0 * np.pi * H_BAR) * np.log(
        (2.0 * abs(mu) - (w + 1j * gam) * H_BAR) / (2.0 * abs(mu) + (w + 1j * gam) * H_BAR))
    return intra + inter


def graphene_nk(freq_hz, mu_c_ev: float, gamma_ev: float,
                thickness_m: float = 1e-9, temp_k: float = 300.0):
    """Effective (n, k) of a ``thickness_m`` slab carrying the sheet conductivity."""
    eps = graphene_eps(freq_hz, mu_c_ev, gamma_ev, thickness_m, temp_k)
    n = np.sqrt(eps.astype(complex))
    return n.real, n.imag


def graphene_eps(freq_hz, mu_c_ev: float, gamma_ev: float,
                 thickness_m: float = 1e-9, temp_k: float = 300.0):
    """Effective permittivity of a ``thickness_m`` slab carrying the sheet conductivity.

    This is the quantity Lumerical's ``Sampled data`` material actually consumes (D-013):
    the ``sampled data`` property is ε(f), not (n, k) — feeding n+ik makes the engine take
    sqrt() of it again, which for graphene (n≈0, k≈51) turned ε≈2611i into 51i, i.e. a
    51x too weak absorber.
    """
    w = 2.0 * np.pi * np.asarray(freq_hz, dtype=float)
    return 1.0 + 1j * kubo_sigma(freq_hz, mu_c_ev, gamma_ev, temp_k) / (EPS0 * w * thickness_m)


# ----------------------------------------------------------------------------- array
# Per-cell parameter arrays (EXP-60).  A metasurface is "one template, N cells, each with its
# own geometry"; the single global `parameters` table cannot express that, because every cell
# would evaluate `d1/2` against the same `d1`.
#
# The fix is *not* a new evaluator: `ev()` already turns a string expression into a float, so
# an array cell only needs a wider scope —
#     global params  ⊕  {"i": row, "j": col}  ⊕  cell_params[row-major index]
# The scope is built per cell and thrown away; nothing leaks into the global table, so a spec
# without an `array` object evaluates exactly as before (EXP-62 regression).
_ARRAY_ENGINES = ("objects",)
# Above this many cells a flat list of objects stops being a sane .fsp (65k objects is minutes of
# lumapi calls and an unopenable file).  The real answer is a structure group whose script loops
# in the engine; that engine is NOT implemented yet (PLAN-2026-11-11-percell-fsp §10-1), so the
# limit is reported as a warning that names the missing engine rather than silently degrading.
_MAX_CELLS_OBJECTS = 2000
# 硬拒绝线（EXP-64）：警告线之上的规模仍然可建（64x64=4096 是本技能存在的理由），
# 但再大一个数量级就是"跑到一半内存爆掉"的领域——宁可建不出来，也不建出半成品 .fsp。
_HARD_LIMIT_CELLS = 8192

# Object types allowed as an array element template.  `group` and `array` are excluded on
# purpose: a nested group cannot carry the per-cell scope, and a nested array has no meaning
# (its own cell_params would be indexed by the outer cell — ambiguity nobody needs).
_ARRAY_ELEMENT_TYPES = ("box", "cylinder", "ellipse", "ring", "polygon", "2drect")


def array_scope(params, i, j, cell):
    """Global params ⊕ cell indices ⊕ per-cell overrides (later wins)."""
    scope = dict(params or {})
    scope["i"] = float(i)
    scope["j"] = float(j)
    for k, v in (cell or {}).items():
        if k in ("i", "j"):
            continue
        scope[k] = v
    return scope


def _cell_name(oid, i, j):
    return "%s_r%dc%d" % (oid, i, j)


def array_cells(arr, params):
    """Expand an ``array`` object into ``[(i, j, scope), ...]`` in row-major order.

    Pure function: no lumapi, no I/O.  Self-tests and ``--check`` both call it, so the object
    names and the parameters that ``--check`` asserts on come from the *same* expansion the
    builder used — the alternative (re-deriving them in the checker) is how a checker ends up
    green on a wrong build.
    """
    grid = arr.get("grid") or {}
    nx, ny = int(grid.get("nx", 0)), int(grid.get("ny", 0))
    if nx <= 0 or ny <= 0:
        raise ValueError("array %r 的 grid.nx / grid.ny 必须是正整数，收到 %r / %r"
                         % (arr.get("id"), nx, ny))
    n = nx * ny
    cells = arr.get("cell_params")
    if not cells:                          # [] 或 None = 所有格子共用全局参数
        cells = [None] * n
    if not isinstance(cells, list):
        raise ValueError("array %r 的 cell_params 必须是列表，收到 %s"
                         % (arr.get("id"), type(cells).__name__))
    if len(cells) != n:
        raise ValueError(
            "array %r: cell_params 有 %d 条，但 grid.nx*ny = %d*%d = %d。\n"
            "  少写会静默错位（第 k 条对应哪个格子就没人知道了），所以这里直接拒绝。\n"
            "  只想全部用同一组参数时，把 cell_params 写成 [] 或省略，不要写半张表。"
            % (arr.get("id"), len(cells), nx, ny, n))
    out = []
    for idx in range(n):
        i, j = divmod(idx, nx)          # 行主序：先走完一行（j 变化），再换行
        cell = cells[idx]
        if cell is not None and not isinstance(cell, dict):
            raise ValueError("array %r: cell_params[%d] 必须是对象，收到 %r"
                             % (arr.get("id"), idx, type(cell).__name__))
        # 显式写出的 i/j 必须与位置一致；写反了说明导出端和装配端对行主序的理解不同，
        # 这种错静默建出来就是一片错位的超表面。
        if cell:
            for key, want in (("i", i), ("j", j)):
                if key in cell and int(float(cell[key])) != want:
                    raise ValueError(
                        "array %r: cell_params[%d] 写着 %s=%r，但按行主序它应是 %s=%d。\n"
                        "  位置与标注不一致，先统一行主序再建。" % (arr.get("id"), idx, key, cell[key], key, want))
        out.append((i, j, array_scope(params, i, j, cell)))
    return out


def array_element_center(arr, i, j, scope):
    """Absolute element centre for cell (i, j) after applying pitch / origin."""
    grid = arr["grid"]
    pitch = grid.get("pitch")
    if not pitch:
        raise ValueError("array %r 缺少 grid.pitch（两轴间距）" % arr.get("id"))
    if len(pitch) != 2:
        raise ValueError("array %r 的 grid.pitch 需要 2 个值（x, y），收到 %d"
                         % (arr.get("id"), len(pitch)))
    px, py = ev(pitch[0], scope), ev(pitch[1], scope)
    origin = grid.get("origin") or ["0", "0"]
    if len(origin) != 2:
        raise ValueError("array %r 的 grid.origin 需要 2 个值（x, y），收到 %d"
                         % (arr.get("id"), len(origin)))
    ox, oy = ev(origin[0], scope), ev(origin[1], scope)
    return ox + j * px, oy + i * py


def array_plan(arr, params):
    """Cheap, engine-free summary — used by ``--dry-run`` and by the assembly skill."""
    cells = array_cells(arr, params)
    nx, ny = int(arr["grid"]["nx"]), int(arr["grid"]["ny"])
    sc0 = cells[0][2] if cells else dict(params or {})
    px = ev(arr["grid"]["pitch"][0], sc0)
    py = ev(arr["grid"]["pitch"][1], sc0)
    return {
        "id": arr.get("id"), "nx": nx, "ny": ny, "cells": nx * ny,
        "pitch_um": [px * 1e6, py * 1e6],
        "over_objects_limit": nx * ny > _MAX_CELLS_OBJECTS,
        "objects_limit": _MAX_CELLS_OBJECTS,
    }


# ----------------------------------------------------------------------------- geometry
def object_extent(o, params, p):
    """Propagation-axis extent of one object WITHOUT touching a session.

    Derived from the same reading of the spec that :func:`build_one` performs.  It exists so
    ``--dry-run`` and the array path can compute the stack range without lumapi, and so the
    extent logic is written once instead of twice.

    Raises ``ValueError`` for object types whose extent is not analytic (``group`` — its
    children live in the engine-side script).
    """
    typ = o["type"]
    if typ == "box":
        c = ev(o["center"][_VEC_INDEX[p]], params)
        s = ev(o["span"][_VEC_INDEX[p]], params)
        return c - s / 2, c + s / 2
    if typ == "polygon":
        verts = np.array([[ev(v, params) for v in pair] for pair in o["vertices"]], dtype=float)
        z, zs = ev(o["z"], params), ev(o["z_span"], params)
        bounds = {"x": (verts[:, 0].min(), verts[:, 0].max()),
                  "y": (verts[:, 1].min(), verts[:, 1].max()),
                  "z": (z - zs / 2, z + zs / 2)}
        return bounds[p]
    if typ == "cylinder":
        c = ev(o["center"][_VEC_INDEX[p]], params)
        r, h = ev(o["radius"], params), ev(o["height"], params)
        return (c - r - h / 2, c + r + h / 2) if p == "z" else (c - r, c + r)
    if typ == "sphere":
        c, r = ev(o["center"][_VEC_INDEX[p]], params), ev(o["radius"], params)
        return c - r, c + r
    if typ == "ellipse":
        verts = np.array([[ev(v, params) for v in pair] for pair in o["vertices"]], dtype=float)
        cz, h = ev(o["z"], params), ev(o["z_span"], params)
        bounds = {"x": (verts[:, 0].min(), verts[:, 0].max()),
                  "y": (verts[:, 1].min(), verts[:, 1].max()),
                  "z": (cz - h / 2, cz + h / 2)}
        return bounds[p]
    if typ == "ring":
        c = ev(o["center"][_VEC_INDEX[p]], params)
        r, h = ev(o["radius"], params), ev(o["height"], params)
        return (c - r - h / 2, c + r + h / 2) if p == "z" else (c - r, c + r)
    if typ == "group":
        return _NO_EXTENT
    raise ValueError("unsupported object type: %s" % typ)


_NO_EXTENT = None        # sentinel: object owns no volume / its extent is not analytic

# ----------------------------------------------------------------------------- geometry
def build_objects(f, spec, params, axes=None):
    """Create every object; return the stack extent along the propagation axis.

    ``axes`` is the tuple from :func:`resolve_axes` — pass it so a 2D model measures the
    stack along its own propagation axis (D-008: the old code hardcoded z and therefore
    could not express a stack that runs along y).
    """
    dim, p, _lateral, invariant = axes or resolve_axes({"dimension": "3D"})
    lo, hi = [], []                       # 沿传播轴的范围
    for o in spec["objects"]:
        if o.get("type") == "array":
            a_lo, a_hi = build_array(f, o, spec, params, p, invariant)
            if a_lo is not None:
                lo.append(a_lo)
                hi.append(a_hi)
            continue
        ext = build_one(f, o, spec, params, p, invariant)
        if ext is _NO_EXTENT:
            continue                      # 2drect / group：不占体积，不参与堆栈
        lo.append(ext[0])
        hi.append(ext[1])

    if not lo:
        raise ValueError("spec 里没有任何有体积的对象，无法确定堆栈范围")
    return min(lo), max(hi)


def build_array(f, arr, spec, params, p, invariant):
    """Create every cell of an ``array`` object; return the propagation-axis extent.

    Object names are ``{id}_r{i}c{j}`` (row-major), which is what the assembly skill's
    ``cell_params`` order refers to.  The extent is the union over cells — a metasurface
    occupies the same slab as one cell, but its lateral span is what sets the region size, and
    that comes from ``lattice``/``simulation`` as usual.
    """
    engine = str(arr.get("engine", "objects")).lower()
    if engine not in _ARRAY_ENGINES:
        raise ValueError(
            "array %r: engine=%r 未实现，本版只支持 %s。\n"
            "  大阵列（>%d 格）的引擎侧脚本引擎在 PLAN-2026-11-11-percell-fsp §10-1 里被推迟，"
            "先在装配端降规模（--target-nx/--target-ny + --mode crop）。"
            % (arr.get("id"), engine, "/".join(_ARRAY_ENGINES), _MAX_CELLS_OBJECTS))
    tpl = arr.get("element")
    if not isinstance(tpl, dict) or not tpl.get("type"):
        raise ValueError("array %r 缺少 element（模板对象，需带 type）" % arr.get("id"))
    etype = tpl["type"]
    if etype not in _ARRAY_ELEMENT_TYPES:
        raise ValueError("array %r: element.type=%r 不支持；可用 %s"
                         % (arr.get("id"), etype, "/".join(_ARRAY_ELEMENT_TYPES)))
    cells = array_cells(arr, params)
    if len(cells) > _HARD_LIMIT_CELLS:
        raise ValueError(
            "array %r: %d 格超过 objects 引擎的硬上限 %d。\n"
            "  这不是警告：65536 格的对象列表会把 lumapi 调用拖到小时级并产出无法打开的 .fsp。\n"
            "  大阵列需要脚本引擎（group_script，PLAN-2026-11-11-percell-fsp §10-1 推迟），"
            "装配端请先降规模（--target-nx/--target-ny + --mode crop）。"
            % (arr.get("id"), len(cells), _HARD_LIMIT_CELLS))
    if len(cells) > _MAX_CELLS_OBJECTS:
        # 不是拒绝：64x64=4096 是它存在的理由。但必须把缺口说出来，而不是让人以为这是常规规模。
        print("WARNING array %r: %d 格 > objects 引擎建议上限 %d —— 建得出来但 .fsp 会很大；"
              "脚本引擎（group_script）尚未实现（PLAN §10-1）"
              % (arr.get("id"), len(cells), _MAX_CELLS_OBJECTS), file=sys.stderr)

    lo, hi = [], []
    for i, j, scope in cells:
        cdx, cdy = array_element_center(arr, i, j, scope)
        # 模板写的是「相对单元中心」的偏移；这里把格子位置烘进绝对坐标。
        inst = dict(tpl)
        if etype != "polygon":
            base = tpl.get("center") or ["0", "0", "0"]
            if len(base) != 3:
                raise ValueError("array %r: element.center 需要 3 个值，收到 %d"
                                 % (arr.get("id"), len(base)))
            bx, by, bz = [ev(v, scope) for v in base]
            inst["center"] = [bx + cdx, by + cdy, bz]
        else:
            inst["z"] = tpl.get("z", "0")            # 表达式原样保留，交给 build_one 求值
            inst["z_span"] = tpl.get("z_span", "0")
            # 多边形顶点整体平移到格子位置（与 ellipse 的 center 烘焙同一思路）
            inst["vertices"] = [[ev(v, scope) + (cdx if k == 0 else cdy)
                                 for k, v in enumerate(pair)] for pair in tpl["vertices"]]
        inst["id"] = _cell_name(arr["id"], i, j)
        inst["type"] = etype
        if arr.get("material"):
            inst.setdefault("material", arr["material"])
        if arr.get("mesh_order") is not None:
            inst.setdefault("mesh_order", arr["mesh_order"])
        ext = build_one(f, inst, spec, scope, p, invariant)
        if ext is _NO_EXTENT:
            continue
        lo.append(ext[0])
        hi.append(ext[1])
    if not lo:
        return None, None
    return min(lo), max(hi)


def _num(v):
    """Keep numbers as floats; ``ev`` already returned a float, this is just for readability."""
    return float(v)


def build_one(f, o, spec, params, p, invariant):
    """Create ONE object from a spec dict; return its propagation-axis extent.

    Returns ``_NO_EXTENT`` for zero-volume objects (``2drect``) and for ``group`` (whose
    children exist only in the engine-side script).   The per-type bodies are the ones that
    were inline in :func:`build_objects` before the ``array`` type was added; splitting them
    out is what lets an array instance the exact same code path instead of a parallel copy.
    """
    oid, typ = o["id"], o["type"]
    mat = o.get("material")
    ext = _NO_EXTENT

    if typ == "box":
        cx, cy, cz = [ev(v, params) for v in o["center"]]
        sx, sy, sz = [ev(v, params) for v in o["span"]]
        f.addrect(name=oid, x=cx, y=cy, z=cz, x_span=sx, y_span=sy, z_span=sz)
        c, s = (cx, cy, cz)[_VEC_INDEX[p]], (sx, sy, sz)[_VEC_INDEX[p]]
        ext = (c - s / 2, c + s / 2)

    elif typ == "polygon":
        verts = np.array([[ev(v, params) for v in pair] for pair in o["vertices"]], dtype=float)
        verts = np.vstack([verts, verts[0]])
        z, zs = ev(o["z"], params), ev(o["z_span"], params)
        f.addpoly(name=oid)
        f.setnamed(oid, "vertices", verts)
        f.setnamed(oid, "z", z)
        f.setnamed(oid, "z span", zs)
        # 多边形在 x-y 平面内，z 方向是挤出长度；按 p 取对应的一个包围盒面
        bounds = {"x": (verts[:, 0].min(), verts[:, 0].max()),
                  "y": (verts[:, 1].min(), verts[:, 1].max()),
                  "z": (z - zs / 2, z + zs / 2)}
        ext = bounds[p]

    elif typ == "cylinder":
        cx, cy, cz = [ev(v, params) for v in o["center"]]
        r, h = ev(o["radius"], params), ev(o["height"], params)
        f.addcircle(name=oid, x=cx, y=cy, z=cz, radius=r, z_span=h)
        ext = ((cx - r, cy - r, cz - h / 2)[_VEC_INDEX[p]],
               (cx + r, cy + r, cz + h / 2)[_VEC_INDEX[p]])

    elif typ == "sphere":
        cx, cy, cz = [ev(v, params) for v in o["center"]]
        r = ev(o["radius"], params)
        f.addsphere(name=oid, x=cx, y=cy, z=cz, radius=r)
        ext = ((cx - r, cy - r, cz - r)[_VEC_INDEX[p]],
               (cx + r, cy + r, cz + r)[_VEC_INDEX[p]])

    elif typ == "ellipse":
        # Elliptical pillar: a polygon with an analytic vertex list. `axes` are FULL diameters,
        # matching how papers quote "a = 285 nm, b = 450 nm" for an elliptical cross-section.
        cx, cy, cz = [ev(v, params) for v in o["center"]]
        ax, ay = ev(o["axes"][0], params), ev(o["axes"][1], params)
        h = ev(o["height"], params)
        n = int(o.get("n_vertices", 48))
        # EXP-64：per-cell 阵列里 rotation_deg 是逐格表达式（"rot"），必须走 ev()；
        # 数字输入 ev() 原样返回，所以普通 spec 行为不变。
        rot = np.deg2rad(ev(o.get("rotation_deg", 0), params))
        th = np.linspace(0, 2 * np.pi, n, endpoint=False)
        u, v = (ax / 2) * np.cos(th), (ay / 2) * np.sin(th)
        verts = np.column_stack([u * np.cos(rot) - v * np.sin(rot),
                                 u * np.sin(rot) + v * np.cos(rot)])
        # `center` 的 x/y 以前被静默丢弃（多边形建在原点）。这里把偏移烘进顶点：
        # 不依赖 "x"/"y" 属性是否可写，且 P02 的 center=(0,0) 结果不变。
        verts = verts + np.array([cx, cy])
        verts = np.vstack([verts, verts[0]])
        f.addpoly(name=oid)
        f.setnamed(oid, "vertices", verts)
        f.setnamed(oid, "z", cz)
        f.setnamed(oid, "z span", h)
        bounds = {"x": (verts[:, 0].min(), verts[:, 0].max()),
                  "y": (verts[:, 1].min(), verts[:, 1].max()),
                  "z": (cz - h / 2, cz + h / 2)}
        ext = bounds[p]

    elif typ == "ring":
        cx, cy, cz = [ev(v, params) for v in o["center"]]
        r, ri, h = ev(o["radius"], params), ev(o["inner_radius"], params), ev(o["height"], params)
        f.addring(name=oid, x=cx, y=cy, z=cz,
                  inner_radius=ri, outer_radius=r, z_span=h)
        ext = ((cx - r, cy - r, cz - h / 2)[_VEC_INDEX[p]],
               (cx + r, cy + r, cz + h / 2)[_VEC_INDEX[p]])

    elif typ == "2drect":
        # Zero-thickness sheet (graphene, metasurface boundary).  It owns no volume, so it
        # must not shift the stack extent.  Spans go on the two axes perpendicular to the
        # surface normal, in axis order: normal z -> (x, y), normal y -> (x, z).
        cx, cy, cz = [ev(v, params) for v in o["center"]]
        normal = str(o.get("surface_normal") or p).lower()
        if normal not in _AXES:
            raise ValueError("对象 %s 的 surface_normal 只支持 x/y/z，收到 %r" % (oid, normal))
        if invariant and normal == invariant:
            raise ValueError(
                "对象 %s 是 %s 法向的 2D 面，但 2D 仿真里 %s 是不变轴 —— 这张面在结果里"
                "不存在。\n  请把它改成 %s 法向（与传播轴同向），或改用 1 nm box（D-2）。"
                % (oid, normal, normal, p))
        spans = [ev(v, params) for v in o["span"]]
        plane_axes = [a for a in _AXES if a != normal]
        if len(spans) != len(plane_axes):
            raise ValueError("对象 %s（2drect）需要 %d 个 span（%s），收到 %d 个"
                             % (oid, len(plane_axes), "/".join(plane_axes), len(spans)))
        f.add2drect(name=oid)
        for k, v in (("x", cx), ("y", cy), ("z", cz)):
            f.setnamed(oid, k, v)
        for a, v in zip(plane_axes, spans):
            f.setnamed(oid, "%s span" % a, v)
        if o.get("surface_normal"):
            f.setnamed(oid, "surface normal", normal)

    elif typ == "group":
        f.addgroup(name=oid)
        f.setnamed(oid, "name", oid)
        if o.get("script"):
            # The geometry truth sometimes lives in the group script (P06: eight octants,
            # one V-antenna each).  Store it verbatim so introspection can read it back.
            f.setnamed(oid, "script", o["script"])

    else:
        raise ValueError("unsupported object type: %s" % typ)

    if mat:
        try:
            f.setnamed(oid, "material", resolve_material(spec, mat))
        except Exception as exc:                  # noqa: BLE001
            raise ValueError(
                "对象 %s（type=%s）不接受材料 %r：%s\n"
                "  2D 面对象只支持 RLC / PEC / 2D 材料表；石墨烯请用 thickness_nm=1 的 box（D-2）。"
                % (oid, typ, mat, str(exc).splitlines()[0])) from exc
        f.setnamed(oid, "override mesh order from material database", 1)
        f.setnamed(oid, "mesh order", o.get("mesh_order", 1))

    return ext



def check_monitor_gap(sim: dict) -> None:
    """监视器到 PML 的最小间距校验（纯函数，可脱机单测）。

    P07 事件：``below_structure=0.15 µm`` 时 R 监视器压进 PML，输出 ``T=-0.80 / A=1.60``，
    而三条收敛判据全过 —— 数值越界是唯一能拦住的信号，所以必须在建模阶段就拒绝。
    """
    gap = float(sim.get("min_monitor_gap", MIN_MONITOR_GAP))
    for key, default in (("air_above", 2.5e-6), ("below_structure", 1.0e-6)):
        val = float(sim.get(key, default))
        if val < gap:
            raise ValueError(
                "%s=%.3f um < 监视器-PML 最小间距 %.3f um：监视器会落进 PML，"
                "getresult 返回全空或非物理值" % (key, val * 1e6, gap * 1e6))


def build_simulation(f, spec, params, p_bottom, p_top, axes=None):
    """Build the FDTD region, BCs, source and monitors.

    ``p_bottom`` / ``p_top`` are the stack extent **along the propagation axis** (returned by
    :func:`build_objects`).  Everything that used to be spelled "z" is now spelled "the
    propagation axis": a 2D model puts the stack along y, and z never receives a boundary
    condition because it is the invariant axis.
    """
    sim = spec["simulation"]
    lat = spec["lattice"]
    dim, p, lateral, invariant = axes or resolve_axes(sim)
    span = {"x": ev(lat["period_x"], params), "y": ev(lat["period_y"], params)}
    sup = lat.get("supercell") or {}
    span["x"] *= int(sup.get("nx", 1))
    span["y"] *= int(sup.get("ny", 1))

    air = float(sim.get("air_above", 2.5e-6))
    below = float(sim.get("below_structure", 1.0e-6))
    check_monitor_gap(sim)
    p_max, p_min = p_top + air, p_bottom - below

    # --- region: lateral axes get the lattice span, the propagation axis gets the stack+air
    region = {"dimension": dim, p: (p_max + p_min) / 2, "%s_span" % p: p_max - p_min}
    for a in lateral:
        region[a] = 0.0
        region["%s_span" % a] = span[a]
    f.addfdtd(**region)

    bc = sim["bc"]
    for a in lateral:                     # 不变轴（2D 的 z）没有可写的边界
        f.setnamed("FDTD", "%s min bc" % a, bc[a])
        f.setnamed("FDTD", "%s max bc" % a, bc[a])
    f.setnamed("FDTD", "mesh accuracy", sim.get("mesh_accuracy", 4))
    f.setnamed("FDTD", "auto shutoff min", sim.get("auto_shutoff", 1e-4))
    if sim.get("simulation_time"):
        f.setnamed("FDTD", "simulation time", sim["simulation_time"])

    mo = sim.get("mesh_override")
    if mo:
        rng = mo.get("%s_range" % p) or mo.get("z_range")
        if rng:
            m0, m1 = ev(rng[0], params), ev(rng[1], params)
        else:
            m0, m1 = p_bottom, p_top
        mesh = {"name": "mesh_fine", p: (m0 + m1) / 2, "%s_span" % p: abs(m1 - m0)}
        for a in lateral:
            mesh[a] = 0.0
            mesh["%s_span" % a] = span[a]
        f.addmesh(**mesh)
        for k in ("dx", "dy", "dz"):
            if mo.get(k):
                f.setnamed("mesh_fine", k, mo[k])

    src = sim["source"]
    mode = sim.get("mode", "reflection")
    if mode == "transmission":
        # light enters through the substrate (bottom) and is collected in air (top)
        p_src = p_bottom - 0.60 * below
        p_R = p_bottom - 0.85 * below      # below the source: only the reflected wave crosses it
        p_T = p_top + 0.60 * air
        default_dir = "Forward"
    else:
        # light enters from above (air) and reflects off the stack
        p_src = p_top + 0.60 * air
        p_R = p_top + 0.85 * air
        p_T = p_bottom - 0.60 * below
        default_dir = "Backward"

    stype = str(src.get("type", "plane")).lower()
    if stype in ("plane", "plane_wave", "planewave"):
        stype = "plane"                     # 旧 spec 写的是 plane_wave，保持兼容
    elif stype not in ("gaussian", "mode"):
        raise ValueError("unsupported source.type: %r（可用 plane / gaussian / mode）" % stype)

    # 频率/波长口径先统一算出来；plane 分支仍按原来的写法落属性，保证旧的 spec 逐字节不变
    if src.get("frequency_range_thz"):
        f0, f1 = [float(v) * 1e12 for v in src["frequency_range_thz"]]
        f_lo, f_hi = min(f0, f1), max(f0, f1)
        lam_lo, lam_hi = C0 / f_hi, C0 / f_lo
    else:
        lam_lo, lam_hi = src["wavelength_range"]
        f_lo, f_hi = C0 / lam_hi, C0 / lam_lo

    if stype == "plane":
        f.addplane(name="source")
        src_props = [("injection axis", p), ("direction", src.get("direction", default_dir)),
                     (p, p_src), ("polarization angle", ev(src.get("polarization_deg", 0), params)),
                     ("amplitude", 1), ("override global source settings", 1)]
        for a in lateral:
            src_props += [(a, 0), ("%s span" % a, span[a])]
        if src.get("plane_wave_type"):
            # Only when the spec asks: 3D runs with periodic BCs have always used the default.
            src_props.append(("plane wave type", src["plane_wave_type"]))
        if src.get("frequency_range_thz"):
            # THz papers quote frequency.  Setting `frequency` directly is inactive on PlaneSource
            # (EXP-28), so the supported route is frequency start/stop, in Hz.
            src_props += [("frequency start", f_lo), ("frequency stop", f_hi)]
        else:
            src_props += [("wavelength start", lam_lo), ("wavelength stop", lam_hi)]
    elif stype == "gaussian":
        g = src.get("gaussian") or {}
        f.addgaussian(name="source")
        src_props = [
            ("injection axis", p), ("direction", src.get("direction", default_dir)),
            (p, p_src), ("amplitude", 1), ("override global source settings", 1),
            ("polarization angle", ev(src.get("polarization_deg", 0), params)),
            # 用 "waist radius w0"：默认 beam parameters='Waist size and position' 时
            # "beam radius wz" 是只读的（inactive），直接写会抛 LumApiError。
            ("waist radius w0", ev(g.get("waist_radius_um", 5.0), params) * 1e-6),
            ("distance from waist",
             ev(g.get("distance_from_waist_um", 0.0), params) * 1e-6),
            ("wavelength start", lam_lo), ("wavelength stop", lam_hi),
        ]
        for a in lateral:
            src_props += [(a, 0), ("%s span" % a, span[a])]
        if g.get("lens_diameter_um"):
            src_props.append(("lens diameter",
                              ev(g["lens_diameter_um"], params) * 1e-6))
        if g.get("fill_lens"):
            src_props.append(("fill lens", 1))
    else:                                   # mode
        m = src.get("mode") or {}
        f.addmode(name="source")
        src_props = [
            ("injection axis", p), ("direction", src.get("direction", default_dir)),
            (p, p_src),
            ("mode selection", m.get("mode_selection", "fundamental TE")),
            ("number of trial modes", int(m.get("n_trial_modes", 1))),
            ("frequency start", f_lo), ("frequency stop", f_hi),
        ]

    for k, v in src_props:
        f.setnamed("source", k, v)

    npts = src.get("npts", 101)
    lam0 = (lam_lo + lam_hi) / 2.0
    # Monitor list: two shapes are in the wild — the historical dict
    # {"R": {"z": "auto"}, "T": {...}} (P01) and an explicit list with `kind` (new specs).
    raw_mons = sim.get("monitors")
    if not raw_mons:
        monitors = [{"name": "R"}, {"name": "T"}]
    elif isinstance(raw_mons, dict):
        monitors = []
        for nm, spec_m in raw_mons.items():
            entry = {"name": nm}
            if isinstance(spec_m, dict):
                entry.update(spec_m)
            monitors.append(entry)
    else:
        monitors = [dict(m) for m in raw_mons]

    made = []
    for mon in monitors:
        nm = str(mon["name"])
        kind = str(mon.get("kind", "power")).lower()
        pos_raw = mon.get(p, mon.get("z", "auto"))
        if pos_raw in (None, "auto"):
            pos = p_R if nm.upper().startswith("R") else p_T
        else:
            pos = float(ev(pos_raw, params))

        # 2D quirk (measured, EXP-46): a power monitor in a 2D cell is a LINE normal to the
        # propagation axis — give it the transverse span only and let the engine name it
        # ("Linear X"), which is exactly what the hand-built P09 project has.  A field/index
        # monitor stays an x-y AREA ("2D Z-normal"), i.e. both in-plane spans.
        if dim == "2D" and kind == "power":
            span_axes = lateral
        elif dim == "2D":
            span_axes = [a for a in _AXES if a != invariant]
        else:
            span_axes = lateral

        explicit = mon.get("span") or {}

        def _span_for(a):
            if a in explicit:
                return float(ev(explicit[a], params))
            inline = mon.get("%s_span" % a)
            if inline is not None:
                return float(ev(inline, params))
            return (p_max - p_min) if a == p else span[a]

        where = {a: 0.0 for a in span_axes}
        where[p] = pos
        for a in span_axes:
            where["%s_span" % a] = _span_for(a)
        mon_type = mon.get("monitor_type") or ("2D %s-normal" % p.upper())

        if kind == "power":
            f.addpower(name=nm, **where)
            if dim != "2D":
                f.setnamed(nm, "monitor type", mon_type)
            for k, v in [("override global monitor settings", 1),
                         ("use source limits", 0),
                         ("wavelength center", lam0),
                         ("wavelength span", lam_hi - lam_lo),
                         ("frequency points", npts),
                         ("use wavelength spacing", 1)]:
                f.setnamed(nm, k, v)
        elif kind == "field":
            f.addprofile(name=nm, **where)
            if dim != "2D":
                f.setnamed(nm, "monitor type", mon_type)
            for k, v in [("override global monitor settings", 1),
                         ("use source limits", 0),
                         ("wavelength center", lam0),
                         ("wavelength span", lam_hi - lam_lo),
                         ("frequency points", int(mon.get("n_freq", 1))),
                         ("use wavelength spacing", 1)]:
                f.setnamed(nm, k, v)
        elif kind == "index":
            f.addindex(name=nm, **where)
            if dim != "2D":
                f.setnamed(nm, "monitor type", mon_type)
            for k, v in [("override global monitor settings", 1),
                         ("use source limits", 0),
                         ("wavelength center", lam0),
                         ("wavelength span", lam_hi - lam_lo),
                         ("frequency points", int(mon.get("n_freq", 1))),
                         ("use wavelength spacing", 1)]:
                f.setnamed(nm, k, v)
        else:
            raise ValueError("unsupported monitor kind: %s" % kind)
        made.append({"name": nm, "kind": kind, "pos": pos, "axis": p})

    info = dict(axis=p, dimension=dim, lateral=lateral,
                pos_src=p_src, pos_R=p_R, pos_T=p_T,
                p_min=p_min, p_max=p_max, monitors=made,
                wavelength_range=[lam_lo, lam_hi])
    if p == "z":                          # 3D 老调用方（build_fsp / run_phase_sweep）的键
        info.update(z_src=p_src, z_R=p_R, z_T=p_T, z_min=p_min, z_max=p_max)
    return info

