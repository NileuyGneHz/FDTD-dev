#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""inspect_fsp.py — reverse-engineer existing Lumerical .fsp projects into JSON evidence.

Consumes : a config JSON listing .fsp paths (and optionally a reference spec_<id>.json)
Produces : manifest.json (object tree / materials / settings / layoutmode / monitors),
           spectra.json  (stored power spectra + derived metrics, or an explicit status
                          explaining WHY no usable spectrum exists),
           diff.json     (FSP layer positions & solver settings vs the reference spec),
           summary.json  (machine-readable one-screen summary, with issues[])

Paths in the config and in --out are resolved RELATIVE TO THE REPOSITORY ROOT
(the workspace directory three levels above this file), never relative to cwd.

Design notes (measured 2026-11-07/08, see references/fsp-property-map.md):
  * Monitors are DISCOVERED by ``selectall()`` + ``getAllSelectedObjects()`` and their
    ``monitor type`` property -- never by assuming names "R"/"T".
  * Power spectra are read BEFORE walking the object tree (group-scope safety).
  * Whether a project has a usable spectrum is a PROPERTY OF THE PROJECT, not a script
    failure: ``layoutmode == 1.0`` or no R/T DFT monitors means "no stored spectrum".
    That is reported as spectra_status + issues[], not swallowed into an empty errors[].
  * Absorption ``A = 1 - R - T`` is only computed when BOTH power monitors are present
    AND 0 <= A <= 1 everywhere. Otherwise derived is null with a reason. This prevents
    the P02/P03 class of bug (non-physical peak_A = 1.774 / -0.943).

CLI     : --config <json> --out <dir> [--dry-run] [--json]
Exit    : 0 = all projects inspected (including "no stored spectrum" projects);
          1 = one or more projects failed to load; 2 = usage/config error
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

# 非 UTF-8 的控制台/管道会让 `--json` 的 print 抛 UnicodeEncodeError：产物四份 JSON
# 已经落盘，进程却 exit 1，调用方把「读成功」误判成「读失败」（defects/D-010）。
# 2026-11-10 实测：本机默认 stdout 是 utf-8，只有显式 PYTHONIOENCODING=cp1252
# （或代码页为 1252 的控制台）才复现；但触发条件不在我们控制内，所以统一钉死 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:                       # noqa: BLE001 - 已被重定向的流无法 reconfigure
    pass

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
    # 2026-11-09 批次 1：
    #   phase —— 圆偏振靠两个正交 TFSF 源 ±90° 凑出来，不读 phase 就分不出 RCP/LCP
    #   script / number / period —— structure group 的真值写在脚本里，不能只报「一个 group」
    "phase", "script", "number", "period x", "period y",
]

MATERIAL_PROPS = [
    "name", "type", "Plasma resonance", "Plasma collision", "Refractive Index",
    "Imaginary Refractive Index", "Permittivity", "conductivity", "mesh order",
]

GEOM_TYPES = {"Rectangle", "Polygon", "Circle", "Sphere", "Ring", "Ellipse"}
# Monitor object types that can carry stored results. Anything else is reported as
# unsupported rather than being silently treated as a power monitor.
MONITOR_TYPES = {"DFTMonitor", "ProfileMonitor", "PointMonitor", "MovieMonitor",
                 "FarfieldMonitor", "FieldMonitor"}
# A "Point" / "2D X-normal" monitor does not produce a transmission-vs-wavelength
# power curve. Only 2D Z-normal (or equivalent) DFT monitors do.
POWER_MONITOR_HINTS = ("2d z-normal", "2d z normal", "linear z", "power")

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
    analysis = cfg.get("analysis") or {}
    if not isinstance(analysis, dict):
        raise UsageError("config.analysis must be a JSON object")
    amode = analysis.get("mode", "auto")
    if amode not in ("auto", "absorption", "transmission", "reflection"):
        raise UsageError("config.analysis.mode must be auto | absorption | transmission | reflection")
    tw = analysis.get("target_wavelength_um")
    if tw is not None and (not isinstance(tw, (int, float)) or tw <= 0):
        raise UsageError("config.analysis.target_wavelength_um must be a positive number")
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


SCRIPT_KEEP = 4000          # 脚本原文只留前 4 k 字符，另存长度与 sha256

