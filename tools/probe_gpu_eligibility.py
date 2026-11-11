#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""probe_gpu_eligibility.py — 判定每个 .fsp 能不能走 GPU 加速，并给出批次。

为什么要有它
------------
本机 GPU 是 RTX 3070 Laptop（8 GiB，real32），有两条硬限制是踩出来的：
  * GPU 引擎**不支持 TFSF 源**（D-011，P05 四个工程全部因此无法加速）；
  * GPU 是单精度，Drude/采样金属易发散，需要 dt<=0.95 且配 CPU 双精度对照；
  * GPU 引擎遇非 ASCII 路径必崩（Windows 1113）。
并行跑多个 case 前必须先分类，否则「有的能加速、有的不能」会混在一个批次里，
要么浪费机时，要么把不能跑的工程送进 GPU 直接失败。

判定顺序（先命中先返回）
------------------------
  1. 路径含非 ASCII                        -> cpu_only
  2. 含 TFSFSource                         -> cpu_only   (D-011)
  3. dimension == 2D                       -> cpu_only   (D-008)
  4. 色散金属（Drude/Sampled/Conductive）  -> gpu_risky  (需 dt<=0.95 + CPU A/B)
  5. 显存估算 > 85% VRAM                   -> cpu_only
  6. 显存估算 > 50% VRAM                   -> gpu（独占，max_parallel=1）
  7. 其余                                  -> gpu

用法
----
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/probe_gpu_eligibility.py --cases cases/P02* cases/P03* cases/P04* cases/P05* \\
          --out _scratch/gpu-probe/2026-11-10
    "$PY" tools/probe_gpu_eligibility.py --cases cases/P02* --dry-run     # 不打开会话

退出码：0 = 全部判定完成（含 cpu_only）；1 = 有工程读取失败；2 = 参数错误。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

try:  # Windows 控制台 cp1252，中文输出会崩
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TOOLS_DIR = Path(__file__).resolve().parent
WS_ROOT = TOOLS_DIR.parent
INSPECT = WS_ROOT / "skills" / "fdtd-lumerical-fsp-introspection" / "scripts" / "inspect_fsp.py"

VRAM_MIB = 8192
BYTES_PER_CELL = 60          # real32 FDTD 的保守估计（含场分量与辅助数组）
SAFETY = 1.5                 # 显存安全系数
LOG_RE = re.compile(r"Simulation size in gridpoints:\s*(\d+)\s*x\s*(\d+)\s*x\s*(\d+)")

# 金属：按“词”匹配（下划线/空格/括号都算分隔符）。
# 别用子串：'Palik' 含 'al'，'Au_Drude_paper' 里 \bau\b 又匹配不到。
METAL_WORDS = {"au", "ag", "al", "cu", "ni", "cr", "gold", "silver",
               "aluminum", "aluminium", "copper", "drude",
               "conductive", "pec"}
# 2026-11-11 订正：原先词表含 "ti" 与 "titanium"，导致 `TiO2 (Titanium Dioxide) - Siefke`
# 被误判成金属（实测：P03 的 t4_tio2_unitcell 被判 gpu_risky）。TiO2 是介质，不是金属。
# 判据本就是「强损耗 / 色散金属」，钛本身在光学里几乎不用裸 Ti，去掉这两个词更安全。
# 真含损耗的介质仍会被 LOSSY_K 判据（虚折射率 > 0.5）抓到，不依赖名字。
LOSSY_K = 0.5           # 虚折射率极强才算金属级损耗（Si 在可见区也有 k，不能按 0.05 判）


