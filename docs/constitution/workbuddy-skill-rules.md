# WorkBuddy skill 挂载规则

版本依据：本机 `F:\WorkBuddy\resources\app.asar`（WorkBuddy 5.5.6 / build `5f969292`）。
取证方式：从 asar 二进制里直接提取 JS 实现 + 本机实测对照。

标记含义：
- **[源码]** 在 `app.asar` 里看到的实现，不是推断
- **[实测]** 本机跑过、有输出为证
- **[推断]** 由源码 + 实测推出，未单独做对照实验

规则适用于 **WorkBuddy**；DSH 是另一套（见 §10）。

---

## 0. 结论速查

| # | 规则 | 等级 |
|---|---|---|
| 1 | 扫描根按 `project → user → connector → builtin → plugin → marketplace` 顺序，**先扫的赢** | [源码] |
| 2 | 只认文件名为 `SKILL.md` 的文件；目录名即默认 skill 名 | [源码] |
| 3 | 扫描**递归 5 层**，且找到 `SKILL.md` 后仍继续钻子目录 | [源码] |
| 4 | 去重靠 `loadedPaths`（绝对路径）+ `loadedNames`（`skill.name`），同名后者被丢弃 | [源码] |
| 5 | `name` / `description` 缺失有降级链，**不是硬性必需**，但自动触发依赖 `description` | [源码] |
| 6 | **project 级是会话创建时的快照**；中途搬进来的 skill 当前会话调不到 | [实测] |
| 7 | **user 级是活链路**；挂 junction 后当前会话立刻可 `Skill(name)`，无需新会话/重启 | [实测] |
| 8 | system prompt 注入的 `available_skills` 列表是会话快照，只影响**自动触发** | [实测] |
| 9 | `Skill()` 只按注册名查，`skill://<name>` 与相对路径形式都无效 | [实测] |
| 10 | Windows junction 会被 `stat()` 跟随解析后正常扫描 | [源码] + [实测] |

---

## 1. 扫描根与顺序（决定优先级）

`getSkillList` 主流程 [源码]：

```js
const results = [], loadedPaths = new Set(), loadedNames = new Set();
if (params?.cwd)
  await scanSkillsDirectory(path.join(params.cwd, ".workbuddy", "skills"), "project", ...);
await scanSkillsDirectory(userSkillsDir, "user", ...);
if (fs.existsSync(path.join(configDir, "connectors", "skills")))
  await scanSkillsDirectory(connectorSkillsDir, "connector", ...);
if (builtinSkillsDir && fs.existsSync(builtinSkillsDir))
  await scanSkillsDirectory(builtinSkillsDir, "builtin", ...);
if (!params?.excludePluginSkills) await scanPluginSkills(configDir, ...);
const manifest = readLocalMarketplaceManifest(marketplaceDir);  // 再补市场清单
```

| 顺序 | source 参数 | 扫描根 | 条件 | 本机实例 |
|---|---|---|---|---|
| 1 | `project` | `<cwd>/.workbuddy/skills` | 必须传 `cwd` | `F:\Lumercial_WS\FDTD_WS\.workbuddy\skills`（5 个 FDTD skill） |
| 2 | `user` | `<configDir>/skills` | 总是 | `C:\Users\saber\.workbuddy\skills`（17 个目录） |
| 3 | `connector` | `<configDir>/connectors/skills` | 目录存在 | 未用到 |
| 4 | `builtin` | `builtinSkillsDir`（随 app 分发） | 目录存在 | 内置 skill |
| 5 | `plugin` | `<pluginDir>/skills` + `<pluginDir>/SKILL.md` | `settings.json` 的 `enabledPlugins` | `tencent-*` / `westock-*` 等 |
| 6 | marketplace | `readLocalMarketplaceManifest()` | 有本地清单 | 市场安装项 |

补充入口 [源码]：
- `buddySkillsDir`：按 `applicationId` / `sceneId` / `resourceSnapshotKey` 解析的场景化目录，以 `source="user"` 扫。
- `skillScanDirs`：`getProductConfiguration()` 下发的额外扫描目录，由 `mergeSkillScanDirs()` 合并进参数；**产品配置级，用户不能直接改**。

`source` 映射 [源码]：`project→localSettings`、`user→userSettings`、`builtin→builtin`、`connector→connector`。

### 配置根 `configDir` 怎么定

