# P02 参数清单 — Kruk et al. 2016 宽带全介质偏振控制器

> **论文来源**：本地 `cases/metasurface/P02_PolarizationControl_045/paper/5论文-Broadband_highly-efficient_dielectric_metadevices_for_polarization_control.pdf`
> 经正文与补充材料核验为 **S. Kruk, B. Hopkins, I. I. Kravchenko, A. E. Miroshnichenko, D. N. Neshev, Y. S. Kivshar,
> "Broadband highly efficient dielectric metadevices for polarization control", APL Photonics 1, 030801 (2016),
> DOI 10.1063/1.4948946**。
> **与任务书给定的默认论文一致**，故不触发「论文来源为默认值，待用户确认」；也不是 Chen 2012《Dual-polarity plasmonic metalens》。
> 页码记法：`p.N` = PDF 第 N 页 = 期刊页码 `030801-N`；`p.13+` 为补充材料 S1–S5（PDF 页 12–16）。
> 单位：论文值按原文用 nm；**本工程一律 SI（米）**，1.55 µm 写 `1.55e-6`。

---

## 1. 主参数表

| 参数名 | 符号 | 论文值 | 单位 | 在本工程中的取值 | 来源（页码/图号） |
|---|---|---|---|---|---|
| 纳米柱短轴（HWP） | a | 280 | nm | `2.80e-7` m | p.5 正文「Our half-wave plate consists of nanoparticles with sizes a = 280 nm, b = 430 nm, c = 850 nm」；Fig.3 同组 |
| 纳米柱长轴（HWP） | b | 430 | nm | `4.30e-7` m | p.5 正文 / Fig.3 |
| 纳米柱短轴（QWP） | a | 310 | nm | `3.10e-7` m | p.5 正文「quarter-wave plate ... a = 310 nm, b = 370 nm」；Fig.4(c)(d) |
| 纳米柱长轴（QWP） | b | 370 | nm | `3.70e-7` m | p.5 正文 / Fig.4(c)(d) |
| 纳米柱高 | c | 850 | nm | `8.50e-7` m | p.5 正文（HWP/QWP 同高）；补充材料 p.14 S5「thickness of the Si film is 850 nm」；p.8「π phase difference is accumulated over 850 nm distance at 1550 nm」 |
| 周期（方晶格） | D | 750 | nm | `7.50e-7` m | p.5 正文「square lattice with period D = 750 nm」；Fig.2 caption 同值 |
| 晶格类型 | — | 方形（square） | — | `square`，`period_x = period_y = D`，supercell 1×1 | p.5 正文；补充材料 p.13「a square lattice makes the xy and yx off-diagonal elements of G zero」 |
| 晶格类型（q-plate） | — | 六角（hexagonal），与方晶格同面密度 | — | 本工程**不建** q-plate（超出本任务范围） | p.5 正文「q-plate consists of the same nanoparticles arranged into hexagonal lattice」；Fig.5 |
| 截面形状 | — | 椭圆（elliptical nanoparticles） | — | `ellipse`，64 顶点多边形近似 | p.5 正文「the long axis of constituent elliptical nanoparticles」；Fig.2(a) 示意 |
| 多极子分析用几何（Fig.2） | a/b/c/D | 285 / 450 / 860 / 750 | nm | 本工程**沿用 Fig.3 的 280/430/850**（目标图是 Fig.3） | p.4 Fig.2 caption「Dimensions are a = 285 nm, b = 450 nm, c = 860 nm, and D = 750 nm」 |
| 窄带对照几何（S1，Q5 用） | a/b/c/D | 160 / 470 / 1080 / 950 | nm | 本工程**不建**（仅作带宽对照引用） | 补充材料 p.13 S1；带宽 19 nm vs 宽带 152 nm，差 8 倍 |
| 纳米柱材料 | — | LPCVD 多晶硅（poly-Si），negligible optical losses | — | 材料库内置 `Si (Silicon) - Palik`，实测 @1550 nm `n = 3.4764, k = 0` | p.4 正文「polycrystalline silicon on quartz substrate」；补充材料 p.14 S5（LPCVD 工艺） |
| 数值仿真的材料数据 | — | **Palik 晶态硅实验介电常数** | — | 同上（用 Palik 与论文数值方法一致，**不是缺 poly-Si 数据的妥协**） | 补充材料 p.13 S4「fullwave numerical simulation of the silicon nanopillar array with CST Microwave Studio, using experimental crystalline silicon permittivity data of Palik」；p.16 Ref.9 |
| 衬底材料 | — | 石英（quartz wafer） | — | 材料库内置 `SiO2 (Glass) - Palik`，实测 @1550 nm `n = 1.4440, k = 0` | p.4 正文；补充材料 p.14 S5「four-inch quartz wafer ... substrate is 500 µm」 |
| 衬底厚度 | t_sub | 500 | µm | `1.0e-6` m（截断，见 §3 假设） | 补充材料 p.14 S5 |
| 工作波段 | — | 通信 C + L 带；设计波长 1550 nm；论文谱轴 1450–1750 nm | nm | 源 `1.40e-6` ~ `1.70e-6` m，101 频点 | p.1 摘要「across multiple telecom bands」；p.4「near unity transmission over both C and L telecommunications bands」；Fig.3/Fig.4 谱轴 |
| 入射方式 | — | 正入射，平面波 | — | `PlaneSource`，`injection axis = z`，`direction = Forward`（衬底侧入射，空气侧收透射） | p.3 式(1)–(4)「normally incident, co-polarized plane wave propagating in ẑ」 |
| 入射偏振 | — | 沿纳米柱两正交主轴；多极子分析时平行短轴；器件工作时与轴成 45° | deg | 扫 `pol = 0°` 与 `90°` 两次；另设 45° 用于 PCE | p.4 Fig.2 caption「incident polarization is parallel to the short axis」；p.5「wave plate axis being at 45° to the axis of the polarizer」；p.6 Fig.4 caption「oriented at 45°」 |
| 目标相位差（HWP） | Δφ = φ_x − φ_y | π（180°）；retardance 0.5 | rad | 判定容差 ±0.1π | p.5 Fig.3(b) caption「ϕx − ϕy shows a constant value of π」；p.8「retardance is close to 0.5」 |
| 目标相位差（QWP） | Δφ = φ_x − φ_y | π/2（90°）；retardance 0.25 | rad | 判定容差 ±0.1π | p.5 正文「adds π/2 phase difference」；p.8「0.25 for the case of the quarter-wave plate」；Fig.4(d) |
| 有效双折射 | Δn | ≈ 0.9（传统双折射晶体 ≤0.3，高 3 倍以上） | — | 由 `Δn = Δφ·λ/(2π·L)` 反推校验 | p.8 正文；Δn = 1550/(2×850) ≈ 0.912 |
| 总透射（实验） | T | ≈ 90%（实验）；≈100%（数值） | — | 判定容差 ±8% | p.1 摘要「reflectionless (∼90% transmission)」；p.2「In experiment, the transmission efficiencies reach 90%」 |
| 偏振转换效率 | PCE | ≈ 99% | — | 判定容差 ±5% | p.1 摘要「∼99% polarization conversion efficiency」；p.2；p.5「virtually 100% of transmitted light by 90°」 |
| 后向散射 / 反射 | R | ≈ 0 | — | 判定阈值 < 5% | p.1 摘要「reflectionless」；p.4 式(4) 令 R=0；Fig.2(c) 反射被压低 |
| 边界条件 | — | 周期阵列（论文为无限周期超表面） | — | `x min/max bc = Periodic`，`y min/max bc = Periodic`，`z min/max bc = PML` | 由 p.4「square lattice」+ 式(1)–(4) 无限周期假设推得；**论文未逐条给 FDTD 边界，此为本工程设定** |
| 网格精度 | — | 未给 | — | `mesh accuracy = 4` + 局部 override `dx=dy=dz=2e-8` m（覆盖 z ∈ [−5e-8, c+5e-8]） | **论文未给，本工程经验值**（承自 `config/spec_p02.json`，P01 上 acc4 vs acc6 差 0.007） |
| 仿真方法 | — | 全波数值仿真：CST Microwave Studio（多极分解）；理论曲线见 Fig.3/4 虚线 | — | **Ansys Lumerical FDTD 2025 R1 (v251)**，3D FDTD，频域功率监视器 + DFT 场监视器 | 补充材料 p.13 S4；p.6 Fig.4 caption「dashed lines—theoretical results」；**求解器不同，属复现而非逐位重算** |
| 求解器精度 | — | 未给 | — | GPU 模式下 `real32` 单精度（本工程已实测可用） | 本工程实测 `_p0.log` |
| 收敛判据 | — | 未给 | — | `auto shutoff min = 1e-4`，`simulation time = 1e-12` s | 本工程设定（承自 `config/spec_p02.json`） |

