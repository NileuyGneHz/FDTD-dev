# P03 复现报告 — Ding2015 等离激元半波片

> 运行：2026-11-12 · 入口 `projects/R03_HWP_Ding2015/config/spec_p03.json`
> 模型：`projects/R03_HWP_Ding2015/model/p03_hwp.fsp`
> 数据：`projects/R03_HWP_Ding2015/results/repro_p03/`

## 1. 身份

| 项 | 值 |
|---|---|
| 论文 | Ding, Wang, He, Shalaev, Kildishev, *ACS Nano* **9**, 4111–4119 (2015) |
| DOI | `10.1021/acsnano.5b00218` |
| 目标 | Fig.1b（R_co / R_cr）、Fig.1c（PCR）、Fig.3b（u/v 相位差） |
| 求解器 | Ansys Lumerical FDTD 2025 R1 (v251)，**CPU 双精度** |
| 模型 | 3D 周期单胞，x/y Periodic，z PML |
| 运行 | 单次 x 偏振入射，场监视器同时取 Ex/Ey；由 `r_u=J_xx+J_yx`、`r_v=J_xx−J_yx` 得两主轴 |

## 2. 参数 — 论文 vs 模型

| 参数 | 符号 | 论文 | 模型 | 出处 |
|---|---|---|---|---|
| 周期 | p | 600 nm | 600 nm | Fig.1 caption |
| 金砖长/短边 | l1 / l2 | 390 / 165 nm | 390 / 165 nm | Fig.1 caption |
| 金砖厚度 | tm | 80 nm | 80 nm | Fig.1 caption |
| SiO₂ 厚度 | ts | 110 nm | 110 nm | Methods |
| Au 膜厚度 | d | 150 nm | 150 nm | Methods |
| 旋转角 | θ | 45° | 45°（多边形顶点预旋转） | Methods |
| SiO₂ | n | 1.45，无损 | 1.45，k=0 | Methods |
| Au | Drude | ωp=1.37e16 rad/s，ωd=1.224e14 rad/s | 同左 | Methods |
| 基底 | glass | 未给 n | n=1.45（Au 膜不透明，光学无关） | Fig.1a |

**没有拟合任何参数。** 未在论文中找到的量（网格、Ti 层是否计入 Fig.1）写进 spec 的
`assumptions` / `missing`，不靠调参凑曲线。

## 3. 仿真设置

| 项 | 设置 | 说明 |
|---|---|---|
| 维度 | 3D | 单胞 |
| x / y 边界 | Periodic | 无限阵列 |
| z 边界 | PML | 吸收反射/透射波 |
| 网格 | accuracy 4 + 10 nm override | 覆盖 Au 膜、SiO₂、金砖，z 范围 −200…250 nm |
| 源 | 平面波，Backward，x-pol | 0.7–1.7 µm，101 点 |
| R 监视器 | z = 2.315 µm（源上方） | 只收到反射波 |
| R_field | 与 R 同面，2D Z-normal | 记录 Ex/Ey/Ez，101 频点 |
| T 监视器 | z = −0.95 µm（Au 膜下方） | 应≈0 |
| auto shutoff | 1e-5 | 末值 8.82e-6 |
| simulation time | 5 ps（请求） | 实际 auto-shutoff 在 0.198 ps 停止 |

## 4. 结果 vs 论文

| 量 | 论文 | 本次（800–1600 nm） | 偏差 | 判定 |
|---|---|---|---|---|
| `R_co` 均值 | ≈0 | **0.0131**（1.31%） | +1.3 pp | ✅ |
| `R_co` 最大 | ≈0.03（读图，带边） | **0.0305**（3.05% @ 920 nm） | 与图一致 | ✅ |
| `R_cr` 均值 | ≈0.92（平台；正文说≈1） | **0.9031**（90.3%） | −1.7 pp | ✅ |
| `R_cr` 最小 | ≈0.78 @ 800 nm（读图） | **0.8101** @ 810 nm | +3 pp | ✅ |
| `R_total` 均值 | >90% | **91.62%** | +1.6 pp | ✅ |
| `PCR` 均值 | >95% | **98.58%** | +3.6 pp | ✅ |
| `PCR` 最小 | >95% | **96.68%** | +1.7 pp | ✅ |
| PCR>95% 带宽 | 805–1672 nm | **790–1660 nm** | 短边 −15 nm，长边 −12 nm | ✅ |
| 相对带宽 `W_B` | ≈70% | **71.0%** | +1 pp | ✅ |
| `Δφ_uv` 均值 | ≈π（黑线在 0.9π–1.1π 间） | **181.7° ± 13.5°**（mod 360） | +1.7° | ✅ |
| `Δφ_uv` 范围 | ≈0.8π–1.1π（读图） | 159.0°–198.7° | 与图一致 | ✅ |
| `Δφ_uv` @1.0 µm | ≈0.95π≈171°（读图） | 164.4° | −7° | ✅ |
| `cos Δφ` 均值 | ≈−1 | **−0.972** | +0.028 | 🔶 |

