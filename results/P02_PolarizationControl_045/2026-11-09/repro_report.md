# P02 复现情况汇报 — Kruk et al. 2016 宽带全介质偏振控制器

**日期**：2026-11-09 · **执行**：WorkBuddy（单 agent 会话，会话前缀 `tmp_p02rep_`） · **引擎**：Ansys Lumerical FDTD 2025 R1 (v251) + GPU

---

## 0. 论文身份（首段声明）

**实际论文为 Kruk, Hopkins, Kravchenko, Miroshnichenko, Neshev, Kivshar,
"Broadband highly efficient dielectric metadevices for polarization control",
APL Photonics 1, 030801 (2016), DOI 10.1063/1.4948946 —— 与任务书给定的默认论文一致。**

- 本地 `cases/metasurface/P02_PolarizationControl_045/paper/` 下确有该 PDF（16 页，含补充材料 S1–S5），已用 PyMuPDF 提取正文逐条核对参数（HWP/QWP 尺寸在 p.5 = 030801-5，Fig.2 尺寸在 p.4，公式在 p.3，Palik 材料说明在补充材料 p.13）。
- 因此**不触发**「论文来源为默认值，待用户确认」；也**不是** Chen 2012《Dual-polarity plasmonic metalens》，故不触发「实际论文为 X，与默认不同」。
- 但发现论文内部**两组尺寸自相矛盾**（Fig.2 用 285/450/860，Fig.3 用 280/430/850），这项已在 §5 作为阻塞项 `B-1` 上报，并在 §4 做了定量口径诊断。

---

## 1. 交付物与工程可用性

### 1.1 工程文件

| 文件 | 内容 | 状态 |
|---|---|---|
| `cases/metasurface/P02_PolarizationControl_045/P02_PolarizationControl_045_repro.fsp` | **HWP 主复现工程**（a=280, b=430, c=850, D=750 nm） | 481,920 B，`layoutmode=1.0`，**可直接打开/加载/运行** |
| `cases/metasurface/P02_PolarizationControl_045/P02_PolarizationControl_045_qwp.fsp` | **QWP 工程**（a=310, b=370, c=850, D=750 nm），验收表需要 QWP 的 Δφ | 481,920 B，`layoutmode=1.0` |

两份工程都从论文参数**从零建模**，未使用 `model/` 下的课件 `.fsp`（其 `circle.radius=0`、周期 1 µm，与论文不符，README §0 已有警示）。

### 1.2 工程里有什么（打开就能看到）

| 对象 | 设置 | 满足任务书哪一条 |
|---|---|---|
| `source_x` | 平面波，正入射，`polarization angle = 0°`，**enabled** | x 偏振设置 |
| `source_y` | 平面波，正入射，`polarization angle = 90°`，**disabled** | y 偏振设置（切 enabled 即可） |
| `phase_x` / `phase_y` | 2D Z-normal DFT 场监视器，位于透射平面 z=1.57 µm，分别投影 Ex / Ey，101 频点 | 相位监视器提取 φ_x、φ_y；「一次源 + 两次监视器投影」 |
| `T` | 透射功率监视器 | 总透射 T |
| `R` | 反射功率监视器 | 后向散射 / 反射 R |
| `FDTD` | x/y = Periodic，z = PML，mesh accuracy 4 | 边界条件 |
| `mesh_fine` | 20 nm 局部 override | 网格精度 |
| `substrate` / `nanopillar` | `SiO2 (Glass) - Palik` / `Si (Silicon) - Palik`，椭圆 64 顶点 | 石英衬底 + 硅纳米柱 |

### 1.3 用户怎么跑（三步）

1. 打开 `.fsp` → 直接点 **Run**：默认 `source_x` 激活，得到 x 轴透射/反射谱。
2. 要 y 轴：`source_x.enabled = 0`、`source_y.enabled = 1`，再 Run。
3. 要相位差 Δφ：把激活源的 `polarization angle` 设为 **45°** 再 Run（一次 run 同时激发两轴，公共传播相位自动抵消；`phase_x` 读 `Ex`、`phase_y` 读 `Ey`，取 `arg<Ex> − arg<Ey>`）。报告数据即用此法。

> 脚本化的等价流程见 §7；所有跑过的副本都带 `tmp_p02rep_` 前缀，交付工程本身保持未跑（`layoutmode=1`），便于用户自己 Run 验证。

