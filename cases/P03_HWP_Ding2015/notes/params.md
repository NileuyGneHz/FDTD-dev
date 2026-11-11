# P03_HWP_Ding2015 — 论文重要参数清单

> **论文来源（已核实，非默认值）**：本目录 `paper/Ding2015_Broadband_High-Efficiency_Half-Wave_Plate.pdf`
> 为黄老师提供的原文（10 页，含 Figure 1–6 与 Methods）。
> 作者 **Fei Ding, Zhuoxian Wang, Sailing He, Vladimir M. Shalaev, Alexander V. Kildishev**，
> *ACS Nano* **2015**, 9(4), 4111–4119，DOI `10.1021/acsnano.5b00218`。
> 作者、年份与目录名 `Ding2015` 一致，且 PDF 第 3 页 Figure 1 caption 明确给出全部几何参数。
> 交叉核对：`notes/论文精读_等离激元半波片.md` §8、`paper/自测题_5问.md` Q3/Q4、`cases/.../README.md` §2。
> ⚠️ 因此**不采用**任务书 §1 的「默认参数回退」；任务书要求的
> 「论文来源为默认值，待用户确认」标注**不适用**，已在 `repro_report.md` 首段说明。

---

## 0. 实际参数 vs 任务书默认参数（差异表）

| 参数 | 任务书默认值 | 论文实际值（PDF） | 差异 / 处置 |
|---|---|---|---|
| 周期 `p` | 600 nm | **600 nm** | 一致 |
| 金砖长×宽 `l1×l2` | 390 × 165 nm | **390 × 165 nm** | 一致 |
| 金砖厚度 `tm` | **未给出** | **80 nm** | 默认值缺项 → 以 PDF 补齐 |
| SiO₂ 厚度 `ts` | 110 nm | **110 nm**（扫参优化所得） | 一致，补充「SI §1 / Fig.S1 扫参」来源 |
| 金膜厚度 `d` | 150 nm | **150 nm** | 一致 |
| 旋转角 | 45° | **绕 z 轴逆时针 45°**（长轴 u 相对 x 轴） | 一致，方向明确 |
| 工作波段 | 800–1600 nm | **800–1600 nm**；PCR>95% 波段 **805–1672 nm**，相对带宽 ≈70% | 一致，补充 PCR 波段 |
| Au 材料模型 | **未指定** | **Drude**：ωp = 1.37×10¹⁶ s⁻¹，ωd = 1.224×10¹⁴ s⁻¹（已含表面粗糙度/晶界效应，ref 27,28） | 默认值缺项 → **关键差异**，禁止用 Palik |
| SiO₂ 折射率 | **未指定** | **常数 n = 1.45，无损** | 默认值缺项 → 以 PDF 补齐 |
| 求解器 / 仿真方法 | 未指定（任务要求 FDTD） | **FEM（finite element method）3D 全波** | **方法学差异**：本工程按任务书用 FDTD，见报告 FAIL 归因 |
| 衬底 | 「下方玻璃衬底」 | 玻璃衬底；Methods 为实际器件加 **5 nm Ti 粘附层**（Au/SiO₂ 两界面） | Figure 1 仿真未声明含 Ti → 本工程按 Fig.1 口径**不加 Ti**，报告注明 |
| 入射 | 「从上向下、反射模式」 | **正入射 θi = 0°，x 线偏振**，平面波 | 一致，明确 θi |
| 边界 | 未指定 | **x、y 周期边界**；z 方向开放（PML/吸收） | 以 PDF 为准 + FDTD 实现需要 |

> 结论：几何尺寸与默认值**完全一致**，差异是**默认值未给出的 4 项**（`tm`、Au Drude 参数、
> SiO₂ n、FEM 求解器）与一项明确的求解器口径冲突。以 PDF 为准。

---

## 1. 参数总表

