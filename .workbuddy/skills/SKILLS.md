# Skill 清单

**（2026-11-06 14:50 复核，本节覆盖下文 11-05 / 13:51 的过时记录）**

实体已移至 `F:\Lumercial_WS\FDTD_WS\skills\<name>\`（5 个真实目录）；本目录
`.workbuddy/skills`、`.agents/skills`、`C:\Users\saber\.workbuddy\skills` 三处均为
**逐条 junction 容器**，每个 `<name>` 指向上面的实体，正文仍只存一份
（三处 `SKILL.md` 实测同一 inode = `IDENTICAL-INODE`）。5 个 skill 统一改名为 `fdtd-` 前缀：
`fdtd-paper-parameter-extraction` / `fdtd-lumerical-unitcell-simulation` /
`fdtd-lumerical-phase-retrieval` / `fdtd-package-workspace` / `fdtd-lumerical-headless`。
下文表里的旧名（`lumerical-*` / `paper-fdtd-*`）、「实体在 `.workbuddy/skills`」、
「顶层 `skills` 是链接」、用户级 junction 的 target 写法，均为 11-05 / 13:51 当时的事实，已失效。
用户级 junction 的实际 target 为 `\\?\F:\Lumercial_WS\FDTD_WS\skills\<name>`。

**本会话（新开的会话）注入的 `available_skills` 已刷新为 47 项，5 个 FDTD skill 全部在列**，
`location` 均为 `C:\Users\saber\.workbuddy\skills\...` → 自动触发已恢复，
13:51 留下的「新建会话后唯一待验证项」**已通过**，不再需要手动 `Read` 兜底。
（`location` 落在用户级、project 根未出现，推测生成注入列表时未传 `params.cwd`；属推断，未从源码复核。）

> 宿主挂载机制（扫描根 / 顺序 / frontmatter / 会话时机 / 链接 / 失败模式）见
> `SKILL-MOUNT-RULES.md`；本文件只记本库的状态与变更。

## 能力清单

| name | 类型 | 状态 | 关联产出 |
|---|---|---|---|
| paper-fdtd-parameter-extraction | 技术 | 显式可调用 | `spec_<id>.json`、假设与缺项清单 |
| lumerical-unitcell-simulation | 技术 | 显式可调用 | R/T/A 谱、summary.csv、.fsp、_p0.log |
| lumerical-phase-retrieval | 技术 | 显式可调用 | 双偏振相位谱、相位差 |
| fdtd-package-workspace | 技术 | 显式可调用 | packages/ 布局、包 README、自检结果 |
| lumerical-fdtd-headless | 技术（薄壳） | 显式可调用 | 根目录 SKILL.md 的八章正文与症状索引 |

`lumerical-fdtd-headless` 是薄壳：宿主加载后拿到 15 条保底速查和正文指针，
正文为 `F:\Lumercial_WS\FDTD_WS\SKILL.md`（77 KB，八章加 §0 症状索引）。
按项目约定，不把正文复制进 skill 目录，避免两份正文各自演化。

## 宿主入口

| 宿主 | 扫描根 | 形式 |
|---|---|---|
| WorkBuddy 项目级 | `.workbuddy/skills` | 实体，无中转 |
| **WorkBuddy 用户级** | `C:\Users\saber\.workbuddy\skills\<name>` | **5 条 junction，指向实体（2026-11-06 13:51 建立）** |
| DSH (rank 200) | `.agents/skills` | 链接，指向 `.workbuddy/skills` |
| 既有引用 | `skills` | 链接，指向 `.workbuddy/skills` |

宿主的 `scanSkillsDirectory` **递归 5 层**、只认文件名 `SKILL.md`，且找到后仍继续钻子目录
（所以 `references/` 里绝不能放 `SKILL.md`，否则会被注册成另一个 skill）。本库主动采用
一层 `<name>/SKILL.md` 布局，但那不是宿主限制。完整规则见 `SKILL-MOUNT-RULES.md`。
新增 skill 时目录名必须等于 frontmatter 的 `name`，并提供非空 `description`。
链接由 Node `fs.symlinkSync(absTarget, link, 'junction')` 创建（PowerShell
`New-Item -ItemType Junction` 亦可），target 为绝对 NTFS 路径
（Git Bash 显示 `/f/...` 只是 MSYS 表示法）。`scanSkillsDirectory` 遇 symlink 会
`stat()` 跟随解析后继续扫，链接形式不影响发现。Git Bash 原生 `ln -s` 会静默退化成复制，别用。

## 变更记录

- 2026-11-05：修复 2026-11-03 把 `.workbuddy\skills` 改名为顶层 `skills` 造成的
  WorkBuddy 项目级自动发现失效。4 个 skill 实体迁回 `.workbuddy\skills\`，
  顶层 `skills` 与 `.agents\skills` 改为 junction，既有 `skills/...` 引用无需改动。
- 2026-11-05：把 C 盘用户级 `lumerical-fdtd-headless` 移入本库，集中管理 FDTD 相关 skill。
  用户级目录现有 **12 个** skill（4 个通用 Windows 工具 + 8 个视频剪辑类，后者为 junction
  链接型），均与 FDTD 无关，保持原位；它们由 `userSkillsDir` 全局扫描，
  **本来就常驻每个 workspace 的注册表**，与本库实体放在哪里无关。
- 所有 SKILL.md 内容零改动，三条路径下 md5 一致。
- 2026-11-06 13:51：按用户要求，在 WorkBuddy 用户级目录建立 5 条 junction，
  模仿原有 8 条视频剪辑 junction 的实现（`dir=True / lnk=False / reparse=True`、
  target `\\?\F:\...`）。**实测本会话即可显式调用这 5 个 FDTD skill**，
  不需要新建会话；详见下方 13:51 验证小节。

## 运行时验证（2026-11-06 00:05，实测）

| 检查 | 结果 |
|---|---|
| `Skill(lumerical-phase-retrieval)` | `Can not find skill` |
| `Skill(lumerical-fdtd-headless)` | `Can not find skill` |
| `Skill(xlsx)`（对照组） | 加载成功 |
| 三条扫描根各发现 | 5 / 5 / 5，md5 一致 |
| frontmatter | 5/5 合规，与可加载的 `windows-cn-docx-python` 同格式 |

结论（00:05）：目录、链接、文件格式、cwd 全部正确，问题只在宿主注册表的**会话级固化**。
⚠️ **13:51 更正**：这条只对「注入列表」成立，不对 `Skill()` 显式调用成立。
挂用户级链接后本会话即可调用，见下节。

## 运行时验证（2026-11-06 13:51，方案 2 执行后实测）

| 检查 | 结果 |
|---|---|
| `Skill(lumerical-phase-retrieval)` | **加载成功**，base dir = `C:\Users\saber\.workbuddy\skills\lumerical-phase-retrieval` |
| `Skill(fdtd-package-workspace)` | **加载成功**，base dir 同上（用户级链接） |
| `Skill(__fdtd_nonexistent_control__)`（阴性对照） | `Can not find skill` |
| `last-launch.json` | 仍 `2026-11-05T15:09:36.607Z` → app 未重启 |
| 会话 | 未更换（同一对话） |

**结论**：用户级 skill 链路是活的，project 级注册表才是会话创建时的快照。
把 5 个名字挂到用户级目录后，**本会话立刻可显式调用，不需要新建会话**。
但本会话注入的 `available_skills` 列表仍是旧的 41 项、不含这 5 个，
所以**不会自动触发**；新建会话后注入列表刷新，自动触发才恢复。
（「实时扫描 vs 目录 watcher 刷新」未区分，以上是已证实的可观测事实，不是机制推断。）

## 运行时机制（2026-11-06 00:25 从 `app.asar` 复核，13:51 更正）

- `getSkillList(params.cwd)` 运行时按需扫 `path.join(cwd, ".workbuddy", "skills")`，
  source=`project`；**project 先于 user 扫**，用 `loadedNames` 按 name 去重，
  所以同名不会重复注册。cwd 实测 `/f/Lumercial_WS/FDTD_WS`，5 个都能读到。
- `addonSelection.projectResources.projectSkillNames` 是**云端项目技能**
  （`project-skill://<skillId>`，需 `projectId`），与本地 `.workbuddy/skills` 无关。
  11-05 日志把它当成本地注入链路是误判，别再引用。
