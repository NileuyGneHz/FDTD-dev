# PLAN-2026-11-11：fsp-build per-cell 变参 + 阵列装配技能

> 状态：**已批准并执行**（2026-11-11 14:08，Nileuy 决策见 §10）
> 前置：`fdtd-holo-phase-retrieval`（stage 1.8）已产出 `quantized_phase.csv`（`x_um,y_um,phase_rad,level` 四列）与 `library_map.json` 占位 schema，本计划是它的下游。

---

## 1. 现有实现分析（读了什么、得出什么）

### 1.1 结构

| 文件 | 角色 | 关键点 |
|---|---|---|
| `_shared/fsp_build.py`（544 行） | **唯一 builder 实现** | `ev()` 表达式求值、`resolve_axes()`、`build_objects()`、`build_simulation()` |
| `skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py`（279 行） | CLI 外壳（build / check / dry-run） | import `_shared`，无自有逻辑 |
| `skills/fdtd-lumerical-fsp-build/SKILL.md` + `references/spec_extensions.md` | 契约文档 | |

`build_objects()` 是逐对象 `if/elif` 分发：box / polygon / cylinder / sphere / ellipse / ring / 2drect / group。每个几何参数都走 `ev(expr, params)`——**参数表驱动的表达式求值是现成的**，per-cell 变参可以完全复用这套机制。

### 1.2 为什么现在不支持 per-cell

`ev()` 的 `params` 是**全局一份**：所有对象共享同一张参数表，`"d/2"` 里只有一个 `d`。整片阵列中每个单元要不同的 `d`，需要在对象层面引入"按格子索引变化"的参数源——这是一个新维度，不是改几行的事，但**改动面可以控制得很小**（见 §3）。

### 1.3 已有的两个可借鉴先例

- **P06 结构组**（SKILL.md §7）：30×30 V-antenna 阵列，几何真相在 `group` 的 `.lsf` 脚本里。说明「引擎侧用脚本循环生成大量单元」是可行路径。
- `ev()` 白名单字符集（`_EXPR_OK`）：安全求值已有边界，per-cell 注入的索引变量 `i`/`j` 落在白名单内。

### 1.4 两个调用方

`_shared/fsp_build.py` 被 `build_fsp.py` 与 `run_fdtd_sweep.py`（unitcell-simulation 技能）共同 import。**改 `_shared` 必须两边回归**——这是 SKILL.md CRITICAL #4 与 D-005/D-006/EXP-02 三次事故的成文约束。

---

## 2. 目标与非目标

**目标**
1. `fsp-build` 能表达「同一模板、逐格不同参数」的阵列（per-cell 变参）。
2. 新技能 `fdtd-metasurface-assembly`：吃 Skill A 的相位 CSV + 单元库映射，产出含完整超表面阵列的 `.fsp`（不 run）。
3. 全程走 skill-change-contract：EXP 台账先行、门禁全绿、不破坏现有 12 个技能。

**非目标（本期不做）**
- 不 run 仿真（仍是 build-only 语义，run 归 stage 2/3）。
- 不做相位 → 几何的反演算法（那是 library 标定的事，本期只做「查表装配」）。
- 不支持单元间的材料变化（每个 array 共用一种材料；材料变参留给以后，理由见 §8-R5）。
- 2D 模型不做阵列阵列面在 x-y 之外的组合（沿用现有 resolve_axes 轴约束，不新增轴向自由度）。

---

## 3. per-cell 变参的接口设计

### 3.1 spec 层：新对象类型 `"array"`

在 `objects` 里加一种 type，**不改任何现有 type 的行为**：

```json
{
  "id": "meta",
  "type": "array",
  "material": "TiO2",
  "engine": "objects",            // "objects" | "group_script"，见 §3.3
  "grid": {
    "nx": 64, "ny": 64,
    "pitch": ["P", "P"],          // 表达式，可用全局 params；两轴可不同
    "origin": ["-W/2", "-W/2"]    // 阵列左下角（表达式）
  },
  "element": {                     // 模板：允许的子集 = box / cylinder / ellipse / ring / polygon / 2drect
    "type": "ellipse",
    "center": ["0", "0"],          // 相对单元中心的偏移（表达式）
    "axes": ["d1", "d2"],          // ← 这些名字会查 per-cell 参数表
    "height": "h",
    "rotation_deg": "rot"
  },
  "cell_params": [                 // 逐格参数覆盖，长度必须 = nx*ny，行主序
    {"i": 0, "j": 0, "d1": "0.22e-6", "d2": "0.25e-6", "rot": "0"},
    {"i": 0, "j": 1, "d1": "0.30e-6", "d2": "0.31e-6", "rot": "45"}
  ]
}
```