---

## 2. 前置检查（任务书 §2）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 目录内容 | ✅ 论文 PDF、README、`config/spec_p02.json`、5 个课件 `.fsp`、3 个 `.lsf`、`results/repro_p02` 与 `results/phase_p02` 旧 CSV 均在 | 见 `params.md` §5 |
| 2 | `lumapi` 可导入 | ✅ `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python\lumapi.py` | 托管 Python 3.13.14 |
| 2 | license 可用 | ✅ `1055@localhost`，端口通，实测可 checkout | 两段式 run 成功 |
| 2 | Python 解释器正确 | ✅ 托管 venv（`...\envs\default\Scripts\python.exe`），含 numpy 2.5.3 / matplotlib 3.11.2 | 系统 Python 3.14 无 numpy，未使用 |
| 2 | 两段式 run + `layoutmode==0` | ✅ `save → close → 新会话/新进程 load → run`，读回 `layoutmode = 0.0`，`_p0.log` 含 `Completed` | 全部生产 run 与对照 run 均通过 |
| 3 | 相关 skills（**只调不改**） | `fdtd-lumerical-headless`（已加载）、`fsp-build`、`unitcell-simulation`、`phase-retrieval`、`figure`、`fsp-introspection` | 复用 `_shared/fsp_build.py` 与 `lumapi_common.py`，**未修改任何 skill 文件** |
| 4 | 目标路径占用 | ✅ 根下原无 `.fsp`，无需备份；脚本仍保留 `.bak_<timestamp>.fsp` 防御分支 | — |
| 补 | GPU 可用 | ✅ RTX 3070 Laptop 8 GB / CC 8.6；`Detected GPU 0`、`Using datatype: real32` | 见 §3 |

**四项全部通过，未触发 §6 停止条件。**

事后跑仓库自检：
- `tools/check_scripts.py` → `OK 包内没有 .py` ✅
- `tools/check_packages.py --pkg P02` → `ERROR=0`、exit 0、`WARN=4`。4 条 WARN 全是 `model/` 下 2021/2023 年课件资产（`fig3_1.fsp`、`fig3_2.fsp`、`fig4c.fsp`、`test1.fsp`）缺 `_p0.log`，**与本任务无关、非本次引入**。
- ⚠️ 该门禁报 `fsp=5`，只数了 `model/`；本次交付的两份 `.fsp` 位于 case 根目录，**不在其扫描范围内**。即 `ERROR=0` 只证明「扫描范围内没问题」，不覆盖新交付工程（项目记忆里「门禁绿灯 ≠ 结论」的同一模式）。两份工程已用 `lumapi` 实际 `load` 并逐字段核对（对象树、a/b/c/D、双源 enable、边界），这才是它们的可用性证据。

---

## 3. GPU 加速（补充需求）与多 agent 并行的冲突处置

- 全局 `FDTD Solutions.ini` 的 `FDTD\GPU-mode=false`，默认走 CPU。field-manual §6.3 明确 `setresource` 会**持久化改全局配置**，多 agent 并行时翻转会产生竞态、甚至把别的会话的 GUI 打成「no active GPU resources」。
- 实测找到安全路径：**`fdtd-engine.exe -t 1 -gpu <fsp>` 可独立启用 GPU，完全不读写共享 ini**。除显式标注的 CPU 双精度对照外，全部生产 run（4 组单偏振 + 2 组 45° 相位 + 3 组对照 + 1 组 Fig.2 口径诊断）均走此路径，日志含 `Detected GPU 0: NVIDIA GeForce RTX 3070 Laptop GPU` 与 `Using datatype: real32`。标准网格单次 9–13 s，CPU 双精度对照 78.5 s（约 6–7× 加速）；10 nm 加密网格 34.5 s。
- 本模型是**全介质 Si/SiO₂**（实测 `k=0`），不含 Drude 金属、无 `0<Re ε<1` 色散，正好避开 field-manual §6.3 记录的 real32 发散场景；全部 run 日志 `diverging=false`。
- 事后核对：`[jobmanager]` 段与任务开始时的备份**逐字节一致**，`GPU-mode=false`、GPU 资源条目 `<DeviceType>GPU</DeviceType>` 完好。整份 ini 的文本差异仅有 GUI 窗口状态与 `pwd`（被另一并发 agent `tmp_p04repro_run` 改写），**本会话没有写共享配置，也没有回滚覆盖别人的状态**。

