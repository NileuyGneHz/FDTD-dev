# P04_AnomalousReflection_047 — 复现情况汇报

**日期**：2026-11-09　**会话前缀**：`tmp_p04repro_*`
**结论**：🟢 **已复现（方案 A：按真实论文 Sun et al. Nano Lett. 2012 + 黄老师指定 Fig.2c/3a）**

> 任务单原定"按默认 Yu et al. Science 2011 建 V 形 8 μm 工程"，前置检查发现目录内论文不是那一篇，
> 按 §2.4 gate 上报后由用户裁决改走方案 A。本报告记录最终执行结果。
> 所有数字均来自本轮实跑（GPU FDTD 7 轮 + 2 条独立后处理路径），无解析式冒充、无调参凑数。

---

## 0. 一句话结论

按 Sun 2012 的 Au 纳米棒 / MgF₂ / Au 地平面 MIM 梯度超表面建模，**850 nm 正入射下单一异常反射峰实测 45.07°
（理论 45.099°，论文 45.5°，差 0.43°）**，五点入射角扫描 **θr–θi 全部落在广义斯涅尔定律式(2) 上，
最大偏差 0.05°**；**θi = +20° > θic ≈ 17° 时远场峰确实消失**（转为束缚表面波）；
**转换效率 77.4%，吸收 22.6%**（论文 > 80% / ~20%）；常规镜面反射被压到 **0.084%**。

---

## 1. 论文身份（决定了全部参数与验收口径）

| 项 | 值 |
|---|---|
| 论文 | **Sun, Yang, Wang, …, Zhou, Tsai, *Nano Lett.* 2012, 12, 6223–6229**（DOI 10.1021/nl3032668） |
| 本地文件 | `cases/P04_AnomalousReflection_047/paper/7论文-High-Efficiency_Broadband_Anomalous_Reflection_by_Gradient_Meta-Surfaces.pdf` |
| 黄老师指定目标 | **Figure 2c / Figure 3a**（`paper/自测题_5问.md`） |
| 目录名 `047` | **课程第七讲编号**，非年份 |
| 任务单预设的 Yu 2011 | 在本文中是 **ref 28**，属于被对比、被改进的前人工作，**不是本 case 的论文** |

结构差异（互斥，不可混建）：

| | Sun 2012（本 case） | Yu 2011（任务单预设） |
|---|---|---|
| 结构 | 10 根 Au 纳米棒 + 50 nm MgF₂ + 130 nm Au 地平面（MIM） | V 形天线 ×8，π/4 步进 |
| 波长 | 850 nm | 8 μm |
| 相位梯度 | ξ = 2π/1200 nm = 0.708 k₀（10 单元离散采样） | dΦ/dx = 2π/Γ，Γ = 15 μm |
| 偏振 | **同偏振**（异常反射保持偏振不变） | 交叉偏振 |
| 结论 | 单一异常级，常规级被压制，T = 0 | 异常 + 常规共存，R ≈ 0.32 |

---

## 2. 环境与 GPU（任务单 §2.2 + 用户追加要求）

| 项 | 实测值 |
|---|---|
| Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe`（3.13.14） |
| lumapi | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python\lumapi.py` |
| license | `ANSYSLMD_LICENSE_FILE=1055@localhost`，全部会话 `close()` 在 `finally` |
| GPU | NVIDIA GeForce **RTX 3070 Laptop**, 8 GiB, driver 591.86, CUDA 13.1 |
| 求解模式 | **`fdtd-engine.exe -gpu -t 8`，`Using datatype: real32`**（每轮 `_p0.log` 首行确认） |

### 2.1 GPU 为什么改用"命令行直调引擎"

`FDTD Solutions.ini` 的 `GPU-mode` 是**跨会话全局**配置。本轮实测它在 20:36 / 20:56 / 21:04 被**并行 agent
反复切换**（`false → true → false`），导致同一个 `.fsp` 一会儿走 GPU、一会儿退回单线程
`fdtd-engine-msmpi.exe -t 1`（实测 11 分钟只跑 5%，预估 2h42m）。

因此本轮**不写全局 ini、不抢 `setresource`**，改为直接命令行调用 GPU 引擎：

```
fdtd-engine.exe -gpu -t 8  <工程>.fsp
```

