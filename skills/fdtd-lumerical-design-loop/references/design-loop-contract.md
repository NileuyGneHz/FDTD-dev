# 设计闭环决策层契约

> 配套：`scripts/design_loop.py`、`assets/design_config.example.json`。
> 上位：L1 `docs/product-context/README.md` §②/③/⑥/⑦、
> `agents/fdtd-sim-agent/AGENT.md` §3.2、根 `AGENTS.md` §5。

## 1. 与 L1 / AGENT.md 的字段对齐（不发明新字段）

| L1 / AGENT.md 字段 | 本技能 config 字段 | 谁填 | 约束 |
|---|---|---|---|
| `targets`（指标 + 容差） | `targets` | 人 | 必须给到可判定数值与容差 |
| `locked`（材料 / 层序 / 拓扑） | `locked` | 人 | agent 不得改；与 `search_space` 同名即拒绝 |
| `search_space`（可调参数及范围） | `search_space` | 人 | `{min, max, step}`，是白名单唯一来源 |
| `mode`（Reproduce / Design） | `mode` | 人 | Reproduce 直接拒绝本技能 |
| ③ 首轮采样 / ④ 选下一组 | `strategy` | agent | 只用 grid / coordinate_descent / local_search |
| 预算 / 三态出口 | `budget` | 人 | `max_runs` / `stale_limit` / `max_wall_minutes` |
| 每轮证据 | `observations` + 本轮 `observation` | 执行层产出 | 追加，不覆盖 |

**没有 `tunable`、没有 `stop`、没有 `FOM` 自定义字段**——统一复用 L1 已有的三个键，
避免「同一概念两套名字」。

## 2. `targets` 判据格式

```json
{"metric": "T", "min": 0.90}
{"metric": "R", "max": 0.05}
{"metric": "dphi_deg_mod360", "kind": "phase", "value": 180.0, "tol_deg": 5.0}
{"metric": "peak_A", "value": 0.97, "tol": 0.02}
```

| 形式 | gap 公式 | 通过条件 |
|---|---|---|
| `value` + `tol`（linear） | `abs(actual - value) - tol` | `gap <= 0` |
| `value` + `tol_deg`（`kind: phase`） | `phase_distance_deg(actual, value) - tol` | `gap <= 0` |
| `min` | `min - actual` | `gap <= 0` |
| `max` | `actual - max` | `gap <= 0` |

`phase_distance_deg(a,b) = abs((a-b+180) % 360 - 180)`：10° 偏差就是 10，
不会报成 350。这与 `fdtd-lumerical-phase-retrieval` 产出的
`dphi_deg_mod360` / `cos_dphi` 是同一口径；**本技能不重新计算相位**，
只读执行层给出的 metric。

数组型 metric 取最后一个值（`_as_scalar`）；空数组 / 缺 metric 记 gap = inf，
FOM = inf，**不允许通过删 target 让它变绿**。

## 3. FOM 与判据

```
FOM = Σ max(0, gap_i)²       # 0 = 所有 targets 达标
```

- FOM 是「离人工指标还有多远」，不是「物理是否正确」——后者归人裁决（L1 §⑨）。
- 逐项 `gap` / `actual` / `expected` 全部写进 `observations.jsonl` 与 `verdict.json`，
  用于「不可达也要给边界证据」。
- 容差来自 `targets` 里人给的 `tol`；**不得由 agent 放宽**
  （`skill-change-contract.md` §4.7）。数值仿真的回归容差另见该契约 §5.2。

## 4. 三种策略（L1 §⑥，不做伴随法）

| `strategy.kind` | 行为 | 何时用 |
|---|---|---|
| `grid` | `search_space` 各维按 `step` 做笛卡尔积；超过 `max_grid_points`（默认 64）直接拒绝 | 首轮摸地形，AGENT.md §3.2 ② |
| `coordinate_descent` | 从历史最佳点（无历史则各维中点）出发，每维 ±step + 当前点 | 默认；AGENT.md §3.2 ④ |
| `local_search` | 最佳点附近定种子随机扰动 `samples` 个（默认 8），clamp 到 `[min,max]` | 坐标下降卡住时换方向 |

`random.Random(seed + len(observations))` 保证**同输入同输出**，可复现。
所有候选都做 `clamp`，且用 `param_key`（参数 JSON 的 sha256 前 16 位）去重，
同一组参数不会被重复提交给执行层——这是 `run_cached()` 形态的轻量版。