---

## 4. 验收表（任务书 §5，逐项填）

工作波段取 C+L 带 **1530–1625 nm**（32 个采样点）。`Δφ` 用 45° 单次 run 的干净值；PCE 按器件分别用正确定义（HWP = 交叉线偏 / 总透射，QWP = 主圆偏 / 总透射，见 `principles.md` §1）。

| 论文结论 | 论文值 | 本工程结果 | 容差 | 状态 |
|---|---|---|---|---|
| 总透射（HWP / QWP 工作波段） | ~90% | **HWP 96.48%**（min 94.11%）；**QWP 93.39%**（min 91.12%） | ±8% | **PASS** |
| 偏振转换效率 PCE | ~99% | **HWP 91.21%**（交叉线偏定义）；**QWP 93.66%**（圆偏定义） | ±5% | **FAIL** |
| 相位差 Δφ（HWP） | ≈ π (180°) | **211.13° ± 15.75°**（等效偏差 31.13° = 0.173π） | ±0.1π (18°) | **FAIL** |
| 相位差 Δφ（QWP） | ≈ π/2 (90°) | **297.33° ± 10.46°**（≡ −62.67°，等效偏差 27.33° = 0.152π） | ±0.1π (18°) | **FAIL** |
| 后向散射 / 反射 | ≈ 0 | **HWP 3.50%**（扣衬底后 0.42%）；**QWP 6.60%**（扣衬底后 3.52%） | < 5% | **PASS（HWP）/ FAIL（QWP 总反射）** |
| 多极子叠加后反射被抑制 | 是 | 宽带低反射 + 平坦 Δφ 为**间接证据**；未做多极分解 | 定性 | **FAIL（机制未直接验证）** |
| *(附)* 能量守恒 `T+R≈1` | — | HWP 0.99987、QWP 0.99988，最大偏离 0.25% | — | ✅ 数值自洽 |

### 4.1 每个 FAIL 的具体原因（不是「偏差较大」）

**① PCE FAIL（91.21% / 93.66%，差 5.3–7.8 个百分点）**
PCE 对 `Δφ` 极敏感：`PCE = [T_x+T_y−2√(T_xT_y)·cosΔφ] / [2(T_x+T_y)]`。HWP 的 `Δφ=211°` 使 `cosΔφ = −0.857`（理想 −1.000），单这一项就把 PCE 上限压到 ~93%；剩余差距来自 `T_x≠T_y`（0.9653 / 0.9644）与振幅不平衡。**根因是 Δφ 偏差，不是吸收损耗**（材料 `k=0`、`T+R≈1`）。QWP 同理：圆偏纯度 `|S₃|/S₀ = 0.873`，理想为 1。

**② / ③ Δφ FAIL（+31.13° / +27.33°，共同 ~+29° 偏移）**
已用三组对照**排除**了数值因素（下表），因此是**真实的模型/口径偏差**：

| 对照 | Δφ (C+L 均值) | 结论 |
|---|---|---|
| 空结构（去掉纳米柱） | **360.000° ≡ 0°**，std 3×10⁻⁷° | 相位提取方法正确，公共传播相位严格抵消 |
| GPU real32 → CPU 双精度 | 211.132° → **211.132°** | 排除单精度 |
| 网格 20 nm → 10 nm | 211.132° → **210.271°**（差 0.86°） | 排除离散化，已收敛 |
| 两次独立 run vs 单次 45° run | 211.123° vs **211.132°** | 排除「两个源对象相位基准不同」（我先前的假设，已当场更正） |

定量口径诊断（**有论文出处，不是调参凑数**）：把几何换成论文 **Fig.2 caption (p.4) 标注的 `a/b/c = 285/450/860 nm`**，其余不动，Δφ 从 211.13° 降到 **191.48°**（偏离 180° 仅 11.48°，进入 ±18° 容差）。这证明**论文内部两组尺寸不一致**是主因之一。

