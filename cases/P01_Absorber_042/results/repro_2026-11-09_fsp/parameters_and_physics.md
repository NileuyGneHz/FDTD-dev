# P01 复现清单 — 论文重要参数与重要物理原理

> 论文：X. Liu, T. Starr, A. F. Starr, W. J. Padilla,
> *Infrared Spatial and Frequency Selective Metamaterial with Near-Unity Absorbance*,
> Phys. Rev. Lett. **104**, 207403 (2010), DOI 10.1103/PhysRevLett.104.207403
> 原文：`cases/P01_Absorber_042/paper/2论文-Infrared_Spatial_and_Frequency_Selective_Metamaterial_with_Near-Unity_Absorbance.pdf`（4 页，均有文本层）
> 文本转储：`_scratch/p01_repro/paper_text.txt`
> 本清单的每一项都标注了「论文页码 / fsp 中的落点」，便于把工程里的对象与论文数字逐一对应。

---

## 1. 重要参数清单

### 1.1 几何（论文单位 µm，`spec_repro_p01.json` 全部换算成 m）

| 参数 | 符号 | 论文值 | spec 采用值 | 论文出处 | fsp 中的落点 |
|---|---|---|---|---|---|
| 单元周期 | `a` | 2.0 | 2.0 µm | p.2 正文 + Fig.1 caption | `FDTD x span / y span` = 2 µm |
| 十字臂长 | `l` | 1.7 | 1.7 µm | 同上 | `cross_x x span`, `cross_y y span` |
| 十字臂宽 | `w` | 0.4 | 0.4 µm | 同上 | `cross_x y span`, `cross_y x span` |
| Al₂O₃ 间隔层厚度 | `t` / `ts` | 0.185 | 185 nm | 同上 + p.2 工艺（ALD 185 nm） | `Al2O3_spacer z span`；层位 `[-185, 0] nm` |
| 两层金属厚度（十字 + 地平面） | `tm` | 0.1 | 100 nm | 同上 | `cross_*` / `Au_ground z span`；层位 `[0,100]`、`[-285,-185]` nm |
| Si 基底厚度 | `t_sub` | **未给出** | 2.0 µm（假设） | p.2 只说 "silicon substrate" | `Si_sub z span` |
| 样品横向尺寸 | — | 140 µm × 140 µm | 不建模 | p.2 工艺 | 无（周期单胞近似无限阵列） |
| UCA writing fields | — | 39 个，间距 4 µm | 不建模 | p.3 | 无 |

> `185 nm` 的量取面已由 `notes/repro-2026-11-07-fsp-calibration.md` 反解析两个课程 `.fsp` 关闭：
> **地平面顶面 → 十字底面**，不是十字中面、不含 Ti 粘附层。课程工程层位与本 spec 逐层一致。

### 1.2 材料模型

| 材料 | 论文表述 | 数值 | spec / fsp 实现 | 出处 |
|---|---|---|---|---|
| 金（十字 + 地平面） | Drude | ωp = 2π × 2175 THz = **1.3665928e16 rad/s**；ωc = 2π × 6.5 THz = **4.08407045e13 rad/s** | `Au_paper`，Lumerical `Plasma` 材料：`Plasma resonance` / `Plasma collision` | p.2 Methods，引 Ordal 1983 |
| Al₂O₃ 间隔层 | ε = 2.28，tan δ = 0.04 | 复折射率 **n = 1.5105, k = 0.0302**（k = n·tanδ/2） | `Al2O3_paper`，`(n,k) Material` | p.2 Methods |
| Si 基底 | "silicon substrate" | 未指定色散数据集 | 内置 `Si (Silicon) - Palik` | p.2 |

**单位/口径陷阱（论文复现最容易翻车的三处）**

1. `2π × 2175 THz` 是**角频率**，必须写成 rad/s 的 `1.3666e16`；写成 `2.175e15` 会让金过反射、吸收峰消失。
2. 论文给的是 `tanδ = 0.04` 不是 `ε''`；`k = n·tanδ/2 = 0.0302`，直接用 0.04 会把介质损耗放大。
3. Lumerical `getindex(material, f)` 收的是**频率 Hz**（`c/λ`），传波长会静默返回错误外推值（本项目记忆：TiO₂ 曾得 5.99 而非 2.45）。
4. 自定义材料必须避开内置名：`Au` / `Al2O3` 会与数据库条目碰撞，故命名 `Au_paper` / `Al2O3_paper`。

### 1.3 仿真与实验条件

