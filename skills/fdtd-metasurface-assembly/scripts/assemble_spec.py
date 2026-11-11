#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble a metasurface spec from a quantised phase map + unit-cell library.

Zero engine: reads ``quantized_phase*.csv`` (the handoff of ``fdtd-holo-phase-retrieval``),
looks each cell's level up in ``library_map.json``, and writes an ``fsp-build`` spec whose
``array`` object carries one ``cell_params`` entry per cell.  Building the ``.fsp`` is the
job of ``fdtd-lumerical-fsp-build``; this script only produces the spec.

    python assemble_spec.py --phase <csv> --library <json> --geometry <json> \
        --out <spec.json> [--target-nx N --target-ny M] [--dry-run] [--json] [--self-test]

Row-major order: the CSV is written with y outer, x inner (Skill A emits y-major), which
matches ``fsp_build.array_cells`` (``divmod(idx, nx)``).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path


class AsmError(Exception):
    """装配错误：列名、档位缺失、行数不符、坐标不一致……一律显式报错，不猜。"""


REQUIRED_CSV_COLS = ("x_um", "y_um", "phase_rad", "level")


# ----------------------------------------------------------------------------- readers
def read_phase_csv(path: Path) -> dict:
    """Read the phase CSV into a plain dict; validate the contract before touching geometry."""
    with path.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if not header:
            raise AsmError("相位 CSV 是空文件：%s" % path)
        cols = [c.strip() for c in header]
        missing = [c for c in REQUIRED_CSV_COLS if c not in cols]
        if missing:
            raise AsmError(
                "相位 CSV 缺少列 %s；实际表头 %s。\n"
                "  契约是 Skill A 的 %s 四列（见 fdtd-holo-phase-retrieval SKILL.md §交接）。"
                % (missing, cols, "/".join(REQUIRED_CSV_COLS)))
        idx = {c: cols.index(c) for c in REQUIRED_CSV_COLS}
        rows = []
        for k, rec in enumerate(reader, 2):
            if not rec or all(not c.strip() for c in rec):
                continue
            try:
                rows.append((float(rec[idx["x_um"]]), float(rec[idx["y_um"]]),
                             float(rec[idx["phase_rad"]]), int(rec[idx["level"]])))
            except Exception as exc:                      # noqa: BLE001
                raise AsmError("相位 CSV 第 %d 行解析失败（%r）：%s" % (k, rec, exc)) from exc
    if not rows:
        raise AsmError("相位 CSV 没有任何数据行：%s" % path)
    xs = sorted({r[0] for r in rows})
    ys = sorted({r[1] for r in rows})
    return {"rows": rows, "xs": xs, "ys": ys}


def read_library(path: Path, levels_needed: set) -> dict:
    """Return {level: params-dict}; every needed level must exist, or the error names them."""
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data.get("cells")
    if not isinstance(cells, list) or not cells:
        raise AsmError("library_map.json 没有 cells 列表：%s" % path)
    table = {}
    for k, c in enumerate(cells):
        lvl = c.get("level")
        if not isinstance(lvl, int):
            raise AsmError("library cells[%d] 缺少整数 level：%r" % (k, c))
        if not isinstance(c.get("params"), dict):
            raise AsmError("library cells[%d]（level=%s）缺少 params 对象" % (k, lvl))
        if lvl in table:
            raise AsmError("library 里 level=%d 定义了两次（cells[%d]）" % (lvl, k))
        table[lvl] = dict(c["params"])
    got = sorted(table)
    missing = sorted(levels_needed - set(table))
    if missing:
        counts = {L: sum(1 for r in _LAST_NEED_ROWS if r[3] == L) for L in missing}
        raise AsmError(
            "单元库缺档：相位图用到 level %s，但 library_map.json 只有 %s。\n"
            "  缺失档位出现次数 %s。\n"
            "  这是装配侧的 missing[]（Skill A 的契约）：先补齐单元库（标定或查论文），"
            "不要在这里硬凑参数。" % (missing, got, counts))
    return table


# 行数统计要跨函数用（报错信息里给出现次数）；放在模块级是刻意的，单线程 CLI 没有竞争。
_LAST_NEED_ROWS: list = []


