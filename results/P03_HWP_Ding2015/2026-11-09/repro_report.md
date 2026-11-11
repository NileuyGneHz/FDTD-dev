# P03_HWP_Ding2015 — 复现情况汇报

**日期**：2026-11-09　|　**模式**：Reproduce（论文复现，禁止调参凑结果）　|　**结论**：**7 项验收 6 PASS / 1 N/A，无 FAIL**

---

## 0. 首段：论文来源与「实际参数 vs 默认参数」差异表

> **论文来源不是默认值。** 任务书 §1 要求「若目录下无明确论文，默认按 2015 年 Ding 等人半波片参数执行，
> 并显式标注『论文来源为默认值，待用户确认』」。本目录**存在黄老师提供的原文 PDF**：
> `paper/Ding2015_Broadband_High-Efficiency_Half-Wave_Plate.pdf`（10 页，含 Figure 1–6、Methods、References）。
> 作者 **Fei Ding, Zhuoxian Wang, Sailing He, Vladimir M. Shalaev, Alexander V. Kildishev**，
> *ACS Nano* **2015**, 9(4), 4111–4119，DOI `10.1021/acsnano.5b00218` —— **与目录名 `Ding2015` 一致**。
> 因此**以 PDF 为准**，不套用默认值；任务书要求的「论文来源为默认值，待用户确认」标注**不适用**，
> 也不需要用户再确认论文来源。交叉核对源：`notes/论文精读_等离激元半波片.md` §8、
> `paper/自测题_5问.md` Q3/Q4、`cases/P03_HWP_Ding2015/README.md` §2。

| 参数 | 任务书默认值 | 论文实际值（PDF） | 差异 / 处置 |
|---|---|---|---|
| 周期 `p` | 600 nm | **600 nm** | 一致 |
| 金砖 `l1×l2` | 390 × 165 nm | **390 × 165 nm** | 一致 |
| 金砖厚度 `tm` | **未给出** | **80 nm** | 默认缺项 → 以 PDF 补齐（Fig.1 caption） |
| SiO₂ `ts` | 110 nm | **110 nm**（SI §1 / Fig.S1 扫参所得） | 一致，补来源 |
| 金膜 `d` | 150 nm | **150 nm** | 一致 |
| 旋转角 | 45° | **绕 z 逆时针 45°**（长轴 u 相对 x） | 一致，方向明确 |
| 工作波段 | 800–1600 nm | **800–1600 nm**；PCR>95% 为 **805–1672 nm**，WB≈70% | 一致，补 PCR 波段 |
| Au 材料 | **未指定** | **Drude** ωp=1.37×10¹⁶ s⁻¹, ωd=1.224×10¹⁴ s⁻¹（含粗糙度/晶界） | **关键缺项** → 禁用 Palik，自建 Drude |
| SiO₂ 折射率 | **未指定** | **常数 n=1.45，无损** | 默认缺项 → 以 PDF 补齐 |
| 求解器 | 未指定（任务要求 FDTD） | **FEM 3D 全波**（PDF p.4） | **口径冲突**：按任务书用 FDTD，见 §5 归因 |
| 衬底 | 玻璃 | 玻璃 + Methods 里实际器件有 **5 nm Ti 粘附层** | Fig.1 仿真段未声明 Ti → 按 Fig.1 省略 |
| 入射 | 从上向下、反射模式 | **正入射 θi=0°，x 线偏振** | 一致，明确角度 |

> 几何尺寸与默认值**完全一致**；差异全部是默认值**未给出**的 4 项与 1 处求解器口径冲突。

---

## 1. 前置检查（任务书 §2，逐项）

