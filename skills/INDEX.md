# skills/INDEX.md — 技能总表

> 新增技能**只改这一张表**。`stage` 是编排顺序的唯一依据。

| name | stage | scripts | consumes | produces | hands_to | 边界（什么时候别用） |
|---|---|---|---|---|---|---|
| `fdtd-package-workspace` | 0 | `check_packages.py` | 包 ID / 工作区路径 | 包结构、README、索引 | `fdtd-paper-parameter-extraction` | 只做归档治理，不做物理建模；批量迁移用仓库级 `tools/migrate_classes_to_packages.py`（不随技能分发，见 D-006） |
| `fdtd-paper-parameter-extraction` | 1 | `extract_pdf_text.py`、`validate_spec.py` | 论文 PDF | `spec_<id>.json` + `missing[]` | `fdtd-lumerical-unitcell-simulation` | 没有 PDF 或只要看图时不要用 |
| `fdtd-lumerical-fsp-introspection` | 1.5 / X | `inspect_fsp.py` | 既有 `.fsp`（+ 可选 spec） | `manifest.json`、`spectra.json`、`diff.json`、`summary.json` | `fdtd-lumerical-unitcell-simulation` | 没有参考工程、只需从零建模时不要用；只读，不代替建模 |
| `fdtd-holo-phase-retrieval` | 1.8 | `gs_retrieval.py` | 目标强度图 + 采样参数 | `phase_map.npz`、`holo_metrics.json`、`quantized_phase*.csv`、`library_map.json` | `fdtd-lumerical-figure`（相位热图）/ `fdtd-metasurface-assembly` | 只设计相位：不建阵列、不跑仿真；要仿真后提取 Δφ 请走 stage 4，方向相反 |
| `fdtd-metasurface-assembly` | 1.9 | `assemble_spec.py` | `quantized_phase*.csv` + `library_map.json` + geometry.json | fsp-build array spec（`cell_params` 逐格参数） | `fdtd-lumerical-fsp-build`（array 类型建 `.fsp`） | 只查表装配：不开引擎、不反演相位、不标定单元库；缺档报错不硬凑；`--mode crop` 保单元周期，`stride` 会放大成光栅（EXP-64） |
| `fdtd-lumerical-fsp-build` | 2 | `build_fsp.py` | 已校验的 spec | `.fsp`、`<tag>_build.json` | `fdtd-lumerical-unitcell-simulation` | **只建不跑**（无 `_p0.log`、layoutmode=1）；要谱请转 stage 2/3。2D 已支持（EXP-71/75 实测），但 2D 相位提取仍不支持（D-008 收窄后的边界） |
| `fdtd-lumerical-oblique-incidence` | 2.5 | `angle_sweep.py` | spec + 角度/偏振网格 | `angle_sweep_plan.json`、`spec_angles.json`、`angle_matrix.csv`、`angle_metrics.json`、`angle_check.json` | `fdtd-lumerical-unitcell-simulation`（runner 真正开引擎）/ `fdtd-lumerical-figure` | **零引擎**：只做角度计划与结果聚合，不建 `.fsp`、不跑仿真；不改已有 `.fsp` 的角度（slice 2）；3D φ≠0 不做；大角度先测收敛上限（P08 实测上限 40°，60° BFAST 发散，课程工程同样） |
| `fdtd-lumerical-unitcell-simulation` | 2 / 3 | `run_fdtd_sweep.py` | 已校验的 spec | `point_*.csv`、`summary.csv`、`.fsp`、`_p0.log` | `fdtd-lumerical-phase-retrieval`（验收量是相位时）/ 否则 `fdtd-lumerical-figure` | 逐点重建会话，参数扫描型；单点微调转 `session-control` |
| `fdtd-lumerical-phase-retrieval` | 4 | `run_phase_sweep.py` | spec + 偏振角 | `phase.csv`、`dphi_deg` | `fdtd-lumerical-figure` | 只想要功率谱时不要用 |
| `fdtd-lumerical-field-map` | 3.5 | `field_map.py` | 场监视器（`.fsp` 或 npz dump）+ 可选背景组 | `field_metrics.json`、`field_map.npz`、曲线 csv | `fdtd-lumerical-figure`（`--kind field` 直接吃 `field_map.npz`） | 只算不画；不报聚焦效率；x-z 剖面不能算 OAM |
| `fdtd-lumerical-field-propagate` | 3.6 | `propagate_field.py` | 场监视器 npz / `.fsp` + 传播距离 | `propagated.npz`、`propagate_metrics.json` | `fdtd-lumerical-field-map`（下一段重新测） | 只传播；不加透镜相位、不做近远场；`dx>λ/2` 直接 exit 2 |
| `fdtd-lumerical-figure` | 5 | `make_figure.py` | csv / npz / spec.json | `*.png` + meta json | 报告撰写 | 零引擎；不建模型、不跑仿真、不读 `.fsp`；缺列会 exit 2 而不是画空白 |
| `fdtd-lumerical-headless` | X | `run_lsf.py` | 任意 `.lsf` + config | 执行结果、`_p0.log` | —— | 它是横切能力，不单独构成流程 |
| `fdtd-lumerical-session-control` | X | `session_control.py` | 既有 `.fsp` + 白名单 `params` | `iteration_NNN.fsp` / `.json` / `_p0.log` | `fdtd-lumerical-design-loop` | 不建模、不判读、不选参数；Reproduce 模式禁止注入参数 |
| `fdtd-lumerical-design-loop` | X | `design_loop.py` | L1 spec（`targets`/`locked`/`search_space`）+ observation | `next_params.json`、`search_log.csv`、`fom_curve.csv`、`verdict.json` | `fdtd-lumerical-session-control` | 不开会话、不建模；复现模式禁用；不做伴随法/拓扑优化 |

