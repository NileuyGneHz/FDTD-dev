# 路径约定

> 违反任意一条 → 仿真会在最贵的地方失败，且报错信息误导。

## 1. 纯 ASCII

**目录名、文件名、`.fsp` 路径，全部只能用 ASCII**（空格可以，中文不行）。

- GPU 引擎（`fdtd-engine.exe`）对非 ASCII 路径报 **Windows 1113 `ERROR_NO_UNICODE_TRANSLATION`**，
  Job Manager 弹窗显示为乱码。
- CPU 引擎（`fdtd-engine-msmpi.exe`）没有这个问题——**所以"CPU 能跑"不能证明路径合规**。
- 判断依据永远看 `<工程名>_p0.log`，不看弹窗。

历史遗留的中文目录名要改，**并记录 old → new 映射**在该单元的 `notes/`。

## 2. 工作根

| 概念 | 值 |
|---|---|
| 工作区根 | `F:\Lumercial_WS\FDTD_WS` |
| 会话启动目录 | **必须是工作区根**（见根 `AGENTS.md` 铁律 1） |
| 临时脚本 | `_scratch\`，**不要写 `%TEMP%`** |
| 交付物 | 单元内 `results\` |

## 3. 零外写

- 不写单元目录之外（`_scratch` 除外）。
- 不写 `cases\` 下的任何文件（只读）。
- 不改 `paper\` 里的 PDF。

## 4. 体积

| 项 | 红线 | 依据 |
|---|---|---|
| 单文件 | **> 100 MB 不入库** | GitHub 直接拒收，不是警告 |
| `*.mp4` / `*.rar` / `*.zip` | 全忽略 | 见 `.gitignore` 第 1 条 |
| `.fsp` | 只有超限的那一个被忽略，其余入库 | 见 `.gitignore` 第 2 条 |
| `*_p0.log` | **必须保留** | 三判据之一，删了就无法证明算过 |

提交前跑 `python tools/check_git_limits.py`，`ERROR=0` 才推。

## 5. 许可席位

每个 `lumapi.FDTD()` = 一个 `fdtd-solutions.exe` = 占 1 个许可席位。
`close()` 必须落在 `finally`；批量脚本漏一个就少一个席位。
