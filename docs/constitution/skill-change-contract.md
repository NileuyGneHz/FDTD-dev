# 技能变更契约

> 一句话：**技能是流水线的 API。改技能 = 改契约。**
> 没有证据、没有回归、没有登记的修改，一律按"破坏"处理，不按"改进"处理。
>
> 配套门禁：`python tools/check_skill_contract.py`（内容规则由 `[K1]`–`[K14]` 覆盖）
> 与 `python tools/skills-doctor.py`（宿主接入）。两者全绿才算改完。

---

## 0. 适用对象与三条不可协商

**适用**：`skills/<name>/` 下的 `SKILL.md`、`scripts/`、`references/`、`assets/`，以及 `skills/INDEX.md`。

### 三条不可协商（违反即回滚）

| # | 规则 | 为什么它是硬的 |
|---|---|---|
| 1 | **名字是 API，不改名、不改目录名** | 引用点散在 `INDEX.md`、`agents/*/skills.yaml`、别的技能的 import、journal 里；改名不会报错，只会静默断 |
| 2 | **证据先于改动** | 没有"命令 + 输出 + 对照"就不许动 CRITICAL 与数值判据，否则技能会退化成个人经验 |
| 3 | **门禁 + 回归 + 登记，三者缺一不算改完** | 少任何一项，下次会话的人（或 AI）就得从零猜 |

---

## 1. 先判归属：这段东西到底该去哪儿

这是最容易错的一步。**复现过程中"为了这次跑通"随手把逻辑塞进技能，是技能库腐烂的唯一原因。**

| 现象 | 去处 | 判据 |
|---|---|---|
| 第二个包还会用到的逻辑 | `skills/<name>/scripts/` | 问一句：P01–P10 里除了当前这个包，还有谁会调它？会 → 技能 |
| 只服务这一次复现 | `_scratch/` | 只跑一次、没有第二个调用者、不需要别人复现 |
| 确定的坑（有因果、会重演） | 先 `defects/D-xxx.md`，**再**决定要不要改 `SKILL.md` | 三段齐全：根因 / 修复 / 可重跑验证 |
| 单个包的偏差解释 | 该包 `notes/` | 回答的是"这次为什么差 4%"，不是通用规律 |
| 论文口径、长表格、约定细节 | `references/` | 长、只在特定阶段读、正文点名即可 |
| 模型可读源 | 单元内 `model/*.lsf` | 必须与 `.fsp` 同包，不进 `skills/` |

### 判定顺序（从下往上，不许跳）

```
defects/D-xxx  →  包 notes/  →  references/  →  scripts/  →  SKILL.md
   （证据）        （上下文）      （细节）       （能力）      （索引）
```

**先记证据，再沉淀能力。** 反过来做，你会得到一堆"当时管用、原因不明"的规则。

---

## 2. 新增技能：8 步，每步都有判据

| 步 | 动作 | 判过标准 |
|---|---|---|
| 1 | 写一句立项声明：`消费 X → 产出 Y → 在 stage N 被调用` | 写不出来就不是技能，是脚本或笔记 |
| 2 | 复制 `skills/_TEMPLATE/` → `skills/<name>/` | 目录名 == frontmatter `name`，形如 `fdtd-<scope>-<thing>`，ASCII kebab，≤64 字符 |
| 3 | 写 `SKILL.md` 六段骨架（概述 / CRITICAL / 核心工作流 / 示例 / 故障排除 / 按需加载）。英文技能可换成等价标题，但 **CRITICAL、排错、按需加载**三段必须有 | 正文 ≤500 行；CRITICAL 每条都是"做了就会坏" |
| 4 | 写 `scripts/*.py` | `--config --out --dry-run --json`；退出码 `0/1/2`；不假设 cwd |
| 5 | `skills/INDEX.md` 加一行 | `name \| stage \| scripts \| consumes \| produces \| hands_to \| 边界` |
| 6 | `python tools/skills-wire.py` → 确认计划 → `--apply` | 两处入口条数 == 技能数；不手改入口目录 |
| 7 | `check_skill_contract.py` + `skills-doctor.py` | 双 `ALL GREEN`，exit 0 |
| 8 | **新建会话**验证发现 | 本会话看不到是正常的（§7），不要为此改结构 |

> `_TEMPLATE/` 永不挂进入口；以 `_` 开头的目录一律视为脚手架。

