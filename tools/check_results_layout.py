#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_results_layout.py — results/ 的长期落位门禁（双轨）。

规则（2026-11-10 定稿两级；2026-11-11 补单元轨，见 path-conventions.md §6.0）
----------------------------------------------------------------------------
交付轨（默认检查，根级）：

    results/
    └─ <PkgID>_<ShortTitle>/        # 纯 ASCII，与 cases/ 同名
       └─ <YYYY-MM-DD>/             # 复现日期，可多个
          ├─ index.json             # {case, date, verdict, solver, artifacts[]}
          └─ ...

单元轨（`--also-cases`，单元内）：

    cases/<P0N>/results/            # 原始产物：.fsp / _p0.log / point_*.csv
    └─ <任意子目录>/                 # 子目录名不做格式约束，不要求 index.json

FAIL 情形（交付轨）：results/ 根下直接放文件；论文目录下直接放文件；日期目录名不合规；
日期目录缺 index.json；index.json 缺键或 date 与目录名不一致。

FAIL 情形（单元轨，仅 --also-cases）：cases/<P0N>/results/ 根下平铺文件；
单文件 > 100 MB（体积红线，path-conventions.md §4）。

占位文件（.gitkeep 等）与隐藏目录不算违规。

用法
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/check_results_layout.py
    "$PY" tools/check_results_layout.py --also-cases
    "$PY" tools/check_results_layout.py --json
    "$PY" tools/check_results_layout.py --self-test
