# PLAN-2026-11-13：入射角改变能力（oblique incidence）+ 角度扫描技能

> 状态：**已批准并执行完成（2026-11-13）** —— EXP-70…76 全部 `verdict=pass`，四门禁全绿。
> 触发：`cases/metasurface/P08_BroadbandAbsorber_043/lecture/第三讲 宽角度完美吸收器.mp4`
> 依据：`docs/constitution/skill-change-contract.md`（A/B/C 三档）、`docs/plans/AGENTS.md`（每步可回退）
> EXP 起编：**EXP-70**（台账已到 EXP-69）；本计划登记 EXP-70…76。
> 开工前置已完成：11-12 的未提交改动在 EXP-70 里以 `2f49a7d` 固化，基线干净。
> ⚠️ 执行中有三条判定偏差，**必读 §11**（D-01 不透明背板 T 噪声 / D-02 GPU / D-03 60° 发散）；
> 交付角度网格是 **0/30/40°**，不是批准时的 0/30/60°，60° 为 N/A 且课程工程同样发散。

---

## 0. 结论先行

课程里「改变入射角」不是改一个数字，而是**三种物理口径 + 一次扫描**：正入射用 Periodic、
斜入射单波长用 Bloch、斜入射宽波长用 BFAST；角度扫描扫的是 `::model::source::angle theta`。

落地方式确定为**两层、一份实现**：

1. **底层（改现有技能，C 档）**：`library/py/fsp_build.py` 把入射角做成 spec 一等公民；
   `build_fsp.py --check` 与 `validate_spec.py` 补双向校验。不改 `ev()`、不改 runner 算法。
2. **上层（新技能，零引擎）**：`fdtd-lumerical-oblique-incidence` 生成角度扫描计划并聚合结果，
   通过 `run_fdtd_sweep.py --sweep-json` 驱动已有 runner —— **不写第二份 builder / runner**。

关键取巧点：`run_fdtd_sweep.py` 的 `--sweep-json '{"theta":[...]}'` 会逐点覆盖
`spec["parameters"]`（`run_point()` 第 212–216 行实测），而 builder 的所有数值都走 `ev()`。
所以**只要角度是 parameters 里的一个变量，角度扫描天然免费**，不需要新 runner。

---

## 1. 视频解析结果（可重放证据）

### 1.1 媒体与解析产物

| 项 | 值 |
|---|---|
| 视频 | `第三讲 宽角度完美吸收器.mp4`，25:00.3 / 30 fps / 45010 帧 / 1280×720 / 531,609,288 B |
| 抽帧 | 35 张采样帧（60 s 间隔 + 前 10 min 加密）、21 张 1280×720 关键帧、3 张带时间标签总览图 |
| 音频 | 16 kHz mono WAV 48,010,744 B；faster-whisper `small` 转写，**1027 段 / 498.7 s** |
| 配套材料 | `上课ppt-宽角度可见光吸收器.pdf`（2 页）、论文 PDF（8 页）、`自测题_5问.md`、7 个课程 `.fsp` + 3 份 `_p0.log` |
| 全部原始产物 | `_scratch/regress/2026-11-13/`（`lecture_frames/`、`lecture_audio.wav`、`lecture_transcript.txt`、`whisper_models/`） |

解析链路：OpenCV `VideoCapture` 解码 → `imageio-ffmpeg` 抽音频 → `faster-whisper`。
两个本机坑：HuggingFace 直连 **502**（走 `HF_ENDPOINT=https://hf-mirror.com` 解决）；
`av` 新版去掉了 `metadata_errors` 参数导致 `decode_audio` 崩（改成 `wave` + numpy 直接喂
`float32` 波形数组绕过）。这两条只影响解析，不影响交付。

### 1.2 课程时间线

| 时段 | 内容 | 关键帧/证据 |
|---|---|---|
| 00:00–02:00 | 论文与结构：4 层 `[12 nm a-Si / 30 nm Ag / 24 nm a-Si / 80 nm Ag]`，400–650 nm 宽带、95.5% 峰值、`A = 1 − R`（底 Ag 挡住 T） | `t00000/t00090` |
| 02:00–13:00 | 正入射建模：2D、injection axis = y、x span 0.8 µm、x BC Periodic、y PML、`Bloch/periodic` 源、θ=0、pol=0、400–800 nm、mesh acc 6、R/T DFT 监视器、椭偏实测 nk | `t00330/t00660` |
| 14:00–17:00 | **Bloch 原理**：λ=1 µm @30°、P=1 µm → 左右边界差 ~180°；换 λ=1.3 µm 相位差就变 → **Bloch 只能单波长** | `t00900.png` + PPT p2 |
| 17:00–21:00 | 两个斜入射工程：先 Bloch @30°（宽带下**算错**），再 BFAST @30°（收敛好、结果正常） | `t01080`（Bloch 跑完 4.64e-5）、`t01200`（BFAST 运行中） |
| 21:00–24:00 | **角度扫描**：Optimizations and Sweeps → 参数 `angle` → `::model::source::angle theta`，0→60°，30 点；Visualizer 出 A(λ,θ) 二维图，对照论文 Fig.5 的 TE/TM 角度分辨谱 | `t01320.png`（Edit Parameter Sweep）、`t01380.png`（A(λ,θ) 热图 + Fig.5） |