---

## 2. 两组器件参数对照（供建工程直接取用）

| 器件 | a (m) | b (m) | c (m) | D (m) | 目标 Δφ | 论文位置 |
|---|---|---|---|---|---|---|
| HWP（主复现对象） | `2.80e-7` | `4.30e-7` | `8.50e-7` | `7.50e-7` | π | p.5 正文 / Fig.3 |
| QWP | `3.10e-7` | `3.70e-7` | `8.50e-7` | `7.50e-7` | π/2 | p.5 正文 / Fig.4 |

---

## 3. 建模假设与歧义（必须在复现报告里一并声明）

| # | 假设 | 理由 / 证据 | 风险 |
|---|---|---|---|
| A1 | `a`、`b` 取为椭圆截面的**全轴长**而非半轴 | 若按半轴解释，`b = 430 nm` ⇒ 全宽 860 nm > D = 750 nm，柱体将超出单胞，物理上不可能 | 中：若论文实为半轴口径，几何整体错一倍 |
| A2 | 用 `Si (Silicon) - Palik` 代替器件实物的 LPCVD poly-Si | **论文补充材料 p.13 S4 自己就用 Palik 晶态硅实验介电常数做全波仿真**；器件是 poly-Si，但数值模型不是 | 低：与论文数值方法对齐；残余差异来自晶界吸收 |
| A3 | 衬底截断为 `1e-6` m 而非 500 µm | 石英在 C+L 带透明，厚度不影响相位差（只加公共传播相位），全厚会把仿真盒拉到米级 | 低：只影响绝对相位，不影响 Δφ |
| A4 | 光从衬底侧入射、空气侧收透射 | 标准 on-glass 超表面透射测量口径；`config/spec_p02.json` 已验证此方向 T→1（源放上方时 T 仅 0.13） | 低 |
| A5 | 椭圆主轴与 x/y 对齐，`pol=0°` 对应哪一轴未由论文定义 | 论文只说「parallel to the short axis」，未在坐标系里定义长轴朝 x 还是 y；两条谱按角度标注 | 中：影响 φ_x/φ_y 的符号，不影响 |Δφ| |
| A6 | Fig.2 的 285/450/860 与 Fig.3 的 280/430/850 视为两组独立参数 | 目标图为 Fig.3，故采用 Fig.3 组；Fig.2 是多极分解的示意几何 | 低 |
| A7 | 论文用 CST，本工程用 Lumerical FDTD | 允许复现，但网格/PML/材料拟合不同，数值不会逐位相等 | 中：偏差归因时需考虑求解器差异 |