---

## 3. 修改技能：分三档，门槛不同

| 档 | 改什么 | 证据要求 | 回归要求 |
|---|---|---|---|
| **A 文档订正** | 错别字、失效路径、措辞、补一条症状 | 改前能指出错在哪（diff 本身即证据） | 不跑仿真，但必须过 `check_skill_contract.py` |
| **B 判据/流程变更** | `CRITICAL`、阈值、步骤顺序、验收条件 | **一个失败案例 + 一个对照案例** | 至少 1 个已完成 case 复跑，结论不变或差异可解释 |
| **C 脚本实现变更** | `scripts/*.py` 的算法、默认值、输出列 | 改动前后**同输入**的数值对比 | 至少 2 个 case（吸收器 + 超表面各一），差异落在 §5 容差内 |

### B / C 档证据格式（写进 `journal/<date>.md`，缺一项就当没做）

```
触发：P0N，哪条曲线/哪个脚本，偏差多少（数字）
假设：为什么判断是这条规则/这段实现的问题
对照：改前 vs 改后，同 spec、同网格、同频率点
结论：ΔR/ΔT/ΔA 的数值；是否在容差内；不在的话为什么可接受
```

禁止写"已确认""应该没问题""效果更好"。**没有数字就等于没验证。**

---

## 4. 禁止清单（违反即回滚）

1. **改名 / 改目录名**。确需重命名 → 先开 `defects/D-xxx`，同轮改完 `INDEX.md`、`skills.yaml`、所有 import 与正文引用。
2. 往 `references/`、`assets/`、`scripts/` 里放 `SKILL.md` —— 宿主递归 5 层扫描，会被注册成**另一个独立技能**。
3. 在 `SKILL.md` 里写绝对路径（`F:\...`、`C:\Users\...`）。换机器即死；只允许仓库相对路径，以及 §8 里那一条托管 Python 解释器路径。
4. 把回归结果写回 `cases/`。`cases/` 是只读参照系，回归输出只能落 `_scratch/regress/`。
5. 脚本偷偷读全局路径 / 依赖 cwd。输入全来自 `--config`，输出全写 `--out`。
6. 删除或弱化 `CRITICAL` 条目而不留 defect 号。
7. **为了让本次跑通而放宽阈值或容差**。容差只能被证据收紧，不能被方便放宽。
8. 手改 `.workbuddy/skills` 或 `.agents/skills`（生成物，由 `skills-wire.py` 重建）。
9. 把 `_TEMPLATE/` 或任何 `_` 开头的目录挂进入口。
10. 在技能目录里联网、`pip install`、写 `%TEMP%`。
11. 在同一个技能里保留两份实现（"新的先放着，旧的还能用"）。**一份实现原则**：要么替换，要么开新技能。

---

## 5. 回归：怎么证明没改坏

**核心约束：`cases/` 只读。** 回归一律输出到 `_scratch/regress/<skill>-<YYYYMMDD>/`。

### 5.1 三层回归（按成本从低到高，前一层不过不进下一层）

| 层 | 命令 | 期望 | 耗时 |
|---|---|---|---|
| L1 契约 | `python tools/check_skill_contract.py` | `ALL GREEN`、exit 0 | 秒级 |
| L1 宿主 | `python tools/skills-doctor.py` | `ALL GREEN`、exit 0 | 秒级 |
| L2 脚本 | `python skills/<name>/scripts/<s>.py --dry-run ...` | 打出计划、**不开会话** | 秒级 |
| L3 数值 | 选 1 吸收器 + 1 超表面 case 复跑 | 差异落在 5.2 容差内 | 分钟–小时 |

### 5.2 容差表（默认值；改容差本身属于 B 档变更）

| 改动性质 | 判据 | 容差 |
|---|---|---|
| 纯重构、无算法改动 | `summary.csv` 逐行 | 逐位相同（`Δ ≤ 1e-6`） |
| 算法改但物理等价 | R / T / A 全频点 | `≤ 0.5%` 绝对 |
| 改网格或收敛策略 | 每条超差曲线 | `≤ 1%`，且必须逐条解释 |
| 新增输出列 | 旧列不变 + 新列可复算 | 旧列逐位相同 |

超差就是 FAIL。**不要**用"整体趋势一致"糊过去。

---

## 6. 改一个技能，必须同步哪几处

