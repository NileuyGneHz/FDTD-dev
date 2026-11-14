# core-skill-authoring — spec.json 格式

## 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | `<pack>-<thing>`，小写 kebab，≤64 字符；**必须等于目录名** |
| `description` | ✅ | ≥20 字符；写「做什么 + 什么时候用 + 触发词」 |
| `domain` | ○ | 默认取 `name` 的前缀；应与 `INDEX.md` 的 pack 表一致 |
| `stage` | ○ | 默认 `X`；合法值 `0`–`4` 或 `X`（按需） |
| `consumes` | ○ | 消费什么；写进 INDEX 的 `consumes` 列 |
| `produces` | ○ | 产出什么；写进 INDEX 的 `produces` 列 |
| `hands_to` | ○ | 默认 `core-lead-agent` |
| `boundary` | ○ | 什么时候别用；写进 INDEX 的边界列 |

## 最小示例

```json
{
  "name": "core-session-handoff",
  "description": "把一次会话的目标、动作、卡点与下一步写成 journal 交接，保证下一个人三分钟内接上。"
}
```

## 完整示例

```json
{
  "name": "lit-quote-verify",
  "description": "验证论文包 README §2 的每条引用块是否能在对应 PDF 内 grep 到原句，输出 found/missed 清单。当归档新论文包、或怀疑引文被手打改动时使用。",
  "domain": "lit",
  "stage": "2",
  "consumes": "包目录（README §2 引用块 + paper/*.pdf）",
  "produces": "每条引文的 found/missed 报告",
  "hands_to": "lit-claim-audit",
  "boundary": "只验证引文是否在 PDF 里，不判断引文选得好不好"
}
```

## 生成物

脚本会创建：

```text
skills/<name>/
├─ SKILL.md            六段骨架（正文由人补）
├─ scripts/main.py     CLI 骨架（--config/--out/--dry-run/--json）
├─ references/format.md
└─ assets/.gitkeep
```

并在 `skills/INDEX.md` 的 `<!-- NEW-SKILL-ROW -->` 上方插入一行。

## 常见错误

| 错误 | 原因 | 修法 |
|---|---|---|
| `invalid name` | 只有一段（如 `handoff`） | 加 pack 前缀：`core-handoff` |
| `description 少于 20 字符` | 写得太短 | 补「什么时候用」 |
| `target exists` | 同名技能已存在 | 换名，或确认后手工删除 |
| 契约检查 K3 失败 | 生成后手工改了目录名 | 目录名与 frontmatter `name` 必须同步改 |
