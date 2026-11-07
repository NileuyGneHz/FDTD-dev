---
name: fdtd-lumerical-session-control
description: >
  在已有 Lumerical FDTD 工程上执行一轮「人定空间、agent 调参」闭环的白名单参数注入与结果读回：
  只改 search_space 内的尺寸，不重建几何；按项目已验证的两段式序列 run，
  读回监视器原始数据并写每轮台账。当需要在 Design 模式下微调尺寸/角度/占空比、
  复跑同一工程、排查 run 静默失效或需要逐轮可追溯证据时使用。
  触发词：微调整、增量改参、同工程复跑、白名单参数、两段式 run、iteration 台账。
agent_created: true
---

# Lumerical 单轮迭代执行器（白名单改参 + 已验证 run 序列）

## 概述

本技能是 L1「agent 调参闭环」的**执行层**：消费一个已建好的 `.fsp` + 一组参数，
产出 `iteration_NNN.fsp`、`iteration_NNN.json`（参数 / 原始结果 / 日志路径 / 耗时）。
它**不建模、不判读指标、不决定下一组参数**——选参数属
`fdtd-lumerical-design-loop`，从零建模属
`fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py`。

会话生命周期不在这里重写：`setup_env` / `open_fdtd` / `ascii_gate` /
`verify_and_run` 全部复用 `fdtd-package-workspace/scripts/lumapi_common.py`，
保持「一份实现原则」。

## CRITICAL（违反即停止）

1. **Reproduce 模式禁止注入任何参数**。L1 §③：为贴合文献改参数 = 数据造假；
   `Reproduce` + 非空 `params` 直接拒绝，不做任何仿真。
2. **`params` 必须是 `search_space` 的子集，且不得命中 `locked`**。越界即停、
   回去问人——材料 / 层序 / 拓扑是人的设计决策，不是 agent 的自由度。
3. **必须走两段式 run**：`save` → `close` → 新会话 `load` → `switchtolayout` →
   `run`。在建模会话里直接 `run()` **静默失效**（`fdtd-lumerical-headless` CRITICAL #1，
   本项目实测）。不要照搬外部 `lumopt` 的单 session 反复 run 写法。
4. **改对象之前必须 `switchtolayout()`**，否则报
   `you cannot modify most simulation objects while in analysis mode`。
5. **`--dry-run` 不得 import lumapi、不得开会话**。它在任何 `lumapi.FDTD()` 之前返回；
   dry-run 还开了 `fdtd-solutions.exe` 就是 bug。
6. **每轮 `save()` 到 `--out` 之后再 `close()`**。未保存的 headless 会话关闭时会弹
   「保存名字为 xxx」；且每个 `lumapi.FDTD()` 占 1 个许可席位，`close()` 必须在 `finally`。
7. **本技能不判读物理结果**。`getresult` 只做 JSON 化与数组截断，达标与否由
   `fdtd-lumerical-design-loop` 判断；不要在这里偷偷算 FOM 或放宽阈值。

## 核心工作流

1. 写 `config`：L1 三字段 `targets` / `locked` / `search_space`，本轮 `params`，
   `parameter_map`（参数 → 对象属性），`base_fsp`，`extract`（监视器 → 结果名）。
   模板见 `assets/session_config.example.json`。
2. **先验白名单 + dry-run**：
   `python skills/fdtd-lumerical-session-control/scripts/session_control.py --config <json> --out <dir> --dry-run --json`
   确认 `session_opened: false`、注入属性数、两段式序列。
3. 实跑（去掉 `--dry-run`）：脚本按已验证序列执行一轮，产出
   `iteration_NNN.fsp`、`iteration_NNN.json` 与 `<工程名>_p0.log`。
4. 把 `iteration_NNN.json` 里的 `results` 作为下一轮 `observation` 喂给
   `fdtd-lumerical-design-loop`，由它算 FOM、判据与三态出口。
5. 任一环节失败：读 `references/session-contract.md` 的错误分类表；只有
   `transient`（ansyscl 端口 TIME_WAIT）会自动重试，其余立即停并报人。

## 示例

**用户：** "P02 的单元胞已经建好， Design 模式下把 `c` 从 850 nm 试到 860 nm，
只改 nanobrick 的 x span，其他都别动，每轮留证据。"

**动作：**

```bash
python skills/fdtd-lumerical-session-control/scripts/session_control.py \
  --config skills/fdtd-lumerical-session-control/assets/session_config.example.json \
  --out _scratch/regress/session-control-20261107 --dry-run --json
# 确认 session_opened=false 后去掉 --dry-run 实跑
```

**结果：** `--out` 下出现 `iteration_001.fsp` 与 `iteration_001.json`；后者含
`params`、`applied`（实际 `setnamed` 的对象/属性/值）、`assert_ran` 结论、
`p0_log` 路径、`results`、`elapsed_s`。**没有任何数值结论**——判读在下一技能。

## 故障排除

| 症状 | 分类 | 处置 |
|---|---|---|
| `Could not bind socket on port …` | transient（可重试） | ansyscl 端口 TIME_WAIT；脚本自动退避重试，别去动 license |
| 日志出现 `diverging` | numerical（停） | dt stability factor 0.99→0.95，或改 CPU 双精度 |
| `layoutmode=1` / `run()` 立刻返回无日志 | sequence（停） | 建模会话直接 run 静默失效；必须 `verify_and_run` 两段式 |
| `analysis mode` 报错 | sequence（停） | 改对象前 `switchtolayout()` |
| 路径报 1113 / 弹窗乱码 | path（停） | 路径含非 ASCII，以 `_p0.log` 为准 |
| `Failed to checkout` / `-97,121` | license（停） | 先跑 `z_fix_license_daemon.cmd`，别重跑仿真 |
| 关闭时弹「保存名字为…」 | sequence（停） | 每轮 `save()` 到 `--out` 后再 `close()` |

完整错误分类与台账字段见 `references/session-contract.md`。

## 按需加载

- 读 `references/session-contract.md` **当**要写 config、核对白名单语义、
  查错误分类表或确认每轮台账字段时——它写的是配置 schema 与两段式序列的实测依据。
- 读 `assets/session_config.example.json` **当**第一次拼 `--config` 时——可直接改后用作模板。
- 读 `fdtd-package-workspace/scripts/lumapi_common.py` **当**需要确认会话工厂、
  `assert_ran` 三判据或 `verify_and_run` 的实际行为时（本技能只调用，不复制）。
- 读 `fdtd-lumerical-headless` 的 CRITICAL **当** run 静默失效或许可异常时——
  它是无界面会话规则的权威入口。