- `settings.json` 的 `skillOverrides` 只对 **user-level** skill 生效，且只能关闭
  （`user-invocable-only` / `off`），开启是删 key；**不能启用项目级 skill**。
  该文件实际无此字段；`enabledPlugins` 里的 `find-skills: true` 是插件开关，别混淆。
- 系统提示里的 `available_skills` **注入列表**在会话创建时固化（本会话仍是 41 项）；
  但 `Skill(name)` 显式调用走活链路，用户级目录新增名字可即时生效。
  **00:25 那条「必须新建会话、文件层改动救不回当前会话」的判断是错的，13:51 已证伪。**
  `Skill` 只按注册名查，`skill://<name>` 与相对路径形式都实测 `Can not find skill`；
  宿主无手动 reload 接口，但用户级目录变化会被感知。

## 修复方案

| # | 做法 | 本会话 | 新会话 | 改动 | 状态 |
|---|---|---|---|---|---|
| 1 | 新建会话（零改动） | ❌ | ✅ | 0 | 仍可用于刷新注入列表 |
| 2 | **用户级目录挂 5 条 junction** | ✅ 已实测 | ✅ | C 盘 skills | **2026-11-06 13:51 已执行** |
| 3 | 手动 `Read` SKILL.md 执行 | ✅ | ✅ | 0 | 兜底，现已被 2 取代 |
| 4 | 输入框 `+` 技能选择器勾 `skill://` chip | 待试 | — | 0 | 未实测 |
| 5 | 改 `skillOverrides` 启用项目级 | ❌ | ❌ | — | **无效路径**，语义不支持 |