### 3.2 求值链（复用 `ev()`，零改动核心）

每个单元求值时构造**三级作用域**，一次合成一个 dict 喂给现有的 `ev()`：

```
scope = 全局 params  ⊕  {i: 行号, j: 列号}  ⊕  cell_params[行主序下标]
```

- `i`/`j` 是新注入的格子索引变量（白名单字符内，无安全问题）。
- `cell_params` 的值允许数字或数字字符串（与 EXP-46 的手写 spec 习惯一致）。
- 模板里不出现的名字不要求出现在 `cell_params`（允许部分列、允许逐格只写变化量；缺省回落全局 params）。
- **数值全是字符串也行**：`"rot": "45"` 走现有 `ev()` 的字符串转 float 路径。

### 3.3 两种 engine（规模决定选择，默认自动）

| engine | 实现 | 适用 | 风险 |
|---|---|---|---|
| `"objects"` | Python 循环逐格 addrect/addpoly…，对象名 `{id}_r{i}c{j}` | ≤ ~2000 格（64×32 内安全） | 每格 2–4 次 lumapi 调用，65k 格会慢到不可用 |
| `"group_script"` | 生成一个 Lumerical 结构组，把参数表写成组内 `script`（.lsf 循环） | 大阵列（>2000 格） | 事实上的**黑盒**：introspection 只能读回脚本原文，不能逐对象核对（P06 同款限制，需写进 SKILL.md） |

**默认策略**：`engine` 缺省时按 `nx*ny` 自动选（阈值 2000，写死为常量并给出处注释）。`--check` 对 `group_script` 引擎降级为「脚本哈希比对 + 对象数抽检」，并在输出里显式标注 `check_coverage: "partial"`——**不假装全查**。

### 3.4 兼容性（不破坏现有 10 个已复现 case）

1. 现有 spec（P01–P07 全部）不含 `type: "array"`，走原路径，行为逐位不变。
2. `ev()`、`resolve_axes()`、`build_materials()`、`build_simulation()` **零改动**；只改 `build_objects()`（新增一个 elif 分支）+ 新增 `~120 行` 的 `_build_array()` 辅助函数。
3. `--check` 读回路径：逐格对象各自比对（与现有一致，只是对象多了）；`group_script` 走降级路径。
4. **两个调用方**：`run_fdtd_sweep.py` 不感知 array（它只管单胞），但因为它 import 同一份 `_shared`，必须在改动后跑一次 P01 全回归（EXP 台账里放证据）。
5. 堆栈范围计算：array 参与传播轴 extent（取全阵列 min/max），与现有 lo/hi 机制天然兼容。

---

## 4. 新技能 `fdtd-metasurface-assembly`（stage 1.9）

### 4.1 定位

| 想做的事 | 用它 |
|---|---|
| 我有 `quantized_phase.csv` + 单元库，要一片完整超表面 `.fsp` | ✅ |
| 只要建普通单胞 / 堆栈 | 转 `fdtd-lumerical-fsp-build`（array 是它的底层能力） |
| 建完要跑全息重建 | 转 stage 2/3 仿真 + `fdtd-lumerical-field-map` |

### 4.2 核心工作流（命令草案）

```bash
# ① phase CSV + library_map → spec.json（零引擎，纯查表，可 dry-run）
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py \
  --phase quantized_phase_L8.csv \
  --library library_map.json \
  --geometry geom.json \        # 阵列 pitch/层数/衬底等少量全局量
  --out spec_meta.json --dry-run --json

# ② spec → .fsp（转调 fsp-build，一份实现不复制）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec spec_meta.json --out <单元内 results/> --check --json
```

`library_map.json` 契约（Skill A 已预留占位，本技能定义实 schema）：