# 非周期组子对象数 = number，展开约 number × 0.06 s；超过这个数就别在常规反解析里付。
# 周期阵列（组带 `period`）另算：子对象数 ≈ number^2 × 每胞对象数，一率跳过（EXP-47）。
GROUP_ENUM_CAP = 256


def read_obj(f, obj, full=False, depth=0, budget=None, max_depth=None, max_objects=None):
    """Read one object; bounded depth/width, duplicate-name aware, group-collapsing.

    三次实测事故（P05/P06/P07）：
      * 30x30 的 structure group 约 4500 个叶子对象，无上限递归 -> 4 工程连跑 6 min 被杀；
      * group 内 21 个**同名** rectangle，逐条记会得到 21 条 unique x=1 的假记录；
      * 涡旋的几何真值写在 ``structure group.script`` 里，只报「一个 group」等于没看见。
    """
    import hashlib

    budget = budget if budget is not None else {"n": 0}
    budget["n"] += 1
    name, typ = getattr(obj, "name", "?"), getattr(obj, "type", "?")
    if full:
        names = prop_names(f, obj, name)
        wanted = names
    else:
        # 只读 CORE_PROPS，不读整张属性表（`--full` 才读）。
        # 注意：D-007 曾把 273 s 记在这里，实测是错的——省掉属性表读取墙钟不变（273 s），
        # 真瓶颈是 `getChildren()`（见下方折叠判断处的注释与 EXP-47）。
        names = []
        wanted = CORE_PROPS
    props = {}
    for p in wanted:
        try:
            v = jsonable(f.getnamed(name, p))
        except Exception:
            try:
                v = jsonable(getattr(obj, p.replace(" ", "_")))
            except Exception:
                continue
        if p == "script" and isinstance(v, str) and len(v) > SCRIPT_KEEP:
            props["script_chars"] = len(v)
            props["script_sha256"] = hashlib.sha256(v.encode("utf-8", "replace")).hexdigest()[:16]
            props["script"] = v[:SCRIPT_KEEP]
        else:
            props[p] = v
    entry = {"name": name, "type": typ, "props": props}
    if full:
        entry["all_property_names"] = names

    # 折叠判断必须在 getChildren() **之前**（EXP-47 实测）：对 30x30 的 structure group，
    # 一次 `getChildren()` 要给 4500 个子对象各建一个 Python 包装，单次 255.8 s。
    #
    # 什么时候可以不展开（判据是实测出来的，不是猜的）：
    #   P06 的组带 `period` 属性（周期阵列，子对象数 ≈ number^2 × 每胞对象数：30 -> 4500）；
    #   P05 的组没有 `period`（手工摆的 21 个柱，子对象数 = number = 21，展开只要 1.3 s）。
    # 所以「有 period」或「number 超过上限」时跳过；其余照旧展开，同名检测照旧生效。
    is_group = "group" in typ.lower()
    if is_group:
        period = None
        try:
            period = f.getnamed(name, "period")
        except Exception:
            period = None
        declared = props.get("number")
        is_array = period is not None or "period x" in props or "period y" in props
        too_big = isinstance(declared, (int, float)) and declared > GROUP_ENUM_CAP
        if isinstance(declared, (int, float)) and (is_array or too_big):
            entry["children_collapsed"] = True
            entry["n_children_declared"] = int(declared)
            entry["children_are_array"] = bool(is_array)
            # 同名检测需要子对象名单，折叠时拿不到。这里不能沉默：写清「没查」，
            # 否则「没有 duplicate_name」会被读成「查过且没有」。
            entry["duplicates_unchecked"] = True
            entry["children_skipped_reason"] = (
                "周期阵列（有 period）或 number>%d：展开要按子对象数 × 0.06 s 付费，"
                "真值在 script 与 number 里；折叠时无法做同名检测" % GROUP_ENUM_CAP)
            return entry

    try:
        kids = list(obj.getChildren() or [])
    except Exception:
        kids = []
    if not kids:
        return entry

    child_names = [str(getattr(k, "name", "?")) for k in kids]
    dup = sorted({n for n in child_names if child_names.count(n) > 1})
    entry["n_children"] = len(kids)
    if dup:
        entry["duplicate_name"] = True
        entry["duplicate_names"] = dup[:8]
        entry["duplicate_warning"] = ("同名子对象 %d 个：逐条读会得到互相覆盖的假记录，"
                                      "只保留每个名字的第一条" % len(dup))

    if is_group and isinstance(declared, (int, float)):
        # 老行为保持不变：structure group 只报 number + 同名标志，不逐条列子对象。
        # 区别只在于「什么时候付枚举的钱」——现在只为非周期、小规模的组付。
        entry["children_collapsed"] = True
        return entry
    if max_depth is not None and depth >= max_depth:
        entry["children_truncated"] = len(kids)
        return entry

    seen, children = set(), []
    for k in kids:
        kn = str(getattr(k, "name", "?"))
        if kn in seen:
            continue
        seen.add(kn)
        if max_objects is not None and budget["n"] >= max_objects:
            entry["children_truncated"] = len(kids) - len(children)
            break
        children.append(read_obj(f, k, full, depth + 1, budget, max_depth, max_objects))
    entry["children"] = children
    return entry


