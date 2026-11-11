# P04_AnomalousReflection_047 — 论文重要参数清单

> **状态：已复现（方案 A）**。本文件是阶段 A 的参数提取结果，依据**目录内真实论文**，不是任务单预设论文。
> 交付工程：`results/P04_AnomalousReflection_047/P04_AnomalousReflection_047_repro.fsp`（已求解，`layoutmode = 0`）。
> "在本工程中的取值"一列**已按交付工程反解析与实测填实**；标注 `【实测】` 的行是本轮跑出来的，
> 其余为建模输入值（来源 `model/fig2c_and_3.fsp` 反解析 + 论文原文）。
> 复现过程、偏离与容差见 `repro_report.md`。

## 0. 论文身份（决定了后面所有参数）

| 项 | 值 |
|---|---|
| 标题 | *High-Efficiency Broadband Anomalous Reflection by Gradient Meta-Surfaces* |
| 作者 | Shulin Sun, Kuang-Yu Yang, Chih-Ming Wang, …, Lei Zhou, Din Ping Tsai |
| 期刊 | **Nano Lett. 2012, 12, 6223–6229**（DOI 10.1021/nl3032668） |
| 本地文件 | `cases/P04_AnomalousReflection_047/paper/7论文-High-Efficiency_Broadband_Anomalous_Reflection_by_Gradient_Meta-Surfaces.pdf`（7 页） |
| 参数笔记 | `paper/自测题_5问.md` —— 记录**黄老师指定的复现目标 = Figure 2c / Figure 3a** |
| 目录名 `047` 的含义 | **课程第七讲编号**，不是年份、不是论文编号（`README.md` §1「课程出处：`Classes/FDTD/课件/047第七讲 异常反射/`」） |
| 任务单预设论文 | Yu et al., *Science* **334**, 333 (2011) —— 在本文中是**参考文献 28**（p.6223 引言、p.6229 ref 28），是被对比、被改进的对象，**不是本 case 的论文** |
| 默认值是否启用 | **否**。任务单 §1「优先读取该目录下的论文 PDF / 参数笔记」→ 目录内有明确论文，默认值条件不成立 |

> ⚠️ 任务单 §3 阶段 A、§4.2、§5 列出的 V 形天线 / 8 μm / Γ=15 μm / −8° / +27° / −57° / R≈0.32
> 全部属于 **Yu et al. Science 2011**（即本文 ref 28），与 Sun 2012 的结构、波长、结论**互斥**。
> 详见 §2 与 `repro_report.md` §2-D1。

---

## 1. 主表：Sun et al. 2012 真实参数

单位换算已统一为 SI；括号内保留论文惯用 nm 便于对照。Lumerical 中一律写米（如 850 nm → `850e-9`）。

