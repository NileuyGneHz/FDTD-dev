# FEAT-001 工作区骨架与双宿主接线

> 这是 L3 能力规格。它描述「仓库本身能干什么」，不是某个技能。
> 每条验收都可被脚本或一次人工检查证实（`docs/features/specs/AGENTS.md` 约束 1）。

## 为什么

工作区要同时被 DSH 与 WorkBuddy 接管，而两者发现技能的机制不同：
DSH 靠向上找 `.git` 定项目根，WorkBuddy 只认 `cwd`。没有一套统一的目录骨架与入口生成规则，
就会出现「同一批技能在一个宿主有、另一个没有」且**不报错**的静默失效。

同时，仓库里混着课程素材（`packages/`、`Classes/FDTD/`）、根级 `SKILL.md`、`agent.md`
等历史形态，不归位就无法判断「哪份是当前有效的」。

## 行为

给定一个从工作区根打开的会话，agent 能在 5 分钟内：

1. 按根 `AGENTS.md` §1 的四步定位到一条可执行任务
2. 从 `docs/tasks/active/` 取到唯一在做的动作
3. 从 `skills/INDEX.md` 查到该动作对应的技能与它的 CLI
4. 两个宿主都列出同一批技能（13 个 `fdtd-*`）

## 验收

对应 `iterations/iter-1-foundation/acceptance.md` 的 A–D 四节，逐条：

| 节 | 判据 | 机器检查 |
|---|---|---|
| A 结构 | `docs/`、`cases/`、`projects/`、`library/`、`defects/`、`journal/`、`iterations/` 七目录都在，各有 `AGENTS.md` | `python tools/check_packages.py` |
| A 结构 | `cases/` 下恰好 10 个 `P0N_*`，每个有 `paper/` 与 `model/`，README 四段齐全 | 同上 |
| B 脚本 | 包内无 `.py` | `python tools/check_scripts.py` 退出 0 |
| B 脚本 | 技能脚本满足 `--config / --out / --dry-run / --json` | `python tools/check_skill_contract.py` |
| C 宿主 | `skills-doctor.py` 输出 `ALL GREEN` | 直接跑 |
| C 宿主 | 两处入口是真目录，条数 == 合格技能数（13） | 同上 `[2][3][4]` |
| C 宿主 | `.dsh/skills` 为空 | 同上 `[5]` |
| D 版本控制 | `git init` 完成，`git status` 无 junction 展开的重复文件 | 人工 + `git status` |
| D 版本控制 | `check_git_limits.py` 报 `ERROR=0` | 直接跑 |

**E 节（可接手性）不属本 FEAT**：那是「迭代真正完成」的判据，需人工阅读验证，
不是结构能力。

## 非目标

- **不做**文献综述平台、云端渲染、论文排版、多用户协作（`docs/product-context/README.md` 非目标）
- **不做**技能本身的正确性——那是各技能自己的 FEAT
- **不做**课程素材的完整迁移（只做归位，不做内容整理）
- **不保证**换机器后仍然绿（`path-conventions.md` §2 的绝对路径是本机事实）

## 当前状态（2026-11-11）

| 节 | 状态 | 证据 |
|---|---|---|
| A | ✅ | `check_packages.py` ERROR=0（WARN=34 为 `_p0.log` 缺失，已登记为 C 档遗留） |
| B | ✅ | `check_scripts.py` OK；`check_skill_contract.py` ALL GREEN（OK 129 / WARN 0） |
| C | ✅ | `skills-doctor.py` ALL GREEN，两处入口各 13 条 |
| D | ⚠️ 部分 | `check_git_limits.py` ERROR=0；但工作区有 46 改 / 2 删 / 110 未跟踪，**尚未提交** |
| E | ⏳ 待人工 | 需真人从零开一次会话验证 |

D 节未完成的原因是「改动尚未提交」——不是结构缺陷。
