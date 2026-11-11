# P01 复现情况汇报（2026-11-09）

> 任务：依据 `cases/P01_Absorber_042` 创建一份**复现版 fsp 工程文件**，覆盖论文重要结论，
> 并给出参数 / 物理原理清单。
> 结论先行：**工程已建成、已求解、含已存谱、已实测可打开可执行**；
> 论文的 **0.97 峰值吸收未能复现**（本工程 Lumerical 口径给出 **0.8069 @ 5.85 µm**），
> 且 Fig.3 / Fig.4 / Fig.5 三类结论**无法用当前 skills 与单胞工程复现**。偏差与缺口逐条列在 §5–§7。
> **未修改、未替换任何 skill 的内容与行为**；只新增文件。
>
> ✅ **人裁决（2026-11-09，Q4 已关闭）**：接受「Lumerical ~0.82 为复现基准 + 显式标注求解器差异」。
> 该裁决已落地到 `spec_repro_p01.json`（`meta.human_verdict` / `acceptance_baseline`）与
> `verify_repro.lsf`（门禁改为 0.82±0.02，论文 0.97 降为 INFO 参考）。
> 复现过程中遇到的问题清单另见 **`skill_gap_backlog.md`**（13 条可施工工单，含本轮一处自我更正 §1）。

---

## 1. 交付物

| 文件 | 大小 | 作用 |
|---|---|---|
| **`P01_Absorber_042_repro.fsp`** | 83,725,405 B（≈79.8 MiB） | **主交付工程**。已求解（layoutmode=0），含 R/T/A 已存谱、场/折射率监视器，打开即可看图 |
| `P01_Absorber_042_repro_buildonly.fsp` | 478,368 B | 轻量版：同一模型、未求解（layoutmode=1），打开后按 Run 即可从头重算；适合入库 / 传阅 |
| `verify_repro.lsf` | — | **执行入口**。在 Lumerical Script File Editor 打开后 Run，自动算 A、峰值、FWHM、能量守恒并逐条判定论文结论 |
| `spec_repro_p01.json` | 13,146 B | **输入数据引用 + 配置总表**：参数、材料 cite、层位、源/网格/边界、9 条 `conclusions` 覆盖矩阵、`assumptions`、`missing` |
| `parameters_and_physics.md` | — | 论文重要参数清单 + 重要物理原理清单（P1–P10）+ 参数→对象速查 |
| `RTA_spectrum.csv` | 9,296 B | 91 点 `lam_um,R,T,A` 谱数据 |
| `RTA_spectrum.csv` 的同源日志 `P01_Absorber_042_repro_p0.log` | 4,942 B | 引擎日志，收敛判据原始证据 |
| `verification.json` | 1,015 B | 机器可读的实测指标 + 收敛判定 |
| `P01_Absorber_042_repro_build.json` | 822 B | build-only 阶段的 manifest（含 `--check` 结果） |
| `RTA_spectrum.png` | 61,416 B | `fdtd-lumerical-figure` 出的 R/T/A 谱图，峰值从 CSV 现算（0.8069 @ 5.85 µm） |
| `layer_stack.png` | 21,820 B | 同技能出的层结构侧视图（5 层，z = −2.285 → 0.1 µm） |
| **`skill_gap_backlog.md`** | — | **复现过程遇到的问题清单**：13 条按 P0/P1/P2 排序的 skill 精进工单，每条带证据、建议改动点与验收自测题；含本轮自我更正 |