| 项 | 论文 | 本工程 | 说明 |
|---|---|---|---|
| 求解器 | **CST Microwave Studio 2009**，time-domain solver | **Ansys Lumerical FDTD v251** | 求解器口径差异是本次最大偏差来源 |
| 维度 / 边界 | 无限周期阵列，"appropriate boundary conditions to approximate a TEM wave" | 3D；x/y = `Periodic`，z = `PML` | PML x/y 会退化成孤立十字并给出 A = 1.111 的非物理值 |
| 入射 | 正入射 TEM，E/H 在面内，k 垂直 | `PlaneSource`，`Backward`（−z），polarization 0°，amplitude 1 | 实验反射在 **20°** 测量，透射在正入射 |
| 光谱范围 | 仿真 Fig.2 横轴约 3–11 µm；实验测量 3–12 µm | 源 4–8.5 µm，91 点 | 未覆盖 10 µm，见汇报 C6 |
| 网格 | 未公开 | `mesh accuracy 4` + `mesh_fine` override 30/30/20 nm（z 覆盖 `−(ts+tm)` → `tm+50 nm`） | 项目已做 acc 4/6/8 收敛对照 |
| 收敛判据 | 未公开 | `auto shutoff min = 1e-4`，`simulation time = 5 ps` | 实测 5987 步、`8.83863e-05`、Early termination |
| 反射/透射定义 | R = \|S11\|², T = \|S21\|²，A = 1 − R − T | R/T 两个 power monitor，A 由脚本/CSV 计算 | fsp 内没有直接的 `A` 监视器，见汇报 D5 |
| 归一化 | R 对 Au 镜、T 对 open aperture | 源 amplitude = 1，平面波归一化 | — |
| 探测 | FTIR + 红外显微镜，MCT 探测器，15× Cassegrain，KBr 分束器 | 无（纯仿真） | 实验装置不可复现 |

### 1.4 论文给出的关键结果数值（结果校验目标）

| 量 | 论文值 | 出处 | 本工程能否校验 |
|---|---|---|---|
| 最大吸收（仿真 + 实验） | **0.97 @ 6.0 µm** | p.1 abstract / p.2 Fig.2(a)(b) | 可算，实测 0.8069（偏差 −0.163）。**2026-11-09 人裁决：以 Lumerical ~0.82 为验收基准（PASS），0.97 降为论文参考值并标注 solver gap** |
| 峰值反射 | R = 0.03 @ 6 µm | p.2 | 可算，实测 0.1931 |
| 透射 | S21 ≈ 0 全频段 | p.1–2 | 可算，实测 max\|T\| = 1.40e-5 |
| FWHM | 1.0 µm | p.2 | 可算，实测 0.80 µm |
| A @ 4 µm | 10% | p.2 | 可算，实测 4.16% |
| A @ 10 µm | 1% | p.2 | **不可算**（源止于 8.5 µm） |
| 等效 ε₁、μ₁ 在 ω₀ 同时过零 | 定性 | p.3 Fig.3 | **不可算**（需复 S 参数反演） |
| 介质损耗比金属欧姆损耗大一个数量级 | 定性 | p.3 Fig.4 | **不可定量**（需 per-layer Pabs） |
| 40 dB 动态范围 / 6 µm 成像 / 10 µm 不可见 | 定性 | p.3–4 Fig.5 | **不可算**（需双尺寸子晶格 + 实验成像） |

---

## 2. 重要物理原理清单

### P1 — 十字谐振器是 electric ring resonator (ERR)，只耦合电场
十字的细臂与中心段让入射光的 **E** 在间隙里强烈局域（"strong focusing of the electric field within gaps"），
形成电偶极子型共振；单独存在时对外磁场几乎不响应（"couples strongly to uniform electric fields,
and negligibly to magnetic fields"）。出处 p.1 ¶3。
**工程落点**：`cross_x` + `cross_y` 两个 100 nm 厚 Au 矩形叠加成实心十字；`E_spacer` 场监视器可看间隙场增强。

### P2 — 地平面引入 antiparallel currents，激活磁共振
十字与连续地平面被 Al₂O₃ 隔开后，光场的 **H** 分量在**十字中心段**与**地平面**上感应出方向相反的电流；
一上一下的反向电流环等价于一个磁偶极子，于是原本不响应磁场的结构出现磁共振。
电共振由十字几何调，磁共振由十字几何 + 两层间距调，**两套自由度可独立调谐**。出处 p.1 ¶3–4。
**工程落点**：`Au_ground`（连续 100 nm Au）+ `Al2O3_spacer`（185 nm）同时存在。

### P3 — 阻抗匹配让 R → 0
分别调电/磁共振的幅度和频率，使等效阻抗 `Z(ω) = √(μ(ω)/ε(ω))` 在某个频率等于自由空间 `Z₀`，
Fresnel 反射被消除，反射率降到最低。出处 p.1 ¶4。
**工程落点**：R 监视器在源上方，直接给 `|S11|²`。

### P4 — 地平面厚度 > 红外趋肤深度，让 T → 0
100 nm Au 远大于红外下金的趋肤深度（十几 nm 量级），"thicker than the penetration depth of light
in the IR range"，所以 `S21` 全频段近零。这是完美吸收的**第二根支柱**；若减到 10 nm，场会穿透、T 上升、峰塌陷。
出处 p.1 ¶4、p.2；Q4/A4、Q5/A5（自测题）。
**工程落点**：`Au_ground z span = 100 nm`；T 监视器在地平面下方。