**未采用**：adjoint / topology optimization / 贝叶斯。L1 §⑦ 明确「不做伴随法 /
拓扑优化（iter-1）」，且 §⑥ 写「够用就行，不追求花哨算法」。
`chriskeraly/lumopt` 的伴随梯度与 `python/adjoint` 因此不进入本技能。

## 5. 三态出口（+ 一个继续态）

| verdict | 触发 | 必须给的东西 |
|---|---|---|
| `PASS` | 任一 observation 的 FOM == 0 | 达标参数；**仍交人裁决**，不写「物理正确」 |
| `INFEASIBLE` | `run_count >= max_runs` 或候选穷尽 | `boundary_evidence`：`best_fom` + `best_params` + 逐项 gap |
| `NEEDS_HUMAN` | 连续 `stale_limit` 轮 FOM 无变化且最优点落在 `search_space` 边界 | 停，问人改 locked；不自己放宽范围 |
| `CONTINUE` | 其余 | `next_params.json`（一组），交执行层 |

`INFEASIBLE` 的语义是「**在给定 search_space 内**最好到 X、差 Y」，不是「跑不动」。
只写「失败」没有数字，按契约 §3 的 B 档证据要求不合格。

## 6. 输出文件（全部落 `--out`）

| 文件 | 内容 |
|---|---|
| `observations.jsonl` | 每轮 params / metrics / FOM / 逐项 gap，追加式重建，不覆盖历史 |
| `search_log.csv` | `run, fom, params, metrics`，对应 AGENT.md §3.2 ③ 的 `results/search_log.csv` |
| `fom_curve.csv` | `run, fom, best_so_far`，L1 §⑥ 的「目标函数曲线」 |
| `verdict.json` | verdict / reason / run_count / best_fom / next_params / boundary_evidence |
| `next_params.json` | 下一组参数（终止态为空 `{}`），直接可填进 session-control 的 `params` |

`--dry-run` **不写任何文件**，只打印计划（策略、run_count、预算、下一组参数、将写文件列表）。
回归输出按 `skill-change-contract.md` §4.4 落 `_scratch/regress/`，不写回 `cases/`。

## 7. 与外部复用来源的对应（只溯源，不含复制代码）

| 来源 | 借鉴的形态 | 落地位置 |
|---|---|---|
| `SiEPIC/gds_fdtd` `convergence.py` | `model_copy(update={field:v})` 单字段改参、`validate()` 离线、`run_cached()` 去重、`recommend(tol)` 收敛推荐、`max_delta_db(floor_db=-30)` 只在有效信号上比 | `next_candidate` / `param_key` / `evaluate`；floor 思路对应「别在低功率处比相位」 |
| `hzzg0727/Metasurface-Design` `MetaTool.py` | `phaseDis` / `phaseNorm = np.angle(np.exp(1j*Δ))` 相位环绕距离 | `phase_distance_deg`（纯 math 实现，无 numpy 依赖） |
| `chriskeraly/lumopt` `optimization.py` | `callable_fom(params)` 与求解器解耦、`fom_hist` / `params_hist` 留证 | 决策/执行分离；`observations.jsonl` + `fom_curve.csv` |
| `geer1895/rfauto` `agent_gate.py` | L1 参数白名单、越界拒绝、能力分级 | `check_whitelist`（在 session-control 侧）与本契约 §1 |
| `raghu1153/MetaOptics` `metaData.py` | `interp1d(phase -> dimension)` 查表反演 | **未采用**：CC-BY-NC-4.0 非商业许可，且属「先建库再反查」的另一条工作流；L1 §⑥ 的网格/坐标下降已够用 |
| `Lex669/LumericalFDTD-skill` | 有限重试 + 错误分类 | 在 session-control 侧落地，本技能不重试 |

## 8. 一份实现原则

- 参数序列只由本技能产生；`fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py`
  的网格扫参是**建模 + 跑谱一体**的另一条链（从零建工程），两者不互相 import。
- 仿真只由 session-control 触发；本技能任何分支都不 `import lumapi`。
- 判据只由本技能算；执行层只做 `getresult` 的 JSON 化。
- 改任一边的实现，只需保证 `iteration_NNN.json.results` → `observation.metrics`
  这个 JSON 契约不变。