```js
function resolveWorkbuddyConfigDir(explicitConfigDir) {
  if (explicitConfigDir?.trim()) return explicitConfigDir.trim();
  if (process.env.WORKBUDDY_CONFIG_DIR?.trim()) return process.env.WORKBUDDY_CONFIG_DIR.trim();
  const suffix = process.env.WORKBUDDY_INSTANCE_NUMBER?.trim() ? `-${...}` : "";
  return path.join(os.homedir(), `.workbuddy${suffix}`);
}
```

优先级：**显式传参 > `WORKBUDDY_CONFIG_DIR` > `~/.workbuddy`**（可带 `-<WORKBUDDY_INSTANCE_NUMBER>` 后缀）。
`userSkillsDir = path.join(configDir, "skills")` 是硬编码拼接 → 设 env 搬的是**整个配置根**，不只是 skills。

⚠️ 两份实现有差异 [源码]：
- `skills-domain-service` 里 project 根硬编码 `path.join(cwd, ".workbuddy", "skills")`。
- `host-power-events` 那份用 `process.env.WORKBUDDY_DATA_FOLDER_NAME?.trim() || ".workbuddy"` 作为目录名。

→ 改 `WORKBUDDY_DATA_FOLDER_NAME` 可能影响其中一条链路，**不要依赖它做隔离**。

---

## 2. 目录与文件结构要求

`scanSkillsDirectory` 函数体 [源码]：

```js
async function scanSkillsDirectory(baseDir, source, results, loadedPaths, loadedNames,
                                   depth = 0, disabledRootSkillDirs) {
  if (depth > 5) return;                                  // 递归上限
  const entries = await fs.promises.readdir(baseDir, { withFileTypes: true });
  for (const entry of entries) {
    if (depth === 0 && disabledRootSkillDirs?.has(entry.name)) continue;  // 顶层可整目录禁用
    let isDir = entry.isDirectory();
    if (!isDir && entry.isSymbolicLink())               // junction 在这里被救回
      isDir = (await fs.promises.stat(path.join(baseDir, entry.name))).isDirectory();
    if (!isDir) continue;
    const skillDir = path.join(baseDir, entry.name);
    const skillFile = path.join(skillDir, "SKILL.md");  // 只认这个名字
    try {
      if ((await fs.promises.stat(skillFile)).isFile() && !loadedPaths.has(skillFile)) {
        const skill = await parseSkillFile(skillFile, source);
        if (skill) {
          if (loadedNames?.has(skill.name)) continue;    // 按 name 去重
          results.push(skill);
          loadedPaths.add(skillFile);
          loadedNames?.add(skill.name);
        }
      }
    } catch {}
    await scanSkillsDirectory(skillDir, source, results, loadedPaths, loadedNames,
                              depth + 1, disabledRootSkillDirs);   // 继续钻子目录
  }
}
```

由此得到：

1. **文件名必须是 `SKILL.md`**，大小写敏感；`skill.md` / `Skill.md` 都不认。
2. **目录名是默认 skill 名**；建议 `目录名 == frontmatter.name`，否则 `Skill()` 按 `name` 查、按目录找文件时会不一致。
3. **递归 5 层**（`depth` 0 起扫到 5，`depth=6` 停止）。这是市场安装 zip 布局
   `<skillId>/<技能名>/SKILL.md` 能被发现的原因。
4. **找到 `SKILL.md` 后仍继续递归该目录的子目录** →
   如果 `references/` 里也放了 `SKILL.md`，它会被当成**另一个独立 skill** 注册。
   所以 `references/` 里只放普通 `.md`，别放 `SKILL.md`。
5. 目录遍历用 `readdir` 原始顺序，**没有显式排序**；同名时靠"先扫的赢"决定，别依赖字母序。
6. `disabledRootSkillDirs` 只在 `depth === 0` 生效，即只能整目录跳过顶层条目。

> 更正：本项目早期文档写过「两个宿主都只扫一层 `<name>/SKILL.md`」——**不准确**。
> 准确说法是：本库主动采用一层布局，但宿主本身会递归 5 层。

---

## 3. frontmatter 规范

解析 [源码]：

```js
const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---/;
function parseFrontmatter(content) {
  const match = FRONTMATTER_RE.exec(content);
  if (!match) return { data: {}, body: content };
  return { data: yaml.parse(match[1]) || {}, body: content.slice(match[0].length)... };
}
```

- 必须是**文件开头**的 `---` 块；`\r\n` / `\n` 都行。
- 内容按 YAML 解析；解析抛错会走降级分支（见下）。
- 正则要求闭合 `---` 后不强制空行，但 `body` 会 `replace(/^\r?\n/, "")`。

### 字段白名单 `asSkillFrontmatter` [源码]

