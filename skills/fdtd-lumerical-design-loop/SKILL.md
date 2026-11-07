---
name: fdtd-lumerical-design-loop
description: >
  L1 设计模式的决策层：在 search_space 内生成下一组参数、按 targets 算 FOM 与逐项容差、
  给出「达标 / 不可达（附边界证据）/ 需要人改结构」三态出口，并把每轮参数与结果写成
  search_log.csv、fom_curve.csv、verdict.json。当 agent 需要决定下一步试哪个尺寸、
  判断指标到没到、或证明在给定空间内不可达时使用。触发词：下一组参数、FOM、
  三态判定、不可达边界证据、坐标下降、search_space、设计闭环。
agent_created: true
---

# L1 设计闭环决策层（选参数 / 判据 / 三态出口）

## 概述

本技能只做**决策**：消费 L1 的 `targets` / `locked` / `search_space` 与每轮
observation，产出 `next_params.json`、`search_log.csv`、`fom_curve.csv`、
`verdict.json`。它**不 import lumapi、不开会话、不建模、不跑仿真**——执行层是
`fdtd-lumerical-session-control/scripts/session_control.py`。

它把 `agents/fdtd-sim-agent/AGENT.md` §3.2 的②首轮采样 / ③跑+读 / ④选下一组 /
⑤三态出口，固化成可重跑的机器步骤；L1 §⑥ 的「每轮可追溯率 100%」由
`observations.jsonl`（追加、不覆盖）保证。

## CRITICAL（违反即停止）

1. **Reproduce 模式禁止加载本技能**。L1 §③：复现模式改参数 = 造假；
   传 `mode: Reproduce` 直接返回失败，不给任何参数建议。
2. **只在 `search_space` 内取点，绝不碰 `locked`**。`search_space` 与 `locked`
   出现同名键即拒绝；`coordinate_descent` / `local_search` 的候选都做 clamp。
3. **不做伴随法 / 拓扑优化 / 贝叶斯优化**。L1 §⑦ 明确 iter-1 非目标；
   策略只允许 `grid` / `coordinate_descent` / `local_search`（L1 §⑥）。
4. **不判读物理正确性**。判据是「与人工 `targets` 的数值距离」，不是
   「物理正确 / 可发表」；后者归人裁决（L1 §⑨）。
5. **相位判据必须用环绕距离**。裸减 `dphi_deg` 会把 10° 的偏差报成 350°；
   `kind: phase` 走 `phase_distance_deg`，与 `fdtd-lumerical-phase-retrieval`
   的 `dphi_deg_mod360` / `cos_dphi` 口径一致。
6. **`INFEASIBLE` 必须带边界证据**。只写「跑不动」不算达标出口；必须给
   `best_fom` + `best_params` + 逐项 gap，说明在给定空间内最好到哪、差多少。
7. **`NEEDS_HUMAN` 即停**。最优点连续 `stale_limit` 轮无改善且落在
   `search_space` 边界上时，说明要改人锁定的结构 —— 停下来问人，不要自己放宽范围。
8. **不覆盖历史**。`observations.jsonl` 逐轮追加；隐瞒失败轮次是 L1 红线。

## 核心工作流

1. 写 `config`：`mode: Design`、`targets`（metric + value/tol 或 min/max）、
   `locked`、`search_space`（min/max/step）、`strategy`、`budget`、
   可选 `observations`（历史）与本轮 `observation`。模板见
   `assets/design_config.example.json`。
2. **dry-run 先验**：
   `python skills/fdtd-lumerical-design-loop/scripts/design_loop.py --config <json> --out <dir> --dry-run --json`
   确认策略、候选数、预算；此步不写任何文件。
3. 实跑（去掉 `--dry-run`）→ 读 `next_params.json`。
4. 把 `next_params.json` 的内容填进 session-control 的 `params` 跑一轮 FDTD，
   再把 `iteration_NNN.json` 的 `results` 作为下一轮 `observation` 传回本技能。
5. 重复 3–4 直到 `verdict ≠ CONTINUE`；`PASS` 交人裁决，
   `INFEASIBLE` 交边界证据，`NEEDS_HUMAN` 停下来问人改结构。

## 示例

**用户：** "P02 要在 C+L 波段 Δφ≈180°±5° 且 T≥0.90，`c` 只允许 800–900 nm，
给我下一组参数和到没到的判定。"

**动作：**

```bash
python skills/fdtd-lumerical-design-loop/scripts/design_loop.py \
  --config skills/fdtd-lumerical-design-loop/assets/design_config.example.json \
  --out _scratch/regress/design-loop-20261107 --dry-run --json
# 确认计划后去掉 --dry-run，读 next_params.json 与 verdict.json
```

**结果：** `--out/verdict.json` 给 `verdict`（PASS / INFEASIBLE / NEEDS_HUMAN / CONTINUE）、
`reason`、`best_fom`、`next_params`；`fom_curve.csv` 给逐轮 FOM 与 best-so-far；
`search_log.csv` 给每轮参数与原始 metrics。全部落在 `--out`，不写回 `cases/`。

## 故障排除

| 症状 | 原因 | 处置 |
|---|---|---|
| `Reproduce 模式禁止调参` | 传了 `mode: Reproduce` | 复现模式只做偏差诊断；要调参先由人切到 Design |
| `参数不在 search_space 内` / `search_space 与 locked 冲突` | 越界 | 回人：要改锁定项得人改结构，agent 不越界 |
| `网格 N 点 > max_grid_points` | step 太小 | 调大 step 或改用 `coordinate_descent`；不要偷偷提高预算上限 |
| `metric missing from observation` | 执行层 `extract` 没读该监视器 | 补 session-control 的 `extract` 配置，不要改判据 |
| FOM 一直是 `inf` | 有 target 的 metric 读不到或数组为空 | 先修数据采集，禁止删 target 让它变绿 |
| 相位 gap 突然变成 ~350 | target 漏写 `kind: phase` | 补 `kind: phase`；用环绕距离 |

完整字段语义与判据公式见 `references/design-loop-contract.md`。

## 按需加载

- 读 `references/design-loop-contract.md` **当**要写 `targets` 判据、确认 FOM 定义、
  理解三态出口语义或核对与 L1 / `AGENT.md` §3.2 的对应关系时。
- 读 `assets/design_config.example.json` **当**第一次拼 `--config` 时——含全部字段与注释性示例。
- 读 `fdtd-lumerical-session-control/scripts/session_control.py` **当**需要确认
  `observation` 的 `metrics` 从哪里来、字段长什么样时（那是执行层输出格式）。