**现状**：方案 2 已完成。本会话显式调用 5 个 FDTD skill 均可用（13:51 实测）；
要恢复自动触发（让注入列表出现这 5 个），新建一个会话即可，不必重启 app。
副作用：这 5 个现在在**所有 workspace** 可见；project 先扫 + 按 name 去重，不会重复注册。

链接由 `.workbuddy/skills/maintain-links.cjs` 幂等维护（普通文件，非 skill 目录）：

```bash
node .workbuddy/skills/maintain-links.cjs check     # 状态：5 条 LINK
node .workbuddy/skills/maintain-links.cjs verify    # 三根各 5、md5 全一致
node .workbuddy/skills/maintain-links.cjs link      # 重建（已存在会 SKIP）
node .workbuddy/skills/maintain-links.cjs unlink    # 只删 5 条链接，实体不动
```

### 与 DSH 的关系（2026-11-06 00:33）

- 用户级目录 `C:\Users\saber\.workbuddy\skills\` 是 **WorkBuddy 专属**（源码 `userSkillsDir`），
  **DSH 不读它**。HANDOVER §1 写「DSH 的 skill 根 = `<repo>/.agents/skills`（rank 200）」，
  §3 决策 2 与第 187 行「链接只是让 DSH 看得见」——DSH 只认仓库内入口。
- 方案 2 已于 13:51 执行完毕，结论不变——它**只修 WorkBuddy**：DSH 走
  `.agents/skills → .workbuddy/skills` 实体，实体和链接都没动，零影响也零帮助。
- 本机 DSH 未安装：`/f/DeepseekHarness/` 为空、PATH 无 `dsh`、
  home 无 `.dsh*` / `.agents` / `.claude` → DSH 侧始终无法实测，只能做文件层验证。
- 双系统：DSH 若在 Linux 侧，读不到 NTFS 的 `C:\` / `F:\`，junction 也不跨系统。
  需在它自己的仓库根放一份 skill 实体 + `.agents/skills` 软链；这会形成第二份正文，
  与「正文只留一份」冲突，需同步机制，属未决设计。

### 链接的可迁移性（2026-11-06 00:37）

- 方案 2 的 5 条用户级链接**已于 2026-11-06 13:51 创建**（`maintain-links.cjs link`）。
  实测类型与原有 8 条视频剪辑 junction 完全一致：Python `lstat` 报
  `dir=True / lnk=False / reparse=True`，target 为 `\\?\F:\Lumercial_WS\FDTD_WS\.workbuddy\skills\<name>`。
  它们是零字节指针、不含正文，换环境时**不需要迁移，删掉重建即可**；实体始终在 `.workbuddy/skills/`。
- junction 的 target 是**绝对 NTFS 路径**：换盘符、改目录名、整盘克隆到新机器，
  链接都会指向旧位置而失效；跨到 Linux 则 junction 概念不存在，改用 `ln -s`。
- 不能单独改用户级 skills 的位置：`userSkillsDir = path.join(configDir, "skills")`
  是硬编码拼接，`configDir` 来自 `WORKBUDDY_CONFIG_DIR` / `~/.workbuddy`。
  设 `WORKBUDDY_CONFIG_DIR` 能搬**整个配置根**，但 memory / mcp.json / connectors /
  logs / plugins / settings.json 会一起搬，且需重启 app，代价远大于收益。
- 若确实要搬实体：移到新位置后在原位留 junction（`scanSkillsDirectory` 遇 symlink
  会 `stat()` 解析后继续扫）。**不推荐**：市场安装/重装会 `mkdirSync`、rename、
  删除该目录下的条目，有覆盖链接的风险。
- 幂等重建已落地为 `.workbuddy/skills/maintain-links.cjs`（**普通文件，不是 skill 目录**，
  宿主只扫一层 `<name>/SKILL.md`，不会被误发现）：
  `node .workbuddy/skills/maintain-links.cjs <check|verify|link|unlink>`。
  内部用 `fs.readlinkSync` 判链接、`fs.unlinkSync` 删链接本身、
  `fs.symlinkSync(absTarget, link, "junction")` 重建。
  **别用 `Remove-Item -Recurse` / `fs.rmSync`**，会跟随链接删掉实体。
  13:19 实测 `check` / `verify`：三条根各 5、5 份 md5 全一致、`ALL GREEN`、exit 0。

## 上下文预算（2026-11-06 13:36 实测）

**结论：把实体搬到工作空间 + 原位留 junction 不增加任何上下文量。**

机制（从 `app.asar` 复核）：会话启动只把每个 skill 的 `name` + `description` 注入
`available_skills`；`SKILL.md` 正文、`references/`、`assets/`、根 `SKILL.md` 一律不进上下文。
调用 `Skill(name)` 才加载**那一份**正文，`references/` 需正文内指引才 `Read`。
宿主 `addSkills` 按 name 去重，junction 是指针不是副本 →
成本 = 唯一 skill 数 × `description` 长度，与实体在 C 盘还是 F 盘、链接有几条无关。
用户级 12 个 skill 由 `userSkillsDir` 全局扫描，**本来就在每个 workspace 的注册表里**；
搬实体不会让它们多出来，也不能让它们只在本 ws 可见。

实测数字：`node .workbuddy/skills/context-budget.cjs`（`--json` 输出机器可读）

| 层 | 内容 | 量级 |
|---|---|---|
| L1 每轮常驻 | 17 个 `name` + `description` | 5279 chars ≈ 2447 tok |
| ├ project | 5 个 FDTD | 2965 chars ≈ 803 tok |
| └ user | 12 个通用（8 个视频剪辑类与 FDTD 无关） | 2314 chars ≈ 1644 tok |
| L2 调用时 | 单个 `SKILL.md` | 4–12 KB |
| L2 特例 | 薄壳二次读根 `SKILL.md` | 77 KB ≈ 31k tok |
| L3 纯磁盘 | 正文 36 KB + refs 37 KB + assets 10 KB | 默认不读 |

13:51 挂 5 条用户级链接后复测：`project=5 / user=17 / unique 仍 17 /
residentDescTokens 仍 2447` → 按 name 去重生效，**上下文零增量**，上表数字不变。

### 可选优化（按性价比排序，本轮均未执行）

| # | 做法 | 省的 | 代价 / 风险 |
|---|---|---|---|
| 1 | 把 5 份 `description` 从单行 575–833 字符压到 120–180 字符（只写「何时用」，触发细则移到正文首段） | 常驻约 500–600 tok | 只改本目录 frontmatter，零结构风险；自动触发命中率可能略降 |
| 2 | 设置页隐藏 8 个用户级视频剪辑 skill（`skillOverrides[name] = "user-invocable-only"`，源码 `overrideDisablesModel()` 确认不再把完整描述交给模型） | 常驻约 1150 tok | **全局生效**，别的 workspace 也看不到；建议走 UI，别手改 `settings.json`（有加密字段降级风险） |
| 3 | frontmatter 加 `disable-model-invocation: true`（源码确认 `disableModelInvocation` 字段） | 常驻整条 description | 不再自动触发；⚠️ 对 project-level 是否生效尚未实测；改动同样要新会话生效 |
| 4 | 渐进式披露：4 份长正文拆「薄壳 + `references/`」，根 77 KB 手册按八章拆、靠 §0 症状索引只读一章 | 单次调用成本，不影响常驻 | 改动最大，需重排「正文只留一份」的组织形式 |
| × | `skillOverrides` 试图启用项目级 skill / 用 `WORKBUDDY_CONFIG_DIR` 做 workspace 隔离 | — | 语义不支持 / 搬整个配置根，代价远大于收益 |

`context-budget.cjs` 是只读度量脚本（普通 `.cjs`、非 skill 目录，不会被误发现），
可用来验证上述任一步的前后差异。**坑**：Windows junction 的
`Dirent.isDirectory()` 返回 false，扫描时必须把 `isSymbolicLink()` 一并算作目录，
否则会静默漏掉链接型 skill（首跑只报 4 个用户级 skill，修正后 12 个）。

## 自检清单（2026-11-06 13:51 更新）

**本会话**（无需新建，已全部通过）：

1. `Skill(lumerical-phase-retrieval)` → 返回正文，base dir 指向用户级链接。
2. `node .workbuddy/skills/maintain-links.cjs verify` → `ALL GREEN`、exit 0。
3. 注入列表仍为旧的 41 项、不含这 5 个 → 正常，只影响自动触发，不影响显式调用。

**新建会话后**（唯一待验证项）：

1. 可用 skill 列表应出现 5 个 FDTD 条目 → 自动触发恢复。
2. 若仍缺：确认 cwd 是 ws 根；`maintain-links.cjs check` 应显示 5 条 `LINK`；
   必要时 `unlink` 后重跑 `link`，再开一个新会话。