| 参数名 | 符号 | 论文值 | 单位 | 在本工程中的取值 | 来源（页码/图号） |
|---|---|---|---|---|---|
| 工作波长 | λ | 850 | nm (`850e-9` m) | `850e-9`（源 `wavelength start/stop = 8.5e-7`） | p.6224 正文；p.6225 Fig.2 caption；Fig.1b caption |
| 工作带宽 | — | 750–900（正文另述 700–900） | nm | 单频点仿真 `frequency points = 1`；宽带有 `fig5e.fsp` | p.6223 Abstract；p.6227 Fig.5 相关正文 |
| 超胞长度（x 向总周期） | Lx | 1200 | nm (`1.2e-6` m) | 10 × `L1` = 1200 nm；`structure group` 脚本 `Lx = L1*num` | **p.6224 Fig.1a caption**；p.6225 正文 |
| 单元周期（x 向） | L1 | 120 | nm | `120e-9`（rod 中心 x = 0,120,240,…,1080 nm） | p.6224 Fig.1a caption；反解析实测 |
| y 向周期 | Ly | 300 | nm | FDTD `y span = 3e-7`；`y min/max bc = Periodic` | p.6224 Fig.1a caption；反解析实测 |
| 超胞内 Au 纳米棒长度 | L | 40, 40, 106, 106, 128, 128, 150, 150, 260, 260 | nm | 同左，`rod1…rod10` 的 `y span` 逐根一致 | **p.6224 Fig.1a caption**；p.6225 正文 |
| Au 棒宽度 | W | 90 | nm | `x span = 9e-8`（所有 rod 一致） | p.6224 Fig.1a caption |
| Au 棒厚度 | d1 | 30 | nm | `z span = 3e-8`，z ∈ [−320, −290] nm | p.6224 Fig.1a caption |
| MgF₂ 间隔层厚度 | d2 | 50 | nm | `z span = 5e-8`，z ∈ [−370, −320] nm | p.6224 正文 + Fig.1a caption |
| MgF₂ 介电常数 / 折射率 | ε / n | ε = 1.892 → n = 1.3755 | — | `<Object defined dielectric>`，`index = 1.3755` | p.6224 正文；反解析实测 |
| Au 地平面厚度 | d3 | 130 | nm | `z span = 1.3e-7`，z ∈ [−500, −370] nm | p.6224 正文 + Fig.1a caption |
| 衬底 | — | **玻璃衬底**（glass substrate），非硅 | — | 未显式建模（地平面下方不透明，光学上不影响） | **p.6225 制备方法段** |
| Au 光学模型 | — | Drude 模型（Shalaev et al., Opt. Lett. 2005 = ref 38） | — | **`Au (Gold) - Johnson and Christy`，Sampled 3D data** ← 口径差异 | p.6226「inaccuracy of the Au Drude model」；反解析 `materials` 字段 |
| 相位梯度 | ξ = ∂Φy/∂x = 2π/Lx | 0.708 k₀ ≈ 0.71 k₀ | rad/m | `2π/1.2e-6 = 5.236e6` rad/m；由 10 根棒的长度序列实现 | **p.6224 Fig.1c caption（ξ = 0.708k₀）**；p.6225 式(1) 附近 |
| 每单元相位步进 | ΔΦ | 2π/10 = 0.2π（**10 单元，不是 8 个**） | rad | 由 L 序列离散采样（成对重复以平滑梯度） | p.6224 Fig.1a/1c；p.6225 正文 |
| 入射偏振 | E ∥ ŷ | y 偏振（`polarization angle = 90°`） | — | `PlaneSource`，`polarization angle = 90`，`direction = Backward` | p.6225 正文；p.6224 Fig.1b caption；反解析实测 |
| 入射角 | θi | 0°, 5°, 10°, 15°, 20° | ° | 本轮跑 **0°, ±10°, ±20°**（论文口径）；Lumerical 的 `angle theta` 与论文 θi **符号相反**，映射关系实测确认：`θi(论文) = −angle theta` | p.6226 Fig.2 caption / 正文 |
| 正入射反常反射角 | θr | sin⁻¹(0.71) ≈ 45°（实测峰 **≈45.5°**） | ° | **【实测】45.07°**（全角复场 DFT，0.025° 网格）／45.11°（`czt`，35–89°，300 点）／理论 45.099° | p.6225 式(2)；**p.6226 Fig.2c / 正文** |
| 临界角 | θic | sin⁻¹(1 − ξ/k₀) ≈ **17°** | ° | **【实测】16.96°（解析）**；θi = +20° 时 35–89° 窗口内无峰（窗口最大值仅为基准峰的 4.7%，且位于 89° 边界）→ 与论文"峰消失"一致 | p.6225 式(2) 后；p.6226 正文 |
| 正入射转换效率 | η | **> 80%**（其余 ~20% 被吸收） | — | **【实测】77.4%**（全反射能量，平整镜面标定）；主瓣（±4°）68.1%；吸收 22.6%。Au 口径 JC vs 论文 Drude，详见 `repro_report.md` §6 | p.6223 Abstract；p.6226 正文 |
| 参考信号 | P₀ | 130 nm 平整 Au 膜在 θi = 20° 的反射 | — | **【本轮已建】** 关闭 `structure group` 的同堆栈工程 `_scratch/tmp_p04repro_run/run_flat_ref.fsp`，R_flat = 0.978（TMM，Au JC @850 nm） | p.6226 正文 |
| 可测角范围 | — | θr + θi > 35°（光纤发射/接收几何限制） | ° | 课程口径 `czt` 扫 `linspace(35, 89, 300)`；本轮另做 **−89…89° 全角复场 DFT** 以覆盖论文测不到的镜面区 | p.6226 正文；`model/draw_fig2c.lsf` |
| x 边界条件 | — | 有限超胞阵列（20 个超胞），x 两端 PML | — | `x min/max bc = PML` | 反解析实测（论文未明写） |
| y 边界条件 | — | 周期 | — | `y min/max bc = Periodic` | 反解析实测 |
| z 边界条件 | — | PML | — | `z min/max bc = PML` | 反解析实测 |
| 网格精度 | — | 论文未给 | — | `mesh accuracy = 8`；另有 z ∈ [−500, −200] nm 的 mesh override | 反解析实测（**非论文值**） |
| dt 稳定性因子 | — | 论文未给 | — | **交付工程用 `0.95`**（原工程 `0.99`）。理由：GPU 走 `real32`，色散金属（`0 < Re ε < 1`）在 0.99 下触发 `fields are diverging`；0.95 下 7 轮全部收敛、无 `0 < permittivity < 1` 警告 | `docs/constitution/field-manual.md` §6.3 实测；本轮 `_p0.log` |
| 仿真时长 / 收敛 | — | 论文未给 | — | `simulation time = 2e-13` s，`auto shutoff min = 1e-5`；**实测 7 轮全部 `Early termination … autoshutoff criteria are satisfied`**，末值 8.4e-6 ~ 9.9e-6 | 反解析实测；本轮 `_p0.log` |
| 仿真方法 | — | **FDTD**（论文用 CONCERTO 7.0，ref 36），实验 + 仿真互证 | — | Ansys Lumerical FDTD v251，**`fdtd-engine.exe -gpu -t 8`（real32）**；近远场用 `czt` 角谱 + 独立 Python DFT 双路对照 | p.6224/6225 正文；`model/draw_fig2c.lsf`；本轮日志 |
| 角度提取方式 | — | 远场散射强度 P(θr, λ)/P₀ | — | `R` 监视器（Linear X，z = 100 nm）→ `czt(Ey, x, k0·sinθr)` | p.6226 Fig.2 正文；`model/draw_fig2c.lsf` |

