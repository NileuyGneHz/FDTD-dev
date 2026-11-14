---
name: core-skill-authoring
description: 按工作区契约创建一个新技能的骨架，并把它登记到 skills/INDEX.md。用于「要新增能力」而不是「改已有技能」的场景；只建骨架与登记位，不替人写正文。
domain: core
stage: 0
version: 1.0.0
---

# core-skill-authoring

## 1. 用途

消费 **一份技能立项 spec（JSON）** → 产出 **`skills/<name>/` 骨架 + `INDEX.md` 一行** → 在 stage 0 被调用。

**什么时候用**：

- 要新增一个会被第二个单元复用的能力。
- 需要保证新技能从第一天就满足目录、frontmatter、六段正文、INDEX 登记。

**什么时候别用**：

- 修改已有技能（走 `skill-change-contract.md` 的 A/B/C 档）。
- 只服务一次的逻辑（放 `_scratch/`）。
- 只是想把一段长文存起来（放 `references/` 或 `docs/`）。

## 2. CRITICAL

1. **不覆盖已存在的目录**。目标存在就 `exit 1`，绝不静默合并。
2. **目录名必须等于 frontmatter `name`**，形如 `<pack>-<thing>`；不合法直接 `exit 2`。
3. **必须登记 INDEX**。没有 INDEX 行的技能 = 不存在；找不到标记时 `exit 1`，不硬写。
4. **本会话创建，下一会话才生效**（WorkBuddy 项目级是会话快照）。不要在同一轮依赖它跑业务。
5. **不写业务正文**。脚本只填元数据与六段骨架；CRITICAL 的具体条目由人写。

## 3. 工作流

1. 写一份 spec JSON（字段见 `references/format.md`）。
2. `--dry-run` 看计划：目标路径、将要创建的文件、INDEX 行。
3. 去掉 `--dry-run` 执行。
4. `python tools/skills_wire.py --apply` 重建两处宿主入口。
5. `python tools/check_skill_contract.py` 与 `tools/skills_doctor.py` 双绿。
6. 补写 `SKILL.md` 的 CRITICAL、工作流细节，再跑一次契约检查。

## 4. 示例

```powershell
# 1. 看计划（不落盘）
python skills/core-skill-authoring/scripts/new_skill.py --config _scratch/spec.json --out _scratch --dry-run

# 2. 执行
python skills/core-skill-authoring/scripts/new_skill.py --config _scratch/spec.json --out _scratch --json

# 3. 接线 + 门禁
python tools/skills_wire.py --apply
python tools/check_skill_contract.py
python tools/skills_doctor.py
```

`_scratch/spec.json`：

```json
{
  "name": "core-session-handoff",
  "description": "把一次会话的目标、动作、卡点与下一步写成 journal 交接，保证下一个人三分钟内接上。",
  "domain": "core",
  "stage": "X",
  "consumes": "会话记录 / 任务状态",
  "produces": "journal/<date>.md + handoff.md",
  "hands_to": "core-lead-agent",
  "boundary": "不做任务拆分；不替代 defects 记录"
}
```

## 5. 故障排除

| 症状 | 根因 | 处置 |
|---|---|---|
| `exit 2 invalid name` | 名字不是 `<pack>-<thing>` | 改 `name`；两段以上，小写 kebab |
| `exit 1 target exists` | 目录已存在 | 改名字，或先手工确认后删除 |
| `exit 1 INDEX marker missing` | INDEX 被改坏 | 恢复 `<!-- NEW-SKILL-ROW -->` 标记 |
| 新建后当前会话调不到 | WorkBuddy 会话快照 | 新开会话；或挂用户级 junction |
| 契约检查 K6 失败 | references 文件没在正文点名 | 在 §6 补一行「何时读」 |

## 6. 按需加载

| 文件 | 何时读 |
|---|---|
| `references/format.md` | 写 spec JSON、需要字段语义与最小示例时 |
