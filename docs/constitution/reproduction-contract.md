# 复现约束（Reproduction Contract）

> **这是什么**：`mode = reproduce` 时，agent 跑一次复现、解释差异、并把经验沉淀成可训练语料的硬判据。
> **给谁看**：接复现任务的 agent、以及之后要拿这些材料训练 / 修订 skills 的人。
> **什么时候读**：开工前读 §1–§3，写报告前读 §5–§7，交付前读 §9。
>
> 配套门禁：`python tools/check_reproduction.py`（本文件每条规则对应 `[R1]`–`[R12]`）。
> 与 `skill-change-contract.md` 的分工：**本契约管「怎么跑一次复现、产出什么证据」；
> 那边管「怎么把证据变成技能」**。两者不重叠，不互相复制条款。
> 上位约束是 L1 `docs/product-context/README.md` §③；冲突时以 L1 为准。

---

## 0. 适用对象与三条不可协商

**适用**：`cases/`（只读参照系）与 `projects/`（在研）中所有 `mode = reproduce` 的单元。
Design 模式不适用本契约，但 §5 的收敛判据与 §6 的输出隔离对两种模式都生效。

| # | 规则 | 为什么是硬的 |
|---|---|---|
| 1 | **Reproduce 模式禁止改几何 / 材料 / 层序去凑目标值** | L1 §③ 明写「为贴合文献改参数 = 数据造假」。P01 把 `ts` 从 185 nm 调到 120 nm 得 0.962 就是反例，那是拟合不是复现 |
| 2 | **口径不同时，差异本身就是产出，不判「复现失败」** | 论文 0.97 出自 CST 2009 + 实验，Lumerical 稳定给 ~0.82。两者不可比，宣判失败会诱导后来者去调参 |
| 3 | **没有可重跑证据的归因，不许写进 SKILL.md** | P01 旧结论「`ts` 量取面差 65 nm ≈0.2 rad」是猜测 + 工程混淆，被反解析推翻。宁可标「未定位」 |

**L1 对每轮的硬要求**（本契约不打折）：参数、目标函数、`_p0.log`、判断依据、停下的理由，五项齐全。
agent 不替人下「物理正确 / 可发表」的结论。

---

## 1. 开工前：口径声明先于任何仿真 `[R1][R3]`

跑第一个 `lumapi.FDTD()` 之前，必须在复现卡里写清：

| 字段 | 含义 | P01 实测值 |
|---|---|---|
| `target.quantity / value / wavelength_um` | 论文给的指标与容差 | `peak_absorption = 0.97 @ 6.0 µm` |
| `target.source` | 数字来自图、正文还是实验 | `paper Fig.2(a) + experiment` |
| `target.solver` | 论文用的求解器 | `CST Microwave Studio 2009` |
| `actual_solver` | 本次用的求解器 | `Lumerical FDTD v251` |
| `locked` | 人锁死、agent 不可动的项 | `materials / layer_stack / topology / geometry` |
| `numerics_aligned_from` | 数值设置以哪个工程为准 | `infrared_perfect_absorber.fsp` |

**判据**：`target.solver != actual_solver` 时，只能做**趋势 / 峰位 / 线形**对照；
`verdict.status` 必须是 `solver_mismatch` 或 `inconclusive`，**禁止**写 `reproduced` 或 `failed`。
`[R3]` 会拦下这一条。

---

## 2. 真相源优先级（本次最贵的教训）

| 级别 | 来源 | 能回答什么 | 陷阱 |
|---|---|---|---|
| 1 | **参考 `.fsp` 及其 `_p0.log`** | 当时**真正跑**的边界、网格、材料、监视器、是否收敛 | 二进制不可 diff；同包多个工程必须逐个单独判定 |
| 2 | 论文正文 / Methods / Fig. | 目标口径、几何定义、材料模型 | Fig 要渲染原图核对，别只看正文文字描述 |
| 3 | 包内 `README.md` / `notes/` / 自测题 | 「当时的判断」，不是事实 | 会过期。P01 自测题 Q4 把 `t=0.185 µm` 写成金属厚度，论文实为 Al₂O₃、金属 0.1 µm |
| 4 | 旧 `SKILL.md` / journal / 记忆 | 线索 | 优先级最低；与 1 冲突时无条件以 1 为准 |

### 硬规则

1. **一个包里的多个 `.fsp` 不是同一个工程** `[R4]`。每个都要单独出
   `layoutmode` + `_p0.log` 收敛判定 + 已存谱。P01 的 `infrared_perfect_absorber.fsp`
   （Periodic，末值 `8.87508e-06`，收敛，0.8196）与 `d2_perfectCross.fsp`
   （PML，跑满 77813 步，末值 `0.046734`，未收敛，无存谱）曾被混为一谈 → `D-001`。