---

## 2. 任务单点名参数：逐项归属核对

> 任务单 §3 阶段 A / §4.1 要求"至少覆盖"以下条目。经核对，前 8 项**不属于本目录论文**。
> 这里逐项回应，不用"N/A"一笔带过，也不编造论文值。

| 任务单要求的参数 | 是否属于 Sun 2012 | 归属与说明 |
|---|---|---|
| V 形天线臂长 h | ❌ 不存在 | **Yu et al. Science 2011** 的结构（本文 p.6223 引言、ref 28）。Sun 2012 用「Au 纳米棒 + MgF₂ + 连续 Au 地平面」MIM 结构，无 V 形、无臂长。本目录本地 PDF 只有 7 页正文、**无 Supporting Information**，未归档 Yu 2011 原文，故不填 h 数值 |
| V 形天线夹角 Δ | ❌ 不存在 | 同上；V 形天线靠 (h, Δ) 双参数扫相位，Sun 2012 只靠棒长 L 单参数 |
| 八个天线的相位梯度 dΦ/dx | ❌ 数量不符 | Sun 2012 是 **10 个**单元 / 超胞（成对重复），ΔΦ = 2π/10 = 0.2π；Yu 2011 才是 8 个天线、步进 π/4。本工程 ξ = 2π/Lx ≈ 0.708 k₀ |
| 单元胞周期 Γ | ❌ 符号不同 | Sun 2012 用 `Lx = 1200 nm`（超胞）与 `L1 = 120 nm`（单元）；Yu 2011 的 Γ = 15 μm 是另一套定义。二者不可互换 |
| 天线阵列周期（横向 1.5 μm） | ❌ 不存在 | 本目录论文的横向周期是 **Ly = 300 nm**、单元 L1 = 120 nm；1.5 μm 未出现在 p.6223–6229 任何位置 |
| 金厚度 | ✅ 有，但含义不同 | Sun 2012 有两层 Au：棒 `d1 = 30 nm`、地平面 `d3 = 130 nm`；另有 5 nm 溅射粘附层 + 125 nm 蒸发层（p.6225 制备段）。不是单一"金厚度" |
| 硅衬底折射率 | ❌ 不存在 | 论文用**玻璃衬底**（p.6225），且 130 nm Au 地平面不透明，衬底光学上不参与。任务单的 Si 衬底属于 Yu 2011（8 μm 中红外常用 Si） |
| 工作波长 8 μm | ❌ 数值不符 | 本论文 λ = **850 nm**（近红外）；8 μm 是 Yu 2011 的工作波长，在本文 p.6223 引言里作为**被引用的前人工作**出现 |
| 入射偏振 | ✅ | E ∥ ŷ（y 偏振，`polarization angle = 90°`）。注意任务单说"产生交叉偏振散射"——**Sun 2012 恰好相反**：论文明确强调异常反射波**保持同偏振**（p.6223 Abstract、p.6225 正文），交叉偏振是 V 形天线的缺点 |
| 边界条件 | ✅ | x PML / y Periodic / z PML（反解析实测）。任务单要求"x、y 周期，z PML"——**与已有正确工程冲突**：x 必须是 PML，因为要模拟 20 个超胞的有限阵列并做 czt 远场角扫描；改成周期会只剩单个衍射级 |
| 网格精度 | ✅（非论文值） | `mesh accuracy = 8` + 金属区 mesh override；论文未给，属课程工程经验值 |
| 仿真方法 | ✅ | FDTD（论文 CONCERTO 7.0 / 本机 Lumerical v251）+ 实验对照；角度谱用 `czt` 而非 farfield 投影 |

