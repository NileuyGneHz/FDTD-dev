---
name: fdtd-lumerical-oblique-incidence
description: >
  把入射角做成 model spec 的一等公民，并生成/聚合不同角度的 FDTD 扫描：零引擎产出
  angle_sweep_plan.json 与 spec_angles.json，交给已有的 run_fdtd_sweep.py --sweep-json 驱动，
  再聚合 A(lambda,theta)、TE/TM 差、收敛与 A 越界检查。覆盖正入射 Periodic、单波长斜入射
  Bloch/periodic、宽带斜入射 BFAST 三种口径。触发词：斜入射、入射角、角度扫描、oblique、
  BFAST、Bloch 边界、angle theta、A(λ,θ)、宽角度吸收器。
agent_created: true
---

# fdtd-lumerical-oblique-incidence（stage 2.5）

## 1. 什么时候用它

| 想做的事 | 用这个技能 |
|---|---|
| 要跑 0/30/60° 的宽带吸收谱、出 A(λ,θ) | ✅ `plan` → runner → `collect` |
| 想知道某个 spec 该用 Bloch 还是 BFAST | ✅ `plan --dry-run` 秒级给决策 |
| 只建一个斜入射 `.fsp`、不扫描 | 直接给 spec 加 `incidence` + `source.angle_theta_deg`，转 `fdtd-lumerical-fsp-build` |
| 想改**已有** `.fsp` 的角度 | slice 2（`fdtd-lumerical-session-control` 白名单），本期不做 |
| 要画 A(λ,θ) 热图 | 本期只出 CSV + json；`figure --kind angle_map` 属 slice 2 |

**边界**：本技能**零引擎**——不开 lumapi 会话、不建 `.fsp`、不跑仿真。
建模是 fsp-build 的事，跑仿真是 unitcell-simulation 的事，本技能只做「角度计划 + 结果聚合」。

## 2. 核心工作流

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
S="skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py"

# ① 脱机自检（50 条解析真值，0.2 s，不需要引擎）
"$PY" "$S" --self-test

# ② 计划（零引擎）：先看 mode / 倾斜轴 / 机时倍率，不写文件
"$PY" "$S" plan --spec <spec.json> --angles 0,30,60 --pol 90 --mode bfast \
  --out <dir> --dry-run --json

# ③ 落计划 + 把角度做成 parameters.theta 的 spec
"$PY" "$S" plan --spec <spec.json> --angles 0,30,60 --pol 90 --mode bfast \
  --out <dir> --json

# ④ 交给已有 runner（本技能不自己开会话）
"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec <dir>/spec_angles.json \
  --sweep-json '{"theta":[0,30,60],"pol":[90]}' --out <dir>/run --json

# ⑤ 聚合：A(λ,θ) / 指标 / 收敛 / 越界与重复曲线检查
"$PY" "$S" collect --plan <dir>/angle_sweep_plan.json --run-dir <dir>/run \
  --out <dir>/angle_matrix.csv --json
