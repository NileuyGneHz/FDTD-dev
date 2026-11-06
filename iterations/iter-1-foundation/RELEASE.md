# iter-1-foundation · RELEASE

> 一句话：把"十个学习包"改造成"可被两个 AI 宿主接管的研究流水线"。
> 每完成一步追加一行，不要等到结营才写。

## 状态

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | 目录骨架（docs / cases / projects / library / defects / journal / iterations） | 进行中 |
| 2 | 根契约 `AGENTS.md` + `CLAUDE.md` | 完成 |
| 3 | L1/L2 文档（product-context、constitution 六篇） | 完成 |
| 4 | 模块级 `AGENTS.md`（cases / projects / library / skills / agents / tools / defects / journal / iterations / tasks / specs / plans / api） | 完成 |
| 5 | `skills/INDEX.md` 与 `agents/INDEX.md` | 完成 |
| 6 | `git init` + `.gitignore`（含 junction 排除） | 完成 |
| 7 | `tools/skills-wire.py`、`skills-doctor.py`、`check_scripts.py` | 完成（doctor ALL GREEN） |
| 8 | `packages/` → `cases/` 迁移（含 `.lsf` 归位 `model/`） | 完成 |
| 9 | 根 `SKILL.md` → `docs/constitution/field-manual.md` 并改指针 | 完成 |
| 10 | `agent.md` → `docs/constitution/collaboration-charter.md`，根契约由 `AGENTS.md` 承担 | 完成 |

## 回顾

- 先定契约再搬文件，是对的：十次搬动里，有四次因为"该放哪"没写清而返工。
- 技能改名（`cut-` / `fdtd-` 前缀）的代价比预期低，因为所有引用都在 `skills.yaml` 与 `INDEX.md` 两处。
- 真正的坑都不是目录，是**宿主边界**：`.git` 缺失、junction 被 git 展开、WorkBuddy 只认 cwd。
