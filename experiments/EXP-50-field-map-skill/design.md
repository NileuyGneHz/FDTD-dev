# EXP-50 — 把 stage 3.5 场分析收编成技能（`fdtd-lumerical-field-map`）

## 假设

P05/P06/P04 各自手写了一份场后处理脚本，算法已经跑通过，但：

- 三份脚本互不复用（P05 `analyze_p05.py` 用圆偏振基 + 背景扣除，
  P04 `field_map_and_decay.py` 用傅里叶滤波 + 指数拟合）；
- 它们都直接 `import lumapi`，无法在无 license 的机器上复算；
- 「焦距」「相位斜率比」这些进 `acceptance.json` 的数字没有唯一实现，
  换个人重算就会得到另一个数。

把它们收编成一个只读场数据、**不开仿真会话也能算**的技能，是 P05/P06 复现
能被审计的前提。同时补上两个真实缺陷：

1. **FWHM 定义会虚高**：原型用「最外层半高交点」，旁瓣一旦超过半高，
   FWHM 会把整条包络算进去。改成「以峰值为中心的连续半高区」。
2. **多频点场监视器静默取第 0 个频点**：所有原型都没处理 `nf>1`，
   `E.reshape(...)` 会按形状硬掰，读到的可能是另一个波长。

## 输入

| 数据 | 路径 | 说明 |
|---|---|---|
| P05 RCP 结构组 | `_scratch/regress/2026-11-10/P05/data/RCP_field.npz` | `E(1429,1,758,1,3)`、`x`、`z` |
| P05 RCP 背景组 | `_scratch/regress/2026-11-10/P05/data/RCP-bk_field.npz` | 同上，几何全 disabled |
| P05 LCP 结构/背景组 | `.../LCP_field.npz`、`.../LCP-bk_field.npz` | 用于极性判别对照 |
| P05 已有结论 | `.../P05/analysis/summary_metrics.json` | RCP `focus_z_um=9.25`、LCP `focus_z_um=4.85`、target 9.3 |

P06/P04 的 run 目录已不在，OAM 与 k-space 只用解析合成场做判据（ℓ 与入射角已知，
比真实数据更硬）。

## 方法

技能 `skills/fdtd-lumerical-field-map/`，stage 3.5，**只算不画**（出图仍归 stage 5）。

数据入口两条，共用同一个载入器：

- `--fsp --monitor`：开一次只读会话，`getresult` 取场，随后立刻 `close`；
- `--npz`：读 `session_control.py` 的 `format=npz` dump，**零引擎**。

四个量测模式（可逗号组合）：

| 模式 | 算什么 | 判据来源 |
|---|---|---|
| `focus` | 轴上扫描 → `z_focus`、`focus_gain`、横向 FWHM、DOF | 合成球面波 f=10 µm |
| `phase` | 探针面解缠相位 → 拟合设计相位（`lens`/`tilt`/`none`）的斜率、RMS、摆幅 | 合成相位面 |
| `oam` | 环上相位 → 缠绕数 ℓ | 合成涡旋 ℓ=3 / −2 |
| `kspace` | 面内 FFT → 峰位 `kx/k0` → 出射角；可选倏逝衰减长度 | 合成斜入射 20° |

载入器必须**记录它推断出来的轴与频点**（`axes.varying`、`freq_index`），
`nf>1` 而未给 `--wavelength-um` 时**报错**，不猜。

## 判据

| 指标 | 期望 | 判据类型 |
|---|---|---|
| 合成高斯 σ=1.2 µm 的 FWHM | 2.3548σ，相对误差 < 1% | 解析真值 |
| 合成 f=10 µm 汇聚波 `z_focus` | 10.0 ± 0.1 µm，`focus_gain > 5` | 解析真值 |
| 合成 ℓ=3 涡旋 | `oam_charge = 3 ± 0.05` | 解析真值 |
| 合成 ℓ=−2 涡旋 | `oam_charge = −2 ± 0.05` | 解析真值 |
| 合成 20° 斜入射 | `kx/k0 = sin20° = 0.3420 ± 0.01` | 解析真值 |
| P05 RCP `z_focus` | 9.25 ± 0.3 µm | 既有结论复算 |
| P05 LCP `z_focus` | 4.85 ± 0.3 µm，且与 RCP 差 > 3 µm | 极性判别 |
| 两瓣合成场（旁瓣 > 半高）的 FWHM | 新定义给单瓣宽，旧定义给全宽 | 缺陷修复 |

`verdict=pass` 要求上表全过，且四个负对照全部按预期失败。

## 负对照（每条都必须真的失败）

1. **背景组**：只给 `RCP-bk_field.npz`（几何全 disabled）跑 `focus` →
   `has_real_focus` 必须为 **false**（没有结构就没有焦点，增益 ≈1）。
2. **不做偏振分解**：用 `|E|²` 代替交叉圆偏振通道跑 P05 RCP →
   `z_focus` 必须偏出 9.25 ± 0.3 µm，或 `focus_gain` 显著变小（证明 CP 基是必需的）。
3. **`nf>1` 不给波长**：合成 `E(nx,1,nz,3,3)` → 必须 `FieldError`，
   不许静默取第 0 个频点。（旧原型在这里会静默算错。）
4. **`--design-kind none` 套在设计相位上**：拟合斜率必须 ≈0 且 `fit_rms` 很大，
   证明「斜率 ≈1 不是恒真」。

## 可重跑命令

```bash
python skills/fdtd-lumerical-field-map/scripts/field_map.py --self-test
python _scratch/regress/2026-11-10/EXP-50/run_checks.py
python skills/fdtd-lumerical-field-map/scripts/field_map.py \
  --npz _scratch/regress/2026-11-10/P05/data/RCP_field.npz \
  --bg-npz _scratch/regress/2026-11-10/P05/data/RCP-bk_field.npz \
  --mode focus,phase --design-kind lens --design-f-um 10 --wavelength-um 0.74 \
  --out /tmp/p05_rcp --json
```

## 停止条件

任一解析真值判据偏差 > 容差，就停并回报，**不调容差去迁就实现**；
P05 的 `z_focus` 若与 9.25 差 > 0.3 µm，先查是不是「轴上强度扫描」的起点定义
与既有脚本不同，查不出就记 `defects/`，不写「已验证」。