| 字段 | 作用 |
|---|---|
| `name` | 注册名；`Skill(name)` 只认它 |
| `description` | 注入 `available_skills` 的文本，决定自动触发 |
| `description_zh` / `description_en` | 多语言描述 |
| `when-to-use` | 何时使用该 skill（内置 skill 会做品牌名替换） |
| `allowed-tools` | 允许的工具列表，逗号分隔或数组 |
| `disable` | `true` 禁用 |
| `disable-model-invocation` | `true` → 不进入模型默认上下文 |
| `user-invocable` | 是否允许用户显式调用 |
| `license` | 许可证 |

**不在白名单里的字段会被忽略**：例如 `agent_created`（SkillManage 用来标记模型创建的 skill，宿主扫描时不读）。
别把关键逻辑放在自定义字段里。

### 降级链 [源码]

```js
const rawDescription = frontmatter.description || body.trim().slice(0, 100) || dirName;
const skillName      = meta?.name || frontmatter.name || dirName;
```

| 字段 | 优先级 |
|---|---|
| `name` | `_skillhub_meta.json` 等 meta 的 `name` > `frontmatter.name` > 目录名 |
| `description` | `frontmatter.description` > 正文前 100 字符 > 目录名 |

元数据文件（按序读第一个存在的）[源码]：`_skillhub_meta.json`、`_marketplace_meta.json`、
`_knot_meta.json`、`_builtin_market_meta.json`、`_user_meta.json`。

YAML 解析失败时 [源码]：不报错、不跳过，走 catch 分支降级为
`name = meta.name || dirName`、`description = dirName`，并用
`readDisableFromFrontmatterLine()` 从原始文本行级读回 `disable: true/false`
（防止 toggle 落盘后被写死成 `false`）。

**结论**：`name` / `description` 不是硬性必需，但缺 `description` 会让自动触发几乎失效；
实际上两者都应显式写。

---

## 4. 去重与优先级

- 两套集合 [源码]：`loadedPaths`（`SKILL.md` 绝对路径，防同一文件被多条链接重复读）、
  `loadedNames`（`skill.name`，防同名 skill 重复注册）。
- 检查顺序：先 `loadedPaths.has(skillFile)`，再 `loadedNames.has(skill.name)`；命中即 `continue`。
- **先扫的赢** → 扫描顺序（§1）就是优先级顺序：project > user > connector > builtin > plugin。

本机实测 [实测]：

| 时刻 | project | user | unique（按 name 去重） | 常驻 description tokens |
|---|---|---|---|---|
| 挂用户级链接前 | 5 | 12 | 17 | 2447 |
| 挂 5 条 FDTD junction 后 | 5 | 17 | **17** | **2447** |

→ 同名挂两处**不会重复注册、不增加常驻上下文**。这也是"实体 + 多条 junction"能成立的基础。

---

## 5. 生效时机（最容易踩坑的一节）

| 改动 | 当前会话 `Skill(name)` | 当前会话自动触发 | 需要新建会话吗 |
|---|---|---|---|
| 往 **project** 级 `.workbuddy/skills/` 新增/搬入 skill | ❌ `Can not find skill` [实测] | ❌ | **要** |
| 往 **user** 级 `~/.workbuddy/skills/` 挂 junction | ✅ 立刻可用 [实测] | ❌ | 显式调用不用；自动触发要 |
| 改 frontmatter 内容 | 已注册的可读到新内容 [推断] | ❌ | 注入列表要刷新 |
| 新建会话 | — | ✅ 注入列表重扫 | — |

实测对照（2026-11-06 13:51）[实测]：

| 检查 | 结果 |
|---|---|
| `Skill(lumerical-phase-retrieval)`（挂链接后） | 加载成功，base dir 指向用户级 junction |
| `Skill(fdtd-package-workspace)` | 加载成功，同上 |
| `Skill(__fdtd_nonexistent_control__)` | `Can not find skill`（阴性对照） |
| `last-launch.json` | 仍是 `2026-11-05T15:09:36.607Z` → app 未重启 |
| 会话 | 未更换 |

**机制边界（可观测事实，非推断）**：
- system prompt 里注入的 `available_skills` **列表**在会话创建时固化 → 本会话仍是旧 41 项、
  不含后加的 5 个 → **不会自动触发**。
- `Skill(name)` 显式调用走的是活链路，用户级目录新增名字可即时生效。
- 「实时按需扫描」还是「目录 watcher 刷新注册表」没有区分开，只记录现象。
- `Skill()` **只按注册名查**；`skill://<name>`、`./.workbuddy/skills/<name>` 都实测
  `Can not find skill`，别试。