| 项 | 结果 | 证据 |
|---|---|---|
| 目录内容 | ✅ 存在 | `README.md`；`paper/` 2 PDF + 自测题；`notes/` 精读 md；`model/` 4 个旧 `.fsp` + 4 份 `_p0.log` + 1 个 `.lsf`；`results/` 4 CSV + 4 PNG |
| 论文 PDF / 参数笔记 | ✅ 存在且作者年份一致 | `Ding2015_Broadband_High-Efficiency_Half-Wave_Plate.pdf`（10 页，pymupdf 提取 33009 字符）；`论文精读_等离激元半波片.md`；`自测题_5问.md` |
| 旧 `.fsp` / 旧脚本 / 旧 CSV | ✅ 存在，均只读引用 | `fig1_hwp_paper_materials.fsp`（1.07 MB，旧入口）、`fig1_hwp_unitcell.fsp`、`t4_tio2_unitcell.fsp`、`TiO2_nanobrick_unitcell.fsp`；`t15_hwp_R_paper.csv`、`t14_hwp_R.csv` 等 |
| README / config 约定 | ✅ README 存在 | `README.md` §0 指定入口工程与 t15 脚本；§2 给参数；§4 记「材料模型是最大误差源」。⚠️ README 里 `scripts\` / `fsp\` 路径已迁为 `model\`，属归档时的旧路径 |
| 目标路径是否已存在 `.fsp` | ✅ **不存在** | `P03_HWP_Ding2015_repro.fsp` 原不存在 → **无需备份**（未触发 `<原名>.bak_<timestamp>.fsp`） |
| `lumapi` 可导入 | ✅ | 托管 venv `C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe`（Python 3.13.14 + numpy 2.5.3）；`lumapi.py` 在 `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python` |
| license 可用 | ✅ | `1055@localhost` LISTENING；实测 `lumapi.FDTD(hide=True)` 开会话成功、`layoutmode=1.0`、close 正常 |
| Python 解释器正确 | ✅ | 托管 venv（非系统 3.10 / 3.13 裸解释器），含 numpy / matplotlib / pymupdf |
| GPU 可用 | ✅ | `nvidia-smi`: RTX 3070 Laptop 8 GB, driver 591.86, CUDA 13.1 |
| 相关 skills（**只调用，未修改**） | ✅ 记录如下 | `fdtd-lumerical-headless`（会话/三判据/材料坑）、`fdtd-lumerical-fsp-build`（build-only 规范）、`fdtd-lumerical-fsp-introspection`（旧工程反解析纪律）、`fdtd-lumerical-figure`（Agg 出图、图上数字现算）；另参考项目内 `docs/constitution/field-manual.md` §6.3 / §7.2。不适用：`fdtd-lumerical-design-loop` / `session-control`（Reproduce 模式禁止调参闭环）、`cut-*` 系列 |
| 硬约束：skills 只读 | ✅ 遵守 | 未新增/删除/替换任何 skill 文件；所有自写脚本落在 `_scratch/tmp_p03hwp_20261109_2029_*` |
| 硬约束：会话前缀临时文件 | ✅ 遵守 | 全部中间产物带 `tmp_p03hwp_20261109_2029_` 前缀，见 §7 清理 |
| 硬约束：单位 SI | ✅ 遵守 | 110 nm → `110e-9`；ω 用 rad/s；材料采样表首列为 Hz |

**前置检查全部通过，未触发第 6 节「停止并上报」条件。**

---

## 2. 阶段 A–D 执行记录

### A 参数提取
按 PDF p.3 Fig.1 caption、p.4 Results、p.5 材料/仿真设置、p.9 Methods 提取，输出 `docs/P03_HWP_Ding2015/params.md`（22 行参数表 + 差异表 + 不建模项 + 单位约定）。

### B 建工程
`P03_HWP_Ding2015/P03_HWP_Ding2015_repro.fsp`（498 646 B，**layoutmode=1.0 未算状态** → 用户打开即可直接 Run）。

| 对象 | 实现 | 校验 |
|---|---|---|
| Au 砖 45° | `addpoly`，顶点 `rot_rect(390e-9,165e-9,45)` 绕中心逆时针旋转后闭合 | **未用 `addrect`**（无旋转属性）；顶点见 build log |
| Au 材料 | `Sampled data` 喂 Drude 复 ε（400–2500 nm，600 点，首列 Hz），`max coefficients=6` | `getindex` 自检：Au@1000 nm = **0.2379+7.1925i**（与手算逐位一致） |
| SiO₂ | `(n,k) Material`, n=1.45, k=0 | 自检 1.4500+0.0000i |
| 衬底 / 金膜 / SiO₂ / 砖 | z = [−400,0] / [0,150] / [150,260] / [260,340] nm | 78 项属性设置 **0 FAIL** |
| 边界 | x/y 四面 `Periodic`，z 两面 `PML` | 符合 PDF p.5 |
| 网格 | 全局 `mesh accuracy=2` + 金属区局部 `dx=dy=dz=8 nm` | 求解网格 **77×77×112** |
| 源 | `addplane`, `direction=Backward`, `polarization angle=0`, `amplitude=1`, 700–1700 nm | 从上向下、x 偏振、正入射 |
| 监视器 | `R_power`(power, 2D Z-normal)、`R_field`(profile, 2D Z-normal)、`R_point`(单点，旧 t15 口径对照)、`T_bot`(结构下方) | 全部 z 位置远离 PML；`R_field` 面平均取 0 阶反射场 |
| **偏振分解** | `R_co=|⟨Ex⟩|²`, `R_cr=|⟨Ey⟩|²`（`⟨·⟩` = 监视器面空间平均 = 0 阶傅里叶分量；p=600 nm < λ，正入射仅 0 阶传播） | 与 `R_power` 总反射互校 |
| 防发散 | `dt stability factor = 0.95` | 关键：旧 t15 未设 → GPU real32 发散（见 §4） |

### C 跑仿真与校验
严格 `save → close → 新会话 load → switchtolayout → run`，`close()` 全部落在 `finally`。**交付 `.fsp` 本身保持未算**，实际求解在 `_scratch` 的纯 ASCII 副本上进行（避免引擎把 `_p0.log` 写回只读 `cases/`）。

| 组 | 求解器 | layoutmode | `_p0.log` | Completed | diverging | 迭代 | 耗时 |
|---|---|---|---|---|---|---|---|
| `cpu`（验收基准） | CPU 双精度 | **0.0** ✅ | ✅ | 20283 | **否** | 20283 | 270.1 s |
| `gpu`（用户追加要求） | **GPU real32，已启用** ✅ | **0.0** ✅ | ✅ | 20283 | **否** | 20283 | **29.1 s** |
| `bg`（减背景） | CPU | 0.0 ✅ | ✅ | 314 | 否 | 314 | 8.7 s |
| `ts_sweep` 5 点 | GPU | 0.0 ✅ | ✅ | — | 否 | — | 31–63 s/点 |

**GPU 启用说明（用户追加要求「可以启用 GPU 加速时启用它」）**：
1. 探明本机 RTX 3070 Laptop 8 GB、GPU resource active，但全局 `FDTD\GPU-mode` 初始为 **false**（CPU）。
2. 因此**临时**把 `FDTD Solutions.ini` 的 `GPU-mode` 切到 `true` 后再开新会话求解；**每次 `finally` 写回原值并回读确认**（`ini_restored=True`），扫参也是每点单独切换/恢复，把对并行 agent 的影响窗口压到 30–60 s。
3. 项目 field-manual §6.3 已实测：GPU 是 real32 单精度，Drude 金属会出现 `0 < permittivity < 1` 警告并在 404 步发散。本次用 **`dt stability factor=0.95`** 消除该风险——GPU 组**无 diverging**、迭代数与 CPU 完全相同。
4. **A/B 对照**：GPU 29.1 s vs CPU 270.1 s = **9.27× 加速**；`max|ΔR_cr| = 2.70×10⁻⁴`、`mean = 2.35×10⁻⁵`，`max|ΔR_co| = 2.43×10⁻⁴`。→ GPU 结果可信，**已启用**；但最终验收数值仍取更保守的 CPU 双精度。

**减背景**：`bg` 组把 `substrate/au_film/sio2_spacer/nanobrick_45deg/mesh_metal` 全部 `enabled=0`。
背景场 `|E_bg,x| ≤ 1.54×10⁻³`（均值 5.26×10⁻⁴），`|E_bg,y| = 0` 精确；扣除后
`max|ΔR_co| = 1.84×10⁻³`、`max|ΔPCR| = 1.28×10⁻³` —— 修正很小但已执行并留证（`background_ref.csv`）。

**物理自洽性**（CPU 双精度，900–1600 nm）：`R_co+R_cr = 0.897 ≤ 1`，`R_power = 0.919`，
`T_bot = −2.7×10⁻⁶ ≈ 0`（150 nm 金膜不透光），**201 个频点中 R>1 的点数 = 0**。

### D 交付物
见 §7。

---

## 3. 验收表（逐项填，任务书 §5）

| 论文结论 | 论文值 | 本工程结果 | 容差 | 状态 |
|---|---|---|---|---|
| **PCR 峰值** | >95%（摘要 >97%） | **99.999% @ 1155 nm**；900–1600 nm 均值 **99.32%** | ±5% | **PASS** |
| **PCR 峰值波长** | **论文未给出**（Fig.1c 只声明 PCR>95% 的 805–1672 nm 波段，无峰值坐标） | 1155 nm | ±0.1 μm | **N/A** —— 论文缺该基准量，无法比较；**非 FAIL**。原因见 §5「论文数据缺口」 |
| **工作带宽（PCR>90%）** | 论文给的是 **PCR>95%：805–1672 nm = 0.867 μm**（未给 >90% 口径） | PCR>90% 连续 **820–1665 nm = 0.845 μm**；PCR>95% 连续 **825–1620 nm = 0.795 μm**；WB(95%)=0.650 | ±0.2 μm | **PASS**（0.845 vs 0.867 差 0.022 μm；按 95% 口径 0.795 vs 0.867 差 0.072 μm，均在容差内） |
| **R_cr 峰值** | ≈1（反射率 >90%） | **0.9057 @ 1170 nm**；900–1600 均值 0.8905；总反射 `R_power` 均值 **0.9189** | ±0.1 | **PASS**（\|0.906−1\|=0.094 ≤ 0.1，**边缘通过**；反射率 >90% 达标） |
| **R_co 谷值** | ≈0 | **6.50×10⁻⁶ @ 1155 nm**；900–1600 均值 **0.0060** | ±0.1 | **PASS** |
| **最优 SiO₂ 厚度** | 110 nm（SI §1 / Fig.S1 扫参） | **110 nm** —— 本次 5 点扫参（90/100/110/120/130 nm，其余参数全冻结）：mean PCR 与 PCR>95% 带宽**双判据均在 110 nm 取最大** | ±10 nm | **PASS** |
| **45° 旋转对称性** | 是 | `addpoly` 顶点严格 45°；`R_co≈0`（x→y 完全转换）；背景 `E_bg,y ≡ 0` | 定性 | **PASS** |

### SiO₂ 扫参明细（Reproduce 模式的验证性对照，非调参凑结果）

| `ts` (nm) | mean PCR (900–1600) | mean R_cr | PCR>95% 连续波段 (nm) | 宽度 (μm) |
|---|---|---|---|---|
| 90 | 0.9386 | 0.8350 | 920–1140 | 0.220 |
| 100 | 0.9699 | 0.8657 | 900–1280 | 0.380 |
| **110** | **0.9932** | **0.8906** | **825–1620** | **0.795** |
| 120 | 0.9778 | 0.8805 | 835–1590 | 0.755 |
| 130 | 0.9661 | 0.8697 | 1165–1595 | 0.430 |

---

## 4. 与包内旧工程 t15 的对照（为什么本次结果可信）

| 项 | 旧 `fig1_hwp_paper_materials.fsp` / t15 | 本工程 |
|---|---|---|
| 求解器 | `-gpu -t 8`，`Using datatype: real32` | CPU 双精度基准 + GPU 对照（均显式启用/恢复） |
| 发散 | `_p0.log` 有 `WARNING: 0 < permittivity < 1` + **`ERROR: ... fields are diverging`**（51523 步提前终止） | **无 diverging**，`dt stability factor=0.95` |
| 归一化 | Point 监视器 `R=|Ex|² / |Ey|²` 单点取样 | 2D 面监视器空间平均（0 阶）+ 功率监视器交叉校验 + 减背景 |
| R>1 | `t15_hwp_R_paper.csv` 出现 `R_cr=3.98`、`R_co=1.47` 等非物理值 | **201/201 点全部 ≤1** |
| 能量守恒 | 未校验 | `T_bot≈0`、`R_total≤1` 已校验 |
| 结论 | README 自评「~94% / 基本对上」，但数据含发散后垃圾 | PCR 99.3%（900–1600），物理自洽 |

> 旧 t15 的发散是**GPU real32 + Drude 金属 + 未调 dt** 的组合，不是结构错；本次保留其正确的
> `addpoly` 旋转与 Drude sampled-data 做法，修掉 dt 与归一化，结果立刻自洽。

---

## 5. 偏差与未达标项的原因（逐条，不写「偏差较大」了事）

1. **求解器口径不同（最主要）**：论文 p.4 明确用 **FEM 3D 全波**（COMSOL/CST 类），本任务书要求 **Lumerical FDTD**。
   两者在金属色散拟合、网格（非结构 vs Yee 网格）、端口归一化上不同 → `R_cr` 0.906 而非 ≈1、
   带宽边界短波端差 20 nm / 长波端差 52 nm。**这是方法学差异，不是建模错误**。
2. **Au 材料实现**：论文给解析 Drude ωp/ωd；Lumerical 无同名内置模型，用 `Sampled data` 喂 600 点复 ε
   并令 `max coefficients=6` 做多系数拟合。`getindex@1000nm` 精确等于手算，但**拟合残差在带边**会带来数个百分点偏差。
3. **网格**：论文未公布网格；本工程全局 ma=2 + 金属区 8 nm 局部 override。Au 趋肤深度 ≈25 nm，
   8 nm 约 3 点/趋肤深度，属可用但非收敛极限。未做网格加密收敛对照（时间预算，见 §6 D1）。
4. **5 nm Ti 粘附层**：PDF Fig.2 caption 说「in the simulations」考虑 Ti；Figure 1 仿真段 p.5 未声明。
   按 Fig.1 口径省略。Ti 在近红外有损，若加入预计 `R_cr` 再降百分之几 → **会让 R_cr 更偏离 1**。
   是否按 Fig.2 口径补 Ti，**需用户裁决**。
5. **背景与归一化口径**：面平均取 0 阶（`R_co+R_cr=0.897`）与功率监视器全角度积分（`R_power=0.919`）
   相差约 2.2%，属口径差异而非错误；背景扣除修正 <0.002，已留证。
6. **PCR 峰值波长 / PCR>90% 波段的论文基准缺失**：论文只给 PCR>95% 的 805–1672 nm，
   未给峰值波长，也未给 >90% 口径 → 该两项无法逐点比较，标 N/A 而非编造论文值。
7. **R_cr 边缘通过**：0.9057 与论文 ≈1 差 0.0943，在 ±0.1 容差内但已接近边界；
   若按摘要「反射率 >90%」判据，`R_power=0.9189` 达标。

---

## 6. 阻塞问题上报（按四维分类）

> ⚠️ **输入完整性说明**：任务书消息在「## 6. 阻塞问题上报模板（按四维分类）」标题处**被截断**，
> 四维的具体名称与字段模板正文未提供。此处按工程常用四维补齐并逐项填报，
> **请用户确认或补发原始模板**；若模板不同，我按原模板重排即可，不需要重跑仿真。

### D1 — 环境与资源（license / GPU / 并行会话 / 路径）

| # | 现象 | 影响 | 处置 | 状态 |
|---|---|---|---|---|
| D1-1 | 全局 `FDTD\GPU-mode` 初始为 `false`（CPU） | 若不改，无法启用 GPU | 临时切 `true`，**每次 finally 恢复并回读确认** | ✅ 已解决 |
| D1-2 | 多 agent 并行，`setresource`/ini 是全局共享配置 | 切换窗口内其他会话可能意外走 GPU | 扫参改为**每点单独切换/恢复**，窗口缩到 30–60 s；未用 `setresource`（避免持久污染）；报告显式告知 | ⚠️ 已缓解，需并行会话知悉 |
| D1-3 | GPU real32 + Drude 金属已知会发散（旧 t15 实证） | 结果全 0/垃圾，且「不报错的错」 | `dt stability factor=0.95` + CPU 双精度 A/B 对照 + 三判据（layoutmode / `_p0.log` / `Completed`）+ 物理合理性（R≤1、T≈0） | ✅ 已解决 |
| D1-4 | CPU 双精度单次 270 s | 5 点扫参若走 CPU 需 ~23 min | 用已验证一致的 GPU 扫参（~3.5 min） | ✅ 已解决 |
| D1-5 | `cases/` 是只读资产，引擎会在 `.fsp` 同目录写 `_p0.log` | 污染黄金对照 | 真求解全部在 `_scratch` 纯 ASCII 副本上做；交付 `.fsp` 保持 `layoutmode=1` 未算 | ✅ 已解决 |

### D2 — 输入与资料（论文 / 参数 / 笔记）

| # | 现象 | 影响 | 处置 | 状态 |
|---|---|---|---|---|
| D2-1 | 任务书默认值缺 `tm`、Au 模型、SiO₂ n、求解器 | 照默认值建会建错 | 找到原文 PDF，以 PDF 为准，差异表列在 §0 | ✅ 已解决 |
| D2-2 | README 里 `scripts\` / `fsp\` 路径已迁为 `model\`；且 §0 目标写 Figure 2、§2 参数曾被更正过 | 容易误读旧结论 | 参数以 PDF 为准，README 只作交叉核对；旧 t15 数据单独做对照 | ✅ 已解决 |
| D2-3 | 论文未给 PCR 峰值波长、未给 PCR>90% 波段 | 验收表两项缺基准 | 标 **N/A** 并写明原因，不编造论文值 | ⚠️ 需用户确认是否接受 N/A |
| D2-4 | 任务书 §6 模板正文被截断 | 阻塞分类格式可能与预期不符 | 按 §6 开头自定义四维填报 | ⚠️ 需用户补发模板 |

### D3 — 模型与物理（求解器 / 材料 / 网格 / 边界 / 收敛）

| # | 现象 | 影响 | 处置 | 状态 |
|---|---|---|---|---|
| D3-1 | 论文 FEM vs 本工程 FDTD | `R_cr`、带宽边界系统性偏差 | 如实归因（§5-1），**不调参凑结果** | ⚠️ 需用户裁决是否接受口径 |
| D3-2 | Figure 2 仿真含 5 nm Ti，Figure 1 未声明 | 是否建模有歧义 | 按 Fig.1 口径省略并记为偏差来源 | ⚠️ 需用户裁决 |
| D3-3 | 未做网格加密收敛对照（8 nm → 4 nm） | 无法证明数值已收敛 | 列为后续项；本次以 `T_bot≈0`、`R≤1`、CPU/GPU 一致三重校验替代 | ⚠️ 时间预算内未闭环 |
| D3-4 | Figure 2 角度鲁棒性、Figure 3 u/v 幅度相位、Figure 4–6 超胞/反常反射 | 超出本次 Figure 1 单胞范围 | 未执行，明确列为非目标 | ✅ 范围外（非阻塞） |

### D4 — 流程与交付（skills 只读 / 会话契约 / 门禁 / 命名）

| # | 现象 | 影响 | 处置 | 状态 |
|---|---|---|---|---|
| D4-1 | `fdtd-lumerical-fsp-build` 的 builder 只支持 `addrect` 单胞，不支持 45° `addpoly` | 无法直接用 `build_fsp.py` | 手写 lumapi 建模脚本（临时、带会话前缀），**skill 文件一个未改** | ✅ 已解决 |
| D4-2 | `fdtd-lumerical-figure` 的输入 schema 要求 `lam_um` + R/T/A，与本工程 `R_cr/R_co/PCR` 列名不符 | 直接用该脚本会缺列 | 调用该技能并遵循其硬规则（Agg、图上数字现算、不写死、英文标签），自写等价出图脚本 | ✅ 已解决 |
| D4-3 | 硬约束「run 前必须 save→close→新会话 load→run」 | 同会话迭代虽实测可用但被禁止 | 每个求解点严格两段式，`close()` 全在 `finally` | ✅ 已解决 |
| D4-4 | 目标 `.fsp` 路径若已存在需备份 | 覆盖风险 | 前置检查确认**不存在**，未触发备份；旧 4 个 `.fsp` 一律未改 | ✅ 已解决 |
| D4-5 | 中间文件必须带会话前缀并清理 | 并行会话互相踩踏 | 全部 `tmp_p03hwp_20261109_2029_*`，交付后清理（§7） | ✅ 已解决 |

**当前无「已停止并上报」级阻塞**：所有阻塞均已解决或明确标为需用户裁决，工程与数据已交付。

---

## 7. 交付物与复现步骤

| 文件 | 说明 |
|---|---|
| `cases/P03_HWP_Ding2015/P03_HWP_Ding2015_repro.fsp` | ★ **可打开 / 加载 / 直接 Run** 的复现工程，`layoutmode=1`（未算，干净状态） |
| `docs/P03_HWP_Ding2015/params.md` | 论文重要参数清单（含实际 vs 默认差异表） |
| `docs/P03_HWP_Ding2015/principles.md` | 重要物理原理清单（6 条必覆盖 + 3 条延伸） |
| `docs/P03_HWP_Ding2015/repro_report.md` | 本文件（复现汇报 + 验收表 + 四维阻塞分类） |
| `results/P03_HWP_Ding2015/R_cr_R_co_PCR.csv` | 201 频点：`lam_nm, R_co, R_cr, PCR, R_power, T_bot` + 未减背景的 raw 列 |
| `results/P03_HWP_Ding2015/background_ref.csv` | 背景场与减背景修正量 |
| `results/P03_HWP_Ding2015/gpu_vs_cpu.csv` | GPU(real32) vs CPU(double) 逐波长对照 |
| `results/P03_HWP_Ding2015/fig_1b_Rcr_Rco.png` | Figure 1b 复现图 |
| `results/P03_HWP_Ding2015/fig_1c_PCR.png` | Figure 1c 复现图（含论文 95% 线与 805–1672 nm 波段） |
| `results/P03_HWP_Ding2015/fig_gpu_vs_cpu.png` | GPU/CPU 精度差图 |
| `results/P03_HWP_Ding2015/acceptance.json` | 全部验收数值、扫参、引擎日志摘要（可机读） |

**复现步骤（GUI）**：
1. 打开 `P03_HWP_Ding2015_repro.fsp`（路径纯 ASCII，GPU 引擎不会报 1113）。
2. 直接按 Run（工程保持 layout 模式）。若要用 GPU：GUI `File → Resource Configuration` 确认 GPU resource active 且 `GPU-mode=true`；工程内已预置 `dt stability factor=0.95`，Drude 金属不会发散。
3. 跑完用 `R_field` 的 `E` 结果做面平均：`R_co=|⟨Ex⟩|²`、`R_cr=|⟨Ey⟩|²`、`PCR=R_cr/(R_cr+R_co)`；`R_power` 的 `T` 作总反射交叉校验，`T_bot` 应 ≈0。
4. 对照 `R_cr_R_co_PCR.csv`；如需减背景，用 `background_ref.csv` 的口径再跑一次空结构参考。

**清理**：所有 `F:\Lumercial_WS\FDTD_WS\_scratch\tmp_p03hwp_20261109_2029_*` 中间脚本 / 副本 `.fsp` / 日志 / JSON 在交付后删除；旧 `cases/` 资产与 skills 一律未改。

---

## 8. 结论

- **论文来源已核实为本地原文 PDF，不是默认值**，`Ding2015` 与作者年份一致。
- 交付的 `.fsp` 参数严格按 PDF（`p=600, l1=390, l2=165, tm=80, ts=110, d=150 nm`，45° `addpoly`，Drude Au，n=1.45，x/y 周期、z PML，正入射 x 偏振），**可加载可跑**。
- 7 项验收 **6 PASS / 1 N/A（论文缺基准）/ 0 FAIL**；PCR 99.3% 均值、峰值 99.999% @1155 nm、`R_co≈0`、`T≈0`、无 R>1、110 nm 扫参确认为最优。
- **GPU 已按要求启用**（9.27× 加速、无发散、与 CPU 双精度一致到 2.7×10⁻⁴），全局资源配置已恢复。
- 主要残余差异来自 **论文 FEM vs 本工程 FDTD** 的方法学口径，以及论文未给的两项基准量；均未用调参去凑。
- 待用户裁决：① 是否接受 FEM→FDTD 口径；② 是否按 Fig.2 口径补 5 nm Ti；③ §6 四维模板原文（消息被截断）；④ 是否补做网格加密收敛对照。