2. **归因必须有证据** `[R2][R7]`。写「因为 X 所以对不上」之前，要有一条可复跑的
   命令 + 输出 + 对照案例。写不出来就标 `未定位`，开 `defects/D-xxx`，**不许**落进 SKILL.md。
3. 论文 Fig 的几何定义、层序、厚度基准面，必须渲染原图核对，不靠二手笔记。

---

## 3. 锁定项 vs 数值设置：边界要写死 `[R2]`

| 类别 | 项 | Reproduce 下能否改 |
|---|---|---|
| `locked` | 材料模型与参数、层序、单元拓扑、周期、几何尺寸（`a/l/w/ts/tm`） | **禁止**。要改先问人 |
| `numerics` | `mesh accuracy` / override、`auto shutoff min`、`simulation time`、波长范围与频点、偏振角、x/y BC（由参考工程定） | **允许**，但只能对齐参考工程或做收敛性对照，且每次改动都要记理由 |
| 白名单外 | 源类型、监视器归一化、材料命名 | 先问人 |

**判据**：`verdict.status == "fitted"` 或卡片里出现「调到 X 以匹配论文」作为结论 → `[R2]` FAIL。
校准数值设置**不算**调参：P01 把 acc 4→8、shutoff 1e-4→1e-5、1 ps→5 ps、
3.5–11 µm/100 pts→4–8.5 µm/91 pts 对齐课程工程，是把**复现条件**对齐，不是拟合。

---

## 4. 顺序：同输入回归 → 反解析 → 重建重跑 `[R6]`

不许一上来就解释差异。按这个顺序：

1. **原 spec 重跑一次**，与历史结果比，`Δ ≤ 5×10⁻³` 才算脚本没坏。
   P01：`0.8083 → 0.8069`，`Δ = 0.0014` ✅
2. **反解析参考 `.fsp`**，出结构与已存谱，单独判收敛。
3. **把反解析出的设置写进 spec 重跑**，与工程已存谱比 `Δ ≤ 5×10⁻³` 且峰位一致。
   P01：`0.8196 → 0.8177`，`Δ = 0.0018`，峰位同为 `6.152 µm` ✅
4. 三条独立结果在目标波长处极差 `≤ 0.005`（P01 实测 `0.0027`）→ 才能说
   「这是本求解器在这套参数下的稳定答案」。

容差沿用 `skill-change-contract.md` §5.2；本契约额外规定**同输入回归阈值 5×10⁻³**
与**跨实现一致性阈值 5×10⁻³**，超了先查脚本，不要开始解释物理。

---

## 5. 收敛三判据与排除清单 `[R5][R7]`

**判「算没算完」缺一不算**（`[R5]` 会自己读日志核）：

1. `layoutmode = 0.0`（analysis 模式，已算过）；`1.0` = 没有可信谱。
2. `_p0.log` 有 `Early termination of simulation, the autoshutoff criteria are satisfied.`
   或 `100% complete` 行；只有 `Completed N iterations` 而无 early termination = 跑满时间上限。
3. **最后一条** `Auto Shutoff` 数值 `<` 该工程设定的阈值。grep 正则必须带指数
   `[0-9.eE+-]+`，否则 `8.87e-06` 被截成 `8.87`，把收敛误判成未收敛。

**排除清单**必须逐嫌疑写四列：嫌疑 / 结论 / 证据 / 可重跑命令。`[R7]` 检查前两列非空，
证据列不许写「已确认」。P01 累计排除：边界条件、网格、收敛、监视器与归一化、
`ts` 量取面、材料实现、十字形状。

---

## 6. 输出隔离与可重跑 `[R9][R12]`

- `cases/` 只读。回归产物一律 `_scratch/regress/<date>/<case>/`，`--out` **必须显式指定**；
  `run_fdtd_sweep.py` 默认落在 spec 同级，会写进 `cases/`（`D-002`）。`[R9]` 检查每条 run 的 `out`。
- 卡片必须带 `rerun_commands[]`，每条都能从仓库根直接执行。`[R12]`。
- **卡内不写绝对路径**（`F:\...`、`C:\Users\...`），换机器即死；只允许仓库相对路径。
  本机解释器 / 仓库根路径属运行时约定，由 `script-contract.md` 管；`[R12]` 只扫卡片文件，
  不扫门禁命令示例。
- 只 `load` 参考 `.fsp`，绝不 `save` 回原文件。

---

## 7. 复现卡：给之后训练 skills 用的机器可读语料 `[R1][R11]`

每次复现结束，在该单元 `notes/repro-card.md` 留一张卡。它是**结构化索引**，
不复制 `notes/` 里的长表格，只指向证据文件；`docs/AGENTS.md` 的「不复制内容」据此成立。