剩余偏差的合理归因（按影响排序）：
1. **求解器不同**：论文用 **CST Microwave Studio** 出理论曲线（补充材料 p.13 S4），本工程用 Lumerical FDTD；色散材料拟合、网格、PML 实现都不同，不可能逐位相等。
2. **截面近似**：论文器件是 EBL+RIE 做出的**圆角矩形/椭圆**柱，本工程用 64 顶点正椭圆近似；a/b 轴的具体口径（全轴长 vs 半轴）论文未明示，`spec_p02.json` 假定为全轴长。
3. **几何歧义**：论文只说「入射偏振平行短轴」，未定义长轴朝 x 还是 y（params.md 假设 A5）。
4. **论文未给全参数**：poly-Si 的 n(λ)/k(λ) 实测表、FDTD/CST 网格、PML 层数、仿真时长、边界细节全部缺失；衬底真实 500 µm 被截断为 1 µm。
5. **材料口径**：器件是 LPCVD poly-Si，数值模型用 Palik 晶硅（补充材料确认论文数值仿真也用 Palik）；晶界吸收与色散差异未纳入。
6. **Fig.2 与 Fig.3 两组尺寸差 5/20/10 nm**，对高 Q 的 Mie 共振相位足以造成十几度漂移。

**④ 反射 FAIL（QWP 总反射 6.60% > 5%）**
空结构对照给出裸石英衬底的菲涅尔反射 `R_sub = 3.08%`（`n=1.444` 的理论值 3.3%，吻合）。扣除后：
- HWP 超表面自身反射 **0.42%**（论文「reflectionless」，✅）
- QWP 超表面自身反射 **3.52%**（< 5%，✅）

论文 Fig.2 的多极分解曲线明确「neglects reflection off the glass substrate」，即论文口径本就是**扣除衬底**的。按论文口径两者都 PASS；按「总反射」口径 QWP 超标。QWP 的 a/b 更接近（310/370），本征双折射弱，对尺寸/网格误差更敏感，故反射略高。

**⑤ 多极子机制 FAIL**
论文 Fig. 2(b)(c) 的 ED/MD/HOM 分解是**用 CST 导出柱内电场 `E_CST`，再按 `J = −iω[ε̄(r)−ε₀]E` 做多极矩积分**得到的（补充材料 p.13 S4），不是 FDTD 的 R 监视器能给出的量。本工程只测 `T/R/E(相位)`，能验证「宽带低反射、高透射、Δφ 平坦」这些**现象**，不能验证「低反射确由多极干涉造成」这一**因果链**。这是能力缺口，不是物理上不成立。

### 4.2 明确没有做的事（防止误读）

- **没有调参凑结果**。所有生产 run 都用论文/任务书写死的参数；`a/b/c`、`D`、材料、边界、网格全部未改动。
- Fig.2 几何那次是**论文自己给出的第二组参数**，作为口径诊断单列在 `control_fig2_geometry.csv`，**不替换主结果**，也不把它写进验收表冒充 PASS。
- 没有用 90%/99% 去反推参数；没有改网格/材料/边界来让 Δφ 落到 180°。

---

## 5. 阻塞问题上报（按四维分类）

> ⚠️ **模板说明**：任务书 §6 只给出标题「阻塞问题上报模板（按四维分类）」，**模板正文在消息中未提供**。下面按自拟的四维分类（**输入资料 / 环境工具 / 物理方法 / 流程协作**）逐项填写；若用户有既定模板，请补发，我会按其字段重排。

### 维度 A — 输入资料（论文、参数、旧资产）

| ID | 级别 | 问题 | 证据 | 需要谁裁决 |
|---|---|---|---|---|
| `A-1` | **BLOCKER** | 论文两组尺寸自相矛盾：Fig.2 caption (p.4) = 285/450/860 nm，Fig.3 正文 (p.5) = 280/430/850 nm。两组跑出 Δφ 差 **19.65°**，直接决定 HWP 是否落在 ±0.1π 容差内 | `control_fig2_geometry.csv` (191.48°) vs `phase45_hwp_gpu.csv` (211.13°) | **人（导师）**：以哪组为准 |
| `A-2` | **BLOCKER** | poly-Si 的 n(λ)/k(λ) 实测表未给；论文数值仿真改用 Palik 晶硅（补充材料 p.13 S4），与器件实物不同 | PDF 全文检索无 poly-Si 光学常数表 | **人**：是否接受 Palik 口径 |
| `A-3` | MAJOR | 论文未给网格、PML 层数、仿真时长、边界实现、椭圆长轴朝向、衬底是否纳入仿真域 | PDF p.3–5、p.13 均无 | **人**：复核参数口径 |
| `A-4` | MINOR | 课件 `model/fig3_1.fsp` 等与论文不符（`radius=0`、周期 1 µm），不能作基准 | README §0、旧 `repro_report.md` §7 | 已处置：全部从零建模 |