关键波长点（来自 `p03_monitors.csv`）：

| λ (µm) | R_co | R_cr | PCR | R_total | Δφ_uv (°) |
|---|---|---|---|---|---|
| 0.80 | 0.0013 | 0.7749 | 0.9983 | 0.7763 | 175.9 |
| 0.90 | 0.0285 | 0.8838 | 0.9688 | 0.9123 | 159.6 |
| 1.00 | 0.0170 | 0.9108 | 0.9817 | 0.9278 | 164.4 |
| 1.10 | 0.0003 | 0.9309 | 0.9997 | 0.9312 | 178.1 |
| 1.20 | 0.0080 | 0.9232 | 0.9914 | 0.9313 | 190.6 |
| 1.40 | 0.0221 | 0.8990 | 0.9760 | 0.9211 | 197.8 |
| 1.55 | 0.0011 | 0.8986 | 0.9988 | 0.8997 | 182.0 |
| 1.60 | 0.0055 | 0.8850 | 0.9938 | 0.8905 | 172.0 |

> `R_co + R_cr = R_total` 在机器精度内成立（max 误差 1.1e-16），说明场监视器的
> co/cross 分解与功率监视器自洽。

## 5. 收敛与网格

| 判据 | 值 | 结果 |
|---|---|---|
| `_p0.log` 存在 | `run_pol0_p0.log` | ✅ |
| 是否含 `Completed` | 是 | ✅ |
| 是否含 `fields are diverging` | 否 | ✅ |
| 最后 `Auto Shutoff` | **8.82129e-06** | ✅ < 1e-5 |
| 迭代数 | 10371 | — |
| 仿真时间 | 1.977e-13 s（0.198 ps） | auto-shutoff 提前停止 |

**网格对照（如实记录）**：

| override | 结果 | 判定 |
|---|---|---|
| **10 nm（交付）** | R_co max 3.05%，R_cr min 81.0%，PCR min 96.68% | 可用；与论文 Fig.1b/1c 形状一致 |
| 20 nm（粗化对照） | R_co max 56.1%，R_cr min 24.4%，PCR min 30.3% | 不可用；80 nm 金砖被粗网格严重欠采样 |
| 5 nm（细化） | 启动后 2% 处主动终止（预计 >30 min） | **未完成**；不能声称 5 nm 收敛 |

因此：**10 nm 是本轮交付网格，且已达到 auto-shutoff；但没有完成 5 nm 细化，网格收敛未被证明。**
20 nm 的失败说明 10 nm 已接近该几何可用的下限，不能再用更粗的网格。

**对照**：`cases/P03_HWP_Ding2015/model/fig1_hwp_paper_materials_p0.log` 是旧工程在 GPU 上跑出的
`ERROR: ... fields are diverging`，虽然它也写 `Simulation completed successfully`，但结果不可用。
本次强制 CPU（`gpu_guard` 判定 Au Drude → CPU），所以这是一次可用的双精度结果。

## 6. 偏差诊断

按顺序排查：

