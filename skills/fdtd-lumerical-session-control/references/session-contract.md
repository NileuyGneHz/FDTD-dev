# 单轮迭代执行器契约

> 配套：`scripts/session_control.py`、`assets/session_config.example.json`。
> 上位：L1 `docs/product-context/README.md` §②/③/⑥、`docs/constitution/skill-change-contract.md`。

## 1. 这个技能在整条链路里的位置

```
人定方向 / 材料 / 几何 (locked)
        │
        ▼
fdtd-lumerical-design-loop   选下一组 params（纯决策，不碰 lumapi）
        │  next_params.json
        ▼
【本技能】                    白名单校验 → 增量改参 → save→run → 原始结果读回
        │  iteration_NNN.json
        ▼
fdtd-lumerical-design-loop   FOM / 逐项 gap / 三态出口（拿 results 当 observation）
        │
        ▼
人裁决
```

**本技能不做的三件事**：从零建模（那是
`fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py`）、
选参数（design-loop）、判读达标（design-loop）。
这样三处各有一份实现，不出现「同一逻辑写两遍」。

## 2. `--config` 字段

| 字段 | 必填 | 语义 |
|---|---|---|
| `mode` | 是 | `Design`（允许调参）/ `Reproduce`（禁止调参，非空 `params` 即拒绝） |
| `iteration` | 否 | 轮次，默认 1；决定 `iteration_NNN.*` 的文件名 |
| `base_fsp` | 是 | 已建好的工程，仓库相对路径；本技能**不建模** |
| `targets` | 否 | L1 指标，仅随台账留证；判读不在这里做 |
| `locked` | 是（可空） | 人锁死的项；与 `params` 有交集即拒绝 |
| `search_space` | 是 | `{param: {min, max, step}}`，白名单唯一来源 |
| `params` | 是（可空） | 本轮要注入的参数，必须是 `search_space` 子集 |
| `parameter_map` | `params` 非空时必填 | `{param: [{object, property}]}`，参数 → `setnamed` 目标 |
| `extract` | 否 | `{metric: {monitor, result}}`，`getresult` 读回白名单 |
| `max_array_items` | 否 | 数组截断上限，默认 2000（防止一次读回撑爆 agent 上下文） |
| `max_retries` | 否 | 仅 `transient` 错误的重试次数，默认 3 |

`object` / `property` 必须按实际 `.fsp` 对象树填写；不确定时用
`fdtd-lumerical-fsp-introspection` 先查 manifest，不要猜。
示例 `assets/session_config.example.json` 里的 `nanobrick` / `x span` 是占位示意。

## 3. 为什么默认两段式 run（2026-11-08 重新实测，结论已订正）

**旧结论（作废）**：CRITICAL #1 曾写「在新建的建模会话里直接 `run()` 会静默失效，必须新会话」。
**新实测（本机 v251，2026-11-08）**：静默失效的真正前提是**从未 `save` 过**，与「是否新会话」无关。

| 序列 | 实测 |
|---|---|
| 建模 → `run()`（未 save） | 4.9 s 返回、无异常、`layoutmode` 仍 1、无 `_p0.log`、`getresult` 报 `Can not find result` |
| 建模 → `save` → `run()`（**同会话**） | `layoutmode` 0、`_p0.log` 4181 B、`Completed 43 iterations` |
| `save` → `close` → 新会话 `load` → `run` | 与上一行**逐位一致**（T_max 相同、同为 43 iterations） |
| 同会话两轮改参（save→run→读回 ×2） | 第二轮波长 1500→1000 nm：`T` 改变、迭代 43→68、`_p0.log` mtime 更新 |

证据：`_scratch/regress/_gate/session_rule/`（`session_rule.json`、`equivalence.json`、`c4b.json`）
与 `_scratch/regress/_gate/probe_session_rule*.py`。

**因此**：默认仍走两段式（它额外买到「工程可复算 / 可重放 / 每轮有独立 `.fsp`」），
但这**不是引擎强制**，**同会话迭代（C4）是允许的**，前提是每轮 `switchtolayout` → 改参 →
`save` → `run` → 读回。可靠序列：

```
① open_fdtd() → load(base_fsp) → switchtolayout()
② 白名单 setnamed（只改数值，不 add* / 不重建几何）
③ save(iteration_NNN.fsp)                     # ③ 是硬前提，不可省
④ run() → assert_ran()                        # 同会话即可；两段式等价
⑤ getresult → 台账 → close()
```

`assert_ran` 的三判据：`layoutmode == 0`、存在 `<工程名>_p0.log`、日志含 `Completed`；
另会扫 `diverging`（发散是「不报错的错」）。**收敛数值（Auto Shutoff）不在这里判**，
由上层读 `_p0.log`，避免把判据复制两份。

