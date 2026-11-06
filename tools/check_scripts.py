#!/usr/bin/env python3
"""check_scripts.py — 包内不许有 .py。

    python tools/check_scripts.py

规则（docs/constitution/script-contract.md）：
    能力脚本 → skills/<name>/scripts/
    模型脚本（.lsf） → 单元内 model/
    一次性脚本 → _scratch/

历史遗留写在 tools/check_scripts.allowlist（一行一个相对路径），只能减不能增。

退出码 0 = 通过。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNITS = ["cases", "projects"]
ALLOWLIST = ROOT / "tools" / "check_scripts.allowlist"


def load_allow() -> set[str]:
    if not ALLOWLIST.is_file():
        return set()
    lines = []
    for ln in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            lines.append(ln.replace("\\", "/"))
    return set(lines)


def main() -> int:
    allow = load_allow()
    violations: list[tuple[str, str]] = []

    for unit in UNITS:
        base = ROOT / unit
        if not base.is_dir():
            continue
        for scripts in base.glob("*/scripts"):
            if not scripts.is_dir():
                continue
            for py in sorted(scripts.rglob("*.py")):
                rel = py.relative_to(ROOT).as_posix()
                if rel in allow:
                    continue
                violations.append((rel, py.parent.parent.name))

    if not violations:
        print("OK  包内没有 .py")
        if allow:
            print(f"     allowlist 仍有 {len(allow)} 条历史遗留")
        return 0

    print(f"FAIL 包内发现 {len(violations)} 个 .py\n")
    for rel, unit in violations:
        print(f"  {rel}")
        print(f"     → 若会被第二个课题用到：迁到 skills/<合适技能>/scripts/ 并遵守 CLI 契约")
        print(f"     → 若只服务一次：移到 _scratch/，不要留在这个单元里")
        print(f"     → 若确实是历史包袱：写进 tools/check_scripts.allowlist（只能减不能增）")
    print(f"\n建议技能归属：建模/求解类 → fdtd-lumerical-unitcell-simulation；"
          f"出图类 → fdtd-result-figure（待建）；文献类 → fdtd-paper-parameter-extraction")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