单一真相源：`skills/INDEX.md` 是唯一技能表，`agents/*/skills.yaml` 是唯一编排，`journal/` 是唯一变更记录。

| 改动 | 必须同步 | 不同步的后果 |
|---|---|---|
| 新增技能 | `INDEX.md` + `skills-wire.py --apply` + `skills.yaml`（若进主链路） | 发现不了 / 编排断 |
| 改名字 | 禁止；确需改 → 全部引用点 + defect | 静默断链，运行时才炸 |
| 改 `scripts/` 文件名 | `INDEX.md` 的 scripts 列 + 正文命令示例 + 跨技能 import | `FileNotFoundError` |
| 改 `CRITICAL` | `journal/` + 对应 `defects/D-xxx` | 判据退化成传说 |
| 改 `references/` 文件名 | 正文「按需加载」段 | 文件等于不存在 |
| 改 `stage` / `hands_to` | `INDEX.md` + `skills.yaml` | 流水线顺序错，且不报错 |
| **任何改动** | `journal/<date>.md` 一笔 | 下次会话从零猜 |

`skills/INDEX.md` 是**全集**，`agents/*/skills.yaml` 是**主链路子集**——所以技能可以只登记 INDEX 不进编排（横切能力、按需能力）。
但 `skills.yaml` 里写下的每一条 `path` 都会由 `[K14]` 验证：指向的目录必须存在且含 `SKILL.md`。
**改名后不同轮改技能表，`check_skill_contract.py` 必红。**

---

## 7. 宿主生效边界（本项目已实测，别再试错）

| 动作 | 当前会话能 `Skill()` 吗 | 什么时候生效 |
|---|---|---|
| 新增/修改 **project 级** `.workbuddy/skills` | ❌ `Can not find skill`（会话快照） | 新建会话 |
| 挂 **user 级** junction（`~/.workbuddy/skills`） | ✅ 立刻 | 自动触发仍需新会话 |
| 改 frontmatter `description` | 已注册的可读到新内容 | 注入列表要刷新 |

**因此本项目规范：技能改动一律假设"下一会话才生效"。**
不要在同一轮里"改完技能 → 立刻依赖它跑流水线"，那条路走不通，会浪费半小时。

要当前会话立刻能用：往用户级目录挂一条 junction（Node API，免管理员、免 CMD）：

```bash
node -e "const fs=require('fs');const n='fdtd-lumerical-x';const s='F:/Lumercial_WS/FDTD_WS/skills/'+n;const u=process.env.USERPROFILE+'/.workbuddy/skills/'+n;if(!fs.existsSync(u))fs.symlinkSync(s,u,'junction');console.log(u)"
```

挂完用注册名显式调用（`skill://` 与相对路径都无效）；确认时用一个不存在的名字做阴性对照，应报 `Can not find skill`。

> **注意**：不要去找 `.workbuddy/skills/maintain-links.cjs` —— 那是 11-05 重构前的旧布局产物，**已删除**。
> 旧文档里的命令会腐烂，这正是 `[K9]` 存在的原因；改结构时必须同轮清引用。

---

## 8. 门禁命令（复制即用）

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