> **一个假轮次的坑（实测）**：`setnamed` 成功、`getnamed` 回读也一致，**不代表该参数会影响指标**。
> 同一模型把 source 的 `x span` 从 0.30 改到 0.45 µm，`T` 一位都没动。
> 所以 design-loop 在把某参数放进 `search_space` 之前，必须有一次**敏感性对照**（改到边界值看指标是否响应），
> 否则搜索会在一维上白跑。这条对应 L1 §⑥「参数写了但没注入」的姊妹情形：**注入了但不在因果链上**。
>
> 与外部调研的取舍更新：`chriskeraly/lumopt` 的「同一 session 反复 save + run」**与本机实测一致**，
> 不再是冲突项；C4 的实现可走单会话，但每轮仍必须落独立 `.fsp` 与 `_p0.log` 以保证可审计。

## 4. 白名单 / 越界规则（L1 红线）

| 检查 | 失败行为 |
|---|---|
| `mode == Reproduce` 且 `params` 非空 | 拒绝，退出码 1，不开会话 |
| `params` 有键不在 `search_space` | 拒绝（越界即停） |
| `params` 有键命中 `locked` | 拒绝，回去问人 |
| 值超出 `[min, max]` | 拒绝 |
| `params` 有键无 `parameter_map` | 拒绝（防止「参数写了但没注入」的假轮次） |

复现模式要改的只能是**数值设置**（网格、simulation_time、边界条件口径），
且属于另一条链；不要借本技能绕过去调几何凑论文曲线。

## 5. 错误分类（与 `classify_error()` 一一对应）

| 关键字 | category | 是否重试 | 处置 |
|---|---|---|---|
| `bind socket` | transient | 是（退避 2s/4s/6s） | ansyscl 端口 TIME_WAIT；报错里「check licenses」是误导 |
| `diverging` | numerical | 否 | dt stability factor 0.99→0.95 或 CPU 双精度 |
| `1113` | path | 否 | 路径含非 ASCII，以 `_p0.log` 为准 |
| `layoutmode` | sequence | 否 | `run` 前没 `save`（或改参前没 `switchtolayout`）；补 `save` 即可，不必换会话 |
| `analysis mode` | sequence | 否 | 改对象前 `switchtolayout()` |
| `Failed to checkout` | license | 否 | 先修 license daemon，别重跑仿真 |
| `Auto Shutoff` | convergence | 否 | 提高 `simulation_time` |
| 其它 | unknown | 否 | 停下来报人，不猜 |

重试上限由 `max_retries` 控制；非 `transient` 一次失败即停。
失败会写 `iteration_error.json`（含分类、hint、attempt、traceback），**不吞异常**、
不把垃圾值当结果。

## 6. 每轮台账 `iteration_NNN.json`

| 字段 | 内容 |
|---|---|
| `iteration` / `mode` / `utc` / `elapsed_s` | 轮次、模式、UTC 时间、耗时 |
| `params` / `param_key` | 本轮参数与其 sha256 前 16 位（去重 / 缓存键） |
| `applied` | 实际 `setnamed` 的 object / property / value 列表（可审计） |
| `base_fsp` / `base_fsp_size` / `iter_fsp` / `p0_log` | provenance：从哪个工程、落到哪、日志在哪 |
| `assert_ran` | 三判据结论（`verify_and_run` 通过才有这一行） |
| `results` | `extract` 里每个 metric 的**原始** `getresult` 数据（JSON 化 + 截断） |
| `retry_count` | 本轮重试次数 |

L1 §⑥「每轮可追溯率 100%」= 参数 + 目标函数 + `_p0.log` + 判断依据 + 停下理由；
本技能负责前三项，`verdict.json`（design-loop）负责后两项，两者用
`param_key` 对上，不要合并成一份文件。

## 7. 预算与席位

- 两段式每轮 2 个 `lumapi.FDTD()`、同会话迭代每轮 1 个，都在 `finally` 里 `close()`；
  每个占 1 个许可席位，别并行开多个迭代。
- `max_wall_minutes` 由 design-loop 的 `budget` 管；本技能只记 `elapsed_s`。
- 输出全部落 `--out`，**绝不写回 `cases/`**（契约 §4.4 / §5）。
- 路径纯 ASCII；`ascii_gate()` 会先拦一道。

## 8. 外部复用来源（只溯源，不含复制代码）

| 来源 | 借鉴的形态 | 本次是否落地 |
|---|---|---|
| `leisymqaz/lumerical-fdtd-mcp` | 命名会话字典、任意脚本注入、`_jsonable` 大数组截断、单次异常不杀会话 | 借鉴形态；该仓库无 LICENSE 文件，**未复制代码** |
| `chriskeraly/lumopt` | `callable_fom(params)` 与执行器解耦、每轮 `save(name_iter)` 存档 | 解耦与留证已落地；单 session 写法按 §3 未采用 |
| `Lex669/LumericalFDTD-skill` | 有限次数重试 + 错误分类驱动修复 | 已落地（仅 transient 可重试） |
| `SiEPIC/gds_fdtd` | `validate()` 离线、`run_cached()` 全量哈希 | 白名单校验已落地；缓存由 design-loop 的 `param_key` 去重承担 |
| `ansys/pylumerical` | `LUMERICAL_HOME` / 自动发现安装目录 | **未采用**：本机 v251 用既有 `lumapi_common.setup_env()`，跨平台留给 Ubuntu 迁移议题 |
