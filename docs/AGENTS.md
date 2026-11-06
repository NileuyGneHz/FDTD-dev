# docs/ — 流程与决策层

## 职责

存放**流程、规范、决策**。不存放研究产出（那里是 `cases/` 与 `projects/`）。

## 目录与层级

| 目录 | 层级 | 放什么 | 谁维护 |
|---|---|---|---|
| `product-context/` | L1 | 为谁做、解决什么、MVP、非目标 | PM，几乎不动 |
| `constitution/` | L2 | 路径、命名、归档契约、宿主接入 | Engineer |
| `features/specs/` | L3 | FEAT-xxx 的能力与验收标准 | PM |
| `plans/` | L4 | 有日期的实现方案 | PM + Engineer |
| `tasks/` | L5 | 动作拆分，分 active / recent / archive | 谁做谁写 |
| `api/` | — | 外部接口索引（指向技能 references，不复制） | Engineer |

## 约束

1. **L1 几乎不动**。它一变，所有 Spec/Plan 都要复审——宁可保守。
2. **只写当前有效的东西**。被替代的方案删掉，历史在 git 里。
3. **不复制内容**。能从 `skills/*/references/` 指过去就指过去，避免两份真相。
4. **每份文档第一行写"这是什么、给谁看、什么时候读"**——这是渐进式披露的入口。
5. `tasks/` 只保留三段：`active/` 正在做、`recent/` 刚做完只留结论、`archive/` 历史。
   **AI 优先读 active，不得自行翻阅 archive 找任务。**

## 命名

见 `constitution/naming.md`。FEAT / TASK / D / PLAN 四类编号互不共用前缀。