格式：Markdown 正文 + 一个 ` ```repro-card ` JSON 代码块（不引入 YAML 依赖）。
`python tools/check_reproduction.py --emit-template` 打印可直接复制的骨架。

| 字段 | 内容 | 对应检查 |
|---|---|---|
| `case / mode / date` | 单元 ID、`reproduce`、日期 | `[R1]` |
| `target / actual_solver / locked / numerics_aligned_from` | §1 口径声明 | `[R2][R3]` |
| `truth_sources[]` | 每个参考 `.fsp` 的 path / role / converged / shutoff / p0_log | `[R4]` |
| `runs[]` | name / out / p0_log / shutoff_final / threshold / peak_A / peak_lam_um | `[R5][R9]` |
| `same_input_regression` | baseline_A / repeat_A / delta / tolerance | `[R6]` |
| `excluded[]` | suspect / verdict / evidence / rerun | `[R7]` |
| `verdict` | status / gap / explainable_by / stop_reason | `[R8]` |
| `defects[]` | 关联的 D 号 | `[R10]` |
| `training_items[]` | 见 §8 | `[R11]` |
| `rerun_commands[]` | 可复跑命令 | `[R12]` |

`--case <id>` 只查一个包；默认扫全部 `cases/*/notes/repro-card.md` 与
`projects/*/notes/repro-card.md`。一张卡都没有时只报 WARN，不阻塞现有门禁。

---

## 8. 训练条目：经验怎么流向技能 `[R11]`

**这是「方便之后训练 skills」的落点**：每次复现至少产出一条 `training_item`，
五字段齐全，之后不必从 journal 里考古。

| 字段 | 要求 |
|---|---|
| `id` | `R-NNN`，与 D 号 / K 号 / TASK 号不共用前缀 |
| `observation` | 一句话现象，写「做了就会坏」或「这样做才判得准」 |
| `evidence` | 命令 + 输出，或指向 `defects/D-xxx` / `notes/*.md` 的路径 |
| `destination` | `defects` / `notes` / `references` / `scripts` / `SKILL.md` 之一 |
| `landed` | 是否已落地；`true` 时必须给 `target_path` 且文件存在 |

**归属顺序**沿用 `skill-change-contract.md` §1（从下往上，不许跳）：

```
defects/D-xxx  →  包 notes/  →  references/  →  scripts/  →  SKILL.md
   （证据）        （上下文）      （细节）       （能力）      （索引）
```

**分级落点**（本次实测归类，别把三种知识混在一起）：

| 知识类型 | 落点 | P01 实例 |
|---|---|---|
| 属性级细节（API 签名、属性名表） | `references/` | `getnamed` 三签名、v251 属性表 |
| 判据级规则（做了就会坏） | `SKILL.md` 的 CRITICAL | 收敛三判据、多个 `.fsp` 不许混、材料按数值匹配 |
| 可复跑能力 | `scripts/` + 立项声明 | `inspect_fsp.py`：`.fsp` → 四份 JSON |
| 单次偏差解释 | 包 `notes/` | `repro-2026-11-07-fsp-calibration.md` |
| 确定会重演的坑 | `defects/D-xxx` | `D-001`（工程混淆）、`D-002`（默认输出写进 cases） |

### 三条硬规则

1. **SKILL.md 里每条因果断言必须有证据锚点**（D 号或 notes 路径）。没有锚点的推断
   一律降级为「待验证」，不许写成 CRITICAL —— 旧的 `ts` 量取面结论就是这么混进去的。
2. **立项触发**：同类操作出现第 2 次 / 踩到「做了就会坏」的坑 / 原型脚本跑通且要复用。
   立项声明（`消费 X → 产出 Y → stage N 被调用`）写不出来，就不是技能，是笔记。
3. **新增或修订技能后**，按 `skill-change-contract.md` §2/§3 走 8 步或 A/B/C 档门槛，
   并同步 `skills/INDEX.md`、按需条目进 `agents/*/skills.yaml`、跑双门禁。
   **本契约不替代那一套**。

---

## 9. 门禁命令（复制即用）

`[R1]`–`[R12]` 只覆盖**可机检**部分。以下靠自觉，脚本不查，别假装能判：
§2 硬规则 3（渲染论文原图核对几何）、§8 硬规则 1（SKILL.md 因果断言的证据锚点）、
§10 坑点表里的定性判断。这类规则按 `docs/constitution/AGENTS.md` 约束 1 处理。

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS

"$PY" tools/check_reproduction.py --case P01        # 复现卡 R1-R12
"$PY" tools/check_reproduction.py --self-test       # 负对照：确认门禁没退化
"$PY" tools/check_reproduction.py --json            # 机器可读，便于流水线串接
"$PY" tools/check_reproduction.py --emit-template   # 打印新卡骨架
"$PY" tools/check_reproduction.py --card cases/P01_Absorber_042/notes/repro-card.md  # 草稿卡自检
"$PY" tools/check_skill_contract.py                 # 内容契约 K1-K14
"$PY" tools/skills-doctor.py                       # 宿主接入
"$PY" tools/check_scripts.py                       # 包内无 .py
"$PY" tools/check_packages.py --pkg P01             # 打包自检
```