# ----------------------------------------------------------------------------- grid
def infer_grid(phase: dict, target_nx: int, target_ny: int, mode: str = "crop") -> dict:
    """Cell coordinates must match the pitch/origin we will write into the spec.

    The CSV's own lattice (its unique-x/y spacing) defines the array pitch.  Two modes:

    ``stride``  —— 每 sx/sy 取一点。⚠️ pitch 变成 dx*s：格子被放大且稀疏化，
    只有"把相位图当连续版图再粗采样"时才有意义；对超表面装配这**不是**物理降采样。
    ``crop``    —— 从中心裁出 target 窗口，pitch 保持 dx 不变。装配超表面用这个：
    单元周期 = 相位图设计时的单胞周期，孔径变小但物理意义不变（EXP-64 判据偏差追记：
    stride 模式把 0.4 µm 单元周期拉成 1.6 µm，产生了周期 1.6 µm @ λ0.74 的光栅——
    那不是要装配的东西，所以 crop 成为默认）。

    Both modes are recorded in the spec meta — silent subsampling would make the delivered
    aperture mean something else than the designed one.
    """
    xs, ys = phase["xs"], phase["ys"]
    nx_full, ny_full = len(xs), len(ys)
    dx = xs[1] - xs[0] if nx_full > 1 else 0.0
    dy = ys[1] - ys[0] if ny_full > 1 else 0.0
    if dx <= 0 or dy <= 0:
        raise AsmError("相位网格间距非正：dx=%r dy=%r" % (dx, dy))
    for name, arr in (("x", xs), ("y", ys)):
        gaps = [round(arr[k + 1] - arr[k], 9) for k in range(len(arr) - 1)]
        if max(gaps) - min(gaps) > 1e-6:
            raise AsmError("%s 方向格距不均匀（%r .. %r）：非均匀网格不在本技能的表达范围内"
                           % (name, min(gaps), max(gaps)))
    if target_nx > nx_full or target_ny > ny_full:
        raise AsmError(
            "目标规模 %dx%d 超过相位图 %dx%d：只允许裁剪/降采样，不允许插值放大。"
            % (target_nx, target_ny, nx_full, ny_full))
    if mode == "crop":
        cx0 = (nx_full - target_nx) // 2
        cy0 = (ny_full - target_ny) // 2
        xsel, ysel = xs[cx0:cx0 + target_nx], ys[cy0:cy0 + target_ny]
        stride = [1, 1]
    else:
        if nx_full % target_nx != 0 or ny_full % target_ny != 0:
            raise AsmError(
                "相位图 %dx%d 无法按整数步长降到 %dx%d。\n"
                "  stride 模式必须是整数步长（否则单元位置与相位档位都会错位）；"
                "想保持单元周期请用 --mode crop（中心裁剪）。"
                % (nx_full, ny_full, target_nx, target_ny))
        sx, sy = nx_full // target_nx, ny_full // target_ny
        xsel, ysel = xs[::sx], ys[::sy]
        stride = [sx, sy]
    # 行主序（y 外层、x 内层）：与 Skill A 的 CSV 行序一致，与 fsp_build 的 divmod 一致
    chosen = [r for r in phase["rows"] if r[0] in xsel and r[1] in ysel]
    # 相同 (x,y) 必须只出现一次
    seen = {}
    for r in chosen:
        key = (r[0], r[1])
        if key in seen:
            raise AsmError("相位 CSV 出现重复坐标 %r（两行相位不同：%r / %r）"
                           % (key, seen[key], r))
        seen[key] = r
    return {
        "nx": target_nx, "ny": target_ny,
        "pitch_um": [dx * stride[0], dy * stride[1]],
        "origin_um": [xsel[0], ysel[0]],
        "source_grid": [nx_full, ny_full],
        "mode": mode,
        "stride": stride,
        "rows": sorted(chosen, key=lambda r: (r[1], r[0])),   # y 外层、x 内层
    }


def build_cell_params(grid: dict, library: dict) -> list:
    """One cell_params entry per cell, in row-major order, straight from the library."""
    out = []
    for k, (x, y, ph, lvl) in enumerate(grid["rows"]):
        params = dict(library[lvl])
        params["i"] = k // grid["nx"]
        params["j"] = k % grid["nx"]
        out.append(params)
    return out