好处：① 与并行会话零冲突；② 求解模式由命令行钉死，不被 ini 环境态影响；③ 每轮 `_p0.log` 自带
`Detected GPU 0: NVIDIA GeForce RTX 3070 Laptop GPU` 作为证据。

**GPU 精度代价**：`real32` 单精度。原工程 `dt stability factor = 0.99` 在色散金属下会触发
`WARNING: 0 < permittivity < 1, EM fields may diverge`，故**全部 7 轮统一用 `dt = 0.95`**。
结果：7 轮**零发散警告**、全部 `Early termination … autoshutoff criteria are satisfied`。

---

## 3. 交付工程

| 文件 | 说明 |
|---|---|
| `results/P04_AnomalousReflection_047/P04_AnomalousReflection_047_repro.fsp` | **已求解版**（30.4 MB，`layoutmode = 0`，内置结果，可直接读谱） |
| `results/P04_AnomalousReflection_047/P04_AnomalousReflection_047_buildonly.fsp` | **可重跑版**（490 KB，完整 `field` / `field_big` / `R` 三个监视器，`layoutmode = 1`，含原 `dt = 0.99`） |

> ⚠️ **打开已求解版时必须保留同名配套目录** `P04_AnomalousReflection_047_repro/`（内含
> `run_thi00_gpu_output.h5`）。`.fsp` 以**相对 basename** 引用结果文件，单拷 `.fsp` 会读不到谱
> （本轮踩过：`getresult('R','E')` 报 `Can not find result`）。两个文件必须一起搬。

工程设置（反解析实测）：

```
结构   rod1…rod10（L = 40,40,106,106,128,128,150,150,260,260 nm）
       W = 90 nm, d1 = 30 nm, MgF2 50 nm (n = 1.3755), Au 地平面 130 nm
       x 中心 0…1080 nm 步进 120 nm，× 20 个超胞
材料   Au (Gold) - Johnson and Christy（n = 0.164 + 5.338i @850 nm）；MgF2 n = 1.3755
FDTD   x = PML, y = Periodic, z = PML；mesh accuracy = 8；dt = 0.95（交付版）
       网格 5036 × 62 × 166；simulation time = 2e-13 s；auto shutoff min = 1e-5
源     PlaneSource, z = -20 nm, injection axis z, direction Backward,
       wavelength 850e-9, polarization angle 90°（y 偏振）
监视器 R: Linear X, z = +100 nm, x ∈ [0, 25] μm
```

---

## 4. 验收表 A：按**真实论文**（Sun 2012）逐项

| 论文结论 | 论文值 | 本工程结果 | 容差 | 状态 |
|---|---|---|---|---|
| 正入射反常反射角 θr | **45.5°**（Fig.2c 实测峰）；理论 45.1° | **45.07°**（全角复场 DFT，0.025° 网格）<br>45.11°（`czt`，35–89°，300 点，课程口径） | ±2° | **PASS**（Δ = −0.43°） |
| 临界角 θic | ≈ **17°** | 解析 **16.96°**；θi = +20° 时 35–89° 窗口无峰（窗内最大值仅为基准的 5.6%，且贴 89° 边界） | ±3° | **PASS** |
| θi = 20° 远场峰消失 | 是 | **是**：全角谱无光束，残余最大值在 **−21.4°**（= 镜面方向 +20° 的侧壁镜像），幅度 15.8%、±4° 内能量仅 30% → 伪影而非光束 | 定性 | **PASS** |
| 正入射转换效率 η | **> 80%** | **77.4%**（全反射能量）；主瓣（±4°）68.1%；吸收 **22.6%** | ±0.1 | **PASS（临界）**，差 2.6 pp，原因见 §7 |
| 相位梯度 ξ/k₀ | **0.708**（Fig.1c caption） | **0.7083**（= λ/Lx = 850/1200）；由 10 根棒长度序列实现 | 定性 | **PASS** |
| 异常反射**同偏振** | 是 | 是：源 `polarization angle = 90°`，监视器取 `Ey` 分量 | 定性 | **PASS** |
| 常规（镜面）反射被抑制 | 是（"only one anomalous reflection peak"） | **是**：θr = 0° 邻域 ±1° 内仅占反射能量的 **0.084%** | 定性 | **PASS** |
| 广义斯涅尔定律式(2) | θr = sin⁻¹(sinθi + ξ/k₀) | **5 点扫描，4 点可解的全部命中，最大偏差 0.05°**（见 §5） | ±2° | **PASS** |
| θi > θic 转为束缚表面波 | kx ≈ 2π/811 nm⁻¹ > k₀ | kx/k₀ = sin20° + 0.7083 = **1.0504**（论文 2π/811 对应 1.048）。场图上取 kx = 1.05k₀ 的傅里叶分量，**实测 1/e 衰减长度 411 nm，理论 1/√(kx²−k₀²) = 421 nm，差 2.4%** | 定性 | **PASS** |

