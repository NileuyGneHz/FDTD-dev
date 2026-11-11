# D-010：`inspect_fsp.py --json` 在非 UTF-8 stdout 上崩，产物却已落盘

**状态**：`resolved`（2026-11-10）

## 根因

`main()` 末尾直接 `print(json.dumps(summary, ensure_ascii=False, indent=2))`，
而 `summary` 里带中文标点（如 `：`）。**进程的 stdout 编码不是 UTF-8 时**，
这一步抛 `UnicodeEncodeError: 'charmap' codec can't encode characters`。
产物四份 JSON 在此之前已全部写好，只有最后一步打印炸掉，进程 exit 1
—— 流水线把「读成功」误判成「读失败」。

### 订正：触发条件不是「中文 Windows 默认」

原文写「本机 Python 3.13 的 stdout 走 `encodings/cp1252.py`」。**这句已被实测推翻**：

| 条件 | stdout 编码 | exit | stdout 字节 |
|---|---|---|---|
| 本机默认（Git Bash 重定向到文件） | `utf-8` | **0** | 1840 |
| `PYTHONIOENCODING=cp1252` | `cp1252` | **1** | 0 |

本机默认是 `utf-8`，所以该缺陷**默认不触发**。它只在调用方的 stdout 编码不是 UTF-8 时出现
（显式 `PYTHONIOENCODING`、代码页 1252 的控制台、某些 CI/编辑器任务封装）。

结论：**现象真实，但归因是「编码由调用方决定」，不是「本机就是 cp1252」**。
这类缺陷不该靠「本机跑得过」来判定，因为触发条件不在仓库控制内。

## 修复

模块顶部（`import numpy as np` 之后）统一钉死 UTF-8：

```python
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:                       # 已被重定向的流无法 reconfigure
    pass
```

选 `reconfigure` 而不是只给最后一句加 `ensure_ascii=True`：脚本里**其他 print 也带中文**
（如「工程处于 layout 模式」），只修最后一行等于把同一颗雷留在别处。
写法与 `tools/check_acceptance.py`、`tools/check_results_layout.py` 一致。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS
B=_scratch/regress/2026-11-10/EXP-46
CFG=_scratch/regress/2026-11-09/EXP-13/cfg_p01.json

# 修前：强制 cp1252 -> exit 1、stdout 0 字节、5 份 JSON 已落盘
PYTHONIOENCODING=cp1252 "$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config "$CFG" --out $B/force_cp1252 --json > $B/force_cp1252/stdout.json; echo $?   # 1

# 修后：同一条件 -> exit 0、1846 字节、json.loads 通过
PYTHONIOENCODING=cp1252 "$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config "$CFG" --out $B/after_cp1252 --json > $B/after_cp1252/stdout.json; echo $?    # 0
```

实测（2026-11-10）：

| case | 条件 | 修前 | 修后 | 数值回归 |
|---|---|---|---|---|
| P01 `infrared_perfect_absorber.fsp` | `PYTHONIOENCODING=cp1252` | exit 1 / stdout 0 B | exit 0 / 1846 B / `json.loads` OK | `derived` 逐位相同，`peak_A=0.8196016 @ 6.1515 µm` |
| P09 `graphene_perfect_absorber.fsp` | 同上 | — | exit 0 / `errors=[]` / `status_counts={'ok': 1}` | `derived` 逐位相同，`peak_R=0.9857253106135158 @ 99.93 µm`，500 点 |

两条都同时覆盖了 `--json`（stdout 被消费）路径；P01 另跑了一次默认输出做对照。

## 影响面

- P05 本轮取证（2026-11-09）：4 个工程实际读取成功，仅打印失败，复现卡因此被记成「读失败」。
- 任何把 `--json` 接到管道、而自身 stdout 编码非 UTF-8 的调用方。

### 同类脚本实测（2026-11-10，`PYTHONIOENCODING=cp1252` 逐个跑）

判据不是「有没有 `ensure_ascii=False`」（16 个脚本里有它），而是**被测代码路径会不会 print 非 ASCII**。
所以逐个真跑，不靠阅读代码推断：

| 脚本 · 命令 | cp1252 下 | 说明 |
|---|---|---|
| `check_reproduction.py --case P01` | **CRASH（已修）** | `ok()` 的中文行必触发；门禁崩掉与判违规同为 exit 1，无法区分 |
| `inspect_fsp.py --json` | **CRASH（已修）** | 本缺陷主体 |
| `run_fdtd_sweep.py --dry-run` / 坏 spec | ok | 正常与错误路径的输出都是 ASCII |
| `build_fsp.py --dry-run --json` / 坏 spec | ok | 同上 |
| `make_figure.py --help` | ok | 同上 |
| `session_control.py --dry-run --json` / 缺 config | ok | 同上 |
| `run_lsf.py --dry-run` / 不存在的 lsf | ok | 同上 |
| `design_loop.py --help` | ok | 同上 |

结论：**风险真实但面窄**——目前只有两个脚本在真实路径上会崩，都已修。
其余脚本的中文只出现在「未被走到的分支」或写文件（写文件用 UTF-8，不受影响），
因此**没有**给全部 16 个脚本不加区分地套 `reconfigure`：那会掩盖一个更该问的问题
——为什么一台中文机器上 stdout 会是 cp1252。触发条件在调用方，仓库只能防御性钉死
自己最关键的出口（门禁 + 产物解析）。

`check_reproduction.py` 的修复验证：cp1252 下 `--case P01` 从 exit 1 变 **exit 0**，
输出与默认编码下**逐字节相同**（`diff` 无输出），`--self-test` 仍 `SELF-TEST PASS`
（12/12 规则被基础卡拦到，diverging 与 unmeasured-honesty 两个定向负对照通过）。
