# 命名表

> 名字是 API。改名 = 破坏性变更，必须同轮改所有引用点。

## 1. 归档单元

```
P0N_<Topic>_<AuthorYear>     复现案例（cases/）   例：P01_Absorber_Liu2010
R0N_<Topic>                  在研课题（projects/）例：R01_PhaseMetasurface
```

- `P` 号**不再新增**，十个已学完的包占定。
- `R` 号从 `R01` 起，按立项顺序，不复用。

## 2. 技能

```
fdtd-<scope>-<thing>[-<verb>]
```

- `scope` ∈ `lumerical` / `paper` / `model` / `result` / `package`
- 小写 kebab，≤64 字符，**目录名必须等于 frontmatter `name`**
- 例：`fdtd-lumerical-unitcell-simulation`、`fdtd-paper-parameter-extraction`

## 3. 角色

```
fdtd-<role>-agent
```

- `role` ∈ `sim`（建模跑谱）/ `review`（审质量）/ `library`（资产治理）/ `survey`（文献）
- 例：`fdtd-sim-agent`

## 4. 编号类

| 类型 | 格式 | 放哪 | 例 |
|---|---|---|---|
| 需求 | `FEAT-<NNN>-<slug>` | `docs/features/specs/` | `FEAT-001-spec-schema` |
| 计划 | `PLAN-<YYYYMMDD>-<slug>` | `docs/plans/` | `PLAN-20261106-case-migration` |
| 任务 | `TASK-<NNN>-<slug>` | `docs/tasks/{active,recent,archive}/` | `TASK-001-case-index` |
| 缺陷 | `D-<NNN>-<slug>` | `defects/` | `D-001-ascii-path-1113` |

## 5. 文件

| 类型 | 格式 | 例 |
|---|---|---|
| 论文 PDF | `<AuthorYear>_<Journal>.pdf` | `Liu2010_PRL.pdf` |
| 模型参数 | `spec_<unit>.json` | `spec_p01.json` |
| 扫参配置 | `sweep_<unit>.json` | `sweep_p01.json` |
| 结果目录 | `results/<run_id>/` | `results/20261106_a` |
| 会话日志 | `journal/<YYYY-MM-DD>.md` | `journal/2026-11-06.md` |

## 6. 保留字

以下名字不得作为技能名：`_TEMPLATE`、`INDEX`、`AGENTS`、`README`。
以 `_` 开头的目录一律视为脚手架，**永不挂进入口**。