- 宿主无手动 reload/refresh 接口，但**用户级目录变化会被感知**。

> 更正：本项目 00:25 写的「本会话无法热加载、任何文件层改动都救不回当前会话」是错的，
> 13:51 已证伪。它只对 project 级与注入列表成立。

---

## 6. 开关与可见性

### frontmatter 级 [源码]

| 字段 | 效果 |
|---|---|
| `disable: true` | 禁用该 skill |
| `disable-model-invocation: true` | `disableModelInvocation` → 不进入模型默认上下文 |
| `user-invocable: false` | 不允许用户显式调用 |

⚠️ `disable-model-invocation` 对 **project 级**是否生效未在本机实测；改 frontmatter 同样受会话快照影响。

### settings 级 `~/.workbuddy/settings.json` [源码]

```json
{ "skillOverrides": { "<key>": "user-invocable-only" | "off" | "name-only" } }
```

- `key` = `frontmatter.name || 文件夹名`（`resolveSkillOverrideKey`），必须与 agent-cli 侧的
  `skill.name` 一致，否则不生效。
- `user-invocable-only` / `off` / `name-only` 都会被 `overrideDisablesModel()` 判为
  "不再把完整描述交给模型"。
- **单项关闭**写 `user-invocable-only`；**全量关闭**写 `off`；**开启 = 删 key**（不写 `on`）。
- **只作用于 user-level skill**，且只能关闭 → **没有任何"启用项目级 skill"的用法**。
- 建议走设置页 UI，别手改 `settings.json`：源码注释明确警告裸 `JSON.stringify` 回写会把
  已加密字段（如 `env.CODEBUDDY_API_KEY`）以明文写回，造成密文降级。

### 其它 [源码]

- `enabledPlugins`（`pluginId@marketplace` 形式）控制 plugin skill 是否扫描。
- `disabledBuiltinSkills` / `disabledRootSkillDirs` 在顶层过滤。
- `addonSelection.projectResources.projectSkillNames` 是**云端项目技能**
  （`project-skill://<skillId>`，需 `projectId`），与本地 `.workbuddy/skills` 无关；
  别把它当本地注入链路。

---

## 7. 链接（junction / symlink）规则

`scanSkillsDirectory` 对链接的处理 [源码]：

```js
let isDir = entry.isDirectory();
if (!isDir && entry.isSymbolicLink())
  isDir = (await fs.promises.stat(path.join(baseDir, entry.name))).isDirectory();
```

- Windows **junction** 的 `Dirent.isDirectory()` 返回 `false`、`isSymbolicLink()` 返回 `true`
  → 走 `stat()` 跟随解析 → 判定为目录 → 正常扫描。
- 因此**链接型 skill 与实体 skill 等价**，不需要复制正文。
- 目标必须是**绝对 NTFS 路径**；换盘符 / 改目录名 / 整盘克隆会失效，跨 Linux 则 junction 概念不存在。
- 用 Node API 创建（免管理员、免 CMD）：`fs.symlinkSync(absTarget, link, 'junction')`。
  删除用 `fs.unlinkSync(link)`（只删链接本身）；**别用 `rmSync` / `Remove-Item -Recurse`**，
  会跟随链接删掉实体。
- Git Bash `ln -s` 在本机会**静默退化成复制**（实测 `[ -L ]` 为 false、内容不共享），别用。
- 本机 junction 的 Python `lstat` 特征 [实测]：`S_ISDIR=True / S_ISLNK=False / reparse=True`，
  `os.readlink()` 返回 `\\?\F:\...`。写扫描/校验脚本时必须把 `isSymbolicLink()` 也算作目录，
  否则会静默漏掉链接型 skill。

本机维护脚本：`node .workbuddy/skills/maintain-links.cjs <check|verify|link|unlink>`（幂等）。

---

## 8. 实际挂载操作（编号步骤）

### 8.1 新增一个 project 级 skill

1. 建目录 `<ws>/.workbuddy/skills/<name>/`，目录名用纯 ASCII、与 `name` 一致。
2. 写 `SKILL.md`，首行 `---` 起 YAML frontmatter，至少 `name` + `description`。
3. `references/` / `assets/` / `scripts/` 放同级子目录；**这些子目录里不要出现 `SKILL.md`**。
4. 自检：`node .workbuddy/skills/context-budget.cjs --json` 看它是否计入 unique。
5. **新建一个会话**（project 级是会话快照，当前会话不会自动出现）。
6. 若想**当前会话立刻可用**：同时在用户级目录挂一条 junction（见 8.2）。

