# library/ — 跨课题复用层

## 职责

存放**被两个以上单元复用的东西**。它本身不是技能，只是资产仓库；技能脚本从这里 import。

## 四个子目录

| 目录 | 放什么 | 谁写 |
|---|---|---|
| `materials/` | 材料模型：名称 + 参数 + cite（Drude / Lorentz / 采样 nk） | 研究时沉淀 |
| `py/` | **纯模块**（无 argparse CLI 入口），被技能脚本 import | Engineer |
| `schemas/` | spec / sweep 的 JSON Schema 与校验器 | Engineer |
| `figs/` | 图样式、配色、导出预设 | 谁出图谁写 |

## 约束

1. **`py/` 里不许有 argparse CLI 入口**（2026-11-11 订正）。

   > 旧版写的是「不许有 `__main__`」，过于严格：`lumapi_common.py` 带一个
   > `if __name__ == "__main__":` 自测块（真启一个会话再关掉，验证环境），
   > 这条自测是**必需的**——没有它，「环境坏了」和「代码坏了」分不开。
   > 判据改为：**不许用 argparse 定义命令行参数**。判「能直接跑的东西」看的是
   > 有没有 CLI 契约，不是有没有 `__main__`。

   自测块的额外约束：**不得写入仓库内文件**（只许读、只许打印、只许开关会话）。
   能对外提供命令行的东西必须归技能——这是 `script-contract.md` 的边界。

2. **只增不改**。要改一个被引用的模块，先 `grep` 全部引用点，同轮改完；改不动就新增版本。
3. **材料必须带 cite**。没有出处的参数一律不许进 `materials/`——那正是"复现对不上"的头号原因。
4. **不放课题专属的东西**。只被一个单元用的，留在那个单元的 `model/` 或 `config/`。
5. **只有一个家**（2026-11-11 新增）。`library/py/` 是共享模块的**唯一实现位置**；
   技能目录下若需要同名模块，只能放**转发壳**（`runpy` 注入命名空间，找不到就 ImportError），
   绝不复制实现。历史教训：D-005、D-006、EXP-02 三次「两份副本随改名腐烂」。

## 与技能的关系

```
skills/<name>/scripts/*.py   ── import ──>   library/py/*.py
```

技能脚本是入口，`library/py` 是零件。零件不单独对外提供命令行。

## 当前内容（2026-11-11 从 `_shared/` 迁入）

| 文件 | 作用 | 谁在用 |
|---|---|---|
| `py/fsp_build.py` | 唯一 builder：材料 / 几何 / 阵列 / 求解区 / 源 / 监视器 | `build_fsp.py`、`run_fdtd_sweep.py`、`assemble_spec.py` |
| `py/lumapi_common.py` | 会话生命周期 + 三判据校验 + ASCII 闸门 + 折射率查询 | `field_map.py`、`session_control.py`、`build_fsp.py`、`run_fdtd_sweep.py`、`check_reproduction.py` |
| `py/README.md` | 迁移说明与函数表 | 人 |

`materials/` / `schemas/` / `figs/` 仍空——它们等真实复用需求出现再填，
**不提前抽象**（`library/` 的存在意义是「已被两处用到」，不是「将来可能用到」）。