def walk_material_names(node, acc):
    m = node.get("props", {}).get("material")
    if isinstance(m, str) and m:
        acc.append(m)
    for c in node.get("children", []):
        walk_material_names(c, acc)
    return acc


def _as_text(v):
    """getmaterial() 在 v251 上返回**字符数组**而不是字符串；不 join 会丢整张表。"""
    if isinstance(v, np.ndarray):
        v = v.ravel().tolist()
    if isinstance(v, (list, tuple)):
        try:
            return "".join(str(x) for x in v)
        except Exception:
            return jsonable(v)
    return v


def material_dump(f, names):
    out = {}
    for nm in sorted(set(n for n in names if isinstance(n, str))):
        rec = {}
        for p in MATERIAL_PROPS:
            try:
                rec[p] = jsonable(_as_text(f.getmaterial(nm, p)))
            except Exception:
                pass
        if rec:
            out[nm] = rec
    return out


def enumerate_monitors(f):
    """Discover monitors by object type, NOT by hardcoded names.

    Measured safe order: selectall() -> getAllSelectedObjects() BEFORE any
    getresult() or getObjectById() tree walk. On the P01 course project this
    still yields working getresult("R","T"). See references/fsp-property-map.md §1.
    """
    out = []
    try:
        f.eval("selectall();")
        objs = f.getAllSelectedObjects()
    except Exception as e:
        return [], ["selectall/getAllSelectedObjects failed: %r" % (e,)]
    for o in objs:
        ty = str(getattr(o, "type", "?"))
        if ty not in MONITOR_TYPES and "monitor" not in ty.lower():
            continue
        nm = str(getattr(o, "name", "?"))
        mt = ""
        try:
            mt = str(f.getnamed(nm, "monitor type"))
        except Exception:
            pass
        out.append({"name": nm, "type": ty, "monitor_type": mt})
    return out, []


def read_power(f, name):
    raw = f.getresult(name, "T")
    item = raw[0] if isinstance(raw, (list, tuple)) else raw
    if isinstance(item, dict):
        return np.asarray(item.get("lambda", item.get("f"))).ravel(), np.asarray(item["T"]).ravel()
    a = np.asarray(item)
    if a.ndim == 2 and a.shape[1] >= 2:
        return a[:, 0].ravel(), a[:, 1].ravel()
    raise ValueError("unexpected getresult layout: %r" % (type(item),))


def inspect_structure(f, full, max_depth=None, max_objects=None):
    root = f.getObjectById("::model")
    tree = read_obj(f, root, full, max_depth=max_depth, max_objects=max_objects)
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


def classify_monitors(monitors):
    """Split discovered monitors into power-capable vs other, with an explicit reason."""
    power, other = [], []
    for m in monitors:
        mt = (m.get("monitor_type") or "").lower()
        if any(h in mt for h in POWER_MONITOR_HINTS):
            power.append(m)
        else:
            other.append(m)
    return power, other


def read_power_spectra(f, monitors):
    """Try EVERY monitor; success of ``getresult`` is the criterion.

    实测事故（P09）：2D 工程的线监视器类型是 ``Linear X``，旧的 hint 白名单只认
    z-normal / power，于是**有 500 点反射谱的工程被判 ``no_stored_spectra``**。
    类型串现在只用于失败时的原因说明，不再当门禁。
    """
    data, errors = {}, {}
    power_candidates, other = [], []
    for m in monitors:
        nm = m["name"]
        try:
            lam, p = read_power(f, nm)
            data[nm] = {"lambda": lam.tolist(), "power": p.tolist(),
                        "monitor_type": m.get("monitor_type")}
            power_candidates.append(m)
        except Exception as e:
            errors[nm] = repr(e)
            other.append(m)
    return data, errors, power_candidates, other


