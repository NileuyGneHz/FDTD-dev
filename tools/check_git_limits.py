#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
check_git_limits.py -- 提交 GitHub 前的体积体检
================================================================================

作用
    在 git add / git push 之前，先告诉你哪些文件会挡住推送：

    ERROR  单文件 > 100 MB 且未被 .gitignore 排除   -> GitHub 直接拒收
    WARN   单文件 50-100 MB 且未被排除              -> GitHub 会警告
    NOTE   已被排除的大文件                         -> 不会进备份，请另行保存

    最后给出「本次将要提交」的文件数与总体积，以及最大的 10 个文件。

为什么需要它
    一旦 7.4 GB 的课程视频或 331.8 MB 的 .fsp 混进 git 历史，.git 目录会跟着膨胀，
    清理需要 git filter-repo 重写历史，代价很高。**在第一次 git add 之前拦住**最省事。

用法
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/check_git_limits.py                  # 默认识别脚本所在目录的上级为仓库根
    "$PY" tools/check_git_limits.py --root D:\tmp\x  # 指定其他目录

判定方式
    是 git 仓库  -> 用 git 自己算：git ls-files（已跟踪）+ git ls-files --others
                    --exclude-standard（未跟踪且未被忽略）= 将来会提交的全集。
                    被忽略的大文件用 --others --ignored --exclude-standard 取出。
    还不是仓库   -> 退化为「简化版 .gitignore 匹配」，结果标注为「估算」。
                    （建议先 git init 再跑，得到精确结果。）

退出码
    0 = 无 ERROR    1 = 有 ERROR（必须先处理再提交）
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认 cp936，中文路径会乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

HARD_LIMIT = 100 * 1024 * 1024   # GitHub 单文件硬限：超出直接拒收
WARN_LIMIT = 50 * 1024 * 1024    # GitHub 提示阈值
TOTAL_NOTE = 1024 * 1024 * 1024  # 仓库建议 < 1 GB