### 测量角度范围（任务单 §3 阶段 A 单列）

- 论文实验：**θr + θi > 35°**（p.6226，光纤发射/接收头几何遮挡），θi ∈ {0°, 5°, 10°, 15°, 20°}。
- 课程脚本 `draw_fig2c.lsf`：`linspace(35, 89, 300)` 度；`draw_fig4.lsf`：`linspace(-85, 85, 300)` 度；`draw_fig5e.lsf`：35–89° × 波长扫描。
- 论文 Fig.3a 的"负反射"区：−45° < θi < 0°（p.6226）。

---

## 3. 待用户确认后锁定的建模基线

若要建 `.fsp`，建议直接以 `model/fig2c_and_3.fsp` 为黄金对照（它就是黄老师要的 Fig.2c / Fig.3a 工程），
复制到 `_scratch/` 纯 ASCII 路径后重跑，**不要**按任务单的 V 形天线参数从零建模。冻结量清单：

1. `L_list = [40,40,106,106,128,128,150,150,260,260] * 1e-9`（m）
2. `L1 = 120e-9`, `Lx = 1.2e-6`, `Ly = 300e-9`, `W = 90e-9`, `d1 = 30e-9`, `d2 = 50e-9`, `d3 = 130e-9`
3. `λ = 850e-9`，y 偏振，正入射（Backward, z 轴）
4. x/y/z 边界：PML / Periodic / PML；`mesh accuracy = 8`
5. `R` 监视器（Linear X, z = 100 nm）+ `czt` 角谱 → P(θr)/P₀
6. Au 材料口径需裁决：课程用 `Au (Gold) - Johnson and Christy`（Sampled 3D），论文用 Drude (Shalaev 2005) —— 两者在 850 nm 的 n,k 不同，会直接影响 45.5° 峰位与 >80% 效率
