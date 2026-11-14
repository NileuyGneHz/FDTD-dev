# 2026-11-07 参考 FSP 校准复现（P01）

> 结论：**§5.4「待确认 ts 量取面」作废**。课程原版工程的层位与本包 spec 完全一致，
> 185 nm = 地平面顶面 → 十字底面。0.82 是 Lumerical 在这套参数下的稳定答案。
> 详见 `defects/D-001-*.md`。本文件只放证据与命令，不重复结论推导。

## 1. 三个工程反解析（`skills/fdtd-lumerical-fsp-introspection`）

| 工程 | x/y BC | acc | override | shutoff | 仿真时长 | 波长 / 点数 | 层位 (nm) | layoutmode |
|---|---|---|---|---|---|---|---|---|
| `model/infrared_perfect_absorber.fsp` | Periodic | 8 | 24 nm | 1e-5 | 1 ps | 3.5–11 µm / 100 | Al₂O₃ `[-185,0]`、地 `[-285,-185]`、十字 `[0,100]` | 0.0（已算） |
| `model/d2_perfectCross.fsp` | **PML** | 8 | 24 nm | 1e-5 | 1 ps | 3.5–11 µm / 100 | 同上 | 1.0（未算） |
| `results/repro_p01/point_00_base.fsp` | Periodic | 4 | 30/30/20 nm | 1e-4 | 5 ps | 4–8.5 µm / 91 | 同上 | 0.0（已算） |

- `d2_perfectCross.fsp` 的 FDTD 中心偏了 `x=-6.23 nm, y=-59.43 nm`，源 span 被撑到
  `2.0125 × 2.1189 µm`（周期 2 µm）→ 该工程还有派生属性问题，不适合当基准。
- 课程主工程的 Si 基底厚 1715 nm，本包 spec 用 2000 nm；在不透明地平面下方，光学上无关。

## 2. 收敛判据（`_p0.log`）

| 日志 | 步数 | 末值 `Auto Shutoff` | 阈值 | 判定 |
|---|---|---|---|---|
| `infrared_perfect_absorber_p0.log` | 7039 | `8.87508e-06` | 1e-5 | ✅ 收敛 |
| `d2_perfectCross_p0_course.log` | 77813 | `0.046734` | 1e-5 | ❌ 跑满时间上限 |
| `_scratch/regress/p01-20261107/baseline/*_p0.log` | 5987 | `8.77453e-05` | 1e-4 | ✅ |
| `_scratch/regress/p01-20261107/fsp_calibrated/*_p0.log` | 7443 | `9.52708e-06` | 1e-5 | ✅ |

## 3. 数值对照

| 来源 | peak A | peak λ | R@peak | A@6 µm |
|---|---|---|---|---|
| 课程主工程已存谱 | 0.8196 | 6.152 µm | 0.1805 | 0.7174 |
| 按课程设置重建后重跑 | 0.8177 | 6.152 µm | 0.1824 | 0.7169 |
| 本包原 spec 重跑（回归） | 0.8069 | 5.85 µm | 0.1931 | 0.7147 |
| 历史 `results/repro_p01` | 0.8083 | 5.85 µm | 0.1917 | 0.7163 |
| **论文 Fig.2(a) / 实验** | **0.97** | **6.0 µm** | 0.03 | — |

- 三个 Lumerical 结果在 6 µm 处极差 **0.0027**；重建与课程工程峰值差 **0.0018**、峰位相同。
- 峰位 5.85 → 6.15 µm 来自数值设置（网格 / 收敛阈值 / 波长采样），不是几何或材料差异。
- 论文 0.97 出自 **CST Microwave Studio 2009** 仿真，实验值同为 97%；不是 Lumerical 结果。

## 4. 已排除项（累计）

| 嫌疑 | 结论 | 证据 |
|---|---|---|
| 边界条件 | 排除 | PML → A=1.111 非物理；Periodic → 0.82 |
| 网格 | 排除 | acc4 0.808 / acc6 0.801 / acc8 0.818 |
| 收敛 | 排除 | 三条独立运行的末值均低于阈值 |
| 监视器 / 归一化 / 单位 | 排除 | T≈0，R+T+A=1 自洽 |
| **`ts` 量取面** | **排除（本次）** | 两个课程 `.fsp` 层位与 spec 逐层相同 |
| **材料实现** | **排除（本次）** | `getindex` 在 4/6/8/10 µm 与 Drude 解析 `(n,k)` 逐位相同（6 µm: `2.8026+43.2457i`） |
| 十字形状 | 排除 | 论文 Fig.1(a) 为实心十字，与两个矩形叠加一致 |

## 5. 可重跑命令

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS

"$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config skills/fdtd-lumerical-fsp-introspection/assets/inspect_config.example.json \
  --out _scratch/regress/fsp-20261107 --json

"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/regress/p01-20261107/baseline

"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec _scratch/p01_probe/spec_fsp_calibrated.json \
  --out _scratch/regress/p01-20261107/fsp_calibrated
```

回归产物在 `_scratch/regress/`，**没有写回 `cases/`**。
