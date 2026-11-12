# 入射角物理与 v251 API 落点

> 本文件是 `fdtd-lumerical-oblique-incidence` 的按需加载参考。
> 数据来源：P08 课程视频（第三讲 宽角度完美吸收器）、课程 7 个 `.fsp` 的 lumapi 读回、
> Ansys 官方文档、以及 2026-11-13 在本机 Ansys Lumerical 2025 R1（v251）的实测探针。
> **所有属性名都是实测，不是按文档猜的。**

## 1. 三种口径

| 情形 | 横向 BC | 平面波类型 | 角度写在哪 | 频率口径 |
|---|---|---|---|---|
| 正入射 θ=0 | `Periodic` | `Bloch/periodic`（默认） | 不写（=0） | 任意带宽 |
| 斜入射单波长 | `Bloch` | `Bloch/periodic` | `source.angle theta` | **只能一个波长** |
| 斜入射宽带 | `Bloch`（BFAST 覆盖横向 BC） | `BFAST`（2018A+） | `source.angle theta` | 宽带 OK |

Bloch 的物理：单元左右边界的相位差

```
Δφ = 2π · P · sinθ / λ
```

P=1 µm、λ=1 µm、θ=30° ⇒ Δφ=π rad = 180°（课程 PPT p2）。
换 λ=1.3 µm 相位差就变 → **宽带下 Bloch 边界对每个频率给了不同的实际入射角**。

BFAST 让源在不同波长自动使用不同相位差，从而在整个带宽里维持同一个 θ。

## 2. 角度漂移（课程/官方解析真值）

`Bloch/periodic` 下 `angle theta` 只在源的中心频率 `f_sim` 成立：

```
θ(f) = asin( sinθ_sim · f_sim / f ) = asin( sinθ_sim · λ / λ_sim )
```

| 设定 | 实测（v251 `getsourceangle`） | 解析 |
|---|---|---|
| λ_sim=600 nm, θ_sim=30°, f=4.0e14 Hz (750 nm) | 38.650° | 38.682° |
| 同上 5.0e14 Hz (600 nm) | 29.977° | 30.000° |
| 同上 7.5e14 Hz (400 nm) | 19.457° | 19.471° |
| 官方 100 THz @30°（中心 125 THz） | — | 38.682° |
| 官方 150 THz @30° | — | 24.624° |

BFAST 下同样三个频点实测 **30.0 / 30.0 / 30.0**（无漂移）。
`getsourceangle('source', f)` 的入参是**频率 Hz**，不是波长（与 `getindex` 同类坑）。

## 3. 课程反例（天然负对照）

课程 17–21 min：先跑 `Bloch + 400–800 nm @30°`，吸收谱长波端「翘起来」，
**700 nm 处 A<0**。原因是漂移导致 R>1 的假信号。换 BFAST 后收敛正常。
现有 runner 的 `check_physical_range()` 原本只查 R/T，会让这个错误静默过关 →
EXP-73 把 `A` 加进了检查。

## 4. 机时倍率（Ansys BFAST 文档，相对正入射）

| θ | 0° | 30° | 60° | 70° | 80° |
|---|---|---|---|---|---|
| 倍率 | 1.0× | 2.0× | **7.5×** | 16.6× | 65.8× |

课程经验上限 **60°**（口述「超过 60 度 FDTD BFAST 做的还有点问题」）；
论文实验椭偏仪到 67°，不是 BFAST。本技能 `|θ|>60°` WARN、`>=85°` 拒绝。

课程日志量级：`wd` 7.586e-6 / 13719 iter、`wide_angle` 9.664e-6 / 18207 iter、
`wd_BFASK` 9.751e-6 / 55081 iter（BFAST 的 dt 更小，同 simulation time 下迭代更多）。

## 5. v251 属性落点（本机实测，2026-11-13）

| 属性 | 对象 | 可写 | 说明 |
|---|---|---|---|
| `angle theta` | `source` | ✅ | **唯一该写角度的地方** |
| `angle theta` | `FDTD` | ❌ inactive | BFAST 下是派生值，写 source 后自动同步（30→30） |
| `angle phi` | `source` | ❌ 2D inactive | **连 0 都不能写**；课程工程只能读到 0 |
| `plane wave type` | `source` | ✅ | 枚举 `BFAST` / `Bloch/periodic` / `Diffracting` |
| `x min bc` / `x max bc` | `FDTD` | ✅ | 斜入射倾斜面写 `Bloch` |
| `pml layers` | `FDTD` | ✅ | 课程默认 8；掠入射建议加厚 |
| `bfast alpha` | `FDTD` | ✅ | 课程 =1；官方建议取最小折射率 |
| `dt stability factor` | `FDTD` | 可读 | 课程 0.99 |
| `dt multiplier` / `pulse length` | — | **找不到** | 官方文档写了但本机 v251 `getnamed` 报 not found，不猜、不写 |

其它：
- 带结果的工程处于 **analysis mode**，任何 `setnamed` 报
  `use switchtolayout first`；改已有 `.fsp` 必须先 `switchtolayout()`。
- BFAST 官方只允许**一个**平面波源；本 builder 只创建一个 source，天然满足。
- X 方向 BC 显示 "overridden by BFAST" 属预期；课程 `wd_BFASK.fsp` 用 Periodic + BFAST
  仍收敛（9.751e-6），但 spec 应写 `Bloch` 保持一致。

## 6. 课程工程读回（`wide_angle.fsp`，30° BFAST）

