# agents/ — 角色包

## 职责

定义"谁来做、按什么顺序做、允许用什么工具"。它不实现能力——能力在 `skills/`。

## 结构（四件套 + 两块私产）

```
<name>/
├─ AGENT.md      唯一运行契约：角色 / 能力边界 / 工作流 / 检查点
├─ agent.yaml    模型、temperature、max_steps、timeout、retry
├─ skills.yaml   按 stage 编排：加载谁、何时、交给谁
├─ tools.yaml    工具白名单
├─ evals/        防退化用例（输入 / 期望动作 / 禁止动作）
└─ memory/       known-issues / materials / conventions / journal
```

## 命名

`fdtd-<role>-agent`，`role` ∈ `sim` / `review` / `library` / `survey`。

## 新增角色

**只加目录，不改已有角色**。多个角色共享同一批技能，靠各自的 `skills.yaml` 分工。

## 约束

1. **`skills.yaml` 里的技能名必须真实存在**，且 `stage` 顺序与 `skills/INDEX.md` 一致。
2. **一次只加载一个主技能 + 必需支撑技能**，不许"以防万一全加载"——它们互相竞争注意力。
3. **`memory/` 只记实测**。没跑过的结论不许写进 `known-issues.md`。
4. **技能与 memory 冲突时，信 memory 里的实测证据**，并在同一轮修技能。
5. `evals/` 每条必须写"禁止动作"——只写"应该做什么"测不出退化。