| 参数名 | 符号 | 论文值 | 单位 | 本工程取值 | 来源（页码 / 图号） |
|---|---|---|---|---|---|
| 单元胞周期 | `p` | 600 | nm | `600e-9` m | PDF p.3 Fig.1 caption；p.4 Results 首段 |
| 金砖长边（u 轴） | `l1` | 390 | nm | `390e-9` m | PDF p.3 Fig.1 caption |
| 金砖短边（v 轴） | `l2` | 165 | nm | `165e-9` m | PDF p.3 Fig.1 caption |
| 金砖厚度 | `tm` | 80 | nm | `80e-9` m | PDF p.3 Fig.1 caption；p.9 Methods |
| SiO₂ 间隔层厚度 | `ts` | 110 | nm | `110e-9` m | PDF p.3 caption；p.4「optimized … 110 nm」，SI §1 / Fig.S1 扫参 |
| 底层 Au 膜厚度 | `d` | 150 | nm | `150e-9` m | PDF p.3 caption；p.4 |
| 旋转角（绕 z） | `θ` | 45（逆时针） | ° | `45.0`，`addpoly` 顶点旋转 | PDF p.4「rotated counterclockwise by 45°」；Fig.1a |
| Au 材料模型 | — | Drude ε(ω)=1−ωp²/(ω²+i·ωd·ω) | — | `Sampled data` 喂 Drude 复 ε | PDF p.5 Results；p.9 Methods 引用 27,28 |
| Au 等离子体频率 | `ωp` | 1.37×10¹⁶ | s⁻¹ (rad/s) | `1.37e16` | PDF p.5 |
| Au 阻尼频率 | `ωd` | 1.224×10¹⁴ | s⁻¹ (rad/s) | `1.224e14` | PDF p.5 |
| Au 背景介电常数 | `ε∞` | 1（Drude 标准式） | — | `1.0` | PDF p.5 公式；notes §7 |
| SiO₂ 折射率 | `n` | 1.45，k=0（无损） | — | `(n,k) Material`, n=1.45, k=0 | PDF p.5「lossless dielectric with a constant refractive index of 1.45」 |
| 玻璃衬底 | — | glass | — | n=1.45 简化，位于金膜下方（光学不参与） | PDF p.2 Fig.1a；p.9 Methods |
| 工作波段 | — | 800–1600 | nm | 源 700–1700 nm（留余量），161/201 频点 | PDF p.5「800 to 1600 nm」；摘要「800 nm bandwidth」 |
| PCR>95% 波段 | `λs–λl` | 805–1672 | nm | 验收判据 | PDF p.5；Fig.1c |
| 相对带宽 | `WB` | ≈70% | — | `2(λl−λs)/(λl+λs)` | PDF p.5 |
| 入射角 | `θi` | 0（正入射） | ° | `0` | PDF p.3 Fig.1 caption「at normal incidence」 |
| 入射偏振 | — | x 线偏振（或 y） | — | `polarization angle = 0` | PDF p.3 caption；p.5 |
| 入射方向 | — | 从上向下（−z），反射模式 | — | `direction = Backward` | PDF p.5「plane wave is incident downward」 |
| 边界条件 x / y | — | Periodic | — | `Periodic` ×4 | PDF p.5「Periodic boundary conditions … x- and y-directions」 |
| 边界条件 z | — | 开放（论文 FEM 用端口/PML 等价） | — | `PML` ×2 | 由 FDTD 实现决定，PDF 未明写 |
| 网格精度 | — | 论文未详述 | — | 全局 `mesh accuracy = 2` + 金属区局部 `dx=dy=dz=8 nm` | PDF 未给 → 本工程自定，**属复现偏差来源** |
| 时间步稳定性 | — | 论文未详述 | — | `dt stability factor = 0.95` | 防 Drude 金属单精度发散（本机 field-manual §6.3） |
| 仿真方法 | — | **FEM，3D 全波** | — | **FDTD，3D** | PDF p.4「finite element method (FEM)」；**口径不同** |
| 反射率指标 | `R` | >90% | — | 验收判据 | PDF 摘要 / p.3 正文 |
| PCR 指标 | — | >95%（摘要 >97%） | — | 验收判据 | PDF 摘要 / p.5 |

---

## 2. 论文明确给出、但本工程**不建模**的项（口径说明）

| 项 | 论文值 | 不建模理由 |
|---|---|---|
| Ti 粘附层 | 5 nm（Au/SiO₂ 两界面） | PDF p.4 Fig.2 caption 说「**in the simulations**」考虑 Ti；但 Figure 1（本次复现目标）的仿真段 p.5 未声明 Ti。按 Figure 1 口径省略，`repro_report.md` 记为偏差来源 |
| 超胞（supercell） | s = 2.4 μm，4 天线，0→2π 相位梯度 | 属 Figure 4–6，不是 Figure 1 单胞；不在本次复现范围 |
| 器件实测尺寸 | 1 mm × 1 mm，1667×1667 单元 | 实验样品参数，周期单元仿真不需要 |
| 测量角度范围 | θi+θr > 36°、最大 40° | Figure 2 角度鲁棒性，非本次目标 |
| 广义斯涅尔定律 | θr = sin⁻¹(sin θi + λ/s) | 超胞反常反射，非单胞 |
| 5 nm Ti + 220 nm PMMA 等工艺 | Methods 加工流程 | 工艺参数，非光学仿真输入 |

---

## 3. 单位与实现约定（硬约束）

- **全部 SI**：110 nm → `110e-9`；80 nm → `80e-9`；ω 用 rad/s。
- 材料 `Sampled data` 采样表第一列是**频率（Hz）** = `C0/λ`，不是波长。
- 自检：Drude 在 λ=1000 nm 应给 `n ≈ 0.2379 + 7.1925i`；SiO₂ 应给 `1.45 + 0i`。
- 45° 旋转用 `addpoly` 显式顶点（矩形 4 顶点绕中心旋转后闭合），**不用 `addrect`**（无旋转属性）。
- 会话：`save → close → 新会话 load → switchtolayout → run`，`close()` 落在 `finally`。
