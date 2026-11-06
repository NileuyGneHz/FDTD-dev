# AGENTS.md — FDTD_WS 运行契约

> 本文件是**索引，不是手册**。规则细节在各目录自己的 `AGENTS.md` 里，按需展开。
> 目标：任何 Agent 进入本工作区，5 分钟能定位到该读的那一篇。

## 0. 一句话

面向超表面科研人员的 Lumerical FDTD 工作区：用 DSH 与 WorkBuddy 两个宿主，
把「读论文 → 提参数 → 建模 → 跑谱 → 判偏差 → 出图」固化成可复现、可审计的流水线。

## 1. 起手必读（按顺序，别跳）

1. `docs/product-context/README.md` —— 为谁做、解决什么、**不做什么**
2. `docs/constitution/workspace-layout.md` —— 目录契约与双宿主接线
3. `docs/tasks/active/` —— 现在在做什么（**AI 优先读这里，别翻 archive**）
4. `iterations/iter-1-foundation/runtime-contract.md` —— 模型、步数、工具白名单

## 2. 三条铁律

1. **会话必须在 `FDTD_WS` 根打开**。DSH 靠向上找 `.git` 定项目根，WorkBuddy 只认 `cwd`；
   从 `projects/R01_x` 打开 = 项目技能全部消失，且不报错。
2. **包内不放 `.py`**。能力脚本进 `skills/`，模型脚本（`.lsf`）留 `model/`，一次性脚本进 `_scratch/`。
3. **入口是生成物**。`.agents/skills`、`.workbuddy/skills` 由 `tools/skills-wire.py` 生成，
   真目录 + junction，永不手改。

## 3. 目录地图

| 目录 | 职责 | 该读哪份约束 |
|---|---|---|
| `docs/` | 流程与决策（L1–L5） | `docs/AGENTS.md` |
| `docs/product-context/` | 为什么存在、MVP、非目标 | 目录内 `README.md` |
| `docs/constitution/` | 路径、命名、归档、宿主接入 | `docs/constitution/AGENTS.md` |
| `docs/features/specs/` | FEAT-xxx 验收标准 | `docs/features/specs/AGENTS.md` |
| `docs/tasks/{active,recent,archive}/` | 动作拆分 | `docs/tasks/AGENTS.md` |
| `cases/` | **只读**：10 个已复现论文（论文 + `.fsp` 同包） | `cases/AGENTS.md` |
| `projects/` | **可写**：在研课题，与 cases 同构 | `projects/AGENTS.md` |
| `library/` | 跨课题复用：材料、模块、schema、图样式 | `library/AGENTS.md` |
| `skills/` | 唯一的可执行能力库 | `skills/AGENTS.md` |
| `agents/` | 角色包（四件套 + evals + memory） | `agents/AGENTS.md` |
| `tools/` | 仓库级自检（不是技能） | `tools/AGENTS.md` |
| `defects/` | D-xxx：根因 / 修复 / 验证 | `defects/AGENTS.md` |
| `journal/` | 会话交接与日记 | `journal/AGENTS.md` |
| `iterations/` | 迭代计划、验收、运行契约 | `iterations/AGENTS.md` |
| `_scratch/` | 一次性脚本、中间 `.fsp`、日志 | 不进库，无约束 |
| `_archive/` | 课程素材、历史日志 | 不进库，只读 |

## 4. 一次会话怎么开（篝火模式）

```
起火  读本文 §1 → 从 docs/tasks/active/ 取一条 → 定位单元 ID（P0N / R0N）
添柴  只动这一个单元；新坑立刻记 defects/D-xxx.md
灭火  写交接：做了什么、卡在哪、下次从哪接 → journal/<date>.md
攒堆  任务移 docs/tasks/recent/；迭代进度记一行 → iterations/iter-1-foundation/RELEASE.md
结营  验收 → acceptance.md + runtime-contract.md 更新
```

**一次会话只烧一个单元**。跨单元修改说明上下文已溢出，停下来写 journal。

## 5. 硬约束（违反即回滚）

- **路径纯 ASCII**：目录名、文件名都算。GPU 引擎对非 ASCII 路径报 Windows 1113，
  弹窗只显示乱码，**以 `_p0.log` 为准**。
- **`.fsp` 是二进制**：无法 diff、无法合并。谁改谁立刻提交；同一天不要两人并行改同一工程。
- **单文件 > 100 MB 不入库**：GitHub 直接拒收，不是警告。
- **许可席位**：每个 `lumapi.FDTD()` 占 1 个席位，`close()` 必须落在 `finally`。
- **产出只落单元内**：`results/`、`config/`；不写 `stuff/`、不写包外、不联网。

## 6. 怎么算做完

- 该单元 `README.md` 的 §0 验收条件全部满足
- `python tools/check_scripts.py` 通过（包内无 `.py`）
- `python tools/check_packages.py` 通过（论文 ↔ `.fsp` 一一对应）
- 若改了技能：`python tools/skills-doctor.py` 报 `ALL GREEN`
- `journal/<date>.md` 写了交接

## 7. 分工

- **PM（人）**：`docs/features/specs/`、`docs/product-context/`、验收标准
- **Engineer（人）**：`library/`、`tools/`、`skills/*/scripts/`
- **AI Agent**：按 `skills/` 与 `agents/` 的编排执行，产出落 `cases/` 或 `projects/`
- **人做最终裁决**：数值是否可信、图是否可发表——AI 只给证据，不下结论

## 8. 索引

- 目录契约全文：`docs/constitution/workspace-layout.md`
- 脚本归属与 CLI：`docs/constitution/script-contract.md`
- 命名表：`docs/constitution/naming.md`
- 双宿主风险：`docs/constitution/host-integration.md`
- 技能总表：`skills/INDEX.md` · 角色总表：`agents/INDEX.md`