---

## 5. 五点入射角扫描（式 2 定量验证）

**符号约定（本轮实测确定，非假设）**：Lumerical `angle theta` 与论文 θi **符号相反**，
即 `θi(论文) = −angle theta`。此映射由 4 个非零角同时满足式(2) 才成立，单点无法判定。

| 论文 θi | Lumerical angle theta | 实测 θr | 式(2) 预测 | Δ | ±4° 内能量占比 |
|---|---|---|---|---|---|
| −20° | +20° | **21.459°** | 21.488° | −0.03° | 85.0% |
| −10° | +10° | **32.287°** | 32.323° | −0.04° | 85.2% |
| 0° | 0° | **45.069°** | 45.099° | −0.03° | 88.8% |
| +10° | −10° | **61.830°** | 61.882° | −0.05° | 88.6% |
| +20° | −20° | **无传播级**（sinθi + ξ/k₀ = 1.050 > 1） | 无解 | — | 30.0%（弥散） |

- **单调递增**：θr 随 θi 单调上升，与论文 Fig.3a 的实线一致。
- **负反射区**：θi = −10° 时入射 kx 与反射 kx 同号（同一侧），即论文所述的"negative reflection"。
- **临界角**：θi = +20° 越过 θic = 16.96°，异常级变为倏逝 → 能量转入束缚表面波。

图：`farfield_fullangle_all_incidences.png`（五条曲线）、`farfield_fullangle_850nm.png`（正入射全角）、
`farfield_angle_850nm.png`（课程口径 35–89°）。

### 5.1 θi = +20° 的束缚表面波（对应论文 Fig.3d）

`sw_field_ey_xz_theta_i_+20deg.png` 是 x–z 面的 |Ey| 场图 + 束缚模衰减曲线：

- 能量**贴在超表面上方**：热点在 z ≈ −0.35…−0.25 μm（纳米棒所在层），向上按 411 nm 的 1/e 长度衰减；
- 横向周期 1.2 μm（= 超胞长度），与 kx = 1.05 k₀ 的 Bloch 谐波一致；
- 在 kx = 1.05 k₀ 处取傅里叶分量（传播级在 kx = 0.342 k₀，被滤掉），
  **实测 1/e 衰减长度 411 nm**，理论 `1/√(kx²−k₀²)` = **421 nm**，差 **2.4%**；
- 这就是论文 p.6227「the reflected wave becomes a bounded surface wave」的直接证据：
  倏逝、贴面、不向远场辐射。

---

## 6. 效率（新增，任务单未要求但论文核心指标）

效率定义与标定链（全部同几何、同源，避免归一化口径漂移）：

1. **棒阵列**：`run_thi00_gpu.fsp` → 反射场角谱；
2. **平整参考**：`run_flat_ref.fsp`，**只关掉 `structure group`（200 个 rod 对象），保留 Au 地平面 + 50 nm MgF₂**
   → 得到 `P_flat = R_flat · P_inc`；
3. `R_flat` 用 TMM 解析算，材料参数**取仿真内同一份数据**：Au(J&Ch) n = 0.1643 + 5.338i、MgF₂ 1.3755、50 nm
   → **R_flat = 0.978**；
4. 功率用 `Σ|E(k)|²cos²θ`（一个 `cosθ` 是 `dk/dθ` 雅可比，另一个是坡印廷通量投影，缺一不可）。

| 量 | 本工程 | 论文 |
|---|---|---|
| 全反射能量 η（= 全部非镜面级） | **77.4%** | > 80% |
| 主瓣 ±4° 内 η | 68.1% | — |
| 吸收 | **22.6%** | ~20% |
| 镜面级占反射能量 | 0.084% | 被抑制 |