全部位于 `F:\Lumercial_WS\FDTD_WS\cases\P01_Absorber_042\results\repro_2026-11-09_fsp\`。
**只在该目录下新增文件，未改动包内任何既有资产（`model/`、`config/`、`repro_report.md` 等）。**

---

## 2. 工程能否打开、能否执行 —— 证据链

| # | 检查 | 结果 |
|---|---|---|
| 1 | `fdtd-lumerical-fsp-build/scripts/build_fsp.py --check` | 34 项属性逐字段比对，**0 mismatch**；`layoutmode=1`、`solves=0`、无 `_p0.log` |
| 2 | `fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py` | 单点求解成功，peak A = 0.8069379708102874 @ 5.85 µm |
| 3 | 收敛（两条独立日志一致） | 5987 iterations；末值 `Auto Shutoff = 8.83863e-05 < 1e-4`；`Early termination of simulation, the autoshutoff criteria are satisfied.`；`Completed 5987 iterations` |
| 4 | 把结果写回主交付工程 | `layoutmode` 1 → 0；`saved_results_into_fsp = true` |
| 5 | `build_fsp.py --only-check`（对**最终** .fsp） | 34 项，**0 mismatch**（写回结果未破坏几何） |
| 6 | `fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py` | `layoutmode=0.0`、12 个对象、4 个监视器、`spectra_status = ok`，从文件**读回** peak A = 0.80694 @ 5.85 µm、A@6 µm = 0.71467 |
| 7 | `verify_repro.lsf` 实测 | headless `eval` 成功（无语法错），9 个变量全部 `getv` 读回，与 CSV 逐位一致 |
| 8 | 同输入回归 | `run_fdtd_sweep.py` 与 `run_and_store.py` 两次**独立**运行 peak A 逐位相同（0.8069379708102874） |

→ **可以打开、可以 Run、可以在 Script Prompt 跑验证脚本、可以读回已存谱。**

> 🔧 **本轮更正（2026-11-09）**：第 4 步「必须靠一次性脚本把结果写回」并非必需。
> 实测 `_scratch/p01_repro/run/point_00_base.fsp`（`run_fdtd_sweep.py` 自己的产物）为
> **83,725,458 B / `layoutmode=0.0` / `getresult("R","T")` 成功** —— 工程只要 `save()` 过，
> `run()` 结束引擎就会把结果写回，不需要再显式 `save()`。这正是项目 11-09 日志的 **EXP-22** 结论。
> `run_and_store.py` 因此保留为「同输入回归」用途（两次独立运行 peak A 逐位一致），而非补齐缺陷。
> 详见 `skill_gap_backlog.md` §1 / G-05。

> ⚠️ 主交付 .fsp 79.8 MiB（含场监视器数据），接近项目 100 MB 单文件入库上限。
> 若只用于归档/传阅，请用 478 KB 的 `..._buildonly.fsp`（打开后 Run 一次即得到同样结果）。见 §6-E1。

---

## 3. 实测结果 vs 论文

| 量 | 论文（CST 2009 + 实验） | 本工程（Lumerical v251） | Δ | 判定 |
|---|---|---|---|---|
| 峰值吸收 A | **0.97**（论文参考值，非门禁） | **0.80694** | −0.163 | ✅ **通过人裁决基准 0.82±0.02**；论文值仅作 solver gap 标注 |
| 峰值波长 | 6.00 µm | 5.85 µm | −0.15 µm | 🟢 在容差内 |
| R @ 峰值 | 0.03 | 0.19307 | +0.163 | ❌ |
| T @ 峰值 | ≈0 | −1.13e-05 | ≈0 | ✅ |
| max \|T\| 全频段 | ≈0 | 1.40e-05 | ≈0 | ✅ |
| FWHM | 1.0 µm | 0.80 µm | −0.20 µm | 🔶 边界 |
| A @ 4 µm | 10% | 4.16% | −5.8 pp | 🔶 |
| A @ 6 µm | ~0.97（峰） | 0.71467 | −0.255 | ❌ |
| A @ 10 µm | 1% | **不可测**（源止于 8.5 µm） | — | ⛔ |
| 能量守恒 \|R+T+A−1\| | 1 | 1.11e-16 | ≈0 | ✅ |

**与项目内既有 Lumerical 结果的一致性**（说明这不是建模错误）：

| 来源 | peak A | peak λ | A@6 µm |
|---|---|---|---|
| 课程 `infrared_perfect_absorber.fsp` 已存谱（收敛 8.875e-06） | 0.8196 | 6.152 µm | 0.7174 |
| 按课程设置重建重跑 | 0.8177 | 6.152 µm | 0.7169 |
| 包内 `results/repro_p01` 基线 | 0.8083 | 5.85 µm | 0.7163 |
| **本次交付工程** | **0.80694** | **5.85 µm** | **0.71467** |

四条独立 Lumerical 结果在 6 µm 处极差 **0.0027**。峰位 5.85 → 6.15 µm 来自数值设置
（acc 8 / 24 nm / 1e-5 / 1 ps / 3.5–11 µm·100 pts），不是几何或材料差异。
论文 0.97 出自 **CST Microwave Studio 2009**（实验亦 97%），属**求解器口径差异，不可由调参消除**。
包内 `notes/repro-card.md` 的裁决为 `status: solver_mismatch`，本工程沿用该裁决，**未把 ts 调到 120 nm 去凑 0.962**。

> ✅ **2026-11-09 人裁决（Q4 关闭）**：上表的 0.97 **不再是验收门禁**。
> 验收基准 = Lumerical ~0.82（`0.82 ± 0.02`），实测 0.80694 **PASS**；
> 峰位基准 5.85 ± 0.30 µm，实测 5.85 **PASS**；T≈0 与 `R+T+A=1` 两条物理判据 **PASS**。
> 与论文的 0.97 / 0.03 / 1.0 µm / 6.0 µm 差异作为**求解器口径差异**保留在表内并在验证脚本里以 INFO 输出，
> **禁止**通过调 `l / w / a / ts` 去消除。裁决已写入 `spec_repro_p01.json: meta.human_verdict`。

---

## 4. 论文结论覆盖矩阵

> 全量机器可读版本见 `spec_repro_p01.json` 的 `conclusions` 字段（含逐条 `experimental_condition` /
> `input_refs` / `fsp_config` / `entry_point` / `check_target` / `coverage`）。

| ID | 论文结论 | 实验条件 + 输入数据引用 | 必要配置 / 执行入口 | 结果校验目标 | 状态 |
|---|---|---|---|---|---|
| **C1** | A = 0.97 @ 6.0 µm（论文参考） | 正入射 TEM、无限周期；`spec.parameters` + `spec.materials`；p.1/p.2 Fig.2 | R/T power monitors；`A=1−R−T`；`verify_repro.lsf` 或 `run_fdtd_sweep.py` | **门禁（人裁决）**：peak A ∈ 0.82±0.02、峰位 5.85±0.30 µm；论文 0.97 @ 6.0 µm 仅作 INFO 对照 | ✅ **按裁决基准验收通过**：实测 0.8069 @ 5.85 µm |
| **C2** | 地平面使 T≈0 全频段 | 100 nm Au ≫ IR 趋肤深度；`Au_ground`, `Au_paper`；p.1–2 | T 监视器在地平面下方；`verify_repro.lsf` | max\|T\| < 1e-3 且 \|R+T+A−1\| < 1e-3 | ✅ **覆盖**：1.40e-5 / 1.11e-16 |
| **C3** | R = 0.03 @ 6 µm | 同 C1；p.2 | R 监视器在源上方；`verify_repro.lsf` | R@peak ≈ 0.03±0.05 | 🟡 **部分**：0.1931 |
| **C4** | FWHM 1.0 µm；A(4µm)=10%、A(10µm)=1% | FTIR 3–12 µm；p.2；`simulation.source` | 91 点 / 4–8.5 µm；`verify_repro.lsf` 或 `RTA_spectrum.csv` | FWHM 1.0±0.2 µm；A(4µm)≈0.10 | 🟡 **部分**：0.80 µm / 0.0416；**10 µm 不可测** |
| **C5** | ERR 电共振 + 地平面磁共振 → Z=√(μ/ε) 匹配 → R≈0 | 十字 + 185 nm Al₂O₃ + 连续地平面；p.1；`spec.objects` | 三层功能层齐备；`E_spacer` 场监视器；对照需另建"去地平面" spec | 定性：场局域在介质/间隙；去地平面后 A 塌陷 | 🟡 **部分**：条件在工程中，无独立电/磁探针、无 A/B 对照 |
| **C6** | 反演 ε₁、μ₁ 在 ω₀ 同时过零；一正一负 ⇒ T≈0 | 复 S11/S21 反演（Smith 2002）；p.3 Fig.3 | **无** | n/a | ⛔ **无法复现** |
| **C7** | 能量主要耗散在 Al₂O₃，比金属欧姆损耗大一个数量级 | 6 µm 逐层 W/m³；p.3 Fig.4 | `E_spacer`/`nidx_spacer` 仅定性 | n/a | 🟡 **部分**：场局域可见，损耗比不可定量 |
| **C8** | UCA/UCB 双尺寸子晶格 → 空间+频率选择性、40 dB、6 µm 成像 / 10 µm 不可见 | 140×140 µm 图案、39 writing fields、50 µm 分辨率、40×28 像素；p.3–4 Fig.5 | **无**（单胞 nx=ny=1） | n/a | ⛔ **无法复现** |
| **C9** | 工艺/测量：100 nm Au / 185 nm ALD Al₂O₃ / 100 nm Au on Si；FTIR 3–12 µm、R@20°、T@0° | p.2 fabrication & characterization | 层厚一致；源为正入射 0° | n/a | 🟡 **部分**：几何/层厚一致，20° 斜入射未建模 |

**状态统计（按 2026-11-09 人裁决口径）**：✅ 验收通过 2 条（C1 按 Lumerical 基准、C2）｜
🟡 部分覆盖 5 条（C3/C4/C5/C7/C9）｜⛔ 无法复现 2 条（C6/C8）。
C1 的 0.97 与 0.8069 之差仍完整列在表中，但**不再是 FAIL**，而是标注的 solver gap。

---

## 5. 明确标注：无法完整复现的部分及原因

1. **峰值吸收 0.97（C1）— ✅ 已由人裁决关闭，但数值差异本身仍存在**：本工程给出 0.8069。
   原因不是建模错误 —— 四条独立 Lumerical 结果（含课程收敛工程）在 6 µm 处聚合在 0.0027 内；
   论文数值来自 **CST Microwave Studio 2009** + 实验，本机无该求解器。
   2026-11-09 人裁决：**接受 Lumerical ~0.82 为复现基准，显式标注求解器差异**；
   因此这一项**不再算「未完成复现」**，而是「按 Lumerical 口径复现完成 + 论文口径差异已标注」。
   项目复现契约仍禁止调参凑数（**未**把 ts 调到 120 nm）。
2. **Fig.3 等效 ε/μ 反演（C6）**：需要复 S11/S21 相位；现有技能只有功率监视器 `|S|²`，
   `fdtd-lumerical-phase-retrieval` 只做周期单胞的透射相位差，不做有效介质参数反演。
3. **Fig.4 逐层损耗密度定量比（C7）**：技能没有 per-layer `Pabs` / loss-density 监视器或分析组，
   只能靠 `E_spacer` 给场局域的定性证据。
4. **Fig.5 空间/频率选择性成像（C8）**：这是 140 µm 尺度**实验图案 + 高光谱扫描**结论，
   需要 UCA/UCB 两种不同十字的超胞；`_shared/fsp_build.py` 的 `supercell` 只复制同一组 objects，
   不能在一个胞内放两套子晶格设计。单胞 FDTD 在原理上也不产生 xy 空间图像。
5. **A(10 µm)（C4 后半）**：源范围 4–8.5 µm，谱里没有 10 µm 数据点。
6. **20° 斜入射反射测量（C9）**：工程是正入射平面波；斜入射需 Bloch/periodic 斜入射重跑。
7. **fsp 二进制载体**：`.fsp` 无法内嵌"实验条件 / 输入数据引用 / 执行入口 / 校验目标"等文字元数据。
   本交付以**同目录**的 `spec_repro_p01.json`（机器可读）、`parameters_and_physics.md`、
   `verify_repro.lsf`（可在工程内执行）承载，工程本体则以对象命名、层位、监视器与已存谱体现物理条件。

---

## 6. 阻塞问题分类汇报

### A. 信息缺失

| 问题现象 | 影响范围 | 当前状态 | 需要我确认的事项 |
|---|---|---|---|
| 论文未给 Si 基底厚度 | `Si_sub` 层位/体积；地平面不透明故对光学无影响 | 采用 2 µm 假设，已写入 `assumptions` | **Q1**：接受 2 µm 假设，还是改成课程工程的 1715 nm？ |
| 论文未公开 CST 的网格 / 边界 / 收敛设置 | 无法逐位对齐论文数值设置 | 采用包内已验证的 Lumerical 基线（acc 4 + 30/30/20 nm override、1e-4、5 ps、4–8.5 µm/91 pts） | **Q2**：是否要我改用课程工程的 acc 8 / 24 nm / 1e-5 / 1 ps / 3.5–11 µm·100 pts 再出一版？该设置已验证给 0.8177 @ 6.152 µm |
| 论文反射测量在 20° 入射，模型是正入射 | C9 与实验曲线的可比性 | 未建模，已列入 `missing` | **Q3**：是否补一轮 Bloch 斜入射（20°）？ |
| 论文 `t = 0.185 µm` 的量取面 | 曾是最可疑偏差源 | **已关闭**：反解析课程 `.fsp` 证实为「地平面顶面 → 十字底面」 | 无需确认（见 `notes/repro-2026-11-07-fsp-calibration.md`） |

### B. 依赖不可用

| 问题现象 | 影响范围 | 当前状态 | 需要我确认的事项 |
|---|---|---|---|
| 本机无 **CST Microwave Studio 2009** | C1/C3/C4 幅值；0.97 无法用论文同款求解器验证 | ✅ **2026-11-09 已裁决**：用 Lumerical v251 替代，接受 ~0.82 为复现基准，差异显式标注；Q4 关闭 | **无需确认**（已裁决）。后续若要做第二引擎交叉验证，属新任务 |
| 无实验 FTIR 原始数据曲线 | 无法比对谱形，只能对论文标注的数字 | 只比标注值 | **Q5**：能否提供论文 Fig.2 的数字化曲线或实验数据？ |
| 无复 S 参数 / per-layer loss 能力 | C6/C7 完全不可复现 | 见 §5 | Q4 已裁决；能力缺口见 `skill_gap_backlog.md` G-08 |

### C. 运行结果偏差

| 问题现象 | 影响范围 | 当前状态 | 需要我确认的事项 |
|---|---|---|---|
| peak A 0.8069 vs 0.97（−0.163） | 头号验收指标 | 已判定 `solver_mismatch`，**未**调参拟合 | Q4 已裁决，本项转为记录项 |
| peak λ 5.85 vs 6.00 µm（−0.15 µm） | 峰位 | 项目已证明由数值设置引起（acc 8 会移到 6.152 µm） | 并入 **Q2** |
| R@peak 0.1931 vs 0.03 | C3 | 与 A 的偏差同源（A=1−R−T） | Q4 已裁决，本项转为记录项 |
| FWHM 0.80 vs 1.0 µm；A(4µm) 4.16% vs 10% | C4 谱形 | 实测记录 | 并入 **Q2** |
| A(10 µm) 无数据点 | C4 后半 | 源止于 8.5 µm | **Q3'**：是否把源扩到 3–12 µm 重跑（会改变既有基线可比性）？ |

### D. skills 能力不足（**严格未修改任何 skill**）

| 问题现象 | 影响范围 | 当前状态 | 需要我确认的事项 |
|---|---|---|---|
| `fdtd-lumerical-fsp-build` 按定义**只建不跑**（layoutmode=1、无结果） | 交付工程"打开即有谱" | ✅ **非阻塞**：`run_fdtd_sweep.py` 的 .fsp 本身就含已存谱，可直接重命名交付；`run_and_store.py` 只用于同输入回归，**未改 skill** | **Q6 已降级**：不再需要"把 run/save 加进技能"；仅确认是否接受"一次性脚本做回归"这一补充动作 |
| ~~`run_fdtd_sweep.py` 产出的 .fsp 无已存谱~~ → **本轮已证伪** | 无（原判断错误） | 实测 `point_00_base.fsp` = 83,725,458 B / `layoutmode=0.0` / `getresult` 成功。真因：工程 `save()` 过后 `run()` 结束引擎自动写回（EXP-22） | 无需确认；已列入 `skill_gap_backlog.md` §1 与 G-05（**知识只留在日志、没进 SKILL.md**） |
| `inspect_fsp.py` 把 index 监视器 `nidx_spacer` 当成功率监视器读 `T`，报 `Can not find result 'T' in the result provider 'nidx_spacer'` | 反解析输出出现 2 条 issues，但 `status=ok`、谱完整 | 属工具按类型排除不彻底，**不是工程损坏**；R/T 谱正常读回 | **Q7**：是否需要我绕过该工具（去掉 index 监视器）以换取全绿输出？去掉会损失 Fig.4 的定性证据 |
| `inspect_fsp.py` 的层位 diff 对含 `lattice` 键的 spec 返回 `unsupported_spec_shape`，`functional_layers_match = null` | 自动层位对照未执行 | `all_settings_match = true`、`all_materials_match = true`；层位已由 `build_fsp.py --check`（34 项）独立验证 | 并入 **Q7** |
| 没有 per-layer 损耗监视器、没有等效 ε/μ 反演 | C6 / C7 | 无法复现，见 §5 | Q4 已裁决，本项转为记录项 |
| 单胞 builder 不能建 UCA/UCB 双尺寸子晶格 | C8 | 无法复现，见 §5 | 是否需要立项做超胞能力（新技能/新 spec 结构）？ |
| 无自动化 A/B 对照（去地平面） | C5 的地平面必要性 | 需另建一份 spec 手动跑 | 是否需要我补一份 `no_ground` 对照工程？ |

### E. 其他阻塞

| 问题现象 | 影响范围 | 当前状态 | 需要我确认的事项 |
|---|---|---|---|
| 主 .fsp 79.8 MiB，接近项目 **100 MB 单文件上限**；P01 包已因 347 MB 课程主工程达 488.8 MB（`repro-card.md` R-007 待办） | git 归档 / 传阅 | 已附 478 KB `_buildonly.fsp` 备用；两版都可用 | **Q8**：入库只放 buildonly，还是两版都放？ |
| 交付目录位于 `cases/.../results/`，而技能把 `cases/` 视为只读参照系 | 归档合规性 | 本次**只新增文件**，未修改/覆盖任何既有资产；回归中间产物一律落在 `_scratch/p01_repro/` | **Q9**：是否要我把交付物整体挪到 `projects/` 下的独立单元？ |
| `.fsp` 二进制不能内嵌文字型元数据 | "工程包含执行入口/校验目标"的字面要求 | 以同目录 `spec_repro_p01.json` / `verify_repro.lsf` / 两份 md 承载 | **Q10**：接受"工程包"形式，还是要我用 Lumerical 分析组把校验逻辑固化进 .fsp（需要新增分析组脚本，会超出"不改 skill"的边界）？ |

---

## 7. 需要你确认的事项（汇总）

1. **Q1** — Si 基底厚度：保持 2 µm 假设，还是改成课程工程的 1715 nm？
2. **Q2** — 是否再出一版「课程工程数值设置」（acc 8 / 24 nm / 1e-5 / 1 ps / 3.5–11 µm·100 pts），把峰位推到 6.15 µm？
3. **Q3** — 是否补 20° 斜入射（Bloch）与 3–12 µm 宽谱重跑？
4. ✅ **Q4 — 已裁决（2026-11-09）**：接受「Lumerical ~0.82 为复现基准 + 标注求解器差异」。已落地到 spec 与验证脚本，本项关闭。
5. **Q5** — 能否提供 Fig.2 的数字化曲线 / 实验数据以便比对谱形？
6. **Q6** — ✅ 已降级：实测 `run_fdtd_sweep.py` 产物自带已存谱，不需要改 skill；仅确认是否接受「一次性脚本做同输入回归」这一补充动作。
7. **Q7** — 是否为换取 introspection 全绿而移除 `nidx_spacer` 监视器？
8. **Q8** — 入库只放 478 KB buildonly 版，还是两版都放（79.8 MiB 接近上限）？
9. **Q9** — 交付位置留在 `cases/P01_Absorber_042/results/`，还是迁到 `projects/`？
10. **Q10** — 接受"工程包（fsp + 同目录清单/脚本）"形式，还是要求把校验逻辑做成 .fsp 内的分析组？

---

## 8. 可重跑命令

```bash
cd F:/Lumercial_WS/FDTD_WS
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
D="cases/P01_Absorber_042/results/repro_2026-11-09_fsp"

