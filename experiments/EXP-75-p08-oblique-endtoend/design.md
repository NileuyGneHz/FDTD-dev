# EXP-75 — P08 端到端角度扫描（真实 FDTD）

**对应计划**：`docs/plans/PLAN-2026-11-13-oblique-incidence.md` §5 步骤 6、§6 正对照 3
**关联偏差**：该计划 §11 的 D-01 / D-02 / D-03
**结论**：`verdict=pass`，但**角度网格由 0/30/60° 改为 0/30/40°**，60° 与 45–55° 记为 N/A（不是失败隐藏）。

## 1. 目标

用真实 Lumerical v251 引擎跑 P08 宽带吸收器的不同入射角，产出可复核的
`A(λ,θ)` 矩阵、每点收敛证据、spec↔fsp 一致性读回，并与课程 `wide_angle.fsp`
及论文 Fig.5 的「角度不敏感」趋势对照。

## 2. 最终配置

| 项 | 值 |
|---|---|
| 引擎 | Ansys Lumerical 2025 R1 (v251)，**CPU**（2D+BFAST 不支持 GPU） |
| 角度网格 | **0 / 30 / 40°**，`pol=90`（TM-like） |
| 模式 | `bfast`（`source.plane wave type=BFAST`），倾斜轴 x 用 Bloch BC |
| 其他 | `pml layers=8`、`bfast alpha=1`、`dt stability factor=0.99`（课程同款） |
| 波段 | 400–800 nm，50 点 |
| 材料 | 椭偏实测 Ag / a-Si n-k；`Sampled data` 按 ε=(n+ik)²（D-013） |
| 结构 | 80 nm Ag / 24 nm a-Si / 30 nm Ag / 12 nm a-Si（玻璃衬底省略，见 §5 边界） |
| 特殊契约 | `simulation.opaque_ground_plane=true`（D-01） |

## 3. 执行中暴露的三件事（都写进了计划 §11）

### D-01 不透明背板的 T 噪声零点
首轮报 `ValueError: T 越界 [-0.003, -0.000]`。证据链：

- 本次 θ=0：`T∈[-0.00305,-0.00007]`，R∈[0.0512,0.9633]，日志收敛 10102 步；
- **课程成品工程** `wd.fsp` / `wd_BFASK.fsp`：`T∈[-0.00420,-0.00009]` / `[-0.00365,-0.00007]`，**同样为负**；
- A/B 对照：T 监视器从 −0.18 µm 移到 −0.60 µm → `T_min` −0.00305→−0.00297；`pml layers` 8→4 → 仍 −0.003。
  → 排除「监视器压进 PML」（P07 是 T=−0.80 量级）。

**处置**：不是放宽 `PHYS_TOL`，而是加**显式物理契约** `opaque_ground_plane=true`：
T 按物理取 0、`A=1−R`；原始值写进 `T_raw` 列并受 `OPAQUE_T_NOISE_MAX=5e-3` 硬闸。
离线负对照 7+2 条（`EXP-73/amend_opaque_t.py`）证明旧 spec 仍红、坏监视器仍红、R/A 门禁不变。

### D-02 GPU
2D+BFAST 报 `GPU simulation only supports 3D` / `does not support BFAST sources`。
→ 全程 `tools/gpu_guard.py --run` 切 CPU（try/finally 自动还原），sweep 网格内嵌进 spec 避免 cmd.exe 引号问题。

### D-03 60° BFAST 发散（课程原工程同样）
0°/30° 收敛，**60° 报 `fields are diverging`**（Auto Shutoff 116454，R 最大 1.028）。
11 组补救对照全部无效（`controls_60.json` / `controls_60_round2.json`）：
dt 0.95/0.90/0.50/0.25、pml 24/32、`bfast alpha`=4、去 mesh override、课程 `simulation time` 5e−14。
其中 dt=0.5/0.25 压住发散却得到 R=1.019/1.018。
**把课程 `wide_angle.fsp` 直接改到 60° 也发散**（shutoff 104477）→ 这是模型/引擎限制，不是 spec 错误。

收敛上限扫描（`angle_ceiling.json`）：35°/40° 干净（R≤0.989）；
45/50/55° 虽无 `diverging` 但 R=1.038/1.073/1.077，**随角度单调变坏**，属源归一化失守，拒绝。

**正确性副产物**：v251 发散后仍打印 `Simulation completed successfully`，且 dt=0.95 时 R 仍在 [0,1]
→ 只靠 `check_physical_range` 会放发散结果过闸。已加 `check_engine_log()` 读 `_p0.log` 的
`diverging` 字面量（离线负对照 H/I：收敛日志过、发散日志红）。

## 4. 结果（全部实机）