退出码：0 全绿 / 1 违规 / 2 路径错误。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CASES = ROOT / "cases"
PKG_RE = re.compile(r"^P\d{2}_[A-Za-z0-9_]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDERS = {".gitkeep", ".keep", ".gitignore"}
SIZE_LIMIT = 100 * 1024 * 1024  # path-conventions.md §4：> 100 MB 不入库


def visible(p: Path) -> list[Path]:
    return [x for x in p.iterdir() if x.name not in PLACEHOLDERS and not x.name.startswith(".")]


def check(root: Path) -> list[str]:
    fails: list[str] = []
    if not root.is_dir():
        return [f"results 目录不存在：{root}"]

    for entry in visible(root):
        if entry.is_file():
            fails.append(f"results/ 根下直接放文件：{entry.name}（应为 <论文名>/<日期>/）")
            continue
        if not PKG_RE.match(entry.name):
            fails.append(f"论文目录名不合规：{entry.name}（应形如 P02_PolarizationControl_045）")
            continue
        for date_dir in visible(entry):
            if date_dir.is_file():
                fails.append(f"{entry.name}/ 下直接放文件：{date_dir.name}（应放进日期子目录）")
                continue
            if not DATE_RE.match(date_dir.name):
                fails.append(f"{entry.name}/ 子目录不是复现日期：{date_dir.name}（应为 YYYY-MM-DD）")
                continue
            idx = date_dir / "index.json"
            if not idx.is_file():
                fails.append(f"{entry.name}/{date_dir.name}/ 缺 index.json")
                continue
            try:
                data = json.loads(idx.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                fails.append(f"{entry.name}/{date_dir.name}/index.json 解析失败：{e}")
                continue
            for k in ("case", "date", "verdict", "artifacts"):
                if k not in data:
                    fails.append(f"{entry.name}/{date_dir.name}/index.json 缺键 {k}")
            if data.get("date") != date_dir.name:
                fails.append(f"{entry.name}/{date_dir.name}/index.json 的 date="
                             f"{data.get('date')} 与目录名不一致")
    return fails


def check_cases(root: Path) -> list[str]:
    """单元轨：cases/<P0N>/results/ 只查平铺文件与体积红线。"""
    fails: list[str] = []
    if not root.is_dir():
        return [f"cases 目录不存在：{root}"]

    for pkg in sorted(root.iterdir()):
        if not pkg.is_dir() or pkg.name.startswith("_") or pkg.name.startswith("."):
            continue
        if not PKG_RE.match(pkg.name):
            continue
        res = pkg / "results"
        if not res.is_dir():
            continue
        for entry in visible(res):
            rel = f"cases/{pkg.name}/results/{entry.name}"
            if entry.is_file():
                fails.append(f"{rel}：单元轨根下不许平铺文件（应放进一次运行的子目录）")
                continue
            for f in entry.rglob("*"):
                if f.is_file() and f.stat().st_size > SIZE_LIMIT:
                    mb = f.stat().st_size / 1024 / 1024
                    fails.append(f"{rel}/{f.relative_to(entry)}：{mb:.0f} MB > 100 MB"
                                 f"（体积红线，须 gitignore 或不入库）")
    return fails


def self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="res_self_"))
    try:
        good = tmp / "P99_SelfTest" / "2026-11-10"
        good.mkdir(parents=True)
        (good / "index.json").write_text(json.dumps(
            {"case": "P99", "date": "2026-11-10", "verdict": "inconclusive",
             "artifacts": ["a.csv"]}), encoding="utf-8")
        if check(tmp):
            print("self-test: good tree should pass: %r" % check(tmp), file=sys.stderr)
            return 1

        (tmp / "stray.csv").write_text("x", encoding="utf-8")
        if not any("根下直接放文件" in f for f in check(tmp)):
            print("self-test: stray root file not caught", file=sys.stderr)
            return 1
        (tmp / "stray.csv").unlink()

        (tmp / "P99_SelfTest" / "flat.csv").write_text("x", encoding="utf-8")
        if not any("下直接放文件" in f for f in check(tmp)):
            print("self-test: flat file in paper dir not caught", file=sys.stderr)
            return 1
        (tmp / "P99_SelfTest" / "flat.csv").unlink()

        (tmp / "P99_SelfTest" / "2026-11-11").mkdir()
        if not any("缺 index.json" in f for f in check(tmp)):
            print("self-test: missing index.json not caught", file=sys.stderr)
            return 1
        (tmp / "P99_SelfTest" / "2026-11-11").rmdir()

        # --- 单元轨（--also-cases）---
        cases = tmp / "cases"
        good_case = cases / "P99_SelfTest" / "results" / "run_a"
        good_case.mkdir(parents=True)
        (good_case / "point_00_base.csv").write_text("x", encoding="utf-8")
        if check_cases(cases):
            print("self-test: good unit track should pass: %r" % check_cases(cases), file=sys.stderr)
            return 1

        flat = cases / "P99_SelfTest" / "results" / "flat.csv"
        flat.write_text("x", encoding="utf-8")
        if not any("单元轨根下不许平铺文件" in f for f in check_cases(cases)):
            print("self-test: flat file in unit-track root not caught", file=sys.stderr)
            return 1
        flat.unlink()

        if not any("体积红线" in f for f in _size_self_test(cases)):
            print("self-test: oversized file in unit track not caught", file=sys.stderr)
            return 1

        print("self-test: 2 正例（交付轨 + 单元轨）+ 5 负例全部符合预期")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _size_self_test(cases: Path) -> list[str]:
    """用稀疏文件造一个 > 100 MB 的假产物，验证体积判据（不真占盘）。"""
    big = cases / "P99_SelfTest" / "results" / "run_a" / "huge.fsp"
    try:
        with open(big, "wb") as fh:
            fh.truncate(SIZE_LIMIT + 1)
    except OSError:
        return []
    try:
        return check_cases(cases)
    finally:
        big.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="results/ 落位门禁（双轨）")
    ap.add_argument("--root", default=None, help="results 根（默认仓库 results/）")
    ap.add_argument("--also-cases", action="store_true",
                    help="同时检查单元轨 cases/<P0N>/results/（平铺文件 + 体积红线）")
    ap.add_argument("--cases-root", default=None, help="cases 根（默认仓库 cases/）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = Path(args.root) if args.root else RESULTS
    fails = check(root)
    cases_root = Path(args.cases_root) if args.cases_root else CASES
    if args.also_cases:
        fails += check_cases(cases_root)
    if args.json:
        print(json.dumps({"root": str(root),
                          "cases_root": str(cases_root) if args.also_cases else None,
                          "failures": fails}, ensure_ascii=False, indent=2))
    else:
        for f in fails:
            print("[FAIL] " + f)
        tag = "  (含单元轨)" if args.also_cases else ""
        print(f"\n汇总：FAIL={len(fails)}  root={root}{tag}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