```json
{
  "levels": 8,
  "phase_rad_center": [0.0, 0.785, 1.571, ...],
  "cells": [
    {"level": 0, "params": {"d1": 0.22e-6, "d2": 0.25e-6, "rot": 0}},
    {"level": 1, "params": {...}}
  ],
  "source": "cases/P0X_... 或 paper-parameter-extraction 的产出路径",
  "wavelength_um": 0.633
}
```

装配逻辑 = 对 CSV 每行 `(x_um, y_um, level)` → 查表得 per-cell params → 填进 §3.1 的 `cell_params`。**相位本身不进 spec**（几何参数才是引擎要的）；`x_um/y_um` 只用来定格子坐标并校验 `nx*ny` 与 CSV 行数一致。

### 4.3 集成方式

- `skills/INDEX.md`：stage 1.9 条目（holo- 族：1.8 相位设计 → 1.9 阵列装配 → 2 建模）。
- `agents/fdtd-sim-agent/skills.yaml`：注册（junction 同款流程，注意 K17 的 stage 数字坑，1.9 同理不进 load_order）。
- 用户级 junction：`~/.workbuddy/skills/fdtd-metasurface-assembly` → 工作区路径。
- 门禁：`check_skill_contract` / `skills-doctor` / `check_experiments` / `check_scripts` 四绿。

---

## 5. 实施步骤（顺序与优先级）

| # | 步骤 | 产出 | 挂 EXP |
|---|---|---|---|| 1 | 登记本计划进任务表 + 新实验先登记（门禁要求） | 计划表条目 | — |
| 2 | `_shared/fsp_build.py` 加 `array` 分支（engine=objects 先行） | `build_objects` 新 elif + `_build_array()` | EXP-60 |
| 3 | `--check` 对逐格对象全量比对；负对照（改一格 d1，check 必须 exit 1） | check 扩展 | EXP-61 |
| 4 | P01 旧 spec 回归（证明零破坏）+ `run_fdtd_sweep.py` 路径冒烟 | 回归证据 | EXP-62 |
| 5 | ~~engine=group_script 生成器~~ | **本期不做**（§10-1） | — |
| 6 | ~~性能实测~~ | **本期不做**（§10-1） | — |
| 7 | `assemble_spec.py`（零引擎、查表装配、dry-run + --self-test） | 新脚本 | EXP-63 |
| 8 | 端到端 64×64：相位 CSV → spec → `.fsp` + check + 规模报告 | 可交付工程 | EXP-64 |
| 9 | SKILL.md ×2 + INDEX + skills.yaml + junction + 四门禁 | 注册与交付 | EXP-65 |

优先级：2–4 是**必须**（底层能力 + 兼容性证明）；5–6 可后置到第二刀（若第一批只做 ≤64×64 的论文复现规模）；7 依赖 2；8–9 收尾。

## 6. 测试与验证方案

1. **正对照**：3×3 手算阵列（pitch、每格 d1/rot 手写期望值），`--check` 逐格比对全过。
2. **负对照**（门禁方法论：删了必须变红）：①改一格 `d1` 10% → check exit 1 且**指名哪个对象哪个属性**；②CSV 行数 ≠ nx*ny → 组装端报错拒绝；③library 缺某 level → 报错而非静默跳过（EXP-49 同类教训：文案与语义相反）。
3. **零破坏回归**：P01 / P04 现有 spec 重建，`--check` 结果与改动前逐位一致（存两次 JSON diff）。
4. **双向检查**：`assemble_spec.py` 输出的 spec 里每个 level 都必须来自 library（单向门禁不验「该写的有没有写」——四犯同病灶）。
5. **自检**：`assemble_spec.py --self-test`（查表纯函数可脱机测，无需引擎）；`build_fsp.py --dry-run --json` 显示阵列规模与单元数。
6. **复现口径**：门禁 `check_skill_contract` / `check_experiments` / `check_scripts` / `skills-doctor`。

## 7. 压缩档（时间不够怎么砍）

| 砍 | 保 |
|---|---|
| 砍 engine=group_script（步骤 5–6）→ 只支持 ≤2000 格 | 逐格 objects 路径 + 负对照 + P01 回归 |
| 砍 assemble_spec.py 的 library 容错（要求严格 schema） | 查表主链与双向检查 |
| 砍性能实测表 | 阈值常量标注「经验值，未实测」 |