def stack_axis(tree):
    """沿哪根轴排层：优先 source 的 injection axis，其次 FDTD 的 dimension（2D 时取 y）。"""
    if not tree:
        return "z"
    for o in tree.get("children", []):
        ty = str(o.get("type", "")).lower()
        p = o.get("props", {})
        if "source" in ty and p.get("injection axis"):
            return str(p["injection axis"]).strip().lower()
        if ty == "fdtd" and str(p.get("dimension", "")).upper() == "2D":
            return "y"
    return "z"


def label_power_monitors(data, tree=None):
    """Assign R / T roles by name convention, then by stack-axis position.

    Third outcome is **unlabeled**: return (None, None) instead of guessing
    ``names[0]``. P07 的 ``initial_trial.fsp`` 里监视器叫 ``monitor``，旧兜底把它当 R，
    报出 ``peak_R=0.0074 @ 0.4 µm`` —— 一个看起来像结果的垃圾数。
    """
    names = list(data)
    r = next((n for n in names if n.lower().startswith("r") and not n.lower().startswith("t")), None)
    t = next((n for n in names if n.lower().startswith("t")), None)
    if r or t:
        return r, t
    axis = stack_axis(tree)
    pos = {}
    if tree:
        for o in tree.get("children", []):
            if o.get("name") in names and axis in o.get("props", {}):
                try:
                    pos[o["name"]] = float(o["props"][axis])
                except (TypeError, ValueError):
                    pass
    if len(pos) == len(names) and len(names) >= 2:
        ordered = sorted(names, key=lambda n: pos[n])
        return ordered[-1], ordered[0]   # 高侧 = 反射，低侧 = 透射
    return (None, None)