def assemble(phase_csv: Path, library_json: Path, geometry: dict,
             target_nx: int, target_ny: int, mode: str = "crop") -> dict:
    phase = read_phase_csv(phase_csv)
    _LAST_NEED_ROWS.clear()
    _LAST_NEED_ROWS.extend(phase["rows"])
    levels_needed = {r[3] for r in phase["rows"]}
    library = read_library(library_json, levels_needed)
    grid = infer_grid(phase, target_nx, target_ny, mode)
    cells = build_cell_params(grid, library)

    for key in ("element", "element_material"):
        if key not in geometry:
            raise AsmError("geometry 缺少 %s（模板对象 / 其材料键）" % key)
    tpl = geometry["element"]
    if tpl.get("type") not in ("box", "cylinder", "ellipse", "ring", "polygon"):
        raise AsmError("element.type=%r 不支持（2drect 阵列请用 fsp-build 手写 spec）"
                       % tpl.get("type"))

    sim = geometry["simulation"]
    pitch = grid["pitch_um"]
    W = grid["nx"] * pitch[0]
    H = grid["ny"] * pitch[1]
    arr = {
        "id": "meta",
        "type": "array",
        "material": geometry["element_material"],
        "grid": {
            "nx": grid["nx"], "ny": grid["ny"],
            "pitch": ["%.12g" % (pitch[0] * 1e-6), "%.12g" % (pitch[1] * 1e-6)],
            "origin": ["%.12g" % (grid["origin_um"][0] * 1e-6),
                       "%.12g" % (grid["origin_um"][1] * 1e-6)],
        },
        "element": tpl,
        "cell_params": cells,
    }
    spec = {
        "schema_version": "1.0",
        "meta": {
            "package": geometry.get("package", "ASSEMBLED"),
            "assembled_from": {
                "phase_csv": str(phase_csv),
                "library": str(library_json),
                "source_grid": grid["source_grid"],
                "stride": grid["stride"],
                "levels": sorted({r[3] for r in grid["rows"]}),
            },
            "wavelength_um": geometry.get("wavelength_um"),
        },
        "parameters": dict(geometry.get("parameters") or {}),
        "lattice": {"type": "square",
                    "period_x": "%.12g" % (W * 1e-6), "period_y": "%.12g" % (H * 1e-6),
                    "supercell": {"nx": 1, "ny": 1}},
        "materials": geometry.get("materials") or {},
        "objects": ([geometry["sub_object"]] if geometry.get("sub_object") else []) + [arr],
        "simulation": sim,
        "targets": [],
    }
    spec["_grid"] = grid
    return spec


# ----------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase CSV + unit-cell library -> fsp-build spec")
    ap.add_argument("--phase", help="quantized_phase*.csv（Skill A 产出）")
    ap.add_argument("--library", help="library_map.json（level -> 单元参数）")
    ap.add_argument("--geometry", help="geometry.json（模板 / 材料 / 仿真段）")
    ap.add_argument("--target-nx", type=int, default=0, help="目标 nx（默认 = 相位图全量）")
    ap.add_argument("--target-ny", type=int, default=0, help="目标 ny（默认 = 相位图全量）")
    ap.add_argument("--mode", default="crop", choices=("crop", "stride"),
                    help="crop=中心裁剪保持单元周期（默认）；stride=整数步长（会放大单元周期）")
    ap.add_argument("--out", help="输出 spec.json")
    ap.add_argument("--dry-run", action="store_true", help="只打印规模，不写文件")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not (args.phase and args.library and args.geometry):
        ap.error("--phase / --library / --geometry 都是必填（--self-test 除外）")
    geometry = json.loads(Path(args.geometry).read_text(encoding="utf-8"))
    phase = read_phase_csv(Path(args.phase))
    nx = args.target_nx or len(phase["xs"])
    ny = args.target_ny or len(phase["ys"])
    spec = assemble(Path(args.phase), Path(args.library), geometry, nx, ny,
                    mode=args.mode)

    summary = {
        "nx": spec["_grid"]["nx"], "ny": spec["_grid"]["ny"],
        "cells": spec["_grid"]["nx"] * spec["_grid"]["ny"],
        "pitch_um": spec["_grid"]["pitch_um"],
        "origin_um": spec["_grid"]["origin_um"],
        "source_grid": spec["_grid"]["source_grid"],
        "stride": spec["_grid"]["stride"],
        "levels_used": sorted({r[3] for r in spec["_grid"]["rows"]}),
    }
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json
              else "\n".join("%-14s %s" % (k, v) for k, v in summary.items()))
        return 0
    if not args.out:
        ap.error("--out is required unless --dry-run / --self-test")
    grid = spec.pop("_grid")
    Path(args.out).write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["out"] = args.out
    print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json
          else "\n".join("%-14s %s" % (k, v) for k, v in summary.items()))
    return 0