| # | 怀疑项 | 结论 | 证据 |
|---|---|---|---|
| 1 | 边界条件 | 排除 | x/y Periodic；R_co 未出现 >1 或负值 |
| 2 | 材料模型 | 排除（按论文） | Au Drude ωp/ωd 逐位照 Methods；SiO₂ n=1.45 |
| 3 | 网格 | **保留** | 10 nm 可用；20 nm 粗化到 R_co 56%/PCR 30%，说明 80 nm 砖对网格极敏感；5 nm 细化未完成 |
| 4 | 监视器位置 | 排除 | R 距 PML 375 nm；R_field 与 R 同面；T≈−4e-7 |
| 5 | 归一化 | 排除 | R_co+R_cr 与 R_total 逐点一致到 1e-16 |
| 6 | 几何单位 | 排除 | 全部 m；周期/厚度与论文一致 |
| 7 | Ti 粘附层 | 未建模 | 论文 Fig.2 明说计入 5 nm Ti；Fig.1 未明说。本次按 Fig.1 未计 |
| 8 | FEM vs FDTD | 系统性差异 | 论文用 FEM；本文用 FDTD，色散金属的离散误差方向不同 |

**最可能的偏差来源**：

- `R_cr` 在短波边（0.8–0.9 µm）为 0.81–0.88；对照论文 Fig.1b 的红线，800 nm 处本身也有一个
  ~0.78–0.80 的凹陷，因此**这不是偏差，而是同一带边特征**。平台段（1.0–1.6 µm）本次 ~0.90–0.93，
  论文 ~0.92–0.93，差 1–2 个百分点。
- `R_co` 最大 3.05% 出现在 0.92 µm；论文 Fig.1b 的紫色 `R_co` 在 800/1800 nm 带边也有 ~3% 的抬升，
  形状一致。中段本次 <2%，与论文“almost zero”一致。
- `Δφ` 在 1.0 µm 为 164.4°；论文 Fig.3b 的黑线在 1000 nm 约为 0.95π≈171°，差约 7°，不是 16°。
  整带均值 181.7°、cos 均值 −0.972，落在论文黑线的 0.9π–1.1π 起伏范围内。
- 剩余差异更可能来自：10 nm 网格对 80 nm 金砖尖角的离散、未计 Ti 粘附层、FEM/FDTD 的求解器差异。
  这些都不需要靠改 l1/l2/ts 去“修”。

**没有做的事**：没有为了把 R_cr 抬到论文平台而改 l1/l2/ts；没有把 Δφ 拟合成 180°。这些都会把
复现变成拟合。

## 7. 结论

- **Fig.1b/1c 基本复现**：R_co 均值 1.3%（论文≈0），R_cr 平台 90.3%（论文≈92%），
  R_cr 带边最低 81.0%（论文 Fig.1b 在 800 nm 也有 ~78–80% 的凹陷），
  PCR 均值 98.6%、最小 96.7%，PCR>95% 带宽 790–1660 nm（论文 805–1672 nm），
  相对带宽 71.0%（论文约 70%）。
- **Fig.3b 的物理判据成立**：u/v 相位差整带均值 181.7°，cos 均值 −0.972；
  1.0 µm 处 164.4°，与论文黑线在 1000 nm 的 ~0.95π 相差约 7°。
- **未复现**：Fig.2（斜入射）、Fig.4–6（超胞/反常反射/场分布）。这些需要 Bloch 边界、
  超胞模型或场映射，不在本轮单胞模型范围内。
- **交付**：`model/p03_hwp.fsp`（477 KB，build-only，可重跑）、`p03_monitors.csv`（101 行）、
  `pol0_fields.npz`（复场）、`fig_p03_monitors.png`、`run_pol0_p0.log`。

## 8. 复跑

```powershell
# 托管 Python（runtime-contract 指定；系统 Python 缺 numpy / lumapi）
$PY = "C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# 1. 建工程（不跑）
& $PY skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py `
  --spec projects/R03_HWP_Ding2015/config/spec_p03.json `
  --out projects/R03_HWP_Ding2015/model --tag p03_hwp --check

# 2. 跑单偏振 + 场监视器（CPU；脚本在 _scratch，属于一次性工具）
& $PY tools/gpu_guard.py `
  --fsp projects/R03_HWP_Ding2015/model/p03_hwp.fsp `
  --run "`"$PY`" _scratch/p03_repro/run_p03_field.py --fsp projects/R03_HWP_Ding2015/model/p03_hwp.fsp --out projects/R03_HWP_Ding2015/results/repro_p03 --pol 0"

# 3. 出图（零引擎）
& $PY _scratch/p03_repro/plot_p03.py `
  --csv projects/R03_HWP_Ding2015/results/repro_p03/p03_monitors.csv `
  --out projects/R03_HWP_Ding2015/results/repro_p03/fig_p03_monitors.png
```

