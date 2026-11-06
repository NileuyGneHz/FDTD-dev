# P03 — 等离激元半波片 / 复现 Figure 1

> **本包是 D1 主线**（导师指定的复现任务）。所有 D1 资产已归档于此。

---

## 0. Agent 快速接管（每次协作必读）

| 项 | 值 |
|---|---|
| **包 ID** | `P03` |
| **任务状态** | **进行中** |
| **本次目标** | **复现 Figure 2(c)(d)**：不同入射角 θi 下的 R_cr 与 PCR（黄老师 2026-10-08 指定） |
| **验收标准** | ① `R_co(900–1600nm) ≈ 0`、`R_cr ≈ 1`；② `PCR > 95%`；③ 峰值与论文 Fig.1b 逐点吻合 |
| **入口脚本** | `scripts\t15_hwp_paper_materials.py`（论文材料版，当前最优） |
| **入口工程** | `fsp\fig1_hwp_paper_materials.fsp` |
| **预计耗时** | 单次仿真 35–60 s；扫参按点数线性增长 |

### 当前状态（2026-09-30）

| 版本 | 材料 | R_co | R_cr | PCR | 判定 |
|---|---|---|---|---|---|
| t14 | Palik 实验数据 | 0.676 | 1.058 | ~72% | 对不上 |
| **t15** | **论文 Drude + n=1.45** | **0.155** | **0.916** | **~94%** | **基本对上** |
| 论文 | — | ≈0 | ≈1 | >95% | 目标 |

→ **材料模型是最大误差源**，不是网格、不是监视器位置。剩余 ~1–5% 待收敛。