**不可砍**：负对照、P01 零破坏回归、EXP 台账。

## 8. 潜在风险

| # | 风险 | 等级 | 应对 |
|---|---|---|---|
| R1 | 65k 对象把 `.fsp` 撑爆 / lumapi 慢到不可用 | 高 | engine 阈值 + group_script 备选路径（步骤 5）；首批先做论文规模 ≤64×64 |
| R2 | 改 `_shared` 波及 `run_fdtd_sweep.py` | 高 | EXP-62 强制回归两个调用方；D-005 教训成文 |
| R3 | `--check` 对大阵列超时 | 中 | 抽检 + partial 显式标注，不静默降级 |
| R4 | group_script 是黑盒（introspection 读不回几何） | 中 | SKILL.md 写明边界（P06 同款）；objects 引擎优先 |
| R5 | 材料逐格变化的隐藏需求（多材料超表面） | 低 | 本期显式拒绝（array 共用一材料），报错而不是猜 |
| R6 | 相位 CSV 与格子的行主序/坐标约定不一致 | 中 | 双向检查 + `nx*ny` 一致性断言；歧义时报错列出 CSV 前三行 |
| R7 | 每格对象名 `{id}_r{i}c{j}` 与既有对象撞名 | 低 | 建前全 spec 扫描 id 唯一性（含展开后的格子名前缀） |
| R8 | 2D 模型 + array 的轴向组合误用 | 中 | 沿用 resolve_axes 现有报错；2D 只允许阵列在 x-(传播轴) 线上排 |

## 9. 判定偏差预案

与 Skill A 相同原则：执行中若发现判定标准不可达（如 check 性能阈值不现实、group_script 不可行），**当场改判据并在本文件 §7 追记**，不静默放宽。

### 执行中的判据偏差追记（2026-11-11）

1. **stride 降采样 → crop 中心裁剪**（EXP-64）：原计划把 256×256 相位图按 stride=4 降到
   64×64，但那会把 0.4 µm 的单元周期拉成 1.6 µm——波长 0.74 µm 下周期 1.6 µm 是光栅，
   不是要装配的超表面。改为 `--mode crop`（中心裁剪，pitch 保持 0.4 µm，孔径 25.6 µm）；
   `--mode stride` 保留但文档标注其物理含义。self-test 加 9b/9c 两条。
2. **objects 引擎硬上限**（EXP-64 负对照）：原设计 `_MAX_CELLS_OBJECTS=2000` 只是警告，
   但 EXP-64 的负对照要求 65536 格"必须报错退出"。加独立硬线 `_HARD_LIMIT_CELLS=8192`
   （64×64=4096 允许+警告，256×256=65536 拒绝，实测 exit 1）。
3. **ellipse 单元的 check 降级**（EXP-64）：ellipse 建成 polygon 后引擎侧没有可读的
   x/y/x span/y span 属性，`--check` 对 ellipse 单元只断言 z / z span；逐格旋转的正确性由
   build 侧 cell_params 的 i/j 标注校验 + 装配端双向检查覆盖。box 模板的逐格尺寸断言
   （改一格必红）由 EXP-61 的 3×3 正负对照覆盖。

---

## 10. 已确认的决策（2026-11-11）

1. **规模目标**：第一批**只做到 64×64**（4096 格，objects 引擎）。`group_script` 引擎**本期不实现**，
   步骤 5–6  postponed；`engine` 字段保留在 schema 里但只接受 `"objects"`，传别的报错并指向本计划。
2. **技能命名**：`fdtd-metasurface-assembly`（沿用 Skill A 预留的交接契约名）。
3. **EXP 编号**：EXP-60 起编，本期实际落账 EXP-60…65（六条）。

> 压缩档生效：砍 §5 步骤 5–6（group_script + 性能实测）。保留项：负对照、P01 零破坏回归、EXP 台账。
> `_MAX_CELLS_OBJECTS = 2000` 的阈值本期**不作为接受上限**，只作为
> 「超过就警告，说明 group_script 缺失」的提示（64×64=4096 > 2000，会触发提示——
> 这是有意暴露缺口，不是失败）。
