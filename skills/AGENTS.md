# skills/ — 唯一的可执行能力库

## 职责

每个子目录 = 一个技能 = 一段可被 AI 宿主（DSH / WorkBuddy）发现的专业能力。

## 结构

```
<name>/
├─ SKILL.md      概述 / CRITICAL / 核心工作流 / 示例 / 故障排除 / 按需加载
├─ scripts/      可执行入口（遵守 script-contract.md）
├─ references/   长篇细节，正文逐个点名并写「何时读」
└─ assets/       模板与静态资源
```

## 命名

`fdtd-<scope>-<thing>[-<verb>]`，`scope` ∈ `lumerical` / `paper` / `model` / `result` / `package`。
**目录名必须等于 frontmatter `name`**，kebab-case，≤64 字符。见 `docs/constitution/naming.md`。

## 新增一个技能（五步，只改一处登记）

1. 复制 `_TEMPLATE/` → `skills/<name>/`，写 `SKILL.md`（六段结构）。
2. `skills/INDEX.md` 加一行：`name | stage | scripts | consumes | produces | hands_to | 边界`。
3. `python tools/skills-wire.py --apply` 重建两处宿主入口。
4. 进主链路就在 `agents/<role>/skills.yaml` 对应 stage 加引用。
5. 新会话验证：DSH 看 catalog，WorkBuddy 看 `<available_skills>`。

## 约束

1. **不改已有技能的名字与目录**。新能力只通过 `stage` + `hands_to` 接线——这是"不断加小路而不破路"的唯一办法。
2. **`SKILL.md` 是索引，不是手册**。正文超过 500 行就拆进 `references/`。
3. **每个 `references/` 文件都必须在正文被点名**，并写清"何时读"；否则 Agent 看不见它。
4. **脚本必须遵守 CLI 契约**（`--config / --out / --dry-run / --json`）。
5. **`_TEMPLATE/` 永不挂进宿主入口**。
6. 改技能 = 改契约。改完同轮跑 `skills-doctor.py`，并在 `journal/` 记一笔。

## stage

```
0 归档定位 → 1 论文萃取 → 2 建模 → 3 求解 → 4 结果分析 → 5 交付出图    X 横切
```

`stage` 是编排顺序的唯一依据。当前分布见 `INDEX.md`。