### P5 — 能量守恒 `A(ω) = 1 − R(ω) − T(ω)`
`R = |S11|²`、`T = |S21|²`；入射能量只有反射、透射、吸收三条去路。
`R≈0` 且 `T≈0` ⇒ `A≈1`。论文验算：仿真 `R=0.03, T≈0 ⇒ A=0.97`；实验同为 97%。出处 p.2。
**工程落点**：`verify_repro.lsf` 计算 `A = 1 − R − T` 并校验 `|R+T+A−1|`（实测 1.11e-16）。

### P6 — 等效参数反演：ε₁、μ₁ 在 ω₀ 同时过零；一正一负保证 T≈0
论文用 Smith 2002 的 S 参数反演法提取等效 `ε(ω)`、`μ(ω)`（Fig.3）：
在吸收极大值 ω₀ 处两者**实部同时过零**（阻抗连续 ⇒ R≈0）；且两者**总是一正一负**
（等效波矢强衰减 / 无源无增益 ⇒ T≈0）。出处 p.3 ¶1。
**工程落点**：**无** —— 功率监视器只给 `|S|²`，没有复相位；见汇报 D3。

### P7 — 损耗主要在 Al₂O₃ 介质层，不是金属
论文逐层计算 6 µm 处的能量耗散（Fig.4），发现 **Al₂O₃ 里的介质损耗比十字 + 地平面的欧姆损耗大一个数量级**。
合理性：金的 ωc 很小 ⇒ 欧姆损耗低；Al₂O₃ 的 `tanδ = 0.04` 不算小，且 E 被 ERR 的 gap 聚焦效应局域在介质层内。
出处 p.3 ¶1。
**工程落点**：`E_spacer` / `nidx_spacer` 只能给出定性场分布，**不能**给 per-layer 损耗比；见汇报 D3。

### P8 — Drude 模型：红外下的金是"有损镜子"
`ε(ω) = 1 − ωp²/(ω² + i·ωc·ω)`。ωp（等离子体频率）决定"金在哪个频率以下像镜子"；
ωc（碰撞频率）是电子散射率、对应 ε 的虚部即欧姆损耗。
`fp = 2175 THz ⇒ λp = c/fp ≈ 138 nm`，工作波长 6 µm 比它大 40 倍以上（ω ≪ ωp），
ε′ 强负 ⇒ 金在红外无疑问是良导体。ωc 越小欧姆损耗越低，这既限制了峰值吸收上限，
也解释了 P7 的损耗分配。出处 p.2 Methods；自测题 Q3/A3。
**工程落点**：`Au_paper` 的 `Plasma resonance` / `Plasma collision` 两个数值。

### P9 — 185 nm 是腔长/磁共振主旋钮，不是随手取的
介质层厚度决定十字与地平面之间的往返相位（MIM 磁共振，`2·n·ts·k₀ ≈ π`），
是调谐吸收峰**位置**的主旋钮之一；论文通过 CST 扫参优化得到 185 nm 使峰落在 6 µm。
本项目已做 `ts` 扫描（120/150/185/220/250 nm → peak A 0.962/0.913/0.808/0.716/0.673），
证明 96% 在物理上可达，但出现在 120 nm。**禁止**为凑 0.97 把 ts 调走 —— 那是拟合不是复现。
出处 p.1 ¶4、p.2；`results/repro_report.md` §5.2。

### P10 — 空间 + 频率选择性（论文的"第二个卖点"）
把高吸收的 UCA 与近零吸收的 UCB（同 2 µm × 2 µm 周期、同地平面与 Al₂O₃ 厚度，十字设计不同）
在 xy 面拼成图案（"B"/"C" 字样），得到 graded perfect absorber：
6 µm 处 UCA 近 1、UCB 近 0 ⇒ 图像对比度最大；10 µm 处整体反射近 1、吸收近 0 ⇒ MPA"不可见"。
动态范围达 **40 dB**，可服务于 SLM / 单像素 / 高光谱 subsampling 成像。出处 p.3 ¶2–3、p.4 Fig.5。
**工程落点**：**无** —— 本工程是 `nx=ny=1` 的单胞，见汇报 D4。

---

## 3. 参数 → fsp 对象速查

| spec 对象 | 材料 | z 层位 (nm) | 对应论文 |
|---|---|---|---|
| `cross_x` + `cross_y` | `Au_paper` | `[0, 100]` | Fig.1(a) ERR 十字 |
| `Al2O3_spacer` | `Al2O3_paper` | `[-185, 0]` | Fig.1(b) 介质间隔层 |
| `Au_ground` | `Au_paper` | `[-285, -185]` | Fig.1(b) 连续地平面 |
| `Si_sub` | `Si (Silicon) - Palik` | `[-2285, -285]` | p.2 Si 基底（厚度假设） |
| `FDTD` | — | `[-3285, 2600]` | Periodic x/y + PML z |
| `source` | — | `z = 1600 nm` 附近（Backward） | 正入射 TEM |
| `R` / `T` | power | `+2225 nm` / `−2885 nm` | S11 / S21 |
| `E_spacer` / `nidx_spacer` | field / index | `−92.5 nm` | P1 / P7 的定性证据 |