def load_inspector():
    """复用反解析技能里的对象树读取，避免第二份实现。"""
    spec = importlib.util.spec_from_file_location("inspect_fsp", INSPECT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def iter_tree(node):
    yield node
    for c in node.get("children", []) or []:
        yield from iter_tree(c)


def cells_from_log(fsp: Path) -> tuple[int | None, str]:
    log = fsp.with_name(fsp.stem + "_p0.log")
    if not log.is_file():
        return None, "no _p0.log"
    try:
        hits = LOG_RE.findall(log.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None, "log unreadable"
    if not hits:
        return None, "no gridpoints line"
    a, b, c = (int(x) for x in hits[-1])
    return a * b * c, f"from {log.name}"


def cells_estimate(tree) -> int | None:
    """没有日志时，用 FDTD 尺寸 / 最细网格做保守估计。"""
    ftd = next((n for n in iter_tree(tree) if n.get("type") == "FDTD"), None)
    if not ftd:
        return None
    p = ftd.get("props", {})
    dx = dy = dz = None
    for n in iter_tree(tree):
        q = n.get("props", {})
        if all(k in q for k in ("dx", "dy", "dz")):
            v = [float(q.get("dx") or 0), float(q.get("dy") or 0), float(q.get("dz") or 0)]
            if all(x > 0 for x in v):
                dx = min(dx, v[0]) if dx else v[0]
                dy = min(dy, v[1]) if dy else v[1]
                dz = min(dz, v[2]) if dz else v[2]
    dx = dx or float(p.get("dx") or 0)
    dy = dy or float(p.get("dy") or 0)
    dz = dz or float(p.get("dz") or 0)
    spans = [float(p.get(k) or 0) for k in ("x span", "y span", "z span")]
    if not all(spans) or not all(v > 0 for v in (dx, dy, dz)):
        return None
    return int((spans[0] / dx) * (spans[1] / dy) * (spans[2] / dz))


def _num(v):
    try:
        return float(v)
    except Exception:
        return None


def classify(fsp: Path, info: dict, cells_override: dict | None = None) -> dict:
    reasons: list[str] = []
    tree = info["tree"]
    src_types = sorted({n.get("type", "") for n in iter_tree(tree)
                        if "source" in str(n.get("type", "")).lower()})
    mats = info.get("materials", {}) or {}
    mat_types = sorted({str(v.get("type", "")) for v in mats.values()})
    mat_names = sorted(mats)

    # 金属/有损：Palik 的 Si、SiO2 也是 "Sampled 3D data"，只按类型判会把介质误伤
    metals = []
    for nm, rec in mats.items():
        t = str(rec.get("type", "")).lower()
        k = _num(rec.get("Imaginary Refractive Index"))
        if (k is not None and k > LOSSY_K) or "drude" in t or "conductive" in t:
            metals.append(nm)
        else:
            toks = {w.lower() for w in re.split(r"[^A-Za-z0-9]+", nm) if w}
            if toks & METAL_WORDS:
                metals.append(nm)

    ftd = next((n for n in iter_tree(tree) if n.get("type") == "FDTD"), None)
    fp = (ftd or {}).get("props", {})
    dimension = str(fp.get("dimension", "3D"))
    dt = fp.get("dt stability factor")

    cells, cells_src = cells_from_log(fsp)
    if cells is None and cells_override:
        v = cells_override.get(fsp.name) or cells_override.get(fsp.stem)
        if v:
            cells, cells_src = int(v), "override (报告实测)"
    if cells is None:
        cells = cells_estimate(tree)
        cells_src = "estimate (无日志，置信度低)"
    confident = not cells_src.startswith("estimate")
    vram = round((cells or 0) * BYTES_PER_CELL * SAFETY / 1024 ** 2, 1) if cells else None

    verdict, max_par = "gpu", None

    if not str(fsp).isascii():
        verdict, max_par = "cpu_only", 0
        reasons.append("路径含非 ASCII -> GPU 引擎 1113")
    elif any("tfsf" in t.lower() for t in src_types):
        verdict, max_par = "cpu_only", 0
        reasons.append("含 TFSFSource -> GPU 引擎明确不支持（D-011）")
    elif dimension.upper() == "2D":
        verdict, max_par = "cpu_only", 0
        reasons.append("dimension=2D -> 2D 链路未通（D-008）")
    else:
        if metals:
            verdict = "gpu_risky"
            reasons.append("金属/有损材料 %s -> real32 易发散，需 dt<=0.95 + CPU A/B" % (metals[:3],))
        if confident and vram and vram > 0.85 * VRAM_MIB:
            verdict, max_par = "cpu_only", 0
            reasons.append("显存估算 %.0f MiB > 85%% VRAM(%.0f)" % (vram, VRAM_MIB))
        elif confident and vram and vram > 0.50 * VRAM_MIB:
            max_par = 1
            reasons.append("显存估算 %.0f MiB -> 必须独占 GPU" % vram)
        elif not confident:
            reasons.append("网格数无日志，显存未判（不据此降级）")
        if verdict == "gpu" and not reasons:
            reasons.append("3D + 平面波源 + 介质/低显存 -> 可走 GPU")

    return {
        "fsp": str(fsp),
        "case": next((p for p in fsp.parts if re.match(r"^P\d{2}_", p)), ""),
        "verdict": verdict,
        "max_parallel": max_par,
        "reasons": reasons,
        "cells_est": cells,
        "cells_source": cells_src,
        "vram_est_mib": vram,
        "vram_confident": confident,
        "dimension": dimension,
        "dt_stability_factor": dt,
        "source_types": src_types,
        "materials": mat_names[:12],
        "metal_materials": metals[:6],
        "material_types": mat_types[:12],
        "layoutmode": info.get("layoutmode"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="GPU 可用性预检")
    ap.add_argument("--cases", nargs="+", required=True, help="包目录或包 ID 前缀")
    ap.add_argument("--out", required=True, help="输出目录（写 gpu_matrix.json）")
    ap.add_argument("--dry-run", action="store_true", help="只列出将检查的 .fsp，不开会话")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-objects", type=int, default=1500)
    ap.add_argument("--cells-override", default=None,
                    help="JSON: {fsp 文件名: 网格数}，用于无 _p0.log 但报告里已实测的工程")
    args = ap.parse_args()
    cells_override = {}
    if args.cells_override:
        p = Path(args.cells_override)
        if not p.is_absolute():
            p = WS_ROOT / p
        cells_override = json.loads(p.read_text(encoding="utf-8")).get("cells", {})

    case_dirs: list[Path] = []
    for raw in args.cases:
        p = Path(raw)
        if not p.is_absolute():
            p = WS_ROOT / raw
        if p.is_dir():
            case_dirs.append(p)
        else:
            hits = sorted((WS_ROOT / "cases").glob(raw))
            case_dirs.extend(h for h in hits if h.is_dir())
    if not case_dirs:
        print("no case dir matched", file=sys.stderr)
        return 2

    fsp_files: list[Path] = []
    for d in case_dirs:
        fsp_files.extend(sorted(
            f for f in d.rglob("*.fsp")
            if "_archive" not in f.parts and ".git" not in f.parts
        ))
    if not fsp_files:
        print("no .fsp found", file=sys.stderr)
        return 2

    if args.dry_run:
        print("dry-run: %d .fsp, no session will be opened" % len(fsp_files))
        for f in fsp_files:
            print("  " + str(f.relative_to(WS_ROOT)))
        return 0

    mod = load_inspector()
    api_path = os.environ.get("LUMERICAL_API_PATH", mod.DEFAULT_API_PATH)
    os.environ.setdefault("ANSYSLMD_LICENSE_FILE",
                          os.environ.get("ANSYSLMD_LICENSE_FILE", mod.DEFAULT_LICENSE))
    if api_path not in sys.path:
        sys.path.insert(0, api_path)
    import lumapi  # noqa: E402

    rows, failures = [], []
    with mod.quiet_native_stdout(True):
        for fsp in fsp_files:
            f = None
            try:
                f = lumapi.FDTD(hide=True)
                f.load(str(fsp))
                info = mod.inspect_structure(f, full=False, max_depth=3,
                                             max_objects=args.max_objects)
                rows.append(classify(fsp, info, cells_override))
                print("  %-46s %s" % (fsp.relative_to(WS_ROOT), rows[-1]["verdict"]))
            except Exception as e:
                failures.append({"fsp": str(fsp), "error": str(e)[:200]})
                print("  %-46s FAILED: %s" % (fsp.relative_to(WS_ROOT), str(e)[:80]))
            finally:
                if f is not None:
                    try:
                        f.close()
                    except Exception:
                        pass

    gpu = [r for r in rows if r["verdict"] in ("gpu", "gpu_risky")]
    cpu = [r for r in rows if r["verdict"] == "cpu_only"]
    budget = []
    if gpu:
        worst = max((r["vram_est_mib"] or 0) for r in gpu) or 1
        budget.append({"rule": "0.5*VRAM / max(vram_est)",
                       "max_parallel": max(1, int(0.5 * VRAM_MIB // worst))})

    matrix = {
        "vram_mib": VRAM_MIB,
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "counts": {"total": len(rows), "gpu": len(gpu) - len([r for r in gpu if r["verdict"] == "gpu_risky"]),
                   "gpu_risky": len([r for r in gpu if r["verdict"] == "gpu_risky"]),
                   "cpu_only": len(cpu), "failed": len(failures)},
        "batches": {
            "GPU": [r["fsp"] for r in gpu],
            "CPU": [r["fsp"] for r in cpu],
        },
        "concurrency": budget,
        "rows": rows,
        "failures": failures,
    }

    out = Path(args.out)
    if not out.is_absolute():
        out = WS_ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "gpu_matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    if args.json:
        print(json.dumps(matrix, ensure_ascii=False, indent=2))
    else:
        print("\nGPU 批 %d / CPU 批 %d / 失败 %d -> %s"
              % (len(gpu), len(cpu), len(failures), out / "gpu_matrix.json"))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
