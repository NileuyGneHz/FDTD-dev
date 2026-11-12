# EXP-71 — builder 实现入射角 mode 矩阵 + 零破坏回归

## 假设

`library/py/fsp_build.py` 是 `build_fsp.py` 与 `run_fdtd_sweep.py` 共用的唯一实现。
把入射角做成 spec 一等公民后：

1. 不含 `incidence` 且不含 `angle_theta_deg` 的旧 spec 必须**逐调用不变**（不是"看起来差不多"）。
2. 斜入射只需要写 `source.angle theta`，`FDTD.angle theta` 由 BFAST 自动同步，绝不能自己写。
3. 角度是 `parameters` 里的表达式（`"theta"`），所以 `run_fdtd_sweep.py --sweep-json` 天然能扫角度。

## 开工前的实测证据（禁止猜 API）

`_scratch/regress/2026-11-13/oblique/probe/probe_api.py` 与 `probe2.py`，v251 本机：

| 事实 | 结果 |
|---|---|
| `setnamed("FDTD","angle theta",45)` | **inactive**，抛错（N1） |
| BFAST 下 `setnamed("source","angle theta",30)` | 成功；`FDTD.angle theta` 自动 0→30 |
| BFAST `getsourceangle(f)` @4e14/5e14/7.5e14 Hz | 30.0 / 30.0 / 30.0（无漂移） |
| Bloch/periodic 单波长 600 nm @30° 同上三频点 | **38.650 / 29.977 / 19.457 度**（漂移） |
| `setnamed("source","angle phi",0)` in 2D | **inactive**（连 0 都不能写）—— 计划未料到 |
| `FDTD.pml layers=24` / `bfast alpha=1` | 均可写、可读回 |
| analysis mode 下 setnamed | `use switchtolayout first` |

课程 `wide_angle.fsp` 读回：2D / y 注入 / x BC Bloch / BFAST / θ=30 / φ=0 / pol=90 /
400–800 nm / mesh acc 6 / auto shutoff 1e-5 / pml layers 8 / bfast alpha 1 / x span 0.8 µm /
FDTD y span 1.0 µm；4 层从下到上 80 Ag / 24 a-Si / 30 Ag / 12 a-Si（两组同名对象）。

## 判据

1. P01（3D）与「无 incidence 的 2D spec」在旧/新 builder 下的 **lumapi 调用序列逐项相同**。
2. P08 BFAST 30° 工程建出来，`source.angle theta` 与 `FDTD.angle theta` 都是 30、
   `plane wave type=BFAST`、x BC=Bloch、pml layers=8、bfast alpha=1。
3. `getsourceangle` 三频点恒 30°；Bloch 漂移解析式与实测 38.650/29.977/19.457 吻合。
4. 五种非法配置全部被拒绝（2D φ≠0 / |θ|≥85 / bloch_single+宽带 / 倾斜面 PML / 口径冲突）。

## 负对照

- **N1**：在**建出来的** `p08_30.fsp` 上 `setnamed("FDTD","angle theta",45)` 必须抛
  `inactive`；若成功，说明 builder 依赖了一个只读派生属性。
- **A/B 阴性**：旧 builder 吃同一份带 `incidence` 的 spec 时**完全不写 `angle theta`**；
  若旧 builder 也写了角度，说明新分支不是 load-bearing（假轮次）。

## 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" _scratch/regress/2026-11-13/oblique/probe/probe_api.py
"$PY" _scratch/regress/2026-11-13/oblique/probe/probe2.py
"$PY" _scratch/regress/2026-11-13/oblique/make_p08_spec.py
"$PY" skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec _scratch/regress/2026-11-13/oblique/spec_p08.json \
  --out _scratch/regress/2026-11-13/oblique/EXP-71/p08 --tag p08_30 --check --json
"$PY" _scratch/regress/2026-11-13/oblique/EXP-71/equiv_legacy.py
```

## 实测结果

- 零破坏：P01 3D `67/67 calls, 0 diffs`；P08 2D legacy `59/59 calls, 0 diffs`；
  P01 `.fsp` 字节数 `474963` 与 EXP-69 基线逐位一致，`--check 39/0`。
- P08 30° 建出 `layoutmode=1`、无 `_p0.log`、`bytes=477778`、`--check 32/0`；
  读回 source/FDTD `angle theta` 均 30.0，`getsourceangle` 三频点 30/30/30。
- 解析漂移 `asin(sin30°·λ/λ_sim)`：750/600/400 nm → 38.682 / 30.000 / 19.471 度，
  与引擎实测 38.650 / 29.977 / 19.457 一致（差 <0.03°，来自中心频率取整）。
- 5 条非法配置全部 `ValueError` 拒绝。

## 判定偏差（同步记入 PLAN §11）

1. **2D 的 `angle phi` 连 0 都不可写** → 新分支彻底不写 `angle phi`；φ≠0 一律拒绝。
   计划 §4.2/§4.3 原写「2D 禁用 φ」，实现更严格：不是"禁用非零"，是这个属性在 2D 不存在可写路径。
2. **P08 没有现成 spec** → 由课程 `.fsp` 对象树 + 实测 nk 现场生成
   `_scratch/regress/2026-11-13/oblique/spec_p08.json`；`cases/` 保持只读。
3. **去掉 glass 衬底** → 底 80 nm Ag 已不透明（T≈0），课程 glass 大半在 FDTD 区外；
   去掉后 FDTD y span 1.146 µm（课程 1.0 µm），代价是 A(λ) 只做趋势对照，不逐点复现。