| 项 | 值 |
|---|---|
| dimension / 注入轴 | 2D / y，source `Backward` |
| FDTD x span / y span | 0.8 µm / 1.0 µm；y ∈ [-0.15, 0.85] µm |
| x BC / y BC | `Bloch` / `PML` |
| source `plane wave type` | `BFAST` |
| source / FDTD `angle theta` | 30 / 30 |
| `polarization angle` | 90 |
| wavelength | 400–800 nm，50 个频点 |
| mesh accuracy / auto shutoff min | 6 / 1e-5 |
| simulation time | 5e-14（另一个 `oblique_BFAST.fsp` 用 2e-13） |
| pml layers / bfast alpha | 8 / 1 |
| 4 层（从下到上，y=0 起） | 80 nm Ag / 24 nm a-Si / 30 nm Ag / 12 nm a-Si |
| mesh override | y ∈ [0, 146 nm]，x span 1 µm |
| R / T 监视器 | Linear X，y=0.8 µm / -0.1 µm |

材料是椭偏实测 n/k（`model/Ag-nk.txt`、`model/aSi-nk.txt`，400–800 nm 步长 10 nm）。
`setmaterial("Sampled data", "sampled data")` 收的是 **ε(f)=(n+ik)²**，不是 (n,k)（D-013）。

## 7. 符号约定

P04 实测 `paper θ_i = −(Lumerical angle theta)`；课程扫 0→+60°。
本技能**永不自动取负**，每份 plan / metrics 都带
`sign_convention: "paper_theta_i = -lumerical_angle_theta"`，由人决定对照时怎么换算。

## 8. 会踩的坑

| 症状 | 根因 | 处置 |
|---|---|---|
| `setnamed("FDTD","angle theta")` 抛 inactive | 该属性只读/派生 | 只写 `source.angle theta` |
| `angle phi` 抛 inactive | 2D 没有这个可写属性 | 不写；φ≠0 拒绝 |
| Bloch + 宽带 A<0 / 长波上翘 | 边界相位差随波长变 | 换 BFAST；`check_physical_range` 补 A |
| analysis mode 报错 | 工程带结果 | `switchtolayout()` |
| `getsourceangle` 传波长 | 入参是 Hz | `c/λ` 换算 |
| 角度扫描所有曲线相同 | sweep 没覆盖到参数 | `collect` 的重复曲线检查会 exit 1 |
| 60° 机时暴涨 / 掠入射 PML 反射 | BFAST 7.5× + 薄 PML | 加 `pml_layers`，查 `_p0.log` 的 `diverging` |
| `T` 恒为小负数（≈−0.003），`check_physical_range` 报 `T 越界` | 不透明金属背板下 DFT 监视器的噪声零点，**不是**监视器压进 PML | spec 显式声明 `simulation.opaque_ground_plane: true`；原始 T 留 `T_raw` 列；别改 `PHYS_TOL` |
| 60° 报 `ERROR: ... fields are diverging`，R 却 >1 | BFAST 在色散 a-Si/Ag 上的角度硬上限；课程 `wide_angle.fsp` 改到 60° 同样发散 | 先测收敛上限再定角度网格；大角度留 N/A + 证据。注意引擎发散后仍打印 `Simulation completed successfully` |
| 45–55° 日志没 `diverging`、auto shutoff 也达标，但 `R=1.04..1.08` | 源归一化/能量守恒在掠入射先坏掉，比发散更早出现 | 不能按「小误差」放行；`check_physical_range` 必须拒绝 |

**角度上限实测表**（P08，v251 默认 dt=0.99 / pml=8 / alpha=1）：

| θ | 收敛 | R 最大 | 判定 |
|---|---|---|---|
| 0° | ✅ | 0.963 | 结果 |
| 30° | ✅ | ≈0.96 | 结果（课程锚点） |
| 35° / 40° | ✅ | 0.956 / 0.989 | 结果 |
| 45° / 50° / 55° | ✅ 日志无 diverging | 1.038 / 1.073 / 1.077 | **非物理** |
| 60° | ❌ diverging | 1.028 | **拒绝** |

试过且**无效**的补救：`dt stability factor` 0.95 / 0.90 / 0.50 / 0.25、
`pml layers` 24 / 32、`bfast alpha`=4、去掉 mesh override、`simulation time` 5e−14。
其中 dt=0.5/0.25 能压住发散，但 R 变成 1.019/1.018，只是换一种非物理。

## 9. 实测证据（EXP-75，v251）

| 对象 | T 范围 | 说明 |
|---|---|---|
| 本次 P08 θ=0 BFAST | `[−0.00305, −0.00007]` | 收敛 10102 步，auto shutoff 9.4e−6 |
| 课程 `wd.fsp` | `[−0.00420, −0.00009]` | 课程自带成品工程，同样为负 |
| 课程 `wd_BFASK.fsp` | `[−0.00365, −0.00007]` | 同上 |
| T 监视器 y=−0.18 → −0.60 µm | `[−0.00297, …]` | 几乎不变，排除 PML 位置因素 |
| `pml layers` 8 → 4 | 仍 −0.003 | 排除 PML 厚度因素 |

判断「PML 压进监视器」要看**量级**：P07 是 `T=−0.80 / A=1.60`，
不透明背板噪声只有 1e−3 量级且与监视器位置无关。
`run_fdtd_sweep.py` 的 `OPAQUE_T_NOISE_MAX=5e-3` 就是按这个量级设的硬闸，
`T=−0.50` 这类真错误仍会被拒。