口述补充（转写原文，术语有 ASR 错字但语义清楚）：
- 「布洛赫边界条件……波长不能是一个宽带的波长范围，必须是一个波长点」
- 「Bfast 的光源……能够自动的对左右两个边界在不同波长下使用不同的相位差……X 方向的边界条件被 Bfast 覆盖」
- 「角度不能超过 60 度，超过 60 度 FDTD BFAST 做的还有点问题，那么我们就准备扫到 60 度……扫 30 个点，也就进行 30 次计算」
- 「2018A 之前没有 BFAST……你要么升级版本，要么用单波长，一个点一个点地扫」

### 1.3 课程给出的三种口径（与官方文档一致）

| 情形 | 边界/源 | 角度落点 | 本期支持 |
|---|---|---|---|
| 正入射（θ=0，任意带宽） | `Periodic` + `Bloch/periodic` | 0 | ✅ 现状即可 |
| 斜入射 **单波长** | `Bloch` + `Bloch/periodic` | `source.angle theta` | ✅ EXP-71 |
| 斜入射 **宽带** | `BFAST` 源（2018A+），横向 BC 被覆盖 | `source.angle theta`（FDTD 区域自动同步） | ✅ EXP-71 |
| 2018A 之前 / 无 BFAST | 单波长扫描 + 插值 | 逐点 | ❌ 本期不做 |

**课程实测反例（天然的负对照）**：Bloch + 400–800 nm @30° → 长波端吸收「翘起来」、
**700 nm 处 A < 0**。现有 `run_fdtd_sweep.py` 的 `check_physical_range()` 只查 R/T，
不查 A，这个错误会**静默过关** —— 必须补。

### 1.4 课程工程读回（lumapi 实测，2026-11-13）

| 工程 | dimension / 注入轴 | x BC | source `plane wave type` | FDTD `angle theta` | source `angle theta` | pol | simulation time | source x span |
|---|---|---|---|---|---|---|---|---|
| `normal_incidence.fsp` | 2D / y | Periodic | Bloch/periodic | 0 | 0 | 0 | 5e-14 | 1.6 µm |
| `oblique_Bloch.fsp` | 2D / y | **Bloch** | Bloch/periodic | **0** | **30** | 90 | 2e-13 | 1.6 µm |
| `oblique_BFAST.fsp` | 2D / y | Bloch | **BFAST** | **30** | **30** | 90 | 2e-13 | 1.6 µm |
| `wide_angle.fsp` | 2D / y | Bloch | BFAST | 30 | 30 | 90 | 5e-14 | 0.8 µm |
| `wd_BFASK.fsp` | 2D / y | **Periodic** | BFAST | 30 | 30 | 90 | 5e-14 | 0.8 µm |

`wd_BFASK` 用 Periodic + BFAST 仍收敛（9.751e-6 / 55081 迭代），因为**BFAST 自己覆盖横向 BC**；
但 GUI 会显示 "overridden by BFAST" 警告。技能仍应把倾斜面 BC 写成 `Bloch` 以保持一致，
并把「用户显式写了 PML/Metal」判为错误。

### 1.5 API 硬事实（本轮实测，禁止猜）

1. `Bloch/periodic`：`FDTD.angle theta` **inactive** —— `setnamed("FDTD","angle theta",45)`
   抛 `the requested property 'angle theta' is inactive`。角度**只能写 source**。
2. `BFAST`：`setnamed("source","angle theta",45)` 后 **`FDTD.angle theta` 自动 30→45**；
   直接 set FDTD 依旧 inactive。→ 角度扫描扫 `source` 就够了，不必碰 FDTD 区域。
3. 带结果的工程处于 **analysis mode**：任何 `setnamed` 报
   `you cannot modify most simulation objects while in analysis mode, use switchtolayout first`。
   「改已有 .fsp 的角度」路径必须先 `switchtolayout()`。
4. 可读属性实测：`pml layers`=8、`pml type`、`pml profile`、`bfast alpha`=1、
   `background index`=1、`dt stability factor`=0.99、`set based on source angle`=1、
   `bloch units`=bandstructure、`source.offset`。
5. **`dt multiplier` / `pulse length` 在本机 v251 上 `getnamed` 报 "not found"** —— 官方文档写了
   「BFAST advanced options」里的这两个参数，但本地属性名不同/不可见。计划里**不写它们**；
   需要调 dt 时另开 EXP 先探测属性名，不许按文档猜。
6. `getsourceangle('source', 5e14)` → **30.0**（BFAST，各频率恒定）；这是漂移校验的现成工具，
   频率入参是 **Hz**。
7. 收敛日志：`wd` 7.586e-6 / 13719 iter、`wide_angle` 9.664e-6 / 18207 iter、
   `wd_BFASK` 9.751e-6 / 55081 iter（BFAST 的 dt 更小，同 simulation time 下迭代更多）。

### 1.6 解析真值（直接给 `--self-test` 用）