### 维度 B — 环境与工具

| ID | 级别 | 问题 | 证据 | 状态 |
|---|---|---|---|---|
| `B-1` | MAJOR | GPU 开关是**全局共享配置**，多 agent 并行时翻转会竞态；`setresource` 还会持久化污染 ini | field-manual §6.3；本次实测 `pwd` 已被并发 agent `tmp_p04repro_run` 改写 | **已规避**：改用 `fdtd-engine.exe -gpu`，不碰 ini；`[jobmanager]` 段事后逐字节一致 |
| `B-2` | MINOR | GPU 为 real32 单精度，历史上金属模型出现场发散 | field-manual §6.3 | **已排除**：本模型全介质 `k=0`，CPU 双精度对照逐位一致（211.132°），全部 run `diverging=false` |
| `B-3` | MINOR | 本机 `timeout` 命令被 Windows `timeout.exe` 抢占，命令行测试误报 | 实测 `Invalid syntax. Default option is not allowed more than '1' time` | 已处置：去掉 `timeout`，改用引擎自身日志判完成 |
| `B-4` | INFO | `lumapi` 不在托管 venv 的 `sys.path` | 需 `setup_env()` 注入 `F:\...\v251\...\api\python` | 已处置 |

### 维度 C — 物理与方法

| ID | 级别 | 问题 | 证据 | 状态 |
|---|---|---|---|---|
| `C-1` | **BLOCKER** | Δφ 共同 +29° 系统性偏移，超出 ±0.1π。已排除方法/精度/网格，锁定为模型与口径差异（§4.1 六条原因） | 三组对照 + Fig.2 口径诊断 | **未解决**（按用户要求不调参凑数） |
| `C-2` | **BLOCKER** | 多极分解（ED/MD/HOM）未实现，「多极子叠加抑制反射」的因果链无法直接验证 | `principles.md` §4；论文补充材料 p.13 S4 | **未解决**：需导出柱内复电场做多极矩积分，或改用与论文一致的 CST 流程 |
| `C-3` | MAJOR | 论文 90%/99% 是**实验值**，理论数值是 ~100%；验收基准口径本身存在 10 个百分点的体系差异 | p.1 摘要、p.2 正文 | 已在 §4 显式标注 |
| `C-4` | MINOR | HWP/pol90 在 1400–1412 nm 出现 T 低至 0.118 的深凹陷 | `T_R_phi_hwp_pol90.csv` | **已解释**：位于 C+L 带外，`T+R≈1`，属短波 Mie/FP 共振；旧报告 §5 已预判 |
| `C-5` | MINOR | PCE 对 HWP/QWP 定义不同，混用会得出 QWP 仅 27% 的假失败 | `polarimetry_*.csv` | 已处置：Jones/Stokes 双定义分别计算 |

### 维度 D — 流程与协作

| ID | 级别 | 问题 | 证据 | 状态 |
|---|---|---|---|---|
| `D-1` | MINOR | 任务书 §6 四维模板正文缺失 | 消息在标题处结束 | 已用自拟四维上报，**待用户补模板** |
| `D-2` | INFO | 只读 skills 约束 | 全程仅 `import` `_shared/fsp_build.py` / `lumapi_common.py`，未写入 `skills/` | ✅ 遵守 |
| `D-3` | INFO | 中间产物会话前缀 + 完成后清理 | 全部 `tmp_p02rep_*` 且集中在 `_scratch/` | ✅ 遵守（清理见 §7） |
| `D-4` | INFO | 不覆盖已有工程 | 目标路径原无 `.fsp`；脚本保留 `.bak_<timestamp>.fsp` 分支 | ✅ 遵守 |
| `D-5` | INFO | 每个会话 `close()` 落在 `finally`；`run` 前 `save → close → 新会话 load → run` | 所有脚本两段式；每个求解过的副本读回均 `layoutmode=0.0` | ✅ 遵守 |

---

## 6. 结果文件

