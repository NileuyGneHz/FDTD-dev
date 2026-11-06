# library/ — 跨课题复用层

## 职责

存放**被两个以上单元复用的东西**。它本身不是技能，只是资产仓库；技能脚本从这里 import。

## 四个子目录

| 目录 | 放什么 | 谁写 |
|---|---|---|
| `materials/` | 材料模型：名称 + 参数 + cite（Drude / Lorentz / 采样 nk） | 研究时沉淀 |
| `py/` | **纯函数模块**（无 `__main__`），被技能脚本 import | Engineer |
| `schemas/` | spec / sweep 的 JSON Schema 与校验器 | Engineer |
| `figs/` | 图样式、配色、导出预设 | 谁出图谁写 |

## 约束

1. **`py/` 里不许有 `__main__`**。能直接跑的东西必须归技能——这是 `script-contract.md` 的边界。
2. **只增不改**。要改一个被引用的模块，先 `grep` 全部引用点，同轮改完；改不动就新增版本。
3. **材料必须带 cite**。没有出处的参数一律不许进 `materials/`——那正是"复现对不上"的头号原因。
4. **不放课题专属的东西**。只被一个单元用的，留在那个单元的 `model/` 或 `config/`。

## 与技能的关系

```
skills/<name>/scripts/*.py   ── import ──>   library/py/*.py
```

技能脚本是入口，`library/py` 是零件。零件不单独对外提供命令行。