# ----------------------------------------------------------------------------- self-test
def self_test() -> int:
    """17 offline assertions over the pure functions; no lumapi, no files in repo tree."""
    import tempfile

    fails = []

    def check(name, cond, detail=""):
        print("  [%s] %s%s" % ("OK  " if cond else "FAIL", name,
                              ("  <- " + str(detail)) if (detail and not cond) else ""))
        if not cond:
            fails.append(name)

    # ---- 合成 3x3 相位：level 序列已知
    rows = []
    lv = [[0, 1, 2], [3, 4, 5], [6, 7, 0]]
    for i in range(3):
        for j in range(3):
            rows.append((j * 0.5, i * 0.5, lv[i][j] * math.pi / 4, lv[i][j]))
    phase = {"rows": rows, "xs": [0.0, 0.5, 1.0], "ys": [0.0, 0.5, 1.0]}
    _LAST_NEED_ROWS.clear()
    _LAST_NEED_ROWS.extend(rows)
    lib = {L: {"d1": 0.1 + 0.01 * L, "rot": L * 22.5} for L in range(8)}
    library = read_library_from(lib)
    grid = infer_grid(phase, 3, 3)
    check("1 行主序首格 = (0,0) 档 0", grid["rows"][0][3] == 0, grid["rows"][0])
    check("2 行主序末格 = (2,2) 档 0", grid["rows"][-1][3] == 0, grid["rows"][-1])
    check("3 pitch 推断 = 0.5 um", grid["pitch_um"] == [0.5, 0.5], grid["pitch_um"])
    check("4 origin 推断 = (0,0)", grid["origin_um"] == [0.0, 0.0], grid["origin_um"])

    cells = build_cell_params(grid, library)
    check("5 cell_params 长度 = 9", len(cells) == 9, len(cells))
    check("6 第 5 格（r1c1）= level 4 的 d1", abs(cells[4]["d1"] - 0.14) < 1e-12, cells[4])
    check("7 每格都带 i/j 索引", all("i" in c and "j" in c for c in cells))

    # ---- 缺档必须报错且给出现次数
    lib_missing = {L: {"d1": 0.1} for L in range(8) if L != 7}
    try:
        read_library_from(lib_missing)
        check("8 缺 level=7 必须报错", False, "没有报错")
    except AsmError as e:
        check("8 缺 level=7 必须报错", "7" in str(e) and "出现次数" in str(e), str(e)[:80])

    # ---- 行数不符（infer_grid 抽样约束）
    try:
        infer_grid(phase, 2, 3, mode="stride")
        check("9 非整除降采样必须报错", False)
    except AsmError as e:
        check("9 非整除降采样必须报错", "整数" in str(e) and "crop" in str(e), str(e)[:80])

    # crop 模式：pitch 保持 dx，不放大单元周期（EXP-64 判据偏差追记后的新行为）
    g_crop = infer_grid(phase, 2, 2, mode="crop")
    check("9b crop 保持 pitch=0.5", g_crop["pitch_um"] == [0.5, 0.5], g_crop["pitch_um"])
    check("9c crop 窗口 = 中心 2x2", g_crop["nx"] == 2 and g_crop["ny"] == 2, g_crop)

    # ---- 放大必须拒绝
    try:
        infer_grid(phase, 6, 3)
        check("10 放大必须拒绝", False)
    except AsmError as e:
        check("10 放大必须拒绝", "插值" in str(e) or "降采样" in str(e), str(e)[:60])

    # ---- 坐标/重复检测
    dup = {"rows": rows + [rows[0]], "xs": phase["xs"], "ys": phase["ys"]}
    try:
        infer_grid(dup, 3, 3)
        check("11 重复坐标必须报错", False)
    except AsmError as e:
        check("11 重复坐标必须报错", "重复坐标" in str(e), str(e)[:60])

    # ---- 哑实现负对照：查表必须真的看 level
    dumb = {0: {"d1": 0.5, "rot": 0.0}}                  # 只有 level 0
    try:
        read_library_from(dumb)
        check("12 哑库缺档必须报错", False)
    except AsmError as e:
        check("12 哑库缺档必须报错", "缺档" in str(e) and "7" in str(e), str(e)[:80])

    cells0 = build_cell_params(grid, read_library_from(
        {L: {"d1": 0.1 + 0.01 * L, "rot": L * 22.5} for L in range(8)}))
    uniq = {(c["d1"], c["rot"]) for c in cells0}
    check("13 9 格至少出现 8 种不同参数", len(uniq) >= 8, len(uniq))

    # ---- 坐标网格一致性：x/y 间距不等时 pitch 分轴
    rows2 = [(j * 0.4, i * 0.6, 0, (i * 3 + j) % 8) for i in range(3) for j in range(3)]
    ph2 = {"rows": rows2, "xs": [0.0, 0.4, 0.8], "ys": [0.0, 0.6, 1.2]}
    g2 = infer_grid(ph2, 3, 3)
    check("14 各向异性 pitch 分轴", g2["pitch_um"] == [0.4, 0.6], g2["pitch_um"])

    # ---- 非均匀网格拒绝
    rows3 = [(0.0, 0.0, 0, 0), (0.5, 0.0, 0, 1), (1.2, 0.0, 0, 2),
             (0.0, 0.5, 0, 3), (0.5, 0.5, 0, 4), (1.2, 0.5, 0, 5)]
    ph3 = {"rows": rows3, "xs": [0.0, 0.5, 1.2], "ys": [0.0, 0.5]}
    try:
        infer_grid(ph3, 3, 2)
        check("15 非均匀网格必须报错", False)
    except AsmError as e:
        check("15 非均匀网格必须报错", "不均匀" in str(e), str(e)[:60])

    # ---- assemble 端到端（纯函数，写临时目录）
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        pcsv = tdp / "p.csv"
        with pcsv.open("w", encoding="utf-8") as fh:
            fh.write("x_um,y_um,phase_rad,level\n")
            for x, y, p, L in rows:
                fh.write("%g,%g,%g,%d\n" % (x, y, p, L))
        ljson = tdp / "lib.json"
        ljson.write_text(json.dumps({
            "levels": 8,
            "cells": [{"level": L, "params": {"d1": 0.1 + 0.01 * L, "rot": L * 22.5}}
                      for L in range(8)]}, indent=2), encoding="utf-8")
        geom = {
            "package": "TEST",
            "element": {"type": "box", "center": ["0", "0", "h/2"],
                        "span": ["d1", "d2", "h"]},
            "element_material": "TiO2",
            "parameters": {"d2": "0.4e-6", "h": "0.6e-6"},
            "materials": {"TiO2": {"kind": "constant_nk", "n": 2.45, "k": 0.0}},
            "sub_object": {"id": "sub", "type": "box", "material": "TiO2",
                           "center": ["0", "0", "-t/2"], "span": ["W", "W", "t"]},
            "simulation": {"dimension": "3D", "bc": {"x": "PML", "y": "PML", "z": "PML"},
                           "mesh_accuracy": 2, "air_above": 2e-6, "below_structure": 1e-6,
                           "source": {"type": "plane_wave", "direction": "Backward",
                                      "wavelength_range": [0.5e-6, 0.8e-6], "npts": 21,
                                      "z": "auto"},
                           "monitors": {"R": {"z": "auto"}, "T": {"z": "auto"}}},
        }
        gjson = tdp / "geom.json"
        gjson.write_text(json.dumps(geom, indent=2), encoding="utf-8")
        # 补 sub_object 需要的 W/t：用显式数字，让 spec 自洽
        geom["sub_object"]["center"] = ["0", "0", "-3e-7"]
        geom["sub_object"]["span"] = ["1.5e-6", "1.5e-6", "6e-7"]
        gjson.write_text(json.dumps(geom, indent=2), encoding="utf-8")

        spec = assemble(pcsv, ljson, geom, 3, 3)
        arr = [o for o in spec["objects"] if o["type"] == "array"][0]
        check("16 spec 的 array.cell_params = 9 条", len(arr["cell_params"]) == 9,
              len(arr["cell_params"]))
        # 每格 d1 必须真的不同（负对照 EXP-63：哑实现会全部同参）
        d1s = [c["d1"] for c in arr["cell_params"]]
        check("17 cell_params 的 d1 至少 8 种", len(set(d1s)) >= 8, sorted(set(d1s))[:3])
        check("18 lattice period = 1.5 um",
              abs(float(spec["lattice"]["period_x"]) - 1.5e-6) < 1e-18,
              spec["lattice"]["period_x"])

    print("\nself-test %s：%d 条判定，%d 条失败" % ("PASS" if not fails else "FAIL",
                                                   18, len(fails)))
    return 0 if not fails else 1


def read_library_from(table: dict) -> dict:
    """Adapter so self-test can inject an in-memory table without writing a file."""
    global _LAST_NEED_ROWS
    needed = {r[3] for r in _LAST_NEED_ROWS}
    missing = sorted(needed - set(table))
    if missing:
        counts = {L: sum(1 for r in _LAST_NEED_ROWS if r[3] == L) for L in missing}
        raise AsmError("单元库缺档：相位图用到 level %s，library 只有 %s。缺失档位出现次数 %s。"
                       "先补齐单元库，不要在这里硬凑参数。" % (missing, sorted(table), counts))
    return {L: dict(v) for L, v in table.items()}


if __name__ == "__main__":
    raise SystemExit(main())
