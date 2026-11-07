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
【本技能】                    白名单校验 → 增量改参 → 两段式 run → 原始结果读回
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

## 3. 为什么是两段式 run（项目实测，别改）

`fdtd-lumerical-headless` CRITICAL #1 与
`fdtd-package-workspace/scripts/lumapi_common.py` 的 `verify_and_run()`（约 260–289 行）
记录的是**本机 v251 实测结论**：在新建的建模会话里直接 `run()` 会静默失效——
不抛异常、立刻返回、没有 `_p0.log`。可靠序列是：

```
① open_fdtd() → load(base_fsp) → switchtolayout()
② 白名单 setnamed（只改数值，不 add* / 不重建几何）
③ save(iteration_NNN.fsp) → close()
④ verify_and_run(iteration_NNN.fsp)   # 内部：save → close → 新会话 load → switchtolayout → run → assert_ran
⑤ getresult → 台账 → close()
```

`assert_ran` 的三判据：`layoutmode == 0`、存在 `<工程名>_p0.log`、日志含 `Completed`；
另会扫 `diverging`（发散是「不报错的错」）。**收敛数值（Auto Shutoff）不在这里判**，
由上层读 `_p0.log`，避免把判据复制两份。

> 与前文外部调研的取舍：`chriskeraly/lumopt` 的 `Simulation` 类是「同一 session
> 反复 `save` + `run`」，但本项目实测规则与之冲突。按契约「证据先于改动」，
> 本次**不引入**未在本机验证过的 persistent-session 实现；C4 的价值通过
> 「工程体不重建 + 只做增量 `setnamed` + 自动逐轮编排」实现。
> 若将来要验证单 session 复用，须先写 `defects/D-xxx` 并带同 spec 的对照数字。

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
| `layoutmode` | sequence | 否 | 建模会话直接 run 静默失效，走两段式 |
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

- 每轮最多 2 个 `lumapi.FDTD()`（两段式），都在 `finally` 里 `close()`；
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
