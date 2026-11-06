# agents/INDEX.md — 角色总表

| name | role | 负责哪几段 | 加载哪些技能 | 状态 |
|---|---|---|---|---|
| `fdtd-sim-agent` | sim | stage 0 → 4 | 按 `skills.yaml` 的 `load_order` | 已建，需按新结构更新路径 |

## 扩展位

| role | 什么时候需要 | 备注 |
|---|---|---|
| `review` | 需要判断"偏差是否可信"时 | 只读 `results/` 与 `notes/`，不跑仿真 |
| `library` | 材料库/脚本库开始重复时 | 管 `library/` 与 `defects/` |
| `survey` | 一次要找很多篇论文时 | 只管 stage 1 之前 |

新增角色**只加目录**，不改 `fdtd-sim-agent/`。多个角色共享同一批技能，靠各自 `skills.yaml` 分工。

## 约定

- 名字：`fdtd-<role>-agent`
- 四件套齐全才算一个角色：`AGENT.md`、`agent.yaml`、`skills.yaml`、`tools.yaml`
- 没有 `evals/` 的角色不算建成——没有回归用例就无法发现退化