退出码：`0` 通过（允许 WARN）/ `1` 有 FAIL / `2` 参数或卡片解析错误。
输出必须指出改哪个文件。

---

## 10. 会踩的坑（本机实测，按踩到频率排序）

| 现象 | 根因 | 处置 |
|---|---|---|
| 两个 `.fsp` 给出相近的 0.82，被当成同一次运行 | 一个收敛、一个跑满时间上限 | 逐个 `layoutmode` + `_p0.log`；见 `D-001` |
| 遍历对象树后 `getresult("R","T")` 报 `Can not find object 'R'` | `getObjectById` / `getChildren` 改变 group scope | 同一会话**先读已存谱、再遍历树**；`references/fsp-property-map.md` §1 |
| 1 ps 被判成等于 5 ps | diff 用了固定 `1e-9` 绝对下限 | 相对容差 `max(1e-18, |spec|*1e-6)` |
| `npts` 读出来对不上监视器 | 错从源读 | 从 DFT monitor 的 `frequency points` 读 |
| 材料比对全部报「不同」 | 按名字比，课程里有 `uesr_Al2O3` 这种笔误 | 按参数数值匹配 |
| `getnamed` 在源 / 网格 / 监视器上抛错 | 返回的是换行分隔属性名字符串，且三签名行为不同 | fallback `dir(obj)` + `getattr`；属性图 §2 |
| 收敛日志被误判 | 正则漏了指数 | `[0-9.eE+-]+`，取**最后一条** |
| 文档里的命令跑不动 | 引用了已删除的脚本 | 改结构时同轮清引用；`skill-change-contract.md` §9 |
| 包内自测题的参数定义与论文矛盾 | 二手笔记会过期 | 以论文正文 + 参考 `.fsp` 为准，`notes/` 只补记不改原文 |
| 默认 `--out` 写进只读 `cases/` | 输出目录跟着 spec 走 | 显式 `--out _scratch/regress/<date>/...` |

---

## 11. 压缩档（时间不够怎么砍）

| 场景 | 可以省 | **绝对不能省** |
|---|---|---|
| 只补一张卡 | 完整 `excluded[]` | 口径声明 `[R3]` + 收敛数值 `[R5]` + `stop_reason` `[R8]` |
| 只跑一次对照 | 「按参考设置重建重跑」 | 同输入回归 `[R6]` + 反解析 `[R4]` |
| 没时间写长报告 | `notes/` 长表格 | 复现卡最小字段 + `defects/D-xxx` 三段齐全 |
| **完全没时间** | **不动任何 skill** | **只写 defect + 复现卡，标 `status=inconclusive`** |

最硬的降级规则（继承 `skill-change-contract.md` §10）：
**宁可让技能库暂时「不知道」，也不要给它「错误的确定感」。**

---

## 12. 与其它规范的关系 / 变更记录

| 规范 | 管什么 | 本契约的边界 |
|---|---|---|
| L1 `product-context/README.md` §③ | 两种模式、禁止调参凑数、每轮五要素 | 本契约是其可执行展开，不新增放宽 |
| `skill-change-contract.md` | 技能怎么加 / 改 / 回归 / 登记 | 本契约 §8 只产出训练条目，改技能仍走那边 |
| `archive-contract.md` / `cases/AGENTS.md` | 包结构、只读 | 本契约规定回归输出不写回 `cases/` |
| `defects/AGENTS.md` | D 号三段格式 | 本契约 `[R10]` 检查三段齐全 |
| `script-contract.md` | 脚本归属与 CLI | 本契约只要求 `rerun_commands` 可执行 |
| `field-manual.md` / 技能 `references/` | lumapi 技术细节 | 本契约**不写教程**，只给判据与指向 |

| 日期 | 变更 |
|---|---|
| 2026-11-07 | 初版，从 P01 参考 FSP 复现中提炼：口径声明、真相源优先级、锁定/数值边界、三层回归、收敛三判据、复现卡与训练条目；配套 `tools/check_reproduction.py`（R1–R12）。首张卡为 `cases/P01_Absorber_042/notes/repro-card.md` |