| 量 | 公式 / 值 | 出处 |
|---|---|---|
| Bloch 边界相位差 | `Δφ = 2π·P·sinθ/λ` → P=1 µm, λ=1 µm, θ=30° ⇒ **π rad = 180°** | PPT p2 与口述 |
| Bloch/periodic 角度漂移 | `θ(f)=arcsin(sinθ_sim·f_sim/f)`；官方例 100–150 THz @30° ⇒ **38.7° / 24.6°** | Ansys 注入角文档 |
| BFAST 机时倍率 | 0° 1.0× / 30° 2.0× / 60° **7.5×** / 70° 16.6× / 80° 65.8× | Ansys BFAST 文档 |
| BFAST 角度上限 | 课程经验 **≤60°**；论文实验到 67°（椭偏仪，非 BFAST） | 口述 + 论文 Fig.5 |
| 符号约定 | P04 实测 `paper θ_i = −(Lumerical angle theta)`；课程扫 0→+60° | `results/P04_.../five_angle_scan.py` |

---

## 2. 现有实现分析（读了什么、缺什么）

| 文件 | 角色 | 现状 / 缺口 |
|---|---|---|
| `library/py/fsp_build.py`（唯一 builder） | `build_simulation()` 写 BC、源、监视器 | 已支持 `source.plane_wave_type`（仅 spec 要求时才写，第 714–716 行）；**没有 `angle theta` / `angle phi`**，没有 `incidence` 决策，没有 `pml layers` / `bfast alpha`；`polarization_deg` 已走 `ev()`（可直接当扫描参数） |
| `skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py` | CLI + `--check` | `expected_properties()` **只断言几何 span/center/radius + mesh accuracy**，完全不查 source / BC → 角度写错了 check 全绿（单向门禁盲区，D-011 同类） |
| `skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py` | 建模 + 跑 + 出谱 | `--sweep-json` 覆盖 `parameters`，`expand()` 笛卡尔积 → **角度扫描可零成本复用**；`check_physical_range()` 只查 R/T，漏 A |
| `skills/fdtd-paper-parameter-extraction/scripts/validate_spec.py` | spec 结构/物理闸 | `BC_ALLOWED` 无角度语义；`--strict` 会放过「θ=30° + Periodic BC」这种物理错误配置 |
| `skills/fdtd-lumerical-session-control/scripts/session_control.py` | 已有 `.fsp` 白名单注入 | 第 221 行已 `switchtolayout`；`parameter_map` 可映射 `angle theta`，但需白名单 + EXP 验证（本期列为 slice 2） |
| `skills/fdtd-lumerical-figure/scripts/make_figure.py` | 出图 | `KINDS = stack/spectra/phase/field/fom/compare`，**没有 A(λ,θ) 热图 kind** → 首版只出 CSV + metrics |
| `agents/fdtd-sim-agent/skills.yaml` | 编排 | 第 114 行 note 仍写「dimension 2D is not supported yet (D-008)」，**已过期**（EXP-46 后支持，P08 全是 2D）→ 执行期 A 档订正 |
| `results/P04_.../five_angle_scan.py` | 一次性角度扫描 | 已有符号约定常量；**只收编约定，不复制脚本**（一份实现原则，D-005/D-006/EXP-02 三次教训） |
| `skills/INDEX.md`「空位」表 | 技能总表 | stage 1.8/1.9 仍列为「现状」说明、3.5+ 缺 Skill C；新增技能需同步 |

两个调用方（`build_fsp.py` 与 `run_fdtd_sweep.py`）import 同一份 `library/py/fsp_build.py`，
**改 builder 必须两边回归**。

---

## 3. 目标态 / 非目标

**目标**
1. spec 能声明入射角，builder 在 Bloch/periodic 与 BFAST 两种模式下都写对属性与 BC。
2. `--check` 与 `validate_spec.py` 对角度/BC 做**双向**校验，物理错误配置直接拒绝。
3. 新技能 `fdtd-lumerical-oblique-incidence`：零引擎生成角度扫描计划、驱动已有 runner、聚合
   `A(λ,θ)` / TE/TM 指标，带 `--self-test` 解析真值。
4. 端到端复现 P08 的 0/30/60° 宽带角度扫描，并与课程 `wide_angle.fsp`、论文 Fig.5 趋势对照。
5. 四门禁全绿、EXP 台账齐全、journal 交接。

**非目标（本期不做）**
- 不写第二份 builder / runner；不改 `ev()` 白名单、不动材料与监视器语义。
- 不实现 GUI parameter sweep 对象（Python 侧扫描等价且可复现）。
- 不做 3D 双轴倾斜（φ≠0）的完整实现：2D 只支持 θ，φ≠0 显式报错；3D φ≠0 留 slice 2。
- 不做 `figure --kind angle_map`（首版只出 CSV + metrics json）。
- 不做「已有 .fsp 直接改角度」的 session-control 白名单（slice 2）。
- 不改 `cases/`（只读），回归输出一律 `_scratch/regress/2026-11-13/`。

---

## 4. 接口设计

### 4.1 spec：单一真相源 = `parameters["theta"]`

```json
{
  "parameters": {"theta": 30, "pol": 90, "P": 0.8e-6},
  "simulation": {
    "dimension": "2D",
    "propagation_axis": "y",
    "bc": {"x": "Bloch", "y": "PML", "z": "PML"},
    "source": {
      "type": "plane",
      "plane_wave_type": "BFAST",
      "angle_theta_deg": "theta",
      "angle_phi_deg": 0,
      "polarization_deg": "pol",
      "wavelength_range": [400e-9, 800e-9]
    },
    "incidence": {
      "mode": "bfast",
      "angle_grid_deg": [0, 30, 60],
      "polarizations_deg": [0, 90],
      "sign_convention": "paper_theta_i = -lumerical_angle_theta",
      "pml_layers": 24,
      "bfast": {"alpha": 1.0}
    }
  }
}
```

