---
name: fdtd-lumerical-figure
description: >
  把仿真数据变成图，零引擎、零许可、无显示器也能跑（matplotlib Agg）。
  六类图：stack（层结构侧视）、spectra（R/T/A 谱并标注峰值）、phase（相位与相位差）、
  field（|E| 场图）、fom（目标函数随迭代）、compare（两条谱对比）。
  每个图上的数字都从被画的数据现算，缺列直接报列名而不是画空白图。
  触发词：出图、画谱、plot、保存 png、场图、收敛曲线、两张谱对比、缺列报错。
agent_created: true
---

# fdtd-lumerical-figure（stage 5）

## 1. 什么时候用它

任何"把已经算出来的数变成图"的场合。它**不碰 lumapi**：不建模型、不跑仿真、不读 `.fsp`。
输入永远是落盘的数据（csv / npz / spec.json）。

| 输入 | kind | 需要的列 / 键 |
|---|---|---|
| spec.json（含 `objects[]`） | `stack` | `center[2]`、`span[2]`（2D 对象自动跳过） |
| sweep 的 `point_*.csv` | `spectra` | `lam_um` + `R`/`T`/`A` 任意 |
| `phase.csv` | `phase` | `lam_um` + (`dphi_deg` 或 `phi_x_deg`+`phi_y_deg`) |
| session-control 的 `.npz` | `field` | 任意二维数组键（优先 `E`） |
| 设计循环台账 | `fom` | `iteration` + `fom` |
| 两个 `point_*.csv` | `compare` | 两边都有 `lam_um` 与同一指标列 |

## 2. 核心工作流

```bash
python skills/fdtd-lumerical-figure/scripts/make_figure.py \
  --kind spectra --input _scratch/regress/2026-11-09/EXP-26/run/point_00_base.csv \
  --out _scratch/fig/p01_spectra.png --json

# 对比两条谱（各自的构建 / 口径）
python skills/fdtd-lumerical-figure/scripts/make_figure.py \
  --kind compare --input a.csv b.csv --label "11-09 build" "11-03 archive" \
  --out _scratch/fig/compare.png --json
```

`--dry-run` 会真的做一次列校验（不是空转）：拿不到必需列就 exit 2。

## 3. CRITICAL（违反即停止）

1. **不碰 lumapi**。这里不建模型、不跑仿真、不读 `.fsp`；一旦引入引擎调用，出图就重新变成
   需要许可与机时的操作，而它本可以是零成本重跑的。
2. **图上任何数字都必须从被画数组现算**。写死一个 "peak = 0.97" 会让图与台账脱钩，
   而图往往比台账更容易被当成结论（EXP-45 就是为此把输入乘 1.05 看标注是否跟随）。
3. **缺必需列时不许画**。`exit 2` + 报列名；画一张空白图比报错危险得多，因为没人会再看第二眼。
4. **中文字体不要假设存在**。默认 DejaVu 不含中文，标题里写中文会变成方框；要中文先装字体并设
   `font.sans-serif`，否则用英文/数字。

## 4. 两条硬规则

1. **图上数字必须来自被画的数据**。`spectra` 的峰值文字、`fom` 的最佳点、`compare` 的
   peak delta 全在绘图时现算并回写到 `--json` 的 meta 里。事件（EXP-45）：把 csv 里
   `A` 整体乘 1.05，标注从 `0.8069` 跟着变成 `0.8473`；如果哪天它不动了，说明有人在图上写死了数。
2. **缺列要报列名，不许画空白图**。事件（EXP-44）：删掉 `lam_um` 后 exit 2，
   输出 `缺少列 lam_um；实际列 = A, R, T`，且一个文件都不写。反过来，删掉 `T` 是允许的
   —— 反射式器件本来就没有 T，这条不是缺陷。

## 4. 常见坑

- 中文字体：默认 DejaVu 不含中文，坐标轴标题目前一律英文/数字，避免方框。要中文标题先装字体
  并设 `matplotlib.rcParams["font.sans-serif"]`，别指望默认能显示。
- `field` 的 npz 里如果还留着 `Lumerical_dataset` 之类的对象数组，读的时候必须
  `allow_pickle=False`（本脚本就是这么读的），所以 dump 端要先过滤——见
  `fdtd-lumerical-session-control` 的 `format: npz`。
- `stack` 只画 z 方向；`2drect` 这种零厚度片没有 z span，会被跳过并在 meta 的
  `skipped_no_z` 里计数，不会静默当成一层。

## 5. Examples

**P01 的谱 + 峰值**（真实产物，`peak A=0.8069 @ 5.85 µm`）：

```bash
make_figure.py --kind spectra \
  --input _scratch/regress/2026-11-09/EXP-26/run/point_00_base.csv \
  --out _scratch/regress/2026-11-09/EXP-44/fig_spectra.png --json
# meta: {"main":"A","peak_value":0.8069379708102874,"peak_lam_um":5.85,...}
```

**同一个脚本出六类图**：见 `experiments/EXP-44` 的 `verify.json`（6/6 非空 + 缺列负对照）。

## 6. 相关文件

| 文件 | 用途 |
|---|---|
| `scripts/make_figure.py` | 唯一入口（六类图 + 列校验） |
| `experiments/EXP-44` | 六类图与缺列负对照 |
| `experiments/EXP-45` | 图数一致性（扰动输入，标注必须跟着动） |
| `skills/fdtd-lumerical-session-control/scripts/session_control.py` | 场数组 `.npz` 的来源 |
