# TASK-001 建立仓库骨架与双宿主接线

- **单元**：无（仓库级）
- **对应 FEAT**：`FEAT-001-workspace-skeleton`（待建）
- **验收**：`iterations/iter-1-foundation/acceptance.md` 的 A、C、D 三节全绿
- **依赖**：无
- **状态**：active

## 子步骤

1. `git init`，首次提交纳入 `docs/`、`skills/`、`agents/`、`tools/`
2. 写 `tools/skills-wire.py`（幂等、跳过 `_*`、dry-run 默认）
3. 跑 `--apply`，确认 `.agents/skills` 与 `.workbuddy/skills` 条数正确
4. 写 `tools/skills-doctor.py`，六项检查全绿
5. 新开两个会话各验一次目录清单

## 别做

- 不要在这一步搬 `packages/` → `cases/`（那是 TASK-002，风险最高，单独烧）
- 不要顺手改技能正文