# ① 从 spec 重建（只建不跑，逐字段自检）
"$PY" skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec "$D/spec_repro_p01.json" --out _scratch/p01_repro/rebuild \
  --tag rebuild --check --json

# ② 跑谱（结果落 _scratch，不写回 cases/）
"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec "$D/spec_repro_p01.json" --out _scratch/p01_repro/rerun --json

# ③ 反解析核对交付工程
"$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config _scratch/p01_repro/inspect_config.json --out _scratch/p01_repro/inspect --json
```

GUI 内：打开 `P01_Absorber_042_repro.fsp` → 看 R/T 监视器结果 →
在 Script File Editor 打开 `verify_repro.lsf` → Run → 读 PASS/FAIL 判定。
若想从零重算，打开 `P01_Absorber_042_repro_buildonly.fsp` → Run。

---

## 9. 合规声明

- 本次**没有修改、替换、重写任何 skill 的 `SKILL.md` / `scripts/` / `_shared/` / `assets/` 文件**。
  调用的均为现有技能：`fdtd-paper-parameter-extraction`（PDF 文本提取）、
  `fdtd-lumerical-fsp-build`（建模 + `--check`）、
  `fdtd-lumerical-unitcell-simulation`（求解 + 谱）、
  `fdtd-lumerical-fsp-introspection`（反解析验证）、
  `fdtd-lumerical-headless`（会话/收敛/结果读回规则）。
- 新增的一次性脚本（`run_and_store.py`、`verify_lsf.py`）与配置
  （`inspect_config.json`、`paper_text.txt`）全部放在 `_scratch/p01_repro/`，不进技能、不进版本库。
- `spec_repro_p01.json` 是从 `cases/P01_Absorber_042/config/spec_p01.json` **派生**的新文件，
  原 spec 未被改动；几何/材料/求解数值保持一致，仅增加场/折射率监视器与结论元数据。
- **Reproduce 模式纪律**：未为满足 0.97 去调 `l / w / a / ts`，未隐瞒失败轮次，
  未替人下"物理正确 / 可发表"的结论。求解器口径差异已于 **2026-11-09 由人裁决**（Q4 关闭）：
  接受 Lumerical ~0.82 为复现基准并显式标注差异。
- **本轮新增动作（2026-11-09 20:56 后）**：补跑 `validate_spec.py --strict`（0 error / 0 warning）
  与 `build_fsp.py --only-check`（34 项 0 mismatch，确认裁决只改元数据、几何未变）；
  重写 `verify_repro.lsf` 后 headless 复验通过；新增 `skill_gap_backlog.md`。
  **skills 本体仍一字未改** —— 精进由人执行。

---

## 10. 本轮更正记录

| 项 | 内容 |
|---|---|
| 上轮错误 | 判定 `run_fdtd_sweep.py` 产出的 .fsp「无已存谱」，据此把「技能链路缺口 / Q6」写成了阻塞。 |
| 证伪证据 | `_scratch/p01_repro/probe_sweep_fsp.py`：`point_00_base.fsp` = 83,725,458 B、`layoutmode=0.0`、`has_stored_R_result=True`。 |
| 真实机制 | 工程 `save()` 过（有磁盘路径）后，`run()` 结束引擎自动把结果写回；只有从未 `save()` 才静默失效。项目 11-09 日志 EXP-22 已记载。 |
| 已改 | 本报告 §2 / §6-D / §7-Q6 措辞；`verify_repro.lsf` 门禁；`spec_repro_p01.json` 裁决字段；`.workbuddy/memory/2026-11-09.md` 更正记录。 |
| 未删 | `run_and_store.py` 保留 —— 它仍提供两次独立运行 peak A 逐位一致的同输入回归证据。 |