def derive(data, r_name, t_name, mode, target_um, layoutmode, other, power_errors):
    """Compute derived metrics ONLY for physically meaningful configurations.

    Returns (derived_or_None, spectrum_or_None, status, reason, issues).
    """
    issues = []
    has_layout = isinstance(layoutmode, (int, float)) and float(layoutmode) == 0.0
    if layoutmode is None or str(layoutmode) == "unknown":
        # mode=spectra 时根本不挂结构，读不到 layoutmode。此时**不能**断言「未保存」。
        issues.append("layoutmode 未读取（本模式未采样结构）：不对「是否已保存结果」下结论")
    elif not has_layout:
        issues.append("layoutmode=%s：工程存盘时处于 layout 模式，无已保存仿真结果"
                      % (layoutmode,))
    if other:
        # 这里 `other` = 「getresult 取不到数据」，不是「不是功率监视器」。两者必须分开说：
        # 32 个 2021 归档工程（layoutmode=1.0、从未跑过）曾被这句写成
        # 「非功率监视器 ['T'] 不产生 R/T 谱」，把事情说反（EXP-49）。
        names = [m["name"] for m in other]
        if layoutmode is None or str(layoutmode) == "unknown":
            issues.append("getresult 取不到谱的监视器：%s（layoutmode 未读到，不判断原因）" % names)
        elif not has_layout:
            issues.append("工程未跑过（layoutmode=%s），%d 个监视器的 getresult 都取不到谱：%s"
                          "——不是监视器类型问题" % (layoutmode, len(names), names))
        else:
            issues.append("getresult 取不到谱的监视器：%s（工程已跑过；可能是类型/频段不匹配）"
                          % names)
    if power_errors:
        issues.append("功率监视器读取失败：%s" % {k: v[:90] for k, v in power_errors.items()})
    if not data:
        reason = "no stored power spectra (layoutmode=%s, %d monitor(s) found)" % (
            layoutmode, len(data) + len(other))
        return None, None, "no_stored_spectra", reason, issues

    # 有谱但认不出 R/T：不猜。猜出来的 peak_R 是一个看起来像结果的垃圾数（P07 实测）。
    if r_name is None and t_name is None:
        issues.append("监视器 %s 既无 R/T 命名约定、也取不到位置：标 unlabeled，不输出派生指标"
                      % sorted(data))
        return None, None, "unlabeled_monitors", \
            "有 %d 条功率曲线但无法判定 R/T 角色" % len(data), issues

    lam = np.asarray(data[next(iter(data))]["lambda"])
    curves = {n: np.asarray(v["power"]) for n, v in data.items()
              if len(v["lambda"]) == len(lam)}
    if mode == "auto":
        mode = "absorption" if (r_name in curves and t_name in curves) else (
            "transmission" if t_name in curves else "reflection")

    if mode == "transmission":
        if t_name not in curves:
            return None, None, "unsupported_monitor_scheme", \
                "transmission 模式需要透射监视器，实际只有 %s" % sorted(curves), issues
        T = curves[t_name]
        i = int(np.argmax(T))
        d = {"analysis_mode": "transmission", "peak_T": float(T[i]),
             "peak_lambda_um": float(lam[i] * 1e6), "npts": int(lam.size),
             "lambda_range_um": [float(lam.min() * 1e6), float(lam.max() * 1e6)]}
        if target_um is not None:
            j = int(np.argmin(abs(lam - target_um * 1e-6)))
            d["T_at_target_um"] = float(T[j])
            d["target_wavelength_um"] = float(target_um)
        return d, None, "ok", None, issues

    if mode == "reflection":
        if r_name not in curves:
            return None, None, "unsupported_monitor_scheme", \
                "reflection 模式需要反射监视器，实际只有 %s" % sorted(curves), issues
        R = curves[r_name]
        i = int(np.argmax(R))
        d = {"analysis_mode": "reflection", "peak_R": float(R[i]),
             "peak_lambda_um": float(lam[i] * 1e6), "npts": int(lam.size),
             "lambda_range_um": [float(lam.min() * 1e6), float(lam.max() * 1e6)]}
        return d, None, "ok", None, issues

    # absorption: BOTH curves + physical A required
    if r_name not in curves or t_name not in curves:
        return None, None, "unsupported_monitor_scheme", \
            "absorption 模式需要同时有 R 与 T 功率监视器，实际只有 %s" % sorted(curves), issues
    R, T = curves[r_name], curves[t_name]
    if not (lam.size == R.size == T.size):
        return None, None, "unsupported_monitor_scheme", \
            "R/T 频点数不一致 (%d vs %d)" % (R.size, T.size), issues
    A = 1.0 - R - T
    if np.any(A < -1e-6) or np.any(A > 1 + 1e-6):
        issues.append("A=1-R-T 超出 [0,1]（min=%.4f max=%.4f）：监视器符号/归一化口径不同，"
                      "拒绝输出非物理吸收率" % (float(A.min()), float(A.max())))
        return None, None, "nonphysical_absorption", \
            "A 超出 [0,1]：min=%.4f max=%.4f，请检查反射监视器符号约定" % (
                float(A.min()), float(A.max())), issues
    i = int(np.argmax(A))
    d = {"analysis_mode": "absorption",
         "peak_A": float(A[i]), "peak_lambda_um": float(lam[i] * 1e6),
         "R_at_peak": float(R[i]), "T_at_peak": float(T[i]),
         "npts": int(lam.size),
         "lambda_range_um": [float(lam.min() * 1e6), float(lam.max() * 1e6)]}
    if target_um is not None:
        j = int(np.argmin(abs(lam - target_um * 1e-6)))
        d["A_at_target_um"] = float(A[j])
        d["target_wavelength_um"] = float(target_um)
        # legacy alias kept for P01 downstream consumers (only when target is 6 um)
        if abs(float(target_um) - 6.0) < 1e-12:
            d["A_at_6um"] = float(A[j])
    spectrum = [[float(x * 1e6), float(r), float(t), float(a)]
                for x, r, t, a in zip(lam, R, T, A)]
    return d, spectrum, "ok", None, issues


def collect_spectra_raw(f, monitors):
    """Stage 1 — read stored results while group scope is still at ::model.

    MUST run before any recursive object-tree walk (references/fsp-property-map.md §1).
    """
    return read_power_spectra(f, monitors)