| θ | 迭代 | Auto Shutoff | diverging | peak A | peak λ (µm) | mean A (400–650) | max\|A(θ)−A(0)\| |
|---|---|---|---|---|---|---|---|
| 0° | 10102 | 9.37e−6 | 否 | 0.9488 | 0.498 | 0.7766 | — |
| 30° | 24549 | 9.95e−6 | 否 | 0.9230 | 0.580 | 0.7537 | 0.0516 |
| 40° | 29580 | 9.66e−6 | 否 | 0.9427 | 0.580 | 0.7334 | 0.0930 |

- `angle_check.json`：**`ok=true`**；3/3 点完整、A∈[0.0111,0.9488]、无重复曲线、3 点收敛全过。
- `angle_matrix.csv`：150 行（3 角 × 50 波长），列为 `theta_deg,pol_deg,lam_um,R,T,A`。
- 每点 `T_raw_abs_max` = 0.003051 / 0.002431 / 0.001984，全部低于 5e−3 噪声上界（D-01 留证）。
- **spec↔fsp 读回**（`fsp_angle_readback.json`）：三份 `.fsp` 的 `source.angle theta` 分别为
  0/30/40，`plane wave type=BFAST`，x BC=Bloch，pml=8，alpha=1；
  `getsourceangle(source, c/λ)` 在 400/600/800 nm 分别为
  **0/0/0、30/30/30、40/40/40** → BFAST 注入角频率无关，漂移 0°（对照 Bloch 会漂到 19–39°）。
- 角度趋势：0→40° 的 `mean_A_400_650` 从 0.7766 降到 0.7334（−5.6% 相对），
  `peak_A` 始终 ≥0.923，最大逐点偏差 0.093 → 在**已验证的 0–40° 范围内**与论文 Fig.5
  「宽带吸收随角度不显著退化」一致。**不能外推到 60°**。

## 5. 负对照与 N/A（不假装覆盖）

| 项 | 状态 | 证据 |
|---|---|---|
| 旧 spec 无 `opaque_ground_plane` + T=−0.003 | 必红 | `amend_opaque_t.py` A |
| `T_raw`=−0.50 / +0.20 | 必红 | 同脚本 C/D |
| `opaque_ground_plane` + `mode=transmission` | 必红（exit 1） | `EXP-73/opaque_transmission_bad.json` |
| 发散日志 | 必红 | 同脚本 I |
| 三个角度曲线完全相同 | 必红（N5） | EXP-74 已验；本轮无重复 |
| 60° BFAST | **N/A** | diverging；课程原工程复现（`controls_60_round2.json`） |
| 45/50/55° | **N/A** | R>1 非物理（`angle_ceiling.json`） |
| TE/TM 双偏振差 | **N/A** | 首版只跑 pol=90（计划批准范围） |
| 论文 Fig.5 的 60° 结论 | **未验证** | 见 D-03；需要 slice 2 的 `bloch_single` 单频扫描 |
| 玻璃衬底 | **省略** | 80 nm Ag 不透明，A=1−R 不受影响；绝对 A(λ) 只做趋势对照 |

## 6. 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
S="_scratch/regress/2026-11-13/oblique"
O="$S/angle_sweep"

# ① 计划（零引擎）
"$PY" skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py plan \
  --spec "$S/spec_p08.json" --angles 0,30,40 --pol 90 --mode bfast --out "$O" --json

# ② 真实仿真：2D+BFAST 必须走 CPU（gpu_guard 自动还原 GPU-mode）
"$PY" tools/gpu_guard.py --fsp "$S/EXP-71/p08/p08_30.fsp" --run \
  "$PY skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
   --spec $O/spec_angles.json --out $O/run --json"

# ③ 聚合 + 检查（ok 必须为 true）
"$PY" skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py collect \
  --plan "$O/angle_sweep_plan.json" --run-dir "$O/run" \
  --out "$O/angle_matrix.csv" --json

# ④ 负对照 / 读回 / 上限
"$PY" "$S/EXP-73/amend_opaque_t.py"
"$PY" "$S/verify_fsp_angles.py"
```

## 7. 产物

`_scratch/regress/2026-11-13/oblique/angle_sweep/`：
`angle_sweep_plan.json`、`spec_angles.json`、`run/point_00..02_*.{csv,fsp,_p0.log}`、
`run/summary.csv`、`run/sweep_result.json`、`angle_matrix.csv`、`angle_metrics.json`、
`angle_check.json`、`fsp_angle_readback.json`、`angle_ceiling.json`、
`controls_60.json`、`controls_60_round2.json`。

对照脚本：`_scratch/regress/2026-11-13/oblique/{probe_rt,probe_course,probe_course_results,
probe_bfast_settings,verify_fsp_angles,run_60_controls,run_60_controls2,run_angle_ceiling}.py`。
