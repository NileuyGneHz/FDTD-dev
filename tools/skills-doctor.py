#!/usr/bin/env python3
"""skills-doctor.py — 六项宿主接入体检。

    python tools/skills-doctor.py

检查项（docs/constitution/host-integration.md §8.3）：
    [1] .git 存在（DSH 靠它定项目根）
    [2] 两处入口是真实目录
    [3] 入口条数 == 合格技能数（排除 _TEMPLATE）
    [4] 每条 junction 可达，且入口名 == 目标 SKILL.md 的 name
    [5] .dsh/skills 为空（rank 100 会静默压过 .agents/skills）
    [6] 用户级同名技能指向不同本体（跨项目冲突）

退出码 0 = ALL GREEN。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
ENTRIES = [ROOT / ".agents" / "skills", ROOT / ".workbuddy" / "skills"]
DSH_LOCAL = ROOT / ".dsh" / "skills"
USER_WORKBUDDY = Path.home() / ".workbuddy" / "skills"
NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)

fails: list[str] = []
warns: list[str] = []


def ok(n: int, msg: str) -> None:
    print(f"  [{n}] OK    {msg}")


def bad(n: int, msg: str) -> None:
    print(f"  [{n}] FAIL  {msg}")
    fails.append(msg)


def warn(n: int, msg: str) -> None:
    print(f"  [{n}] WARN  {msg}")
    warns.append(msg)


def is_link(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except OSError:
        return False


def norm(p) -> str:
    """去掉 Windows 扩展前缀 \\?\，再 realpath + normcase。"""
    s = str(p)
    if s.startswith("\\\\?\\"):
        s = s[4:]
    return os.path.normcase(os.path.realpath(s))


def name_of(skill_dir: Path) -> str | None:
    f = skill_dir / "SKILL.md"
    if not f.is_file():
        return None
    m = NAME_RE.search(f.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def main() -> int:
    print(f"仓库: {ROOT}\n")

    # [1]
    if (ROOT / ".git").exists():
        ok(1, ".git 存在")
    else:
        bad(1, ".git 缺失 —— DSH 找不到项目根，从子目录开会话将看不到任何项目技能")

    skills = {}
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        n = name_of(d)
        if n is None:
            bad(3, f"skills/{d.name} 无 SKILL.md")
            continue
        if n != d.name:
            bad(3, f"skills/{d.name} 的 name={n} 与目录名不一致")
            continue
        skills[n] = d
    print(f"       合格技能 {len(skills)} 个")

    # [2] [3] [4]
    for entry in ENTRIES:
        rel = entry.relative_to(ROOT).as_posix()
        if not entry.exists():
            bad(2, f"{rel} 不存在")
            continue
        if is_link(entry):
            bad(2, f"{rel} 是链接，必须是真实目录（DSH 会整根丢弃）")
            continue
        ok(2, f"{rel} 是真实目录")

        items = sorted(entry.iterdir())
        if len(items) != len(skills):
            bad(3, f"{rel} 有 {len(items)} 条，技能数 {len(skills)}")
        else:
            ok(3, f"{rel} 条数一致（{len(items)}）")

        for item in items:
            if item.name not in skills:
                bad(4, f"{rel}/{item.name} 没有对应技能（孤儿）")
                continue
            if not is_link(item):
                bad(4, f"{rel}/{item.name} 不是 junction")
                continue
            target = (entry / item.name).resolve()
            if not target.exists():
                bad(4, f"{rel}/{item.name} 断链 → {target}")
                continue
            n = name_of(target)
            if n != item.name:
                bad(4, f"{rel}/{item.name} 指向的 SKILL.md name={n}")
                continue
        ok(4, f"{rel} 全部可达且名字一致")

    # [5]
    if not DSH_LOCAL.exists():
        ok(5, ".dsh/skills 不存在（等价于空）")
    else:
        leftover = [p.name for p in DSH_LOCAL.iterdir()]
        if leftover:
            bad(5, f".dsh/skills 非空（rank 100 会静默压过 .agents/skills）: {', '.join(leftover)}")
        else:
            ok(5, ".dsh/skills 为空")

    # [6]
    if USER_WORKBUDDY.exists():
        clash = []
        for item in USER_WORKBUDDY.iterdir():
            if item.name not in skills:
                continue
            try:
                tgt = os.readlink(item)
            except OSError:
                tgt = None
            if tgt is not None and norm(tgt) != norm(skills[item.name]):
                clash.append(item.name)
        if clash:
            warn(6, f"用户级同名但指向不同本体（会互相覆盖）: {', '.join(clash)}")
        else:
            ok(6, "用户级无跨项目同名冲突")
    else:
        ok(6, "用户级目录不存在，无冲突")

    print()
    if fails:
        print(f"FAIL {len(fails)} 项" + (f"，WARN {len(warns)} 项" if warns else ""))
        return 1
    print("ALL GREEN" + (f"（{len(warns)} 项 WARN）" if warns else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
