#!/usr/bin/env python3
"""skills-wire.py — 重建两处宿主入口的 junction。

用法：
    python tools/skills-wire.py                 # dry-run，只打印计划
    python tools/skills-wire.py --apply         # 执行
    python tools/skills-wire.py --apply --prune # 顺便删掉已无对应技能的入口

规则（docs/constitution/host-integration.md）：
    1. 只挂「目录名 == frontmatter name」且存在 SKILL.md 的条目
    2. 跳过以 _ 开头的脚手架（_TEMPLATE 等）
    3. 幂等：已正确 → 跳过；指向错误 → 报错，不静默覆盖
    4. 入口必须是真实目录（根是链接会被 DSH 整根丢弃）

零第三方依赖，只用标准库。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
ENTRIES = [ROOT / ".agents" / "skills", ROOT / ".workbuddy" / "skills"]
NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)


def is_link(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except OSError:
        return False


def link_target(p: Path) -> str | None:
    try:
        return os.readlink(p)
    except OSError:
        return None


def real_dir(p: Path) -> bool:
    return p.is_dir() and not is_link(p)


def norm(p) -> str:
    """规范化：去掉 Windows 扩展前缀 \\?\，再 realpath + normcase。"""
    s = str(p)
    if s.startswith("\\\\?\\"):
        s = s[4:]
    return os.path.normcase(os.path.realpath(s))


def frontmatter_name(skill_dir: Path) -> str | None:
    f = skill_dir / "SKILL.md"
    if not f.is_file():
        return None
    m = NAME_RE.search(f.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def valid_skills() -> list[tuple[str, Path]]:
    out = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        name = frontmatter_name(d)
        if name is None:
            print(f"  SKIP  {d.name}: 无 SKILL.md")
            continue
        if name != d.name:
            print(f"  FAIL  {d.name}: frontmatter name={name} 与目录名不一致")
            continue
        out.append((name, d))
    return out


def make_junction(link: Path, target: Path) -> None:
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError((r.stdout or "") + (r.stderr or ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--prune", action="store_true")
    args = ap.parse_args()

    skills = valid_skills()
    print(f"技能数: {len(skills)}")
    if not skills:
        print("没有合格技能，中止")
        return 1

    plan: list[str] = []
    plan += [f"OK    {n}  (已正确)" for n, _ in skills]  # 占位，下面细化
    actions = 0
    errors = 0

    for entry in ENTRIES:
        print(f"\n== {entry.relative_to(ROOT)} ==")
        if entry.exists() and not real_dir(entry):
            print("  FAIL  入口是链接，必须是真实目录；请先手工修好")
            errors += 1
            continue
        if not entry.exists():
            print("  新建目录")
            if args.apply:
                entry.mkdir(parents=True, exist_ok=True)

        wanted = {n for n, _ in skills}

        for name, sdir in skills:
            link = entry / name
            target = sdir
            if link.exists() or is_link(link):
                cur = link_target(link)
                if cur is not None and norm(cur) == norm(target):
                    print(f"  OK    {name}")
                    continue
                if cur is None:
                    print(f"  FAIL  {name}: 已存在且不是链接（真实目录/文件）")
                    errors += 1
                    continue
                print(f"  FIX   {name}: 指向 {cur} → 应指向 {target}")
                if args.apply:
                    os.rmdir(link)
                    make_junction(link, target)
                actions += 1
            else:
                print(f"  ADD   {name} -> {target}")
                if args.apply:
                    make_junction(link, target)
                actions += 1

        # 孤儿入口
        if entry.exists():
            for child in sorted(entry.iterdir()):
                if child.name in wanted:
                    continue
                if args.prune:
                    print(f"  PRUNE {child.name}: 没有对应技能")
                    if args.apply and is_link(child):
                        os.rmdir(child)
                    actions += 1
                else:
                    print(f"  WARN  {child.name}: 没有对应技能（--prune 可清理）")

    print(f"\n动作 {actions} 项，错误 {errors} 项" + ("（dry-run，未落盘）" if not args.apply else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
