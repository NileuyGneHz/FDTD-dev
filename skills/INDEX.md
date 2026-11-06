# skills/INDEX.md — 技能总表

> 新增技能**只改这一张表**。`stage` 是编排顺序的唯一依据。

| name | stage | scripts | consumes | produces | hands_to | 边界（什么时候别用） |
|---|---|---|---|---|---|---|
| `fdtd-package-workspace` | 0 | `check_packages.py`、`migrate_classes_to_packages.py` | 包 ID / 工作区路径 | 包结构、README、索引 | `fdtd-paper-parameter-extraction` | 只做归档治理，不做物理建模 |
| `fdtd-paper-parameter-extraction` | 1 | `extract_pdf_text.py`、`validate_spec.py` | 论文 PDF | `spec_<id>.json` + `missing[]` | `fdtd-lumerical-unitcell-simulation` | 没有 PDF 或只要看图时不要用 |
| `fdtd-lumerical-unitcell-simulation` | 2 / 3 | `run_fdtd_sweep.py` | 已校验的 spec | `point_*.csv`、`summary.csv`、`.fsp`、`_p0.log` | 结果分析技能 | 全器件（透镜/全息）不适用 |
| `fdtd-lumerical-phase-retrieval` | 4 | `run_phase_sweep.py` | spec + 偏振角 | `phase.csv`、`dphi_deg` | 出图技能 | 只想要功率谱时不要用 |
| `fdtd-lumerical-headless` | X | `run_lsf.py` | 任意 `.lsf` + config | 执行结果、`_p0.log` | —— | 它是横切能力，不单独构成流程 |

## 空位

| stage | 建议技能 | 现状 |
|---|---|---|
| 5 交付出图 | `fdtd-result-figure` | 图脚本散在 P02/P04/P05/P06 各写一遍，是下一个要收编的对象 |

## 约定

- 名字是公开 API，改名 = 破坏性变更。
- 每个技能一条目，`scripts` 列写实际文件名（不带路径）。
- `_TEMPLATE/` 不登记。