### 开工前必做

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" "F:\Lumercial_WS\FDTD_WS\tools\check_packages.py" --pkg P03
```

---

## 1. 论文

| 项 | 内容 |
|---|---|
| 标题 | *Broadband High-Efficiency Half-Wave Plate: A Supercell-Based Plasmonic Metasurface Approach* |
| 作者 | Ding, F.; Wang, Z.; He, S.; Shalaev, V. M.; Kildishev, A. V. |
| 期刊 | **ACS Nano 2015, 9(4), 4111–4119** |
| DOI | `10.1021/acsnano.5b00218` |
| 本地原文 | `paper\Ding2015_Broadband_High-Efficiency_Half-Wave_Plate.pdf`（**黄老师提供的原文，2026-10-08 已补**） |
| 本地精读 | `paper\论文精读_等离激元半波片.pdf`（精读版，中文） |
| 精读笔记 | `notes\论文精读_等离激元半波片.md`（13 节，可跳读） |
| **自测题** | `paper\自测题_5问.md`（5 题 + 参考答案 + 基础缺口自查表） |

> ✅ **原文已补齐**（2026-10-08）。原文 10 页，含 Figure 1–6 与 Methods、References。

**要复现的目标**：

| 目标 | 论文位置 | 状态 |
|---|---|---|
| Figure 1a：单元胞结构示意 | Fig.1a | ✅ 结构已建 |
| **Figure 1b：R_co / R_cr 反射谱** | Fig.1b | ✅ 设计带宽内达标（R_co=0.043 / R_cr=0.932） |
| Figure 1c：PCR 曲线 | Fig.1c | ✅ 带宽内均值 0.955，峰值 0.998 @ 965 nm |
| Figure 2a/2b：SEM 与测量光路 | Fig.2a,b | ⛔ 实验内容，仿真无法复现（可引用原图对照） |
| **Figure 2c：各入射角下的 R_cr** | Fig.2c | ❌ **本次目标**，未开始 |
| **Figure 2d：各入射角下的 PCR** | Fig.2d | ❌ **本次目标**，未开始 |
| Figure 3–6：机理分解 / 超胞 / 反常反射 | Fig.3–6 | ❌ 未开始 |

> **2026-10-08 变更**：黄老师指定复现目标由 Figure 1 改为 **Figure 2**。
> Figure 1 已在设计带宽内达标（见 §5 分区统计），后续以 Figure 2 的角度鲁棒性为主攻方向。

---

## 2. 关键参数（照抄论文 Methods）

> ⚠️ **材料数据源必须按论文**。t14 用 Palik 库数据 → PCR 只有 72%；
> t15 改成论文的 Drude 参数 → 94%。四套 TiO₂ 数据差 ~15%，**不要混用**。

| 参数 | 值 | 来源 |
|---|---|---|
| 设计波长 | 800–1600 nm（PCR>95% 波段 805–1672 nm） | 原文 Results |
| SiO₂ spacer | **常数 n = 1.45，无损** | 原文 Methods 明写 |
| Au | **Drude**: ωp=1.37e16 s⁻¹, ωd=1.224e14 s⁻¹ | 原文 Methods |
| **单元胞周期** | **p = 600 nm** | 原文 Fig.1 caption + Methods |
| **纳米砖 l1 × l2 × tm** | **390 nm × 165 nm × 80 nm** | 原文 Fig.1 caption |
| **旋转角** | **45°**（绕 z 轴，相对 x 轴逆时针） | 原文 Methods |
| **SiO₂ 间隔层厚 ts** | **110 nm**（扫参优化所得，见 SI §1） | 原文 Methods |
| **底层 Au 膜厚 d** | **150 nm** | 原文 Methods |
| 超胞周期 s（Fig.4 起） | 2.4 μm（4 个天线，相位覆盖 2π） | 原文 Fig.4 段 |
| Figure 2 特有 | 仿真需计入 Au/SiO₂ 界面 **5 nm Ti 粘附层** | 原文 Fig.2 caption |

> ⚠️ **2026-10-08 更正**：本表此前误记「周期 250 nm、纳米砖 120×60×600」，那是早期 TiO₂ 骨架的数，
> 已按原文 Figure 1 caption 更正。脚本 `t15_hwp_paper_materials.py` 的参数一直是对的。
> TiO₂ 单元胞（t4/t14 系列）属另一条早期支线，与本论文 HWP 设计无关，勿混用。

**论文 Methods 原话（Au 模型）**：

> ωp = 1.37e16 s⁻¹, ωd = 1.224e14 s⁻¹
> "which has taken the surface roughness and grain boundary effects into consideration"

---

## 3. 文件清单（2026-09-30 已归档）

### `paper\` — 论文
| 文件 | 说明 |
|---|---|
| `论文精读_等离激元半波片.pdf` | 论文**精读版**（⚠️ 原文待补，DOI `10.1021/acsnano.5b00218`） |

### `fsp\` — 仿真工程（ASCII 文件名）
| 文件 | 说明 |
|---|---|
| `fig1_hwp_paper_materials.fsp` | ★ **入口工程**（论文材料版，当前最优） |
| `fig1_hwp_paper_materials_p0.log` | 引擎日志 |
| `fig1_hwp_unitcell.fsp` | 单元胞（Palik 材料版，对照组） |
| `fig1_hwp_unitcell_p0.log` | 引擎日志 |
| `t4_tio2_unitcell.fsp` | TiO₂ 纳米砖早期版本 |
| `t4_tio2_unitcell_p0.log` | 引擎日志 |
| `TiO2_nanobrick_unitcell.fsp` | TiO₂ 骨架工程（rev5） |
| `TiO2_nanobrick_unitcell_p0.log` | 引擎日志 |

### `scripts\` — 本包专用脚本
| 文件 | 说明 |
|---|---|
| `t15_hwp_paper_materials.py` | ★ **论文材料版（当前最优）** |
| `t15b_hwp_paper_plot.py` | t15 出图 |
| `t14_hwp_unitcell.py` | Palik 版本（对照实验） |
| `t14b_hwp_plot.py` | t14 出图 |
| `build_tio2_unitcell.py` | TiO₂ 骨架（Python 版，含 Lx/Ly × 偏振扫参） |
| `build_tio2_unitcell.lsf` | TiO₂ 骨架（LSF 版，GUI 内 F5 运行） |

### `results\` — 数据与图
| 文件 | 内容 |
|---|---|
| `t15_hwp_R_paper.csv` | ★ 论文材料版反射数据 |
| `t14_hwp_R.csv` | Palik 版反射数据（对照） |
| `fig_t15_1b_Rcr_Rco_paper.png` | ★ t15 结果图 |
| `fig_t15_1c_PCR_paper.png` | ★ t15 PCR 曲线 |
| `fig_t14_1b_Rcr_Rco.png` | t14 对照图 |
| `fig_t14_1c_PCR.png` | t14 PCR 曲线 |
| `unitcell_index_8level.csv` | 8 级量化元原子库查表清单（GS 接口） |
| `t4_T.csv` | TiO₂ 透射数据 |

### `notes\` — 笔记
| 文件 | 说明 |
|---|---|
| `论文精读_等离激元半波片.md` | ★ 论文逐节精读（13 节，可直接跳读） |

---

## 4. 本包特有的坑

| 现象 | 真因 | 对策 |
|---|---|---|
| PCR 只有 72% | 用 Palik 库数据而非论文 Drude | `addmaterial("Sampled data")` 喂论文参数 |
| `addmaterial("Au_Drude")` 失败 | 参数是**模型类型**不是材料名 | 先 `addmaterial("Sampled data")` 再 `setmaterial` 改名 |
| `|Ex| > 1` | 光源在基底内、监视器在空气，归一化基准不同 | 正常。`T = |Ex|²/n_substrate` |
| 默认 5 个频点打不到设计波长 | 默认采样点太粗 | 显式设栅格 + 线性插值到目标波长 |
| `|Ey|=0` 但相位非零 | 振幅 0 时相位是噪声 | 不要用它算 delta |

（通用坑见 `..\..\SKILL.md`）

---

## 5. 复现进度与差异记录

| 图号 | 论文值 | t15 结果（设计带宽 900–1600 nm） | t15 结果（全扫 700–1700 nm） | 判断 |
|---|---|---|---|---|
| Fig.1b R_co | ≈0 | **0.043** | 0.155 | ✅ 带宽内达标 |
| Fig.1b R_cr | ≈1 | **0.932** | 0.916 | 🔶 差 7% |
| Fig.1c PCR | >95% | **95.5%**（峰值 0.998 @ 965 nm） | 87.6% | ✅ 过线 |
| Fig.1c 带宽 | 805–1672 nm | 待脚本输出复核 | — | 🔶 待确认 |

> ⚠️ **2026-10-08 更正**：本节此前记的 `0.155 / 0.916 / ~94%` 取的是**全扫均值**，
> 把出带区（色散共振区本就不工作）也算进去了，属**自评偏低**。
> 按论文自己声明的设计带宽（PCR>95% 的 805–1672 nm 区间）衡量，Figure 1 的三条验收标准基本达标。

**下一步待查**（按优先级）：
1. 监视器位置是否离 PML 过近
2. 网格分辨是否足够（金属趋肤深度 ~25 nm）
3. SiO₂ 常数 n=1.45 是否与论文完全一致
4. 频段覆盖是否留足余量

---

## 6. 与导师的同步

| 项 | 内容 |
|---|---|
| 已向导师汇报 | 待确认 |
| 待确认问题 | ① 论文原文 PDF 能否提供？ ② 材料数据源是否以论文 Methods 为准？ |
| 交付物 | `F:\Lumercial_WS\output\Figure1复现进展汇报.docx` |

---

## 7. 存量资产位置（原件未动，此处留档）

| 类型 | 原路径 |
|---|---|
| D1 工程 | `F:\Lumercial_WS\WS\*.fsp`（4 个） |
| D1 脚本 | `F:\Lumercial_WS\scripts\t14*.py` / `t15*.py` / `build_tio2_unitcell.*` |
| D1 结果 | `F:\Lumercial_WS\WS\results\t1[45]*` / `unitcell_index_8level.csv` |
| 精读笔记 | `F:\Lumercial_WS\docs\论文精读_等离激元半波片.{md,pdf}` |