---

## 4. 论文本身未给全、无法逐位复现的量

- **poly-Si 的光学常数**：论文只给器件工艺（LPCVD），数值仿真改用 Palik 晶硅；未给 poly-Si 的 n(λ)、k(λ) 实测表。
- **FDTD/全波设置**：网格、PML 层数、仿真时长、边界细节全部未给（论文用 CST，只述「fullwave numerical simulation」）。
- **椭圆的长轴朝向**（A5）、**衬底是否纳入仿真域**（论文 Fig.2 caption 提到「neglects reflection off the glass substrate」的多极分解口径，与主数值曲线口径不同）。
- **90%/99% 的实验值与 ~100% 的理论值并存**：验收表用实验值 ~90% / ~99% 作基准，但本工程是数值仿真，理论上应趋近 100%。

---

## 5. 前置检查记录（2026-11-09）

| 项 | 结果 |
|---|---|
| Python 解释器 | `C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，3.13.14（托管，含 numpy 2.5.3 / matplotlib 3.11.2） |
| `lumapi` | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python\lumapi.py`，导入 OK |
| license | `1055@localhost`，实测可 checkout，两段式 run 成功 |
| 会话 / 判据 | `save → close → 新会话 load → run`，`layoutmode = 0.0`，`_p0.log` 含 `Completed` |
| GPU | RTX 3070 Laptop 8 GB / CC 8.6，`Detected GPU 0` + `Using datatype: real32` 实测可用 |
| 目标路径 | `cases/metasurface/P02_PolarizationControl_045/` 根下无 `.fsp`，无需备份 |