"$PY" tools/check_skill_contract.py    # 内容契约 K1–K14（含 INDEX 登记与 skills.yaml 编排）
"$PY" tools/skills-doctor.py           # 宿主接入 6 项
"$PY" tools/check_scripts.py           # 包内不得有 .py
"$PY" tools/skills-wire.py             # dry-run：看入口计划（--apply 才落盘）
```

四条 exit 0 才算改完。任何一条非 0，**不许提交**。

---

## 9. 会踩的坑（本机实测，按踩到频率排序）

| 症状 | 根因 | 处置 |
|---|---|---|
| frontmatter 读不到，`name` 为空 | 文件带 UTF-8 BOM，首行实际是 BOM + `---`，`startswith("---")` 判假 | 解析前 `lstrip("\ufeff")`；本仓库 `fdtd-lumerical-headless` 就是这种 |
| `description` 解析成空串 | 用了折叠块 `description: >`，正则只抓第一行 | 先识别 `>`，再收集后续缩进行 |
| 引用看着对，实际不存在 | 跨技能引用漏了前缀，写成 `scripts/run_fdtd_sweep.py`（实际在 `fdtd-lumerical-unitcell-simulation/scripts/`） | 跨技能必须写全 `<skill>/scripts/<file>`；`[K9]` 会抓 |
| 改完 `Skill(name)` 立刻报 `Can not find skill` | project 级是会话快照，不是文件坏了 | 新开会话；要立刻用就挂 user 级 junction |
| `references/` 里多出一个技能 | 递归 5 层，子目录的 `SKILL.md` 被注册 | 子目录只放普通 `.md` |
| `ln -s` 建完内容不共享 | Git Bash 的 `ln -s` 静默退化成复制 | 用 Node `fs.symlinkSync(..., "junction")` |
| 扫不到链接型技能 | junction 的 `Dirent.isDirectory()` 为 false | 把 `isSymbolicLink()` 一并算作目录 |
| `--dry-run` 还是开了仿真会话 | 只"打印参数"就返回，没在校验阶段拦 | dry-run 必须在 `lumapi.FDTD()` **之前** return |
| 换机器后规则全失效 | 文档里写了 `F:\Lumercial_WS\...` 绝对路径 | 只写仓库相对路径 |
| 文档里的命令指向已删除的脚本 | 目录重构后没人清引用（实例：`maintain-links.cjs` 已于 11-05 删除） | 改结构时同轮 grep 旧名；`[K9]` 只覆盖技能正文，规范文档要人工扫 |
| 提交后仓库里多了 `__pycache__` | 本地缓存进了库 | `git ls-files '*.pyc'` 应为空；`.gitignore` 已覆盖 |

---

## 10. 压缩档（时间不够怎么砍）

| 场景 | 可以省 | **绝对不能省** |
|---|---|---|
| 只改错别字 / 路径 | 数值回归、宿主检查 | `check_skill_contract.py` + journal 一笔 |
| 改判据（B 档） | 第二个 case 回归（只跑 1 个） | **对照案例 + 容差数字** |
| 没时间写 references | 长内容压进正文（注意 ≤500 行） | 「按需加载」段 + 文件被点名 |
| **完全没时间** | **不动 skill** | **只写 `defects/D-xxx`，三段齐全** |
| 急着当前会话就要用 | 不写 references、不补 Examples | 挂 user 级 junction + 过契约检查 |

**最硬的一条降级规则**：没时间就只写 defect，**不要改技能**。
技能库宁可暂时"不知道"，也不能有"错误的确定感"。

---

## 11. 与其它规范的关系

| 规范 | 管什么 | 本契约的边界 |
|---|---|---|
| `script-contract.md` | 脚本放哪、CLI 长什么样 | 本契约只管"技能内脚本是否合规"，归属判定引用它 |
| `naming.md` | 名字形状、保留字 | 本契约不重复定义命名，只规定"改名 = 破坏性变更" |
| `host-integration.md` | 双宿主怎么接线 | 本契约引用其结论，不重新推导 |
| `defects/AGENTS.md` | 缺陷三段格式 | 本契约规定"改 B/C 档前先有 defect" |
| `cases/AGENTS.md` | 归档包只读 | 本契约规定回归输出不得写回 `cases/` |
| `reproduction-contract.md` | 复现怎么跑、证据怎么留、`training_items` 怎么产出 | 本契约管「怎么把条目变成技能」，不重复复现流程 |
| `skills/AGENTS.md` | 目录结构与五步入库 | 本契约是其"约束"节的展开与强制执行 |

---

## 12. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-07 | 初版：确立归属判定顺序、A/B/C 三档修改门槛、容差表、门禁四条、压缩档降级规则；配套 `tools/check_skill_contract.py`（K1–K14），首次运行 5 个技能 `ALL GREEN`（5 项 WARN） |
| 2026-11-07（二轮） | **首次实战检验**：按 §2 的 8 步新增 `fdtd-lumerical-fsp-introspection`，按 §3 的 B 档订正 `fdtd-lumerical-unitcell-simulation`（失败案例 + 对照案例 + 2 个 case 数值回归，见 `journal/2026-11-07.md`）。结论：8 步够用，且「证据先于改动」直接拦下了一次错误结论（P01 的 ts 量取面猜测）。新增 §2 步骤 6 的 `skills-wire.py --apply` 与 §6 的按需编排（`skills.yaml` 加条目但不进 `load_order`）两个实操细节，已写入对应文件。技能数 5→6，门禁 `ALL GREEN`（FAIL 0 / WARN 4，WARN 全为既有脚本 CLI，属 C 档遗留） |
