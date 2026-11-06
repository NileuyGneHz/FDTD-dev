# 双宿主接入（DSH 与 WorkBuddy）

> 一句话：两个宿主读**同一批技能本体**，只是发现入口不同。

## 1. 扫描根

| 宿主 | 项目级 | 用户级 | 生效时机 |
|---|---|---|---|
| **DSH** | `<git根>/.dsh/skills`(100) → `<git根>/.agents/skills`(200) | `~/.dsh/skills`(400) → `~/.agents/skills`(500) | watcher，近实时 |
| **WorkBuddy** | `<cwd>/.workbuddy/skills`（不向上搜索） | `~/.workbuddy/skills` | 项目级=会话快照；用户级=活链 |

`rank` 小者赢；同名时高优先级静默覆盖低优先级。

## 2. 本仓库的接线

```
skills/fdtd-*/           本体（真目录，进 git）
.agents/skills/<name>    junction → ../../skills/<name>     DSH 项目入口
.workbuddy/skills/<name> junction → ../../skills/<name>     WorkBuddy 项目入口
```

两处入口都由 `python tools/skills-wire.py --apply` 生成，**永不手改**。

## 3. 六个会静默失效的点

| # | 症状 | 根因 | 处置 |
|---|---|---|---|
| 1 | 子目录开会话，项目技能全无 | DSH 找 `.git` 定根 | `git init` + 从根开会话 |
| 2 | WorkBuddy 子目录开会话只剩用户级 | 根是硬编码 `cwd/.workbuddy/skills` | 同上 |
| 3 | `_TEMPLATE` 混进清单 | 布线未过滤 | wire 跳过 `_*`、无 `SKILL.md` 的目录 |
| 4 | `git init` 后多出几百个待提交文件 | git 跟随 junction 展开 | `.gitignore` 写 `.agents/`、`.workbuddy/skills/fdtd-*/` |
| 5 | 新技能 DSH 有、WorkBuddy 没有 | 前者 live，后者快照 | 新技能先挂用户级，或重开会话 |
| 6 | 技能被旧版静默顶掉 | `.dsh/skills`(100) 覆盖 `.agents/skills`(200) | 该目录永久留空 |

## 4. 技能格式的硬要求（两宿主交集）

- 目录名 == frontmatter `name`，kebab-case
- `name` + `description` **都必须有**；DSH 缺一个直接丢弃
- 只认文件名 `SKILL.md`（大写）
- 入口必须是**真实目录 + 逐技能 junction**；根是链接会被 DSH 整根丢弃
- 用户级目录（C 盘）**只放 junction**，本体永远在 `skills/`

## 5. 自检

```
python tools/skills-doctor.py
```

六项：`.git` 存在 · 两处入口是真目录 · 条数 == 技能数 · junction 可达且名字一致 ·
`.dsh/skills` 为空 · 无跨项目重名。