def finalize_spectra(monitors, raw, mode, target_um, tree=None, layoutmode=None,
                     root_results=None, extra_issues=None):
    """Stage 2 — combine raw spectra with structure info and derive metrics."""
    data, errors, power_candidates, other = raw
    r_name, t_name = label_power_monitors(data, tree)
    derived, spectrum, status, reason, issues = derive(
        data, r_name, t_name, mode, target_um,
        layoutmode if layoutmode is not None else "unknown", other, errors)
    if root_results:
        issues.append("root 结果 %s 属分析组/扫描/远场数据，不在功率谱口径内"
                      % root_results[:8])
    for msg in extra_issues or []:
        issues.append(msg)
    return {
        "spectra_status": status,
        "reason": reason,
        "layoutmode": layoutmode,
        "monitor_inventory": monitors,
        "power_monitor_candidates": [m["name"] for m in power_candidates],
        "R_monitor": r_name, "T_monitor": t_name,
        "analysis_mode": mode, "target_wavelength_um": target_um,
        "power": data,
        "power_errors": errors,
        "derived": derived,
        "spectrum": spectrum,
        "issues": issues,
    }


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


def unsupported_shape(spec):
    """Recognise spec shapes this diff cannot honestly judge.

    P02 uses objects[] + lattice + ellipse; the old code compared them against a
    flat a/l/w/ts box model and always returned functional_layers_match=false,
    masquerading as a real layer mismatch. Return an explicit unsupported status.
    """
    reasons = []
    objs = spec.get("objects") or []
    shapes = {str(o.get("shape", o.get("type", ""))).lower() for o in objs}
    if any(s and s not in {"box", "rectangle", "rect"} for s in shapes):
        reasons.append("objects[] 含非 box 形状 %s" % sorted(shapes - {"box", "rectangle", "rect", ""}))
    if spec.get("lattice"):
        reasons.append("spec 含 lattice 键（超胞/晶格形状，扁平层位模型不适用）")
    if objs and not spec.get("parameters"):
        reasons.append("objects[] 但缺 parameters 表，无法解析表达式")
    if not objs and not spec.get("parameters"):
        reasons.append("既无 objects[] 也无 parameters，无法构造层位")
    return reasons


def build_diff(manifest, spec):
    shape_reasons = unsupported_shape(spec)
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
    result = {
        "layers": pairs, "spec_layers_without_fsp_match": unmatched,
        "settings": settings, "materials": materials,
        "functional_layers": functional,
        "substrate_mismatch": substrate,
        "substrate_note": ("substrate thickness differs; optically irrelevant when the metallic "
                           "ground plane is thicker than the IR skin depth (T is ~0)"),
        "unsupported_spec_shape": bool(shape_reasons),
        "unsupported_reasons": shape_reasons,
        "functional_layers_match": bool(functional) and all(p["match"] for p in functional),
        "all_layers_match": all(p["match"] for p in pairs) and not unmatched,
        "settings_mismatches": [r["field"] for r in settings if not r["match"]],
        "all_settings_match": all(r["match"] for r in settings),
        "all_materials_match": all(r["match"] for r in materials),
    }
    if shape_reasons:
        # Do NOT disguise "cannot judge" as "layers differ".
        result["functional_layers_match"] = None
        result["all_layers_match"] = None
        result["status"] = "unsupported_spec_shape"
        result["status_reason"] = "; ".join(shape_reasons)
    else:
        result["status"] = "ok"
        result["status_reason"] = None
    return result


# ---------------------------------------------------------------- main
@contextlib.contextmanager
def quiet_native_stdout(enabled: bool):
    """--json: Lumerical writes engine noise ({!!} lines) straight to fd 1.

    Redirect fd 1 to devnull for the whole session so stdout contains ONLY the
    final JSON document. Restored in finally, even if a project fails.
    """
    if not enabled:
        yield
        return
    sys.stdout.flush()
    saved = os.dup(1)
    sink = os.open(os.devnull, os.O_WRONLY)
    os.dup2(sink, 1)
    try:
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)
        os.close(sink)