```

关键取巧点：`run_fdtd_sweep.py` 的 `--sweep-json` 逐点覆盖 `spec["parameters"]`，
而 builder 的所有数值都走 `ev()`。**把角度写成 `parameters.theta` 就免费拿到角度扫描**，
不需要第二份 runner。本技能只生成那个 spec 和扫描参数。

## 3. CRITICAL（违反即停止）

1. **角度只写在 `source.angle theta`**。v251 本机实测：`FDTD.angle theta` 是 inactive，
   `setnamed` 会抛错；BFAST 下写 source 后 FDTD 区域会**自动同步**（30→30）。
   扫描扫 source，永远不碰 FDTD 求解区的角度。
2. **宽带斜入射必须用 BFAST**。`Bloch/periodic` 的边界相位差 `2πP·sinθ/λ` 随 λ 变：
   600 nm 设 30°，实测 750 nm → 38.65°、400 nm → 19.46°。课程反例是 Bloch + 400–800 nm
   在 700 nm 处算出 **A<0**。`bloch_single` + 宽带会被直接拒绝，不静默放宽。
3. **2D 下 `angle phi` 连 0 都不可写**（v251 inactive）。`angle_phi_deg ≠ 0` 一律拒绝；
   3D φ≠0 属 slice 2。本版生成的 spec 从不带这个字段。
4. **角度符号不自动取反**。P04 实测 `paper θ_i = −(Lumerical angle theta)`，课程扫 0→+60°。
   每份 plan / metrics 都带 `sign_convention` 字段，由人决定对照时怎么换算。
5. **不写第二份 builder / runner**。物理决策全部调用 `library/py/fsp_build.py` 的
   `resolve_incidence()`；本技能只有 `scripts/angle_sweep.py` 一个入口。
6. **收敛才算数**。每个点必须读 `_p0.log` 的最后一个 `Auto Shutoff` 与 `Completed`；
   出现 `diverging` 或 A 越界一律不算结果（`collect` 会 exit 1）。
   ⚠️ 引擎在 `ERROR: ... fields are diverging` 之后**仍会打印** `Simulation completed successfully`，
   所以只看 `completed` 会把发散当成收敛；必须同时查 `diverging` 字面量。
7. **不透明背板 ≠ 监视器坏了**。80 nm Ag 这类不透明地平面下 T 物理恒为 0，但 DFT 功率
   监视器会给出约 −0.003 的**噪声零点**（课程 `wd.fsp` 是 −0.0042，`wd_BFASK.fsp` 是 −0.0037）。
   若器件确有不透明背板，spec 必须显式写 `simulation.opaque_ground_plane: true`：runner 把 T
   按 0 代入、原始值留在 `T_raw` 列并受 `OPAQUE_T_NOISE_MAX=5e-3` 硬闸约束。
   **不要**直接放宽 `check_physical_range` 的容差；透射式器件禁止声明该字段。
8. **大角度 BFAST 有硬上限，别硬刚**。P08（a-Si/Ag 色散层）在 v251 实测：
   0/30/40° 收敛且 `R≤0.989`；45/50/55° 收敛但 `R=1.038/1.073/1.077`（非物理且随角度单调涨）；
   60° `fields are diverging`。**把课程 `wide_angle.fsp` 直接改到 60° 也一样发散**，
   说明是模型/引擎限制，不是 spec 错误。`dt stability factor` 0.95/0.5/0.25、`pml layers`
   24/32、`bfast alpha`=4、去 mesh override、缩短 simulation time **都没能同时满足
   「不发散 + R≤1」**。做法是先用小角度网格测出收敛上限再定 grid，把大角度留成 N/A + 证据。
   `_p0.log` 的 `diverging` 字面量是判据，`Simulation completed successfully` 不是。

## 4. spec 接口（角度是参数，不是硬编码）

```json
{
  "parameters": {"theta": 30, "pol": 90},
  "simulation": {
    "dimension": "2D",
    "propagation_axis": "y",
    "bc": {"x": "Bloch", "y": "PML", "z": "PML"},
    "source": {
      "type": "plane",
      "angle_theta_deg": "theta",
      "polarization_deg": "pol",
      "wavelength_range": [400e-9, 800e-9]
    },
    "incidence": {"mode": "bfast", "pml_layers": 8, "bfast": {"alpha": 1.0}}
  }
}
```

| `incidence.mode` | 平面波类型 | 倾斜面 BC | 频率口径 |
|---|---|---|---|
| `normal` | 不改现状 | 不改现状 | 任意 |
| `bloch_single` | `Bloch/periodic` | `Bloch` | **单频点**，宽带即拒绝 |
| `bfast` | `BFAST` | `Bloch`（引擎会覆盖） | 宽带 OK |
| `auto` | 单频→Bloch，宽带→BFAST，θ=0→Periodic | 同上 | 同上 |

不含 `incidence` 且不含 `angle_theta_deg` 的旧 spec：builder **一个属性都不多写**
（EXP-71 用调用序列 A/B 验证：P01 3D 67 calls、P08 2D 59 calls，0 diffs）。

## 5. 输出契约

| 文件 | 由谁产出 | 内容 |
|---|---|---|
| `angle_sweep_plan.json` | `plan` | mode、倾斜轴、每角度的 source 属性 / BC / 机时倍率、driver 命令、角度网格 SHA、check_coverage |
| `spec_angles.json` | `plan` | 注入 `parameters.theta/pol` 与 `incidence` 的 spec，供 runner 消费 |
| `point_XX_*.csv` + `_p0.log` | runner | 每角度的 R/T/A 谱与收敛日志；声明 `opaque_ground_plane` 时多一列 `T_raw`（原始监视器值，留证） |
| `angle_matrix.csv` | `collect` | `theta_deg,pol_deg,lam_um,R,T,A` |
| `angle_metrics.json` | `collect` | 每角度 `mean_A_400_650`、`peak_A`、`delta_lambda_A90`、TE/TM 最大差、各点收敛 |
| `angle_check.json` | `collect` | 点数完整、A 越界、重复曲线、BFAST 漂移对照、`ok` |

`check_coverage` 会**明确列出没查什么**（`angle phi`、`FDTD.angle theta` 是引擎不可写/派生值），
不假装全覆盖。

## 6. 已知边界（不假装支持）

- 只支持 2D θ-only；3D 仅 `propagation_axis=z` 且 φ=0。
- `|θ| > 60°` 给 WARN（课程经验上限、7.5× 机时）；`>= 85°` 直接拒绝。
- 首版不画 `figure --kind angle_map`，不出 TE/TM 双偏振之外的指标。
- `dt multiplier` / `pulse length` 在本机 v251 上属性名找不到，**不写、不猜**。
- 若 `collect` 找不到 `point_*.csv` 的角度 tag（文件名形如
  `point_00_theta_30_pol_90.csv`）或 `sweep_result.json`，会明确报错而不是产出空表。

## 7. Examples

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
S="skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py"
SPEC="_scratch/regress/2026-11-13/oblique/spec_p08.json"
OUT="_scratch/regress/2026-11-13/oblique/angle_sweep"

"$PY" "$S" plan --spec "$SPEC" --angles 0,30,60 --pol 90 --mode bfast --out "$OUT" --json
# mode=bfast tilt_axis=x n_points=3 angle_grid_sha256=<16 hex> cost=10.5x

"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec "$OUT/spec_angles.json" --sweep-json '{"theta":[0,30,60],"pol":[90]}' \
  --out "$OUT/run" --json

"$PY" "$S" collect --plan "$OUT/angle_sweep_plan.json" --run-dir "$OUT/run" \
  --out "$OUT/angle_matrix.csv" --json
```

## 8. References / 按需加载

| 文件 | 什么时候读 |
|---|---|
| `references/angle-physics.md` | 需要三种口径的物理推导、漂移公式、机时表、v251 属性落点与课程工程读回表时 |
| `skills/fdtd-lumerical-fsp-build/SKILL.md` §incidence | 要手写带角度的 spec 或理解 `--check` 断言时 |
| `library/py/fsp_build.py`（`resolve_incidence`） | 要改 mode 矩阵或物理拒绝规则时 |
| `skills/fdtd-lumerical-unitcell-simulation/SKILL.md` | 要理解 `--sweep-json` 如何覆盖 parameters 时 |

## 9. 相关文件

| 文件 | 用途 |
|---|---|
| `scripts/angle_sweep.py` | 唯一入口：`plan` / `collect` / `--self-test`（46 条解析真值） |
| `experiments/EXP-70…76` | 基线、builder、check、物理闸、本技能、P08 端到端、注册 |
| `_scratch/regress/2026-11-13/oblique/` | 视频解析、API 探针、P08 spec、角度扫描产物 |
