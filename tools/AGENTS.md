# tools/ — 仓库级自检

## 职责

把 `docs/constitution/` 里的规范变成**可判真假的命令**。工具本身不是技能，也不被技能调用。

## 清单

| 脚本 | 检查什么 | 何时跑 |
|---|---|---|
| `check_packages.py` | 归档单元结构、论文↔`.fsp` 一一对应、README 四段 | 每次交付前 |
| `check_scripts.py` | 包内出现 `.py` → FAIL，并给出该迁往的技能 | 每次提交前 |
| `check_git_limits.py` | 单文件 > 100 MB、总体积 | `git push` 前 |
| `skills-wire.py` | 重建 `.agents/skills` 与 `.workbuddy/skills` 的 junction | 增删技能后 |
| `skills-doctor.py` | 六项宿主接入检查 | 增删技能后 / 换机器后 |

## 约束

1. **一个规范一条检查**。`constitution` 里判不了的规则，不要在这里假装能查。
2. **退出码即结论**：`0` 通过，非 `0` 失败，输出必须指出"改哪个文件"。
3. **幂等**。重复跑不改变结果；`--apply` 类操作必须先 dry-run。
4. **不写业务逻辑**。这里只做检查与布线，不碰仿真。
5. 新增检查脚本必须在 `docs/constitution/AGENTS.md` 的表格里登记。
