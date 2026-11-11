---
name: fdtd-lumerical-field-map
description: >
  把场监视器的原始复场变成可进验收表的几何量：焦斑（焦距/增益/横向 FWHM/DOF）、
  相位面俯仰（与设计相位拟合）、OAM 电荷、面内 k 谱与倏逝衰减长度。
  读 .fsp 或 session-control 的 npz dump，只算不画。
  当超透镜、涡旋光、异常反射这类「结论不在 R/T 谱里，而在场里」的复现需要出数时使用。
  触发词：焦斑、焦距、相位面、涡旋、OAM、远场、k 空间、场图后处理、field map。
---

# 场后处理的唯一实现

## 概述

`scripts/field_map.py` 读一个场监视器，输出 `field_metrics.json` + `field_map.npz` + 曲线 CSV。
它**只算不画**：图上色仍归 `fdtd-lumerical-figure`；`field_map.npz` 的第一个二维数组是
`I`，直接 `figure --kind field --input field_map.npz` 就能出图。

收编前 P05 与 P04 各有一份手写脚本（`analyze_p05.py`、`field_map_and_decay.py`），
算法各自对、但「焦距」有两个实现。本技能是唯一实现，两份原型不再演进。

## CRITICAL（违反即停止）

1. **`axes.prop_axis_source` 不是 `cli` 时，必须在报告里写明传播轴是按默认值推的。**
   `--prop-axis` 缺省给 `z`（2D 仿真给 `y`），x-y 面在 3D 里到底是横向面还是剖面，
   数据本身分不出来。
2. **`off_axis_ratio > 2` 且 `has_real_focus=false` 时，不许写「没有焦点」。**
   那是**离轴焦**：主指标只扫 `|u| <= --half-width-um`，焦斑挪到 2 µm 它就瞎了。
   改 `--half-width-um` 或把窗口挪到峰位再判，并把 `warning` 原文抄进报告。
3. **`n_freq_total > 1` 必须给 `--wavelength-um`**，否则脚本报错退出 2。
   静默取第 0 个频点会在另一个波长上算出一组「看着合理」的数——这是本项目
   反复出现的假轮次第三种形态（D-013 就是同类）。
4. **`--basis cpol` 且 `--cp-channel auto` 必须给背景组。** 没有背景就判不了哪一路是
   转换通道；猜错得到的是同偏振场，它也可能「看起来像焦斑」。
5. **相位只报 `|slope|` 是错的。** `|slope|≈1` 说明相位面形状对，**符号**说明极性
   （收敛透镜为 −1）。两个都要写，只写一个等于丢掉一半结论。
6. **本技能不报聚焦效率。** 那需要入射功率归一化，属 stage 2/3 的账；
   用这里的强度比值冒充效率是错的。

## 核心工作流

1. **取场**。两种入口，等价：
   - 已有 dump：`--npz <run>/field_field.npz`（`session_control.py` 的 `format: npz`）
   - 直接读工程：`--fsp <run>/iteration_001.fsp --monitor field`（开一次只读会话，不求解）
   先跑 `--dry-run` 看它推断出的 `axes` 与 `freq`，别一上来就算。
2. **确认轴与频点**。`axes.prop` 与 `prop_axis_source`、`freq.index` 必须与工程里的监视器
   法向一致；不一致就显式给 `--prop-axis` / `--wavelength-um`。
3. **选模式**，可逗号组合：
   | 模式 | 产出 | 需要什么 |
   |---|---|---|
   | `focus` | `z_focus_um` `focus_gain` `fwhm_um` `dof_um` `off_axis_ratio` | 沿传播轴有多个切面 |
   | `phase` | `fit_slope` `fit_slope_abs` `fit_rms_rad` `phase_swing_over_2pi` | 同上 + `--design-kind` |
   | `oam` | `oam_charge` `oam_charge_round` `oam_fit_rms` | 横向面（法向 = 传播轴） |
   | `kspace` | `kx_over_k0_main` `angle_deg_main` `peaks[]`，可选 `decay` | 同上 |
4. **判读数**。焦距对照设计值；`|slope|` 对照 1；OAM 对照设计电荷；
   `kx/k0` 对照 `sin(θ)`。对不上先跑 `--self-test` 排除实现问题，再去查模型。

## 示例

**用户：** "P05 的 RCP 焦点跑到哪了，相位面斜多少？"

**动作：**

```bash
python skills/fdtd-lumerical-field-map/scripts/field_map.py \
  --npz _scratch/regress/2026-11-10/P05/data/RCP_field.npz \
  --bg-npz _scratch/regress/2026-11-10/P05/data/RCP-bk_field.npz \
  --mode focus,phase --basis cpol --wavelength-um 0.74 \
  --design-kind lens --design-f-um 10 --out /tmp/p05_rcp --json
```

**结果：** `z_focus_um = 9.30`（论文目标 9.3）、`focus_gain = 5.21`、`fwhm_um = 0.812`、
`|slope| = 1.047`（设计 f=10 µm）、`fit_rms = 0.12 rad`、`phase_swing = 1.06 × 2π`。
交叉通道自动判成 `c_minus`，说明 RCP 入射转成 LCP。

## 故障排除

| 症状 | 处置 |
|---|---|
| `FieldError: 场监视器有 N 个频点，但没给 --wavelength-um` | 补 `--wavelength-um`；若 npz 里没有频率轴，用 `session_control.py` 重 dump 并带上频点 |
| `FieldError: 监视器只沿 x 变化（线监视器）` | 换成面监视器。2D 仿真里 power 监视器本来就是一条线（D-008），场必须用 `addprofile` |
| `FieldError: oam 需要横向平面监视器` | 当前是 x-z 剖面。涡旋要在 x-y 面（`2D Z-normal`）上取场，法向沿传播轴 |
| `has_real_focus=false` 但 `off_axis_ratio` 很大 | 离轴焦，见 CRITICAL 2，不要下「无焦」结论 |
| `|slope|` 明显小于 1 且 `fit_rms` 很大 | 探针面选在了透镜内部/太靠近结构；用 `--probe-z-um` 挪到出射面外侧，或先查近场是否还在收敛 |
| `kx/k0` 恰好落在 `sin(θ)` 的邻格 | 已做 ×16 零填充 + 抛物插值，`bin_width_kx_over_k0` 会告诉你剩余分辨率 |
| `--fsp` 报 `找不到 library/py/lumapi_common.py` | 技能目录被单独拷走了。本脚本复用共享会话工具，不另写一份（D-005/D-006 的教训） |

## 按需加载

- 读 `references/metrics.md` **当要把某个数写进 `acceptance.json` 或报告时**——
  它逐字段给定义、单位、符号约定与已知陷阱，避免「同名不同义」。
- 自检不读任何文件：`python skills/fdtd-lumerical-field-map/scripts/field_map.py --self-test`
  （9 条解析真值，无 license 也能跑）。
