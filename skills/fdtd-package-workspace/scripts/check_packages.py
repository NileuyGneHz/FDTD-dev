# -*- coding: utf-8 -*-
"""
check_packages.py —— 打包文件夹自检工具
================================================================================

用途
    协作前跑一次，确认「论文 <-> fsp」的打包结构完整、命名合规。
    把"靠记忆维护目录"变成"靠脚本校验"。

用法
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/check_packages.py                # 检查全部包
    "$PY" tools/check_packages.py --pkg P03      # 只查 P03
    "$PY" tools/check_packages.py --json         # 输出 JSON（给 agent 解析）
    "$PY" tools/check_packages.py --strict       # 有警告也算失败（退出码 1）

检查项
    [ERROR] 包目录名不符合 P0N_xxx 规范
    [ERROR] 缺 README.md
    [ERROR] README.md 里还有未填的占位符 <...>
    [ERROR] fsp/ 下有非 ASCII 文件名的文件      <- GPU 引擎会崩，最要紧
    [ERROR] 有 .fsp 但没有对应 README 记录
    [WARN ] paper/ 为空（论文未归档）
    [WARN ] scripts/ 与 results/ 同时为空（包刚建，正常）
    [INFO ] 各子目录文件数、包总体积

退出码
    0 = 无 ERROR（有 WARN 也返回 0，除非 --strict）
    1 = 存在 ERROR（或 --strict 下有 WARN）

⚠️ 本脚本**只读**，绝不修改任何文件。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---- 配置 ----------------------------------------------------------------

# packages 目录 = 本脚本所在目录的上一级 / packages
TOOLS_DIR = Path(__file__).resolve().parent
WS_ROOT = TOOLS_DIR.parent
PKG_ROOT = WS_ROOT / "packages"

# 包目录命名：P01_xxx / P10_xxx
PKG_NAME_RE = re.compile(r"^P\d{2}_[A-Za-z0-9_]+$")

# 标准子目录（缺了给 WARN，不算 ERROR）
SUBDIRS = ["paper", "fsp", "scripts", "results", "notes"]

# README 里不允许残留的占位符
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,60}>")

# 这些占位符是"格式说明"性质，不算未填（模板本身允许）
IGNORE_PLACEHOLDERS = {"<包名>", "<一句话主题>", "<P0N>", "<fsp\\或 scripts\\下第一个该跑的脚本>"}

# 忽略的目录
IGNORE_DIRS = {"_TEMPLATE"}

# 占位文件：不算"真实内容"（否则空目录会因为放了 .gitkeep 而不再被报"为空"）
PLACEHOLDER_FILES = {".gitkeep", ".keep", ".gitignore"}


def real_files(d: Path) -> list[Path]:
    """列出目录下的真实文件，排除占位文件。"""
    return [f for f in d.rglob("*") if f.is_file() and f.name not in PLACEHOLDER_FILES]


# ---- 工具函数 ------------------------------------------------------------


def is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def human(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f}{unit}"
        nbytes /= 1024
    return f"{nbytes:.1f}TB"


class Issue:
    def __init__(self, level: str, pkg: str, msg: str):
        self.level = level  # ERROR / WARN / INFO
        self.pkg = pkg
        self.msg = msg

    def as_dict(self):
        return {"level": self.level, "pkg": self.pkg, "msg": self.msg}

    def __str__(self):
        return f"[{self.level:5}] {self.pkg:26} {self.msg}"


# ---- 单包检查 ------------------------------------------------------------


def check_one_pkg(pkg_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    name = pkg_dir.name

    # 1) 目录命名
    if not PKG_NAME_RE.match(name):
        issues.append(
            Issue("ERROR", name, f"目录名不符合 'P0N_<英文短名>' 规范（建议改名，勿用中文）")
        )

    # 2) README
    readme = pkg_dir / "README.md"
    if not readme.exists():
        issues.append(Issue("ERROR", name, "缺 README.md（agent 无法接管）"))
    else:
        try:
            txt = readme.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            issues.append(Issue("ERROR", name, f"README.md 读取失败: {e}"))
            txt = ""
        if txt:
            left = {
                m.group(0)
                for m in PLACEHOLDER_RE.finditer(txt)
                if m.group(0) not in IGNORE_PLACEHOLDERS
            }
            if left:
                sample = "、".join(sorted(left)[:5])
                more = f" 等 {len(left)} 处" if len(left) > 5 else ""
                issues.append(
                    Issue("ERROR", name, f"README.md 有未填占位符: {sample}{more}")
                )

    # 3) 子目录 + 非 ASCII 文件名（最要紧）
    counts = {}
    for sub in SUBDIRS:
        d = pkg_dir / sub
        if not d.is_dir():
            issues.append(Issue("WARN", name, f"缺子目录 {sub}\\"))
            counts[sub] = 0
            continue
        files = real_files(d)
        if sub == "paper":
            # paper\ 里只有 PDF 算"论文"；md（自测题、笔记）单独计数，否则会虚高
            counts["paper"] = sum(1 for f in files if f.suffix.lower() == ".pdf")
            counts["paper_md"] = sum(1 for f in files if f.suffix.lower() != ".pdf")
        else:
            counts[sub] = len(files)

        # ASCII 检查（只对 fsp / scripts —— 这两个目录会进仿真路径）
        if sub in ("fsp", "scripts"):
            bad = [f for f in files if not is_ascii(f.name)]
            for f in bad:
                rel = f.relative_to(pkg_dir)
                issues.append(
                    Issue(
                        "ERROR",
                        name,
                        f"文件名含非 ASCII -> GPU 引擎必崩: {rel}",
                    )
                )

    # 4) 是否有 .fsp
    fsp_dir = pkg_dir / "fsp"
    fsp_files = list(fsp_dir.rglob("*.fsp")) if fsp_dir.is_dir() else []
    has_fsp = len(fsp_files) > 0

    # 5) paper 为空
    if counts.get("paper", 0) == 0:
        issues.append(Issue("WARN", name, "paper\\ 为空（论文未归档）"))

    # 6) 新包特征
    if counts.get("scripts", 0) == 0 and counts.get("results", 0) == 0 and not has_fsp:
        issues.append(Issue("WARN", name, "scripts\\ 与 results\\ 均为空且无 .fsp（新包？）"))

    # 7) 有 fsp 但没 _p0.log —— 可能从未实跑
    if has_fsp:
        for f in fsp_files:
            log = f.with_name(f.stem + "_p0.log")
            if not log.exists():
                issues.append(
                    Issue(
                        "WARN",
                        name,
                        f"{f.name} 无同名 _p0.log（未实跑过？或日志在别处）",
                    )
                )

    # 8) 统计体积
    total = sum(f.stat().st_size for f in real_files(pkg_dir))
    detail = "  ".join(f"{k}={v}" for k, v in counts.items())
    issues.append(Issue("INFO", name, f"{detail}  体积={human(total)}  fsp={len(fsp_files)}"))

    return issues


# ---- 主流程 --------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="FDTD 打包文件夹自检")
    ap.add_argument("--pkg", help="只检查指定包，如 P03")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--strict", action="store_true", help="有 WARN 也算失败")
    args = ap.parse_args()

    if not PKG_ROOT.is_dir():
        print(f"[ERROR] 找不到 packages 目录: {PKG_ROOT}", file=sys.stderr)
        return 1

    pkg_dirs = sorted(
        d
        for d in PKG_ROOT.iterdir()
        if d.is_dir() and d.name not in IGNORE_DIRS and not d.name.startswith(".")
    )
    if args.pkg:
        pkg_dirs = [d for d in pkg_dirs if d.name.startswith(args.pkg)]
        if not pkg_dirs:
            print(f"[ERROR] 没有匹配 '{args.pkg}' 的包", file=sys.stderr)
            return 1

    all_issues: list[Issue] = []
    for d in pkg_dirs:
        all_issues.extend(check_one_pkg(d))

    errors = [i for i in all_issues if i.level == "ERROR"]
    warns = [i for i in all_issues if i.level == "WARN"]
    infos = [i for i in all_issues if i.level == "INFO"]

    if args.json:
        print(
            json.dumps(
                {
                    "packages": [d.name for d in pkg_dirs],
                    "errors": len(errors),
                    "warnings": len(warns),
                    "issues": [i.as_dict() for i in all_issues],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if errors else 0

    # ---- 人类可读输出 ----
    print("=" * 78)
    print(f"打包自检  |  根目录 {PKG_ROOT}")
    print(f"共 {len(pkg_dirs)} 个包")
    print("=" * 78)

    for d in pkg_dirs:
        mine = [i for i in all_issues if i.pkg == d.name]
        errs = [i for i in mine if i.level == "ERROR"]
        wns = [i for i in mine if i.level == "WARN"]
        infos_mine = [i for i in mine if i.level == "INFO"]

        if errs:
            mark = "[X]"
        elif wns:
            mark = "[!]"
        else:
            mark = "[OK]"
        print(f"\n{mark} {d.name}")

        for i in infos_mine:
            print(f"      {i.msg}")
        for i in wns:
            print(f"      WARN  {i.msg}")
        for i in errs:
            print(f"      ERR   {i.msg}")

    print("\n" + "=" * 78)
    print(f"汇总:  ERROR={len(errors)}   WARN={len(warns)}")
    if errors:
        print("\nERROR 列表:")
        for i in errors:
            print("  " + str(i))
    print("=" * 78)

    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