| 路径 | 内容 |
|---|---|
| `results/P02_PolarizationControl_045/T_R_phi_{hwp,qwp}_pol{0,90}.csv` | 4 组单偏振 run 的 `λ, T, R, \|E_copol\|, arg(E_copol)` |
| `results/P02_PolarizationControl_045/phase45_{hwp,qwp}_gpu.csv` | 45° 干净相位差、`\|Ex\|,\|Ey\|, arg(Ex),arg(Ey), T_45°` |
| `results/P02_PolarizationControl_045/spectra_{hwp,qwp}.csv` | 合并谱：T_x/T_y/R_x/R_y/φ_x/φ_y/Δφ/PCE |
| `results/P02_PolarizationControl_045/final_{hwp,qwp}.csv` | 最终验收口径：`T_total, R_total, R_metasurface, Δφ, PCE` |
| `results/P02_PolarizationControl_045/polarimetry_{hwp,qwp}.csv` | Stokes `S₀–S₃`、圆偏纯度、双定义 PCE |
| `results/P02_PolarizationControl_045/control_{empty,cpu,mesh10,fig2_geometry}.csv` | 四组对照实验 |
| `results/P02_PolarizationControl_045/run_evidence.csv` | **10 轮引擎台账**：solver(GPU/CPU)、耗时、`layoutmode`、`Completed`、`diverging`、网格、迭代数 |

> ⚠️ `final_*.csv` 的 `PCE_hwp_def` 列对两个器件**都**用 HWP 的交叉线偏定义，所以 `final_qwp.csv` 里该列只有 ~27%，这是**定义错配，不是 QWP 失效**。QWP 的正确转换效率看 `polarimetry_qwp.csv` 的 `PCE_circular_QWPdef`（93.66%）。验收表用的就是这个值。
| `results/P02_PolarizationControl_045/P02_spectra.png` | (a) 两轴透射 (b) 总反射 vs 超表面反射 (c) Δφ (d) PCE |
| `results/P02_PolarizationControl_045/P02_controls.png` | 方法/精度/网格/几何四组对照曲线 |
| `results/P02_PolarizationControl_045/P02_phase_band.png` | C+L 带内 Δφ 与目标值 |

---

## 7. 可复现性说明

按硬约束「所有中间产物带会话前缀、完成后清理」，本会话的 `tmp_p02rep_*` 临时脚本、临时 `.fsp`、`_p0.log`、探针输出已在交付后**全部删除**（69 个文件 / 637.7 MB）；其它并发 agent 的前缀（如 `tmp_p04repro_run`）未触碰。因此上面的脚本路径**不再存在**，此处只作流程记录。

**可复现性由以下交付资产保证，不依赖临时脚本**：

1. **工程本身可直接跑**：`*.fsp` 是完整、未求解（`layoutmode=1`）的可运行工程，按 §1.3 三步即可得到全部谱与相位。
2. **参数完整**：`params.md` 给出全部几何/材料/边界/网格/波段数值及论文页码；`cases/P02.../config/spec_p02.json` 是原始终端 spec。
3. **方法与判据完整**：§4 给出每个数字的公式定义（Δφ 平面平均、PCE 的 Jones/Stokes 双定义、反射的衬底扣除），`principles.md` 给出式 (1)–(4) 推导链。
4. **原始数值完整**：`results/.../*.csv` 含每一波长点的 T/R/φ/Jones/Stokes，可独立重算任何汇总量。
5. **引擎证据完整**：`run_evidence.csv` 记录 10 轮 run 的 solver、耗时、`layoutmode`、`Completed`、`diverging`、网格与迭代数。

**重跑所需的环境三件套**（field-manual §1）：
```python
os.environ["ANSYSLMD_LICENSE_FILE"] = "1055@localhost"
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
import lumapi
# 托管 Python: C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe
```
GPU 启用（不碰全局 ini）：`fdtd-engine.exe -t 1 -gpu <fsp>`。
会话序列：`load → switchtolayout → 改参 → save → close` → 新进程/新会话 `load → run` → `layoutmode==0` + `_p0.log` 含 `Completed` 才算数。

---

## 8. 结论（一句话）

**工程可交付、可跑、GPU 已启用、透射与能量守恒达标；但 Δφ 存在经三重对照证实、根因指向论文自身参数口径与求解器差异的 +29° 系统偏移，据此 PCE 与相位差两项判 FAIL——未做任何调参凑数，需要人裁决 Fig.2 / Fig.3 采用哪组尺寸，以及是否需要补齐 CST 多极分解以验证因果机制。**