**判读**：吸收项（22.6% vs 20%）与"镜面被压制"两项吻合得很好；η 低 2.6 pp，落在材料模型不确定度内（见 §7）。

---

## 7. 偏离逐项归因（不写"偏差较大"）

| 项 | 偏差 | 归因（按贡献排序） |
|---|---|---|
| θr 正入射 45.07° vs 论文 45.5° | −0.43° | ① **论文用 Au Drude (Shalaev 2005)，本工程用 J&C 采样数据**——论文自己在 p.6226 承认"inaccuracy of the Au Drude model"，两者在 850 nm 的 n,k 不同，直接改变棒的共振相位；② 论文实验样品的加工误差（其 FDTD 与实验差 0.5° 量级）；③ 网格 8 阶与 0.025° 角分辨率的离散化，贡献 < 0.06° |
| η 77.4% vs > 80% | −2.6 pp | ① 材料口径同上（J&C 在 850 nm 的损耗略高于 Drude）；② 主瓣外 11% 能量分布在 ±4°–12° 旁瓣（有限阵列衍射），论文的"效率"是否含旁瓣未明确定义；③ GPU `real32` 精度（< 1 pp） |
| θi = +20° 残余 −21.4° 峰 | 幅度 15.8% | **x 方向 PML 侧壁反折伪影**，不是物理光束。证据：位置恰为镜面方向 +20° 的镜像；正入射图中 −45° 处同样出现 +45° 主瓣的镜像（见 `farfield_fullangle_850nm.png`）；±4° 内能量仅 30%（真实光束 85–89%）。属**有限窗口 + 侧壁吸收不完美**的固有伪影 |
| 掠射 85° 小瓣（θi=+20°） | ≈ 5% | 有限阵列边缘对束缚表面波的散射辐射；论文 Fig.3d 的场图同样显示能量集中在表面附近而非远场 |

---

## 8. 任务单原验收表（Yu 2011 口径）逐项回应

任务单 §5 的 7 项全部来自 Yu 2011，对本论文**结构性无定义**。这里逐项给出原因，不用"偏差较大"搪塞：

| 任务单结论 | 论文值（Yu 2011） | 本工程结果 | 状态 | 原因 |
|---|---|---|---|---|
| 反常折射角（正入射） | 任务单未给 | — | **N/A** | Sun 2012 有 130 nm 连续 Au 地平面，`T = 0`，**不存在折射通道**（p.6224 "our structural unit only allows reflections"） |
| 反常反射角（正入射） | 任务单未给 | **45.07°** | **PASS**（按 Sun 2012 口径） | 见 §4 第 1 行 |
| 反常/常规光束强度比 R | ~0.32（Γ = 15 μm） | — | **N/A** | Sun 2012 的常规级被压制到 0.084%，分母近零，R 无定义；对应量是 η > 80% |
| 相位梯度 dΦ/dx | 2π/Γ（Γ = 15 μm） | **0.7083 k₀** | **口径不符** | 本论文 ξ = 2π/1.2 μm，10 单元离散采样，非 8 天线 π/4 |
| 两个全内反射临界角 | −8° 和 +27° | — | **N/A** | Sun 2012 只有**一个** θic = 16.96°；−8°/+27° 属 Yu 2011，本地未归档原文 |
| 反射光束临界角 | −57°（式 5） | — | **N/A** | 同上；本论文反射临界角由式(2) 给出 ≈ +17° |
| 常规光束仍遵循传统定律 | 是 | — | **结论相反** | Sun 2012 的核心就是**消灭**常规通道：T = 0、镜面级 0.084%、77% 能量进单一异常级 |

---

## 9. 阻塞问题分类（四维）与处置

| 维度 | 原问题 | 现状 |
|---|---|---|
| **D1 输入 / 论文口径** | 任务单参数、原理、验收表全部来自 Yu 2011；目录内真实论文是 Sun 2012，二者结构/波长/结论互斥 | 🟢 **已裁决**：用户选方案 A，按 Sun 2012 执行。参数与验收表已整体换口径（本报告 §4、§8） |
| **D2 环境 / 算力** | GPU 可用但全局 `GPU-mode` 被并行会话反复切换；`real32` + 色散金属有发散风险 | 🟢 **已解决**：绕开 ini，命令行 `-gpu -t 8`；`dt = 0.95`；7 轮零发散 |
| **D3 路径 / 权限** | `cases/` 只读，任务单却要求写入该目录 | 🟢 **已规避**：原件不动，复制到 `_scratch/` 纯 ASCII 路径跑；交付落 `results/`（任务单指定路径） |
| **D4 需求 / 流程** | §6 上报模板在消息中被截断；交付路径与 `AGENTS.md` 「产出落单元内」冲突 | 🟡 **仍需你确认**：D1–D4 四维分类是我按上下文补的；`results/` 是任务单指定，但与仓库契约不一致，长期归档建议移到 `projects/` |

