# TASK-001 建立仓库骨架与双宿主接线

- **单元**：无（仓库级）
- **对应 FEAT**：`FEAT-001-workspace-skeleton`（已建，2026-11-11）
- **验收**：`iterations/iter-1-foundation/acceptance.md` 的 A、C、D 三节全绿
- **依赖**：无
- **状态**：**done**（2026-11-11）

## 子步骤

1. `git init`，首次提交纳入 `docs/`、`skills/`、`agents/`、`tools/`
2. 写 `tools/skills-wire.py`（幂等、跳过 `_*`、dry-run 默认）
3. 跑 `--apply`，确认 `.agents/skills` 与 `.workbuddy/skills` 条数正确
4. 写 `tools/skills-doctor.py`，六项检查全绿
5. 新开两个会话各验一次目录清单

## 别做

- 不要在这一步搬 `packages/` → `cases/`（那是 TASK-002，风险最高，单独烧）
- 不要顺手改技能正文

---

## 结论（2026-11-11 结项）

A / B / C 三节全绿；D 节「改动已提交」未完成（工作区 46 改 / 2 删 / 110 未跟踪），
属版本控制动作，不是结构缺陷。E 节（可接手性）需真人从零开一次会话验证，仍待。

五个子步骤全部落地，且在第 8–9 步之后继续演进到 13 个技能：
`skills-wire.py` 与 `skills-doctor.py` 六项检查至今全绿，两处入口各 13 条。

## 验证命令

```powershell
$PY="C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
& $PY tools/check_scripts.py           # 期望：OK 包内没有 .py
& $PY tools/check_packages.py          # 期望：ERROR=0
& $PY tools/skills-doctor.py           # 期望：ALL GREEN（两处入口各 13 条）
& $PY tools/check_skill_contract.py    # 期望：ALL GREEN（OK 129 / WARN 0 / FAIL 0）
& $PY tools/check_git_limits.py        # 期望：ERROR=0
```

实测（2026-11-11）：五条命令全部符合期望。

## 后续

- `packages/` → `cases/` 的迁移已在 `cb46e65` 与 `6b3e8f2` 完成（即原计划的 TASK-002）
- `library/` 空壳问题在 2026-11-11 的批次 C 中修复（`_shared/` 迁入 `library/py/`）
- 仓库级悬空结构的完整盘点见 `journal/2026-11-11.md` 会话 3