**为什么不把角度写两份**：数值只在 `parameters` 里一份；`source.angle_theta_deg` 是表达式
（默认 `"theta"`，缺省 0），`incidence` 只放决策/元数据/扫描网格，不重复存数值。
`run_fdtd_sweep.py --sweep-json '{"theta":[0,30,60],"pol":[0,90]}'` 直接覆盖 `parameters`。

### 4.2 builder 写入规则（mode 矩阵）

| `incidence.mode` | plane wave type | 角度写到 | 倾斜面 BC | 频率口径 | 校验 |
|---|---|---|---|---|---|
| `normal`（θ=0 或缺省） | 现状不动（逐字节兼容） | 不写 | 现状不动 | 任意 | — |
| `bloch_single` | `Bloch/periodic` | `source.angle theta` / `angle phi` | 强制 `Bloch` | **单频点**（`wavelength_start == stop`） | 宽带且未显式 `allow_drift` → 拒绝 |
| `bfast` | `BFAST` | `source.angle theta` / `angle phi`（FDTD 区域自动同步） | 写 `Bloch`（引擎会覆盖） | 宽带 OK | 只许一个平面波源；`bfast alpha` = 最小折射率 |
| `auto` | 按带宽自动选：单频→Bloch，宽带→BFAST，θ=0→Periodic | 同上 | 同上 | 同上 | 选择结果写进 `build.json` |

倾斜轴由 `resolve_axes()` + φ 自动推导，**不接受用户手填**：2D 只有一个横向轴；
3D φ=0 → 注入轴 z 时倾斜面为 x；φ≠0 → 报错（slice 2）。

### 4.3 兼容性（8 条）

1. 不含 `incidence` 且不含 `angle_theta_deg` 的 spec：builder 不写任何新属性 → **P01 / P08 正入射逐位不变**。
2. 现有 `plane_wave_type` 行为保留；新增值 `"BFAST"` 走原有 `src_props` 通路，不新建分支。
3. **绝不写 `FDTD.angle theta`**（本机 inactive）；BFAST 靠 source 自动同步，check 读回两边比对。
4. `angle_phi_deg != 0` + `dimension: "2D"` → exit 2，附「2D 只有 θ」。
5. `|θ| > 60°` → WARN（课程经验 + 7.5× 机时）；`|θ| >= 85°` → 拒绝。
6. `bloch_single` + 宽带：用 `getsourceangle(f)` 算漂移，超 2° 拒绝（除非 `allow_drift: true`
   并在输出里记录逐频点实际角度）——**不静默放宽**。
7. BFAST 只允许一个平面波源；检测到第二个源 → 拒绝（官方限制）。
8. 倾斜面 BC 若被显式写成 `PML` / `Metal` → 拒绝；写成 `Periodic` → WARN 并改回 `Bloch`。

### 4.4 新技能 CLI（唯一脚本 `angle_sweep.py`）

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
S="skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py"

# ① 计划态：零引擎、不开会话，产出 angle_sweep_plan.json
"$PY" "$S" plan --spec cases/metasurface/P08_BroadbandAbsorber_043/config/spec_p08.json \
  --angles 0,30,60 --pol 0,90 --mode bfast \
  --out _scratch/regress/2026-11-13/angle_sweep --dry-run --json

# ② 交给已有 runner（本技能不自己开 lumapi 会话）
"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec <plan 产出的 spec_angles.json> \
  --sweep-json '{"theta":[0,30,60],"pol":[0,90]}' \
  --out _scratch/regress/2026-11-13/angle_sweep/run --json

# ③ 聚合：读 point_XX_*.csv + _p0.log，查收敛、查 A 越界、算指标
"$PY" "$S" collect --plan <.../angle_sweep_plan.json> \
  --run-dir <.../run> --out <.../angle_matrix.csv> --json

