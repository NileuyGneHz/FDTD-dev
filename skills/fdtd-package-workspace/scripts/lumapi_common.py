# -*- coding: utf-8 -*-
"""lumapi_common.py — 转发壳（唯一实现在 `library/py/lumapi_common.py`）

为什么是壳而不是副本
--------------------
本文件曾经是唯一实现的**逐字节副本**（10660 B，`diff` 无输出）。
D-005（`check_packages.py`）与 D-006（`migrate_classes_to_packages.py`）已经因为同一原因
各烂过一次：改名之后只有一份被改，另一份静默失效。这是第三次，所以改成壳。

行为
----
导入本模块 = 执行 `library/py/lumapi_common.py` 并把它的公开名字注入本模块命名空间。
因此 `from lumapi_common import open_fdtd` 在任何调用方看来完全不变。

找不到唯一实现时**直接 ImportError**，绝不回退到「本地副本」——那种回退正是病灶。

历史
----
2026-11-11：唯一实现从 `_shared/` 迁到 `library/py/`（`workspace-layout.md` §10）。
本壳的指向同步改；`_shared/` 目录已删除。
"""

from __future__ import annotations

import pathlib
import runpy

# <repo>/library/py/lumapi_common.py
# __file__ = <repo>/skills/fdtd-package-workspace/scripts/lumapi_common.py
#   parents[0] = scripts  [1] = fdtd-package-workspace  [2] = skills  [3] = <repo>
_SHARED = pathlib.Path(__file__).resolve().parents[3] / "library" / "py" / "lumapi_common.py"

if not _SHARED.is_file():  # 宁可炸，也不要悄悄用别的实现
    raise ImportError(
        "找不到 lumapi_common 的唯一实现: %s\n"
        "本文件只是转发壳，不含实现。请确认 library/py/ 未被删除或改名。" % _SHARED
    )

# run_name 故意不是 "__main__"：否则会执行共享模块底部的自测块
_NS = runpy.run_path(str(_SHARED), run_name="_lumapi_common_shared")

globals().update({k: v for k, v in _NS.items() if not k.startswith("__")})
