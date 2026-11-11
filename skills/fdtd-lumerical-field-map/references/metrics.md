# `field_metrics.json` 逐字段定义

写进 `acceptance.json` 或报告前先看这张表：同一个名字在不同论文里含义不同，
这里只有一个定义。

## 顶层

| 字段 | 含义 | 注意 |
|---|---|---|
| `source` | `--npz` 的路径，或 `<fsp>:<monitor>` | 台账要能追到具体文件 |
| `component` | 实际参与计算的那一路：`\|E\|` / `Ex` / `Ey` / `c_plus…` / `c_minus…` | **报告必须抄这一行**。写「交叉偏振」而不写是哪一路，别人无法复算 |
| `basis` | `cartesian` 或 `cpol` | |
| `background_subtracted` | 是否减了背景组 | `false` 时数字里含入射场，不能直接当散射场用 |
| `wavelength_um` | 选中的波长 | `nf>1` 时这是必填项，脚本不猜 |
| `axes.varying` | 实际变化的坐标轴 | 与监视器法向一起决定数据是「剖面」还是「横向面」 |
| `axes.prop` | 传播轴 | `prop_axis_source` 是 `default` 时，报告要写明「按默认值推的」 |
| `axes.prop_axis_source` | `cli` / `default` / `invariant-axis` | |
| `axes.transverse` | 横向轴（`focus`/`phase`/`kspace` 的 `u`） | |
| `freq.index` / `freq.n_total` | 选中第几个频点 | `n_total>1` 而没给波长时脚本直接退出 2 |

## `focus`

| 字段 | 单位 | 定义 |
|---|---|---|
| `z_focus_um` | µm | 轴上强度剖面 `I_onaxis(v)` 在 `v > --z-start-um` 区间的**最大值位置**。`I_onaxis` = `|u| <= --half-width-um` 内 `|E|²` 的算术平均 |
| `focus_gain` | — | `I_onaxis(z_focus) / I_onaxis(第一个 v > z-start 的点)`。**不是**聚焦效率 |
| `has_real_focus` | bool | `focus_gain > 1.2` 且 `fwhm_um` 有限 |
| `fwhm_um` | µm | 焦斑平面上 `I(u)` 的**连续半高全宽**：从峰值向两侧走，取第一次跌破半高处的线内插值。旁瓣不参与 |
| `dof_um` | µm | 轴上剖面 `>= 峰值/2` 的连续区间长度 |
| `peak_I_on_axis` | — | 轴上峰值强度（与 `|E|²` 同单位，随源归一化） |
| `off_axis_ratio` | — | `\|u\|>half-width` 区域峰值 / 轴上峰值。**>2 且 `has_real_focus=false` 时是离轴焦，不是无焦** |
| `z_virtual_um` | µm | `v < -z-start` 区间的峰值位置（反射/虚像） |
| `warning` | str | 离轴告警原文，出现时必须抄进报告 |

**已知边界**：焦点离轴时 `z_focus_um` 与 `fwhm_um` 都在骗人（它们只看 `|u|<=half-width`）。
先看 `off_axis_ratio`。

## `phase`

| 字段 | 单位 | 定义 |
|---|---|---|
| `probe_z_um` | µm | 实际取到的探针面（离 `--probe-z-um` 最近的一层） |
| `fit_slope` | — | `measured_phase` 对 `design_phase` 的**加权**最小二乘斜率，权重 `\|E\|²`。`\|slope\|=1` 表示形状对；符号是极性（收敛透镜为 −1） |
| `fit_slope_abs` | — | 上式的绝对值，验收表通常用这个 |
| `fit_offset_rad` | rad | 拟合常数项（任意，含源相位） |
| `fit_rms_rad` | rad | 加权残差 RMS。>0.5 rad 说明相位面本身不平滑，斜率没有意义 |
| `phase_swing_over_2pi` | ×2π | 解缠相位的摆幅，只用 `\|E\|>10%` 峰值的点统计 |
| `n_used_frac` | — | 参与摆幅统计的点占比 |

**已知边界**：`--design-kind none` 时 `fit_slope` 显式为 `null`，不是 0——
0 会被读成「测了且为 0」。

## `oam`

| 字段 | 单位 | 定义 |
|---|---|---|
| `oam_charge` | — | 半径 `ring_radius_um` 的圆环上 `φ(θ)` 的线性斜率，`E ~ exp(i·l·θ)` |
| `oam_charge_round` | int | 四舍五入到整数，用于「设计电荷 = 3」这类判据 |
| `oam_fit_rms` | rad | 线性拟合残差。>0.3 rad 说明环上不是一个纯涡旋 |
| `ring_radius_um` | µm | 实际取样半径（缺省 `0.4 × min(\|u\|max, \|v\|max)`） |
| `n_used` | — | `\|E\| > 0.2×中位数` 的点数；太少时不给电荷 |

**已知边界**：需要**横向面**监视器（法向 = 传播轴）。x-z 剖面里谈方位角相位是错的，
脚本会直接报错。

## `kspace`

| 字段 | 单位 | 定义 |
|---|---|---|
| `kx_over_k0_main` | — | 面内 FFT 主峰（×16 零填充 + 抛物插值后的值），`k0 = 2π/λ` |
| `angle_deg_main` | deg | `asin(kx/k0)`；`\|kx\|>k0` 时为 `null`（倏逝，没有出射角） |
| `peaks[]` | — | 前 N 个峰：`kx_over_k0` / `angle_deg` / `power_frac` / `bin_width_kx_over_k0` |
| `decay.decay_length_um` | µm | 给定 `--decay-kx` 时，该 `kx` 分量沿传播轴的 `A·exp(-v/L)+C` 拟合长度 |
| `decay.theory_um` | µm | `1/sqrt(kx²-k0²)`，只在 `\|kx\|>k0` 时有定义 |

**判读**：`bin_width_kx_over_k0` 是这块网格能分辨的最小间隔。要分辨两个相近级次，
先加密横向采样，不要靠插值。

## 不报的量（不要拿别的数冒充）

| 量 | 为什么不在这里 |
|---|---|
| 聚焦效率 | 需要入射功率归一化（源平面监视器 / `T` 谱），属 stage 2/3 的账 |
| 绝对相位 | 源相位未被标定；本技能只给相对量（斜率、摆幅、相位差） |
| 远场方向图 | 需要近场到远场的传播积分；`kspace` 给的是面内角谱，不是 2π 立体角上的方向图 |
