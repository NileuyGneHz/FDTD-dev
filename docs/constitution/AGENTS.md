# constitution/ — L2 规范层

## 职责

定义"这个仓库怎么组织、怎么命名、怎么交付"。这一层的文档是**判据**，不是建议：
`tools/` 下的检查脚本按它们实现，`AGENTS.md` 引用它们。

## 本目录的文件

| 文件 | 回答什么问题 | 谁检查 |
|---|---|---|
| `workspace-layout.md` | 目录长什么样、每个目录放什么 | 人 |
| `path-conventions.md` | 路径怎么写、什么绝对不能出现 | `tools/check_packages.py` |
| `naming.md` | 包 / 技能 / 角色 / 缺陷 / 任务怎么编号 | `tools/skills-doctor.py` |
| `script-contract.md` | 脚本放哪、怎么调、CLI 长什么样 | `tools/check_scripts.py` |
| `archive-contract.md` | 一个归档单元必须有什么 | `tools/check_packages.py` |
| `host-integration.md` | DSH / WorkBuddy 怎么发现技能 | `tools/skills-doctor.py` |

## 约束

1. **一条规范一条可执行检查**。写进这里的规则，必须有脚本能判真假；判不了的写进 `AGENTS.md`，
   明确标注"靠自觉"。
2. **改规范必须同轮改检查脚本**，否则规范会退回成口号。
3. **不写教程**。怎么用 lumapi 是 `field-manual.md` 与技能的事，本目录只管"边界"。
4. 本目录的文档改动会影响其他所有模块，改完要在 `journal/<date>.md` 记一笔。