## 光计算轨（lit-* / core-*，2026-11-14 从 L&E_ws 并入）

> 这四个技能服务 `cases/photonic/` 下的文献包，**不进 FDTD 流水线的 stage 编排**，
> 也不进 `agents/fdtd-sim-agent/skills.yaml` 的 `load_order`。它们是横切能力。

| name | stage | scripts | consumes | produces | 边界（什么时候别用） |
|---|---|---|---|---|---|
| `lit-paper-intake` | L1 | `intake.py` | 新论文 PDF | 论文包骨架 + `config/paper.json` | 只建包与登记，不读内容、不抽参数 |
| `lit-quote-verify` | L2 | `verify_quotes.py` | 包内 README §2 引用块 + PDF | `found/missed` 清单 | 只核「能否 grep 到原句」，不判断语义是否支持结论 |
| `lit-claim-audit` | L3 | `audit_claims.py` | `results/claims.csv` + PDF | 核数报告 | 只核数字与出处，不评价方法 |
| `core-skill-authoring` | L0 | `new_skill.py` | 技能名 + 描述 | 技能骨架 + INDEX 登记行 | 只建骨架，不替人写正文 |

## 空位

| stage | 建议技能 | 现状 |
|---|---|---|
| 1.8 | `fdtd-holo-phase-retrieval` | 2026-11-11 落地（EXP-52…59）：目标图 → 连续/N 阶相位 + 重建指标 |
| 1.9 | `fdtd-metasurface-assembly` | 2026-11-11 落地（EXP-60…65）：相位 CSV + 单元库 → per-cell array spec；`fsp-build` 新增 `type: array`（objects 引擎，64×64 实测） |
| 2.5 | `fdtd-lumerical-oblique-incidence` | 2026-11-13 落地（EXP-70…76）：入射角成为 spec 一等公民；P08 0/30/40° BFAST 端到端，60° 发散留 N/A 证据 |
| 3.5+ | 近远场/全息重建 | **仍缺**：`farfield3d`/角谱远场 + 全息效率/SNR 的统一口径（技能C） |

2026-11-10：stage 3.5 已由 `fdtd-lumerical-field-map` 补上（EXP-50），收编了 P05
`analyze_p05.py` 与 P04 `field_map_and_decay.py` 两份原型；它们不再演进。

## 约定

- 名字是公开 API，改名 = 破坏性变更。
- 每个技能一条目，`scripts` 列写实际文件名（不带路径）。
- `_TEMPLATE/` 不登记。
- **stage X 的调参闭环**：`fdtd-lumerical-design-loop`（决策，不碰 lumapi）与
  `fdtd-lumerical-session-control`（执行，复用 `fdtd-package-workspace/scripts/lumapi_common.py`）
  互为 `hands_to`，通过 `next_params.json` ↔ `iteration_NNN.json` 的 JSON 契约构成循环。
  二者都按 L1 §③ 的双模式门控（Reproduce 禁止调参）、只在 `search_space` 内活动，
  属按需横切能力，不进 `agents/fdtd-sim-agent/skills.yaml` 的 `load_order`。
- 从零建模仍走 stage 2 的 `fdtd-lumerical-unitcell-simulation`；X 层只作用于已建好的 `.fsp`，
  避免「同一逻辑两份实现」。
- **stage 4 是条件环节**：只有验收量是相位（`dphi` / `phase` / 偏振态）时才插在 2/3 与 5 之间；
  纯功率复现直接 `unitcell → figure`。漏掉它的后果不是「少一步」，而是波片的两个偏振透射率
  都 ≈ 1、指标反而更好看（D-012）。
- **stage 列的语义是机检的**：含数字 = 流水线环节，必须出现在 `agents/*/skills.yaml`
  （`[K17]`）；`X` = 横切/按需能力，可以只登记本表（`headless` 就是这类）。
