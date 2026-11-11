# D-016：`PLAN-2026-11-11-gs-phase-retrieval.md` 头部从未写入（§0 / §1 缺失）

**状态**：`unresolved`（内容不可恢复）——2026-11-11 盘点发现，如实登记，不编造

## 根因

该文件现存内容从 `## 2. 技术方案与模块划分` 开始，**没有一级标题、没有 §0（现状）、
没有 §1（目标态）**；且 `## 7. 执行记录与判据偏差` 排在 §2 之前，说明是分次追加时顺序错乱。

实测判据（2026-11-11）：

| 检查 | 结果 |
|---|---|
| 首字符码点 | `U+000A`（换行），**不是 BOM**，排除「编码头损坏」 |
| 含 `## 0.` | False |
| 含 `## 1.` | False |
| 含一级标题 `^# ` | False |
| `git log --all -- '*gs-phase*'` | 空——**该文件从未入库**，无历史可恢复 |
| 全仓搜 `*gs-phase*` | 仅此一份，无副本 |

因此这不是「搬家时截断」——文件从一开始就缺这两节。

## 修复

**不修复**。按 `docs/AGENTS.md` 约束 2「只写当前有效的东西」与 `journal/AGENTS.md`
约束 1「只写事实与决定」，缺失的决策记录不应事后编造。

已做的处置：

1. 补了一级标题与状态行（`DONE 2026-11-11`，EXP-52…59 落账）
2. 在文件顶部显式标注「§0/§1 从未写入、不补写」，让后来者知道这是残缺而非自己找错
3. 在 `docs/plans/AGENTS.md` 的格式要求里，`§0 现状` 与 `§1 目标态` 本就是必填项——
   本条是**违反该格式的唯一现存实例**

## 验证

```powershell
$PY="C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
# 期望：有 1 个 PLAN 缺 §0/§1（已知且已标注），不阻塞门禁
Select-String -Path docs/plans/PLAN-*.md -Pattern '^## 0\.|^## 1\.' | Group-Object Filename
```

## 影响面

`docs/plans/PLAN-2026-11-11-gs-phase-retrieval.md` 一份。
不影响 `check_experiments.py`（EXP 编号在正文里，D1 仍 65/65），也不影响任何技能。

## 遗留

若将来要补 §0/§1，只能由人依据 `journal/2026-11-11.md` 与 `experiments/EXP-52…59`
反推当时的现状与目标——**agent 不代写**。