# ④ 脱机自检（解析真值，无需引擎）
"$PY" "$S" --self-test
```

一个脚本两个子命令，**不拆两份实现**；`plan` / `collect` / `--self-test` 全部零引擎，
`--dry-run` 必须在任何 `import lumapi` 之前 return。

### 4.5 输出契约

| 文件 | 内容 |
|---|---|
| `angle_sweep_plan.json` | mode、倾斜轴、BC、每个角度的 source 属性、符号约定、机时倍率预估、PML 层数、driver 命令、角度网格哈希 |
| `spec_angles.json` | 注入了 `incidence` 与 `parameters.theta/pol` 的 spec（供 runner 消费） |
| `angle_matrix.csv` | `theta_deg,pol_deg,lam_um,R,T,A` |
| `angle_metrics.json` | 每角度 `mean_A_400_650`、`delta_lambda_A90`、峰值漂移、TE/TM 最大差、各点 `auto_shutoff` / 迭代数、`sign_convention`、`check_coverage` |
| `angle_check.json` | A 越界检查、重复曲线检查、`getsourceangle` 漂移对照结果 |

### 4.6 集成点（改动文件清单）

| 文件 | 变更 | 档 |
|---|---|---|
| `library/py/fsp_build.py` | `angle_theta_deg` / `angle_phi_deg` / `incidence` 解析 + 写入 + `pml layers` / `bfast alpha` | C |
| `skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py` | `expected_properties()` 补 source/BC 双向断言 | C |
| `skills/fdtd-lumerical-fsp-build/SKILL.md` + `references/spec_extensions.md` | 新字段、CRITICAL #5（角度写 source 不写 FDTD）、mode 矩阵 | B |
| `skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py` | `check_physical_range` 补 A（课程 A<0 反例） | C |
| `skills/fdtd-paper-parameter-extraction/scripts/validate_spec.py` | 角度/BC 一致性规则 | B |
| `skills/fdtd-lumerical-oblique-incidence/`（新） | `SKILL.md` + `scripts/angle_sweep.py` + `references/angle-physics.md` | 新增 |
| `skills/INDEX.md` / `agents/fdtd-sim-agent/skills.yaml` | stage 2.5 条目 + 过期 note 订正 | A |
| `docs/plans/PLAN-2026-11-13-oblique-incidence.md` | 状态 → 已批准并执行；§11 偏差追记 | A |
| `experiments/EXP-70…76/` + `journal/2026-11-13.md` | 台账与交接 | — |
| 用户级 junction + `tools/skills-wire.py --apply` | 宿主接入 | — |

---

## 5. 实施步骤（每步可独立回退）

| # | 步骤 | 产出 / 判据 | EXP | 回退 |
|---|---|---|---|---|
| 1 | 固化基线：提交 11-12 未提交改动；跑四门禁存基线输出；把 §1 的解析产物路径写进台账 | `baseline/gates.txt` + 视频/工程取证表 | **EXP-70** | 删除本计划文件即可，无代码改动 |
| 2 | `fsp_build.py` 实现 §4.2 mode 矩阵；P01（3D）+ P08 正入射（2D）零破坏回归 | 旧 spec 逐位不变；BFAST 30° 读回 source/FDTD 都是 30 | **EXP-71** | 单文件 revert；旧 spec 无 `incidence` 不走新分支 |
| 3 | `build_fsp.py --check` 补 source/BC 断言 + 负对照（改 spec 角度不重建必红） | 断言数、0 mismatch、负对照 exit 1 | **EXP-72** | revert `expected_properties()` |
| 4 | `validate_spec.py` 角度/BC 物理闸 + runner 的 A 越界检查 | 每条违规配置都被拒；A<0 负对照被抓 | **EXP-73** | revert 两处新增检查 |
| 5 | 新技能 `angle_sweep.py`（plan / collect / --self-test，零引擎）+ SKILL.md | 解析真值 n/n、不 import lumapi、dry-run 秒级 | **EXP-74** | 删目录 + 回滚 INDEX/yaml |
| 6 | P08 端到端：0/30/60° × pol 0/90 BFAST；对照课程 `wide_angle.fsp` 与论文 Fig.5 趋势 | `angle_matrix.csv` + 每点收敛 + TE/TM 差 + 漂移对照 | **EXP-75** | 输出只在 `_scratch/regress/`，删目录即可 |
| 7 | 注册（INDEX / skills.yaml / junction / skills-wire）+ 四门禁 + journal + 计划标 DONE | 四门禁 exit 0；K17 负对照必红 | **EXP-76** | `skills-wire.py` 可重建入口；junction 用 `fs.unlinkSync` 删链接本身 |

优先级：2–4 是**必须**（底层正确性 + 负对照）；5 依赖 2；6 是交付证据；7 收尾。
**正确性（算错）必须排在门禁去噪（判错）之前** —— 先让角度真的写对，再补 check。

### 门禁影响（计划态，必须说清）

本文件登记 EXP-70…76 后，`check_experiments.py` 会报 **7 条 WARN**（缺 `result.json`），
这是「计划已登记、实验未执行」的预期状态，不是回归。批准执行时逐条补 `design.md` +
`result.json`（`verdict=pass` / `metrics` 有数字 / `negative_control.failed=true`）后转全绿。
**禁止为了当下全绿把 EXP 号移出 PLAN 或改文件名**（D-011 同类假绿），也禁止先写
`verdict: pass` 占位。

---

## 6. 测试与验证方案

**正对照**
1. 课程 5 个 `.fsp` 读回表（§1.4）逐字段对照 builder 产物。
2. BFAST @30°：`getsourceangle(f)` 在 400/600/800 nm 三处恒为 30°（本机已实测 5e14 → 30.0）。
3. P08 角度扫描 A(λ,θ) 与论文 Fig.5「到 60° 几乎不漂移」的趋势一致。

**负对照（每条必须红，且指名对象/属性）**
| # | 操作 | 期望 |
|---|---|---|
| N1 | `setnamed("FDTD","angle theta",45)` | 抛 `inactive`（本机已实测）→ builder 不得这么写 |
| N2 | 在 analysis mode 的工程上 setnamed | 抛 `use switchtolayout first`（本机已实测） |
| N3 | 改 spec 角度 30→35 但不重建，跑 `--check` | exit 1，报 `source.angle theta expected=35 actual=30` |
| N4 | `validate_spec.py --strict` 吃「θ=30 + Periodic BC」/「Bloch + 宽带」/「2D + φ≠0」 | 三条全拒绝 |
| N5 | 扫描计划里删掉 `theta`（所有角度相同） | `collect` 检出重复曲线并失败 |
| N6 | 从 `skills.yaml` 删掉新技能条目 | `[K17]` FAIL（沿用 EXP-65 已验证的门禁） |
| N7 | 构造课程那个 Bloch+宽带反例 | `A < 0` 被 `check_physical_range` 抓住，不许当成结果 |

**零破坏回归**：P01（3D）与 P08 正入射（2D）spec 重建，`.fsp` 字节数 /
`--check` 断言集 / `run_fdtd_sweep.py --dry-run` 输出与基线逐位一致（§5.2 容差表：≤1e-6）。

**物理漂移对照**：`bloch_single` 下用 `getsourceangle` 实测 θ(f)，与
`arcsin(sinθ_sim·f_sim/f)` 相差 ≤0.5°；`bfast` 下漂移 ≈0。

**收敛**：每个角度点读 `_p0.log` 的最后一个 `Auto Shutoff`（含指数），须 < `auto shutoff min`；
无 `Completed` / 有 `diverging` 一律不算数。课程参照：7.586e-6 / 9.664e-6 / 9.751e-6。

**门禁**：`check_skill_contract.py`、`skills-doctor.py`、`check_scripts.py`、
`check_experiments.py --require-all` 四条 exit 0；若动了复现流程再跑 `check_reproduction.py`。

---

## 7. 压缩档（时间不够怎么砍）

| 可砍 | 必须保 |
|---|---|
| 砍 TE/TM 双偏振（只跑 `pol=90`，课程默认） | 0/30/60° 三点 BFAST 扫描 |
| 砍 `collect` 子命令（只出 plan + 手工跑 runner） | `plan` + `--self-test` 解析真值 |
| 砍 `figure --kind angle_map`（首版只出 CSV + json） | `angle_metrics.json` 与收敛记录 |
| 砍「已有 .fsp 注入角度」session-control 路径（slice 2） | spec → 新 `.fsp` 主路径 |
| 砍 3D φ≠0、砍 `bfast alpha` 自动推断 | 2D θ-only + 不匹配时**显式报错** |
| 砍 P08 全量 30 点扫描（只做 3 点） | 与课程 `wide_angle.fsp` 的 30° 单点对照 |

**不可砍**：N1–N7 负对照、P01/P08 零破坏回归、EXP 台账、`getsourceangle` 漂移对照、
builder 单一实现、A 越界检查（课程反例）。

---

## 8. 风险与止损

| # | 风险 | 等级 | 止损 |
|---|---|---|---|
| R1 | **BFAST 与低损色散半导体发散**：官方文档明说 silicon 类材料可能因数值介电常数增益而发散；P08 的 a-Si 正是这类 | 高 | 先用课程 `wide_angle.fsp` 的实测 nk 与网格；每点查 `diverging`；必要时退回 `bloch_single` + 单频扫描（片 2） |
| R2 | 大角度 PML 掠入射反射 | 高 | `pml layers` 按角度加厚（本机默认 8）、`steep angle` PML；用「理想导体镜 R≈1」做角度无关性对照 |
| R3 | `dt multiplier` / `pulse length` 属性名本机找不到 | 中 | 不猜、不写；另开 EXP 探测；实在不行用 `dt stability factor` 并在台账标注降级 |
| R4 | 角度符号约定（P04 负号 vs 课程正角） | 中 | `sign_convention` 写进每份输出，永不自动取负；非对称结构必须显式声明 |
| R5 | Bloch/periodic 宽带角度漂移被当成「角度不敏感」 | 高 | `auto` 模式宽带强制 BFAST；`getsourceangle` 漂移对照；超 2° 拒绝 |
| R6 | 2D 注入轴 y（P08）与多数 spec 的 z 混淆，倾斜轴推错 | 中 | 由 `resolve_axes()` 推导并写进 plan；与 spec 显式值冲突时报错 |
| R7 | 改 `library/py/fsp_build.py` 波及两个调用方 | 高 | EXP-71 强制双调用方回归；单一实现不复制 |
| R8 | 工作区已有未提交改动，回归基线不干净 | 中 | 步骤 1 先提交/stash 并留基线输出 |
| R9 | 60° 机时 7.5×、30 点扫描 × TE/TM = 60 次运行 | 中 | 首版 3 点 × 1 偏振；课程日志给出 13719 / 18207 / 55081 迭代量级预算 |
| R10 | `cases/` 只读被写坏 | 低 | 全部输出落 `_scratch/regress/2026-11-13/`；`check_scripts.py` 把关 |
| R11 | 计划态 EXP WARN 被误判为回归 / 被人为消掉 | 中 | §5 门禁影响写死；禁止移出扫描范围 |

---

## 9. 会踩的坑（本机实测，按频率排序）

| 症状 | 根因 | 处置 |
|---|---|---|
| `setnamed("FDTD","angle theta")` 抛 inactive | 该属性在 `Bloch/periodic` 下只读；BFAST 下也是派生值 | **只写 `source.angle theta`**；BFAST 会自动同步 FDTD 区域 |
| `you cannot modify ... in analysis mode` | 载入的工程带结果，`layoutmode=0` | 先 `switchtolayout()` 再注入 |
| Bloch + 宽带的吸收谱长波上翘 / A<0 | 边界相位差随波长变，Bloch 只适用单波长 | 换 BFAST；同时给 `check_physical_range` 补 A |
| `plane wave type` 字符串写错 | 引擎只认 `BFAST` / `Bloch/periodic` / `Diffracting` | 用枚举常量，别拼字符串 |
| X 方向 BC 显示警告 "overridden by BFAST" | BFAST 自带横向边界 | 属预期；spec 仍写 `Bloch` 保持一致，不要改成 PML |
| `angle phi` 与 `polarization angle` 混用 | 前者定传播方向，后者定 E 场方向；θ=0 时 φ 与偏振角等价是特例 | 分开写，2D 禁用 φ |
| `getsourceangle` 传波长 | 入参是**频率 Hz**（与 `getindex` 同类坑） | `c/lambda` 换算 |
| BFAST 多光源 | 官方限制「ONLY one plane wave source」 | builder 检测并拒绝 |
| 课程 30° 用 `simulation time=2e-13`、正入射 5e-14 | BFAST 收敛慢、dt 更小 | 别把 200 fs 当通用默认；按角度设并查 `_p0.log` |
| `skills.yaml` 的 2D 过期 note | 11-12 未同步 | 执行期 A 档订正 |

---

## 10. 待确认的三件事（批准时告诉我）

1. **范围**：推荐「只做 slice 1」= spec→角度建模 + 角度扫描；「已有 `.fsp` 直接改角度」
   （session-control 白名单注入）和 `figure --kind angle_map` 放 slice 2。
2. **技能名 / stage**：推荐 `fdtd-lumerical-oblique-incidence`，stage **2.5**
   （`fsp-build`(2) 之后、`unitcell-simulation`(2/3) 之前；`hands_to` = runner）。
   备选 `fdtd-lumerical-angle-sweep`（更窄，只描述扫描）。
3. **EXP 起编与规模**：推荐从 **EXP-70** 起，首版 7 条 EXP-70…76；
   P08 端到端首版做 **3 角度 × 1 偏振**（0/30/60°、`pol=90`），不是课程的 30 点 × TE/TM。

> 确认后才动代码。执行中若发现判据不可达（如 BFAST 对 a-Si 发散、属性名找不到），
> **当场改判据并在 §11 追记**，不静默放宽。

## 11. 执行中的判定偏差追记

格式参考 `PLAN-2026-11-11-percell-fsp.md` §9：原判据 → 实测反证 → 新判据 → 影响哪些 EXP。

### D-01（EXP-75，2026-11-13）：不透明背板下 `T` 的判据

**原判据**（§5 步骤 4 / EXP-73）：`metrics()` 对 R、T、A 都用 `check_physical_range()`
卡 `[0,1]±1e-3`，其中 `T` 直接取 T 监视器的原始值。P08 0° 首轮因此 `ValueError:
T 越界 [-0.003, -0.000]`，三个角度一个都没落盘。

**实测反证**（全部实机，非猜测）：

| 证据 | 结果 |
|---|---|
| 本次 P08 θ=0 BFAST（`point_00_theta_0_pol_90.fsp`） | `T ∈ [-0.00305, -0.00007]`，均值 −0.00106；`R ∈ [0.0512, 0.9633]`；`_p0.log` 显示 BFAST 生效、auto shutoff 收敛、10102 步、`Simulation completed successfully` |
| **课程自己的成品工程** `wd.fsp` / `wd_BFASK.fsp` | `T ∈ [-0.00420, -0.00009]` / `[-0.00365, -0.00007]`，均值 −0.00144 / −0.00122；`R ∈ [0.0465, 0.9707]` / `[0.0542, 0.9419]` |
| A/B 对照 1：T 监视器从 y=−0.18 µm 移到 −0.60 µm（`below_structure` 0.3→1.0 µm） | `T_min` −0.00305 → −0.00297；`R_min` 0.0511566 → 0.0511557（差 9e−7） |
| A/B 对照 2：`pml layers` 8→4 | 仍报 `T 越界 [-0.003, -0.000]` |

结论：这是 **80 nm Ag 不透明背板下 DFT 功率监视器的数值噪声零点**（物理上 T≡0），
与监视器压进 PML 无关（P07 那种是 `T=−0.80 / A=1.60` 量级）。课程工程同样存在，
不是本次建模引入的错误。

**新判据**（不静默放宽，改成显式物理契约）：

1. spec 必须**显式声明** `simulation.opaque_ground_plane: true` 才走新路径；
   旧 spec 逐位不变（EXP-71 的调用序列 A/B 等价性保持）。
2. 新路径里 `T` 按物理取 0、`A = 1 − R`；但**原始监视器值不丢弃**：写进 `res["T_raw"]`、
   `T_raw_abs_max` 与 `point_*.csv` 的第 5 列 `T_raw`，并进 `summary.csv`。
3. **硬噪声上界 `OPAQUE_T_NOISE_MAX = 5e-3`**：`|T_raw|` 超过即报错。真正坏的监视器
   （`T=−0.50` / `+0.20`）依旧被拒，门禁仍然 load-bearing。
4. `validate_spec.py` 拒绝 `opaque_ground_plane=true` + `mode="transmission"`（矛盾声明），
   也拒绝非 bool 值。
5. R / A 的 `[0,1]` 门禁**完全不变**；声明后 `A` 是派生量，`A<0` 必先被 R 门禁抓到。

离线负对照 `_scratch/regress/2026-11-13/oblique/EXP-73/amend_opaque_t.py`：7 条全过
（A 旧 spec 仍红 / B 声明后接受且留证 / C·D 噪声上界抓坏监视器 / E R 门禁 / F A 门禁 / G 派生关系）。

**影响哪些 EXP**：EXP-73（门禁语义，追加 amendment，不改原 `verdict`）、EXP-75（P08 端到端，
spec 加 `opaque_ground_plane` 并重跑）、EXP-76（文档与门禁回归）。§6 正对照 3 的
「A(λ,θ) 趋势」判据不变。

### D-02（EXP-75）：首轮 GPU 失败

首轮 `run_fdtd_sweep.py` 报 `GPU simulation only supports 3D` + `GPU simulation does not
support the use of BFAST sources`。根因是全局 `FDTD\GPU-mode=true`。
**处置**：2D+BFAST 一律走 `tools/gpu_guard.py --run` 切 CPU（try/finally 自动还原）；
并把 sweep 网格内嵌进 `spec_angles.json`，避免 cmd.exe 下 `--sweep-json` 引号被吞。
判据不变。

### D-03（EXP-75）：60° BFAST 发散，且**课程原工程同样发散**

**原判据**（§5 步骤 6 / §6 正对照 3）：P08 端到端做 0/30/60° × `pol=90` BFAST，
「到 60° 几乎不漂移」与论文 Fig.5 趋势对照。

**实测反证**：0° 与 30° 均收敛（10102 / 24549 步，auto shutoff 9.4e−6 / 9.95e−6），
但 **60° 报 `ERROR: Early termination of simulation, the electromagnetic fields are diverging`**
（60157 步、Auto Shutoff 冲到 116454、R 最大 1.028）。

| 对照 | 配置改动 | 结果 |
|---|---|---|
| v1 | `dt stability factor` 0.99→0.95 | R 落在 [0,1] 但 **仍 diverging**（shutoff 8966）→ 门禁漏判 |
| v2 / v3 / v4 | `pml layers` 24 / dt0.95+pml24 / dt0.90+pml32 | 全部 diverging，R>1 |
| b1 / b2 | dt 0.50 / 0.25 | 不 diverging 且 shutoff≈9.8e−6，但 **R 最大 1.019 / 1.018**（非物理） |
| b3 / b4 | `bfast alpha` 4 / dt0.5+alpha4+pml24 | diverging |
| b5 | 去掉 mesh override | diverging（shutoff 2825） |
| b6 | `simulation time` 改课程值 5e−14 | diverging（shutoff 112731） |
| **course_60** | **直接把课程 `wide_angle.fsp` 的 `source.angle theta` 改成 60 并跑** | **diverging（shutoff 104477）** |

结论：60° 发散是 **v251 上这套 a-Si/Ag 色散材料 + BFAST 的固有限制**，课程自己的工程
也复现，不是本次 spec 建模错误。`dt=0.5` 只压住发散却把 R 推到 1.019，属于换一种非物理，
不接受。§6 风险表 R1（BFAST 与低损色散半导体发散）实际发生。

**收敛上限实测**（默认 v251 设置：dt=0.99 / pml=8 / alpha=1，即课程同款）：

| θ | 收敛 | R 最大 | 判定 |
|---|---|---|---|
| 0° | ✅ 10102 步 | 0.963 | 结果 |
| 30° | ✅ 24549 步 | ≈0.96 | 结果（课程锚点） |
| 35° / 40° | ✅ shutoff ≈9.7e−6 | 0.956 / **0.989** | 结果 |
| 45° / 50° / 55° | 无 diverging、shutoff≈9.8e−6 | **1.038 / 1.073 / 1.077** | 非物理，拒绝 |
| 60° | ❌ diverging | 1.028 | 拒绝；课程工程同样发散 |

BFAST 的 R>1 随角度单调增长，先于发散出现，是**源归一化/能量守恒被破坏**的信号，
不能当「小误差」放过去。

**新判据**：角度网格改为 **0 / 30 / 40° × pol=90**（3 点，保留批准网格里的 0° 与课程
30° 锚点，把不可达的 60° 换成实测干净上限 40°）。判据不变：**每点必须收敛且 R/T/A
落在 [0,1]**。60° 与 45/50/55° 作为 **N/A + 证据** 留在 `_scratch/regress/2026-11-13/oblique/`
的对照台账（`controls_60.json` / `controls_60_round2.json` / `angle_ceiling.json`），
不写成结果、不写「到 60° 不漂移」。论文 Fig.5 的趋势对照只在 0–40° 已收敛范围内陈述。

**副产物（正确性修复，不是去噪）**：v251 在 `fields are diverging` 之后仍打印
`Simulation completed successfully`，且 v1 的 R 仍在 [0,1] —— 只靠 `check_physical_range`
会**放发散结果过闸**。已在 `run_fdtd_sweep.py` 增加 `check_engine_log()`：
读 `<fsp>_p0.log`，`diverging` 字面量出现即抛错；日志比 fsp 旧则报 N/A 不假装收敛。
离线负对照 H/I 已验证（收敛日志过、发散日志红）。

**影响哪些 EXP**：EXP-73（追加 amendment）、EXP-75（角度网格与判据）、EXP-76（文档）。