def fmt(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    return f"{n / 1024 ** 2:.1f} MB"


# ----------------------------------------------------------------------------
#  git 交互
# ----------------------------------------------------------------------------
def _git(root: Path, *args: str):
    """跑 git，返回 bytes；失败返回 None。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def is_repo(root: Path) -> bool:
    out = _git(root, "rev-parse", "--is-inside-work-tree")
    return out is not None and out.strip() == b"true"


def _zsplit(raw: bytes) -> list[str]:
    return [p for p in raw.decode("utf-8", "replace").split("\0") if p]


def git_candidates(root: Path) -> tuple[list[Path], list[Path]]:
    """返回 (将来会被提交的文件, 被 .gitignore 排除的文件)。"""
    will: list[Path] = []
    for args in (("ls-files", "-z"),
                 ("ls-files", "--others", "--exclude-standard", "-z")):
        raw = _git(root, *args)
        if raw:
            will += [root / p for p in _zsplit(raw)]

    ignored: list[Path] = []
    raw = _git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    if raw:
        ignored += [root / p for p in _zsplit(raw)]

    return _dedup_existing(will), _dedup_existing(ignored)


def _dedup_existing(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        if p.is_file():
            out.append(p)
    return out


# ----------------------------------------------------------------------------
#  退化模式：简化版 .gitignore 匹配
# ----------------------------------------------------------------------------
def load_patterns(root: Path) -> list[str]:
    gi = root / ".gitignore"
    if not gi.is_file():
        return []
    pats: list[str] = []
    for line in gi.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.rstrip()
        if not s or s.lstrip().startswith("#"):
            continue
        pats.append(s)
    return pats


def match_path(rel: str, is_dir: bool, pattern: str) -> bool:
    """单个 gitignore 模式是否命中（简化实现，够本项目用）。"""
    neg = pattern.startswith("!")
    pat = pattern[1:] if neg else pattern
    dir_only = pat.endswith("/")
    pat = pat.strip("/")
    if not pat:
        return False
    parts = rel.split("/")
    if "/" in pat:
        # 路径型模式（含 ** 时 fnmatch 的 * 也能跨越 /，足够近似）
        return fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/")
    # 名字型模式：匹配任意层级
    for i, comp in enumerate(parts):
        if fnmatch.fnmatch(comp, pat):
            if i < len(parts) - 1:      # 命中中间目录 -> 整棵子树
                return True
            if is_dir:                  # 末段是目录
                return True
            return not dir_only         # 末段是文件；dir_only 模式不算命中
    return False


def is_ignored(rel: str, is_dir: bool, patterns: list[str]) -> bool:
    """last-match-wins 语义。"""
    ignored = False
    for pat in patterns:
        neg = pat.startswith("!")
        if match_path(rel, is_dir, pat):
            ignored = not neg
    return ignored


def scan_filesystem(root: Path, patterns: list[str]) -> tuple[list[Path], list[Path]]:
    will: list[Path] = []
    ignored: list[Path] = []
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".git/") or rel == ".git":
            continue
        try:
            is_dir = p.is_dir()
        except OSError:
            continue
        if is_ignored(rel, is_dir, patterns):
            if p.is_file():
                ignored.append(p)
            continue
        if p.is_file():
            will.append(p)
    return will, ignored


# ----------------------------------------------------------------------------
#  主流程
# ----------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="GitHub 提交前体积体检（>100MB 单文件会拒收）"
    )
    ap.add_argument("--root", default=None, help="仓库根目录，默认取脚本上级目录")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"ERROR: 目录不存在: {root}")
        return 1

    repo = is_repo(root)
    if repo:
        will, ignored = git_candidates(root)
        mode = "精确（git 仓库，用 git 自身判定）"
    else:
        patterns = load_patterns(root)
        will, ignored = scan_filesystem(root, patterns)
        mode = "估算（尚未 git init，用简化版 .gitignore 匹配）"

    errors: list[tuple[Path, int]] = []
    warns: list[tuple[Path, int]] = []
    for p in will:
        try:
            s = p.stat().st_size
        except OSError:
            continue
        if s > HARD_LIMIT:
            errors.append((p, s))
        elif s > WARN_LIMIT:
            warns.append((p, s))

    ignored_big: list[tuple[Path, int]] = []
    for p in ignored:
        try:
            s = p.stat().st_size
        except OSError:
            continue
        if s > WARN_LIMIT:
            ignored_big.append((p, s))

    total = 0
    for p in will:
        try:
            total += p.stat().st_size
        except OSError:
            pass

    W = 78
    print("=" * W)
    print("  GitHub 提交前体积体检")
    print("=" * W)
    print(f"  仓库根 : {root}")
    print(f"  判定方式: {mode}")
    print(f"  将提交 : {len(will)} 个文件，合计 {fmt(total)}")
    print(f"  已排除 : {len(ignored)} 个文件（不进仓库）")
    print()

    # --- ERROR ---
    if errors:
        print(f"[ERROR] {len(errors)} 个文件超过 100 MB 硬限，push 会被直接拒绝！")
        for p, s in sorted(errors, key=lambda x: -x[1]):
            print(f"        {fmt(s):>10}  {p.relative_to(root).as_posix()}")
        print("        处理办法：加进 .gitignore 第 2 节，或改用 Git LFS")
        print("                 （见 readme/03_使用说明.md 第 6 节）")
    else:
        print("[ERROR] 无 —— 没有超过 100 MB 的待提交文件。")
    print()

    # --- WARN ---
    if warns:
        print(f"[WARN] {len(warns)} 个文件在 50-100 MB 区间，GitHub 会提示（不会拒收）：")
        for p, s in sorted(warns, key=lambda x: -x[1]):
            print(f"        {fmt(s):>10}  {p.relative_to(root).as_posix()}")
        print("        体积可接受就保留；想更轻则加进 .gitignore 或改用 LFS。")
    else:
        print("[WARN] 无 —— 没有 50-100 MB 的待提交文件。")
    print()

    # --- NOTE：被排除的大文件（提醒这些不在备份里）---
    if ignored_big:
        print(f"[NOTE] 以下 {len(ignored_big)} 个大文件已被 .gitignore 排除，不会进备份：")
        for p, s in sorted(ignored_big, key=lambda x: -x[1]):
            print(f"        {fmt(s):>10}  {p.relative_to(root).as_posix()}")
        print("        如需备份：Git LFS（.gitattributes 文末有步骤）或网盘。")
        print()

    # --- 总体积 ---
    if total > TOTAL_NOTE:
        print(f"[NOTE] 将提交总体积 {fmt(total)}，超过 GitHub 建议的 1 GB，建议精简。")
    else:
        print(f"[NOTE] 将提交总体积 {fmt(total)}，在 GitHub 建议范围（< 1 GB）内。")
    print()

    # --- 最大的 10 个 ---
    sized = []
    for p in will:
        try:
            sized.append((p, p.stat().st_size))
        except OSError:
            pass
    sized.sort(key=lambda x: -x[1])
    print("  将提交的最大 10 个文件：")
    for p, s in sized[:10]:
        print(f"        {fmt(s):>10}  {p.relative_to(root).as_posix()}")
    print("=" * W)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