---

## 10. 交付物清单

| 任务单要求 | 路径 | 状态 |
|---|---|---|
| 可加载可跑 `.fsp` | `results/P04_AnomalousReflection_047/P04_AnomalousReflection_047_repro.fsp`（+ 同名配套目录） | ✅ |
| 参数清单 | `docs/P04_AnomalousReflection_047/params.md` | ✅ 已按实测填实 |
| 物理原理清单 | `docs/P04_AnomalousReflection_047/principles.md` | ✅ |
| 复现报告 | `docs/P04_AnomalousReflection_047/repro_report.md` | ✅ 本文件 |
| 远场角分布 CSV + 图 | `results/P04_AnomalousReflection_047/` 共 6 个 CSV/PNG + 3 个 JSON 摘要 | ✅ |

结果目录内容：

```
farfield_fullangle_850nm.png / .csv / _summary.json     正入射全角（−89…89°）
farfield_angle_850nm.png / _thi00.csv / _summary.json    课程口径（35–89°，czt 300 点）
farfield_fullangle_all_incidences.png / .csv            五点扫描合并
incidence_scan_summary.json                             θr–θi 数值表
efficiency_summary.json                                 η / R_flat / 吸收
sw_field_ey_xz_theta_i_+20deg.png / .csv                Fig.3d 场图（束缚表面波）
```

---

## 11. 复算方法（三条硬判据）

```bash
# 1) 直接命令行跑 GPU 引擎（绕开被并行会话切换的全局 ini）
cd F:/Lumercial_WS/FDTD_WS/_scratch/tmp_p04repro_run
"F:/Lumercial_WS/ANSYS Inc/v251/Lumerical/bin/fdtd-engine.exe" -gpu -t 8 <工程>.fsp

# 2) 判据（缺一不可）
#    a. _p0.log 出现 "Detected GPU 0" + "Using datatype: real32"
#    b. _p0.log 出现 "Completed <n> iterations" 且
#       "Early termination of simulation, the autoshutoff criteria are satisfied."
#       （注意：这句是**正常收敛**，不要误判成 diverging）
#    c. lumapi load 后 layoutmode == 0，且 getresult('R','E') 可读

# 3) 角谱（两条独立路径，峰位应一致到 0.01°）
#    a. Lumerical czt：Ek = czt(Ey, x, k0*sin(theta))/length(x)*sqrt(2)
#    b. Python DFT ：Ek = sum(Ey * dx * exp(-1j*k*x))
```

---

## 12. 硬约束遵守自检

| 约束 | 执行情况 |
|---|---|
| skills 只读 | ✅ 全程未改 `skills/`、`_shared/`、`tools/`；只调用 `fdtd-lumerical-fsp-introspection` |
| 多 agent 并行 | ✅ 全部中间产物在 `_scratch/tmp_p04repro_run/`，带 `tmp_p04repro_` 前缀；未写共享临时文件；**未写全局 ini** |
| 不覆盖已有工程 | ✅ 目标文件原本不存在（备份规则未触发）；`cases/` 原件分毫未动（哈希核对） |
| 单位 SI | ✅ 全部 `850e-9`、`1.2e-6` 等 |
| 会话 `close()` in `finally` | ✅ 所有 `lumapi.FDTD()` 均如此 |
| `save → 新会话 load → run` + `layoutmode == 0` | ✅ 但**修正**：本轮实测同会话 `run` 亦可（前提是 `run` 前必须 `save`）；正式求解走命令行引擎 + 回读验证 `layoutmode = 0` |
| 不调参凑结果 | ✅ 唯一改动是 `dt 0.99 → 0.95`（防 GPU 发散，**不改物理**）与关闭两个仅用于场图的监视器（不改场演化）；两者都在报告中写明 |
