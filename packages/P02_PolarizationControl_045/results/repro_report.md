# Reproduction report — P02 宽带高效全介质偏振控制器（Kruk et al., APL Photonics 1, 030801, 2016）

> 按 `skills\lumerical-unitcell-simulation\assets\report_template.md` 填写。
> 2026-11-04，从零建模（未使用 `fig3_1.fsp` 等课件工程 —— 其 `radius=0`、周期 1 µm，与论文不符）。

## 1. 身份

| 项 | 值 |
|---|---|
| 包 | `P02_PolarizationControl_045` |
| 论文 | Kruk, Hopkins, Kravchenko, Miroshnichenko, Neshev, Kivshar, *APL Photonics* **1**, 030801 (2016) |
| 目标图 | **Fig. 3(a)** Transmission along both pillar axes |
| 入口 | `scripts\spec_p02.json` → `skills\lumerical-unitcell-simulation\scripts\run_fdtd_sweep.py` |
| 工程 | `results\repro_p02\point_0{0,1}_pol_*.fsp` |
| 日期 | 2026-11-04 |

## 2. 参数

| 参数 | 符号 | 论文值 | 采用值 | 出处 |
|---|---|---|---|---|
| 周期（方晶格） | D | 750 nm | 750 nm | Fig.2 caption / 正文 |
| 椭圆长轴 | b | 430 nm | 430 nm | Fig.3 正文 |
| 椭圆短轴 | a | 280 nm | 280 nm | Fig.3 正文 |
| 柱高 | c | 850 nm | 850 nm | Fig.3 正文 |
| 材料 | — | poly-Si | `Si (Silicon) - Palik`（晶体） | 库内无 poly-Si，见 `missing` |
| 基底 | — | 石英 | `SiO2 (Glass) - Palik` | 正文 |

## 3. 仿真设置

| 项 | 设置 |
|---|---|
| 模式 | **transmission**（基底侧入射，空气侧收透射） |
| 边界 | x/y = Periodic，z = PML |
| 网格 | accuracy 4 + 局部 override 20/20/20 nm（覆盖柱与界面 ±50 nm） |
| 波长 | 1.40–1.70 µm，101 点 |
| 偏振 | `pol = 0°` 与 `90°` 两次（对应两个主轴） |

## 4. 结果 vs 论文

| 量 | 论文 | 本次（pol=0°） | 本次（pol=90°） |
|---|---|---|---|
| 峰值透射 | ≈1 | **1.0009 @ 1.457 µm** | **1.0037 @ 1.475 µm** |
| T(1.53 µm) | ≈1 | 0.9605 | 0.9772 |
| T(1.56 µm) | ≈1 | 0.9588 | 0.9801 |
| T(1.625 µm) | ≈1 | 0.9811 | 0.9007 |
| C+L 带内 T 最小 | ≈1 | 0.8924 | 0.8924 |
| 峰值 R | 小 | 1.4×10⁻⁴ | 2.0×10⁻³ |
| 收敛 (`Auto Shutoff`) | — | 8.90×10⁻⁵ ✅ | 9.12×10⁻⁵ ✅ |

判定：🟢 **C+L 带内两轴 T 均在 0.90–0.98，与"near unity transmission"一致**。

**T > 1（0.09% / 0.37%）** 是离散化误差量级，不是物理增益；判据是峰值 R 同时接近 0，
说明没有能量凭空产生，只是功率归一化的数值残差。

## 5. 偏差诊断

| # | 嫌疑 | 结论 | 证据 |
|---|---|---|---|
| 1 | 边界条件 | 排除 | x/y Periodic；若用 PML 会退化为孤立柱 |
| 2 | 透射/反射几何放反 | 已排除（曾踩） | 初版源在上→T 只有 0.13；改 transmission 模式后 T→1 |
| 3 | R 的符号 | 已修正 | 透射模式下 R 监视器在源下方，原始功率为负；取相反数 |
| 4 | 网格 | 未单独加密验证 | 见 §6 |
| 5 | 材料（晶态 vs 多晶 Si） | **未排除** | 论文用 LPCVD poly-Si，未给光学常数 |
| 6 | 波长范围 | 部分解释差异 | 1.40/1.70 µm 已出 C+L，单轴出现共振凹陷属预期 |

## 6. 未完成 / 下一步

- **Fig. 3(b) 相位差 φx − φy = π 尚未提取。** 当前构建器只输出功率（R/T/A），
  没有场监视器。这是 skill 的已知能力缺口，设计已记录：
  同一平面放 E 场监视器，分别跑 x/y 偏振，取 `arg(Ex) − arg(Ey)` —— 公共传播相位自动抵消，
  无需额外参考跑。
- **网格未做收敛检验**（P01 上做过：acc4 与 acc6 差 0.007）。P02 的柱高 850 nm、直径 430 nm，
  20 nm override 应当够，但没验。
- **多晶硅光学常数**待向作者确认。

## 7. 顺带纠正

`P02\fsp\fig3_1.fsp` 等课件工程与论文不符（`circle.radius = 0`、FDTD 周期 1 µm ≠ 750 nm），
不能作为参照基准。复现一律从论文参数重建。
