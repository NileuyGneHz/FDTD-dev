# FDTD_WS 结构规范（修订版 v3）

版本：2026-11-06。本文是工作区的**唯一结构定义**：搬目录之前先改本文，再改磁盘。

---

## 0. 三条铁律

| # | 铁律 | 违反的后果 |
|---|---|---|
| 1 | **会话必须在 `FDTD_WS` 根打开** | DSH 靠向上找 `.git` 定项目根，WorkBuddy 只认 `cwd`。从 `projects\R01_x` 打开 = 项目技能全部消失，且不报错 |
| 2 | **包内不放 `.py`**，脚本只有三种归宿（§5） | 能力散落在包里，技能调不到，同一逻辑写三遍 |
| 3 | **入口是生成物**：真目录 + 逐技能 junction，永不手改 | 根是链接会被 DSH 整根丢弃；手改会与 `skills\` 漂移 |

---

## 1. 定位

- **给谁**：做超表面 / 超材料数值研究的科研人员。
- **解决什么**：把「读论文 → 提参数 → 建 Lumerical 模型 → 跑谱 → 判偏差 → 出图」固化成
  **DSH 与 WorkBuddy 都能接管的形状**——同一批技能，两个宿主，一条流水线。
- **已有资产**：10 个已学透的复现包（P01–P10），转为**只读知识资产**。
- **非目标**：文献综述平台、云端渲染、论文排版、多用户协作系统。

## 2. 五条设计原则

1. **一个归档单元 = 一篇论文/一个课题**：论文、`.fsp`、`.lsf`、参数永远同包。
2. **三层分离**：`cases\`（只读）、`projects\`（在研）、`library\`（复用）互不写对方。
3. **能力只在技能里**：任何可执行入口都属于某个技能。
4. **技能与角色是插件**：新增 = 加目录 + 登记一行，不改已有文件。
5. **流程与产出分离**：`docs\` 只放流程与决策。

---

## 3. 全景结构

```
FDTD_WS\                          ★ 所有会话都从这里打开
├─ AGENTS.md                      L0 运行契约：定位 / 铁律 / 路径 / 标准循环
├─ CLAUDE.md                      → @AGENTS.md
├─ README.md  README.en.md        人类入口
├─ .gitignore  .gitattributes
│
├─ docs\                          ── 流程与决策
│  ├─ product-context\README.md       L1 给谁做、解决什么、首版范围、非目标
│  ├─ constitution\                   L2
│  │  ├─ field-manual.md              Lumerical v251 八章正文（唯一技术正文）
│  │  ├─ path-conventions.md          工作根 / ASCII / 零外写 / 体积红线
│  │  ├─ naming.md                    包·技能·角色·缺陷·任务 命名表
│  │  ├─ archive-contract.md          一个归档单元必须有什么
│  │  ├─ script-contract.md           脚本归属与 CLI 契约
│  │  └─ host-integration.md          DSH / WorkBuddy 接入事实与风险
│  ├─ features\specs\                 L3 FEAT-xxx 能力验收
│  ├─ features\feature-v1\            首版能力地图
│  ├─ plans\                          L4 有日期的方案
│  ├─ tasks\{active,recent,archive}\  L5 动作拆分
│  └─ api\                            Lumerical API 索引（指向技能 references）
│
├─ cases\                         ── 【只读】10 个已完成复现
│  ├─ INDEX.md                        十行表：ID/主题/论文/结论/可复用点
│  ├─ _TEMPLATE\
│  └─ P01_Absorber_Liu2010\           ★ 归档单元（下面详述）
│
├─ projects\                      ── 【可写】在研课题，与 cases 同构
│  ├─ _TEMPLATE\
│  └─ R01_<topic>\
│
├─ library\                       ── 跨课题复用（只增不改）
│  ├─ materials\                      材料模型：名称 + 参数 + cite
│  ├─ py\                             纯函数模块（无 __main__），被技能脚本 import
│  ├─ schemas\                        spec / sweep 的 JSON Schema 与校验器
│  └─ figs\                           图样式、配色、导出预设
│
├─ skills\                        ── 【可扩展】唯一的可执行能力库
│  ├─ INDEX.md                        总表：name / stage / scripts / consumes / produces / 边界
│  ├─ _TEMPLATE\                      新技能脚手架（永不挂进入口）
│  └─ fdtd-*\
│     ├─ SKILL.md
│     ├─ scripts\                     ★ 所有可执行入口
│     ├─ references\
│     └─ assets\
│
├─ agents\                        ── 【可扩展】角色包
│  ├─ INDEX.md   _TEMPLATE\
│  └─ fdtd-sim-agent\
│     ├─ AGENT.md  agent.yaml  skills.yaml  tools.yaml
│     ├─ evals\
│     └─ memory\
│
├─ .agents\skills\                ── 【生成物】DSH 项目入口（真目录 + junction）
├─ .workbuddy\skills\             ── 【生成物】WorkBuddy 项目入口（同上）
│
├─ tools\                         仓库级自检（不是技能，也不被技能调用）
│  ├─ check_packages.py               归档单元自检
│  ├─ check_scripts.py                包内出现 .py → FAIL
│  ├─ check_git_limits.py             提交前体积体检
│  ├─ skills-wire.py                  重建两处入口 junction
│  └─ skills-doctor.py                六项风险一次查完
│
├─ defects\                       D-xxx：根因 / 修复 / 验证
├─ journal\                       会话交接：handoff.md、<date>.md、MEMORY.md
├─ iterations\iter-1-foundation\  RELEASE / acceptance / runtime-contract
├─ _scratch\                      一次性脚本、中间 .fsp、日志（gitignore）
└─ _archive\                      课程素材、历史日志（gitignore）
```

---

## 4. 归档单元契约

```
P01_Absorber_Liu2010\
├─ README.md    §0 目标与验收 · §1 论文 · §2 参数 · §3 偏差诊断
├─ paper\       论文 PDF + SI（只读，AuthorYear_Journal.pdf）
├─ model\       .fsp（状态） + .lsf（可读源） + spec_<id>.json（参数）
├─ config\      sweep_*.json / run_*.json —— 只有参数，没有逻辑
├─ results\     csv / 图 / report.md / _p0.log（与 model 那次运行一一对应）
└─ notes\       踩坑、口径、待问作者（每条最终收敛成 defects\D-xxx）
```

| 子目录 | 必须 | 规则 |
|---|---|---|
| `README.md` | ✅ | 接手者只看它就能开工 |
| `paper\` | ✅ | 只读；不改名、不移动 |
| `model\` | ✅ | **路径纯 ASCII**；`.fsp` 是状态、`.lsf` 是源、spec 是参数，三者同放 |
| `config\` | ○ | 脚本从它读输入；不含任何逻辑 |
| `results\` | ○ | 一次运行一个子目录 |
| `notes\` | ○ | 写的是「还没定论的东西」 |

编号：`cases` 用 `P01…P10`（不再新增），`projects` 用 `R01…`。所有单元由对应 `INDEX.md` 收录。

---

## 5. 脚本归属（任何脚本都必须能被技能调用）

| 类型 | 放哪 | 判定 |
|---|---|---|
| **能力脚本** | `skills\<name>\scripts\` | 会被第二个课题用到，或本身就是流水线一环 |
| **模型脚本**（`.lsf`） | 单元内 `model\` | 它是 `.fsp` 的可读源，必须同放；由 `run_lsf.py` 统一执行 |
| **一次性脚本** | `_scratch\` | 只服务一次，不进包、不入库 |

**纯模块**（`lumapi_common.py` 这类，无 `__main__`）放 `library\py\`，被技能脚本 import，不直接运行。

### 5.1 CLI 契约

```
python skills\<name>\scripts\<script>.py --config <json> --out <dir> [--dry-run] [--json]
```

- 不假设工作目录；输入来自 `--config`，输出写 `--out`
- 退出码 `0` 成功 / `1` 可诊断失败 / `2` 参数错误
- 必须支持 `--dry-run` 与 `--json`
- 不得写 `stuff\`、不得写包外、不得联网

### 5.2 强制执行

`tools\check_scripts.py` 扫 `cases\*\scripts\` 与 `projects\*\scripts\`，出现 `.py` 即 FAIL 并指出该迁往哪个技能。
历史遗留写 `allowlist`，只能减不能增。

---

## 6. skills 规范（可扩展）

### 6.1 命名

`fdtd-<scope>-<thing>[-<verb>]`，小写 kebab，≤64 字符，**目录名 == frontmatter `name`**。
`scope` 固定五个：`lumerical` / `paper` / `model` / `result` / `package`。新 scope 先写进本文。

**名字是公开 API**：改名 = 破坏性变更，必须同轮改 `skills\INDEX.md`、`agents\*\skills.yaml`、两处入口。

### 6.2 目录

```
skills\<name>\
├─ SKILL.md     概述 / CRITICAL / 核心工作流 / 示例 / 故障排除 / 按需加载
├─ scripts\     ★ 可执行入口，遵守 §5.1
├─ references\  正文逐个点名并写「何时读」
└─ assets\
```

### 6.3 登记位（新增技能只改这一处）

`skills\INDEX.md` 每行：`name | stage | scripts | consumes | produces | hands_to | 边界`

| stage | 含义 | 现有 |
|---|---|---|
| 0 | 归档定位 | `fdtd-package-workspace` |
| 1 | 论文萃取 | `fdtd-paper-parameter-extraction` |
| 2/3 | 建模 / 求解 | `fdtd-lumerical-unitcell-simulation` |
| 4 | 结果分析 | `fdtd-lumerical-phase-retrieval` |
| 5 | 交付出图 | **空位**（图脚本散在 P02/P04/P05/P06） |
| X | 横切 | `fdtd-lumerical-headless`（+ `run_lsf.py`） |

### 6.4 新增技能的五个动作

1. 复制 `skills\_TEMPLATE\` → `skills\<name>\`，写 `SKILL.md`（六段结构）。
2. `skills\INDEX.md` 加一行。
3. `python tools\skills-wire.py --apply` 重建两处入口。
4. 进主链路就在 `agents\<role>\skills.yaml` 的对应 stage 加引用。
5. 新会话验证：DSH 看 catalog，WorkBuddy 看 `<available_skills>`。

**不改已有技能的名字与目录**，新能力只通过 `stage` + `hands_to` 接线。

---

## 7. agents 规范（可扩展）

命名 `<domain>-<role>-agent`，`role` 固定词表：`sim`（建模跑谱）/ `review`（审复现质量）/
`library`（资产治理）/ `survey`（文献初筛）。

```
agents\<name>\
├─ AGENT.md      唯一运行契约
├─ agent.yaml    模型 / 温度 / 步数 / 超时 / 重试
├─ skills.yaml   按 stage 编排：加载谁、何时、交给谁
├─ tools.yaml    工具白名单
├─ evals\        防退化用例
└─ memory\       known-issues / materials / conventions / journal
```

新增角色只加目录，不改 `fdtd-sim-agent\`。

---

## 8. 双宿主接入与风险

| 宿主 | 项目级 | 用户级 | 生效时机 |
|---|---|---|---|
| **DSH** | `<git根>\.dsh\skills`(100) → `<git根>\.agents\skills`(200) | `~\.dsh\skills`(400) → `~\.agents\skills`(500) | watcher，近实时 |
| **WorkBuddy** | `<cwd>\.workbuddy\skills`（**不向上搜索**） | `~\.workbuddy\skills` | 项目级 = 会话快照；用户级 = 活链 |

### 8.1 六个会静默失效的点

| # | 症状 | 根因 | 处置 |
|---|---|---|---|
| 1 | 子目录开会话，项目技能全无 | DSH 找 `.git` 定根 | `git init` + 从根开会话 |
| 2 | WorkBuddy 子目录开会话只剩用户级 | 根是硬编码 `cwd/.workbuddy/skills` | 同上 |
| 3 | `_TEMPLATE` 混进清单 | 布线时未过滤 | wire 跳过 `_*`、无 `SKILL.md` 的目录 |
| 4 | `git init` 后多出几百个待提交文件 | git 跟随 junction 展开 | `.gitignore` 写 `.agents/`、`.workbuddy/skills/fdtd-*/` |
| 5 | 新技能 DSH 有、WorkBuddy 没有 | 前者 live，后者快照 | 新技能先挂用户级，或重开会话 |
| 6 | 技能被旧版静默顶掉 | `.dsh\skills`(100) 优先级高于 `.agents\skills`(200) | 该目录永久留空，doctor 检查为空 |

### 8.2 wire 脚本三条规则

```
1. 只挂「目录名 == frontmatter name」且存在 SKILL.md 的条目；排除 _TEMPLATE / _* / .gitkeep / INDEX.md
2. 幂等：已是正确 junction → 跳过；指向错误 → 报错，不静默覆盖
3. 挂完自检：条数 == 合格技能数；每条目标可达；.dsh\skills 为空
```

### 8.3 `tools\skills-doctor.py` 检查项

`[1]` `.git` 存在 · `[2]` 两处入口是真目录 · `[3]` 条数 == 技能数（排除 `_TEMPLATE`）·
`[4]` junction 目标可达且目录名 == name · `[5]` `.dsh\skills` 为空 · `[6]` 无跨项目重名

---

## 9. 流程层与篝火模式

| 阶段 | 动作 | 落点 |
|---|---|---|
| 起火 | 读 `AGENTS.md` → 从 `docs\tasks\active\` 取一条 → 定位单元 ID | 5 分钟 |
| 添柴 | 只动一个单元；新坑立刻记 | `defects\D-xxx.md` |
| 灭火 | 写交接：做了什么、卡在哪、下次从哪接 | `journal\<date>.md` |
| 攒堆 | 任务移 `docs\tasks\recent\`；迭代记一行 | `iterations\iter-1-foundation\RELEASE.md` |
| 结营 | 验收 + 更新运行契约 | `acceptance.md` / `runtime-contract.md` |

三条纪律：**一次会话只烧一个单元**；**坑先记 defects 再修**；**docs 与单元内冲突时以单元内为准**。

---

## 10. 与现状的映射

| 现状 | 去向 |
|---|---|
| `packages\P01…P10` | `cases\P01…P10` |
| `packages\PACKAGES.md` | `cases\INDEX.md` |
| 各包 `scripts\` 下 18 个 `.lsf` | 单元内 `model\` |
| P03 的 5 个 `.py` | 通用建模 → `fdtd-lumerical-unitcell-simulation\scripts\`；绘图 → stage 5 新技能；一次性 → `_scratch\` |
| 各包 `scripts\` 下 8 个 json | 单元内 `config\` |
| 根 `SKILL.md` | `docs\constitution\field-manual.md`（同轮改三处指针） |
| `agent.md` | `AGENTS.md` |
| `WhaleNote.md` / 两个 Log | `journal\handoff.md` + `journal\<date>.md` |
| `_shared\lumapi_common.py` | `library\py\` |
| `typora-user-images\` | `docs\assets\` |
| `course_media\` | `_archive\course_media\`（gitignore） |
| `skills\` `agents\` 两处入口 | 不动，补 `INDEX.md` 与 `_TEMPLATE` |

---

## 11. 验收清单

- [ ] `git init` 完成；`.gitignore` 覆盖 `_scratch\`、`_archive\`、`**\*.fsp`、`.agents\`、`.workbuddy\skills\fdtd-*`
- [ ] 每个单元有 `paper\`、`model\`，`README.md` 四段齐全
- [ ] `.fsp` 路径纯 ASCII，单元内不跨目录引用论文
- [ ] `cases\*\scripts\` 与 `projects\*\scripts\` 下**没有任何 `.py`**
- [ ] 所有技能脚本有 `--config / --out / --dry-run / --json`
- [ ] `skills\INDEX.md` 与 `skills\` 目录一一对应，无孤儿
- [ ] `agents\*\skills.yaml` 引用的技能全部存在，stage 顺序与 INDEX 一致
- [ ] 两处入口是真目录，条数 == 合格技能数，`.dsh\skills` 为空
- [ ] 新会话里 DSH 与 WorkBuddy 都能列出全部技能