### 8.2 挂到用户级（推荐给"现在就要用"）

1. 确认 `C:\Users\saber\.workbuddy\skills\<name>` 不存在（避免同名冲突）。
2. `node .workbuddy/skills/maintain-links.cjs link`（或自行
   `fs.symlinkSync(absTarget, link, 'junction')`）。
3. `node .workbuddy/skills/maintain-links.cjs verify` → 期望 `ALL GREEN`、exit 0。
4. 当前会话直接 `Skill(<name>)` 验证；阴性对照用一个不存在的名字应报 `Can not find skill`。
5. 要恢复**自动触发**，新建会话刷新注入列表。
6. 回滚：`node .workbuddy/skills/maintain-links.cjs unlink`。

### 8.3 验收清单

| 检查 | 期望 |
|---|---|
| 三条入口（project / user junction / 旧引用 junction）读到的 md5 | 完全一致 |
| frontmatter 首行 / `name == 目录名` / `description` 非空 | 全过 |
| `unique` 按 name 去重后数量 | 不因新增链接而增加 |
| `residentDescTokens` | 不因新增链接而增加 |
| 阴性对照 `Skill(不存在名)` | `Can not find skill` |

---

## 9. 常见失败模式（坑点表）

| 症状 | 根因 | 对策 |
|---|---|---|
| `Can not find skill`，但文件明明在 `.workbuddy/skills/` | project 级是会话快照，skill 是会话创建后才放进去的 | 新建会话；或挂用户级 junction 立刻生效 |
| 挂了链接仍 `Can not find skill` | 名字写错 / `name` 与目录名不一致 / 用了 `skill://` 或路径形式 | 只用注册名；核对 frontmatter `name` |
| `ln -s` 建完内容不共享 | Git Bash 的 `ln -s` 退化成复制 | 用 Node `junction` |
| junction 建了但脚本扫不到 | `Dirent.isDirectory()` 对 junction 返回 false | 把 `isSymbolicLink()` 一并算作目录 |
| `references/` 里多出一个 skill | 递归 5 层，子目录里的 `SKILL.md` 也会被注册 | 子目录里别放 `SKILL.md` |
| 改了 `description` 但没变化 | 注入列表是会话快照 | 新建会话 |
| 同名 skill 内容不是预期的那份 | 先扫的赢（project > user > ...） | 改扫描顺序里的前者，或改名 |
| 想用 `skillOverrides` 启用项目级 skill | 语义只支持 user-level 且只能关闭 | 别试，改挂用户级链接 |
| 想按 workspace 隔离用户级 skill | `userSkillsDir` 是全局的 | 隐藏不相关项，或接受全局可见 |
| 市场安装后链接被覆盖 | 安装流程会 `mkdirSync` / rename / 删条目 | 别把用户级 skills 根目录本身变成链接 |

---

## 10. 与 DSH 的区别

WorkBuddy 与 DSH 是**两套命名空间**，不要混：

| | WorkBuddy | DSH |
|---|---|---|
| skill 根 | `<cwd>/.workbuddy/skills`（project）+ `<configDir>/skills`（user） | `<repo>/.agents/skills`（HANDOVER §1，rank 200） |
| 入口形式 | 实体或 junction | `.agents/skills` 链接指向实体 |
| 是否读用户级目录 | 是 | **否** |
| 本机状态 | 已装、已实测 | `/f/DeepseekHarness/` 为空、PATH 无 `dsh`，未安装 |

双系统下 DSH 若在 Linux 侧，读不到 NTFS 的 `C:\` / `F:\`，junction 也不跨系统；
它需要在自己的仓库根有一份可访问的 skill 实体，这会与本项目「正文只留一份」冲突，需另定同步机制。

---

## 11. 证据来源

- 源码：`F:\WorkBuddy\resources\app.asar`（297,824,907 bytes），关键词定位
  `scanSkillsDirectory` / `parseSkillFile` / `getSkillList` / `asSkillFrontmatter` /
  `resolveWorkbuddyConfigDir` / `mapScanSourceToSkillSource` / `skillOverrides`。
- 实测记录：`.workbuddy/skills/SKILLS.md`（13:51 验证小节）、
  `.workbuddy/memory/2026-11-06.md`。
- 度量工具：`.workbuddy/skills/context-budget.cjs`（`--json`）、
  `.workbuddy/skills/maintain-links.cjs`（`check|verify|link|unlink`）。