def main():
    ap = argparse.ArgumentParser(description="Inspect existing Lumerical .fsp projects")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-depth", type=int, default=None,
                    help="对象树最大递归深度（默认不限；遇到 30x30 结构组时用 2-3）")
    ap.add_argument("--max-objects", type=int, default=None,
                    help="对象树最多读取多少个对象（默认不限；4500 叶子的组用 800 左右）")
    args = ap.parse_args()

    try:
        cfg = load_config(args.config)
    except UsageError as e:
        print("config error: %s" % e, file=sys.stderr)
        return 2

    fsp_paths = [resolve_repo(x) for x in cfg["fsp"]]
    out_dir = resolve_repo(args.out)
    analysis = cfg.get("analysis") or {}
    plan = {
        "repo_root": str(REPO_ROOT), "mode": cfg.get("mode", "both"),
        "fsp": [str(p) for p in fsp_paths], "out": str(out_dir),
        "reference_spec": str(resolve_repo(cfg["reference_spec"])) if cfg.get("reference_spec") else None,
        "full_props": bool(cfg.get("full_props", False)),
        "analysis_mode": analysis.get("mode", "auto"),
        "target_wavelength_um": analysis.get("target_wavelength_um"),
        "monitor_discovery": "selectall + getAllSelectedObjects by monitor type (no R/T hardcoding)",
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
    with quiet_native_stdout(args.json):
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
                # ORDER MATTERS. Monitor discovery via selectall is safe before
                # getresult (measured), but the recursive object-tree walk must
                # come AFTER all stored results have been read (group scope).
                # ORDER MATTERS (references/fsp-property-map.md §1):
                #   1. selectall enumeration  (safe, does not need getresult)
                #   2. read stored spectra    (group scope still ::model)
                #   3. recursive tree walk   (may change group scope)
                #   4. finalize/derive       (pure Python, no lumapi calls)
                monitors, discover_issues = enumerate_monitors(f)
                m["monitors"] = monitors
                m["monitor_discovery_issues"] = discover_issues
                raw = None
                if plan["mode"] in ("spectra", "both"):
                    raw = collect_spectra_raw(f, monitors)
                structure = (inspect_structure(f, plan["full_props"],
                                               max_depth=args.max_depth,
                                               max_objects=args.max_objects)
                             if plan["mode"] in ("structure", "both") else None)
                if raw is not None:
                    spectra_all[key] = finalize_spectra(
                        monitors, raw, plan["analysis_mode"],
                        plan["target_wavelength_um"],
                        tree=structure["tree"] if structure else None,
                        layoutmode=structure["layoutmode"] if structure else None,
                        root_results=structure["root_results"] if structure else None,
                        extra_issues=discover_issues)
                if structure is not None:
                    m.update(structure)
                m["probe_seconds"] = round(time.time() - t0, 1)
                manifests.append(m)
                if spec and plan["mode"] in ("structure", "both"):
                    diffs[key] = build_diff(m, spec)
                if not args.json:
                    s = spectra_all.get(key) or {}
                    print("%s: layoutmode=%s objects=%d status=%s derived=%s (%.1fs)"
                          % (key, m.get("layoutmode"),
                             len(m.get("tree", {}).get("children", [])),
                             s.get("spectra_status"), json.dumps(s.get("derived")),
                             m["probe_seconds"]))
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

    projects = []
    for m in manifests:
        name = Path(m["fsp"]).name
        s = spectra_all.get(name) or {}
        projects.append({
            "name": name,
            "layoutmode": m.get("layoutmode"),
            "n_objects": len(m.get("tree", {}).get("children", [])),
            "root_results": m.get("root_results"),
            "monitors": [x["name"] + ":" + (x.get("monitor_type") or "?")
                         for x in m.get("monitors", [])],
            "spectra_status": s.get("spectra_status"),
            "spectra_reason": s.get("reason"),
            "issues": s.get("issues", []),
            "derived": s.get("derived"),
            "diff": ({k: diffs.get(name, {}).get(k)
                      for k in ("status", "unsupported_spec_shape", "unsupported_reasons",
                                "functional_layers_match", "all_layers_match",
                                "all_settings_match", "settings_mismatches",
                                "all_materials_match", "substrate_mismatch")}
                     if diffs.get(name) else None),
        })
    summary = {
        "plan": {"mode": plan["mode"], "out": plan["out"],
                 "analysis_mode": plan["analysis_mode"],
                 "target_wavelength_um": plan["target_wavelength_um"]},
        "projects": projects,
        "errors": errors,
        "issues": sorted({i for p in projects for i in p["issues"]}),
        "status_counts": {st: sum(1 for p in projects if p["spectra_status"] == st)
                          for st in sorted({p["spectra_status"] for p in projects
                                            if p["spectra_status"]})},
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("outputs -> %s (manifest.json / spectra.json / diff.json / summary.json)" % out_dir)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
