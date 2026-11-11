# constitution/ — L2 规范层

## 职责

定义"这个仓库怎么组织、怎么命名、怎么交付"。这一层的文档是**判据**，不是建议：
`tools/` 下的检查脚本按它们实现，`AGENTS.md` 引用它们。

## 本目录的文件

| 文件 | 回答什么问题 | 谁检查 |
|---|---|---|
| `workspace-layout.md` | 目录长什么样、每个目录放什么 | 人 |
| `path-conventions.md` | 路径怎么写、什么绝对不能出现；`results/` 两级落位与 `index.json` | `tools/check_packages.py`、`tools/check_results_layout.py` |
| `naming.md` | 包 / 技能 / 角色 / 缺陷 / 任务怎么编号 | `tools/skills-doctor.py` |
| `script-contract.md` | 脚本放哪、怎么调、CLI 长什么样 | `tools/check_scripts.py` |
| `skill-change-contract.md` | 技能怎么加、怎么改、什么禁止、怎么回归 | `tools/check_skill_contract.py` |
| `reproduction-contract.md` | 复现怎么跑、差异怎么判、经验怎么变成训练语料；§7 复现卡、§7.1 验收表 | `tools/check_reproduction.py`、`tools/check_acceptance.py` |
| `archive-contract.md` | 一个归档单元必须有什么 | `tools/check_packages.py` |
| `host-integration.md` | DSH / WorkBuddy 怎么发现技能 | `tools/skills-doctor.py` |
| `path-conventions.md` §5 / `field-manual.md` §6.3 | GPU 引擎怎么切、什么工程不能上 GPU | `tools/gpu_mode.py`、`tools/gpu_guard.py`、`tools/probe_gpu_eligibility.py` |

## 约束

1. **一条规范一条可执行检查**。写进这里的规则，必须有脚本能判真假；判不了的写进 `AGENTS.md`，
   明确标注"靠自觉"。
2. **改规范必须同轮改检查脚本**，否则规范会退回成口号。
3. **不写教程**。怎么用 lumapi 是 `field-manual.md` 与技能的事，本目录只管"边界"。
4. 本目录的文档改动会影响其他所有模块，改完要在 `journal/<date>.md` 记一笔。
5. **加门禁必须同轮补契约**（2026-11-10 的教训）。只往 `tools/` 加脚本、不写进本表第 1 列的
   对应契约，结果是 53 条 FAIL 无处可查——`check_acceptance.py` 要求
   `config/acceptance.json`，而当时任何规范都没定义这个文件，4 个包只能靠猜。
   判据：新脚本必须在上面这张表里出现，且它检查的每个字段都能在对应契约里找到一行。
