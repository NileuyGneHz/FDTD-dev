# -*- coding: utf-8 -*-
"""check_packages.py —— 本技能入口的薄壳，实现在 tools/check_packages.py。

为什么是壳而不是实现
    2026-11-08 实测：这里原本是一份完整副本，`packages/` → `cases/` 改名后没跟上，
    于是 `WS_ROOT` 解析成 `skills/fdtd-package-workspace/packages`（不存在），
    任何调用都直接 `[ERROR] 找不到 packages 目录`。而 `tools/check_packages.py`
    早已改好（`cases`、UTF-8 输出、`paper/model/results/notes` 四目录）。
    两份实现必然漂移，所以这里只保留一个转发，唯一实现在 tools/。

用法（与原命令完全一致，退出码也透传）
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" skills/fdtd-package-workspace/scripts/check_packages.py
    "$PY" skills/fdtd-package-workspace/scripts/check_packages.py --pkg P03 --strict
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "tools" / "check_packages.py"


def main() -> int:
    if not TARGET.is_file():
        print(f"[ERROR] 找不到唯一实现: {TARGET}", file=sys.stderr)
        return 2
    try:
        runpy.run_path(str(TARGET), run_name="__main__")
    except SystemExit as e:  # 透传被转发脚本的退出码
        return int(e.code or 0)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
