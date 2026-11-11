---
name: fdtd-holo-phase-retrieval
description: >
  从目标强度图反推相位版图：Gerchberg-Saxton 交替投影，产出全息面连续相位、
  N 阶量化相位（2/4/8）与重建指标（效率/RMSE/Strehl），零引擎、零许可。
  当超表面全息、超透镜、涡旋这类课题需要先定「每个像素该给什么相位」再建模时使用；
  已有仿真结果要提取 dphi 的请走 stage 4，别用本技能。
  触发词：全息、相位恢复、GS、Gerchberg-Saxton、目标图、相位版图、hologram。
---

# GS 相位设计：目标图 → 相位版图

## 概述

`scripts/gs_retrieval.py` 消费一张目标强度图（png/npz）与采样参数，用 GS 交替投影
反推全息面相位，输出 `phase_map.npz`（连续相位）、`quantized_phase*.csv`（N 阶量化）、
`holo_metrics.json`（效率/RMSE/Strehl）。**只算不画、不建阵列、不跑仿真**。

它和 stage 4 的 `fdtd-lumerical-phase-retrieval` 方向相反：那个是**仿真后**从场里提取
Δφ 做验收，这个是**仿真前**把目标图变成相位。调错技能不会报错，只会得到一份
「用设计相位去验收设计输出」的循环证据。

## CRITICAL（违反即停止）

1. **`eta` 是信号区能量占比，不是量化效率。** 量化效率是 Strehl
   `|<exp(i dphi)>|^2`，只有它能与 `sinc^2(pi/N)` 比。实测同一相位 L=2/4/8：
   `eta_support/eta_cont = 0.832 / 0.831 / 0.955`（**非单调**，L=2 反而略高），
   `Strehl = 0.405 / 0.810 / 0.950`（单调且贴 `sinc^2` = 0.405 / 0.811 / 0.950）。
   拿 eta 去比理论上限，会得出「L=2 效率 83%」这种假结论。
2. **目标是振幅，不是强度。** `target_amplitude()` 必须开方并归一化到
   **孔径实际可交付能量**（空孔径传播一次的结果），不是 `aperture.sum()`：
   角谱有倏逝损耗，两者差 ~0.5%。唯一能抓住这类错的是「解析相位回灌」正对照
   （self-test 11）：当前实现读 0，漏开方（变异测试）读 0.311（FFT）/ 0.349（角谱）。
3. **`--method fourier` 的像面像素是 `lam*z/(N*dx)`，`pad=1` 不允许。**
   pad=1 时设计窗与周期复制贴在一起，信号区和鬼影分不开；给 `dx_img_max_um` 时
   超采样会直接 exit 2，不许靠放大目标图糊过去。`angular_spectrum` 要求
   `dx <= lam/2`，超过就是空间混叠，不是「精度差一点」。
4. **RMSE 口径唯一：相对 L2 `|| |v| - A || / ||A||`。** 不许与 RMS
   `sqrt(mean(...))` 混用——实测同一场两个口径读 0.392 与 0.196（差 2.0 倍
   = `sqrt(512^2)/sqrt(65536)`），谁先写进报告谁就成了「同一次仿真两个结论」。
5. **单强度面求出的相位不唯一，别把「与设计相位之差」当验收量。** 实测：透镜目标
   强度 RMSE 0.032（好），但恢复相位与解析透镜相位差 1.19 rad（不是错）。
   验收量是强度 RMSE / eta / Strehl；相位只能作为定性对照。
6. **npz 写出前查空数组，读回 dtype 白名单必须含 `c`。** `"fiub"` 会把复数 E 丢掉
   （D-015）。空数组必须报错，不许写出一份「看起来成功」的空 npz。

## 核心工作流

1. **写 config**（JSON，相对路径按仓库根解析）：

   ```json
   {
     "target": {"path": "path/to/target.npz", "key": "I",
                "threshold_frac": 0.01, "uniform": false},
     "grid":   {"n": 256, "pad": 2, "dx_um": 0.4, "wavelength_um": 0.74,
                "distance_um": 20.0, "method": "fourier", "dx_img_max_um": 0.2},
     "gs":     {"max_iter": 200, "n_seed": 4, "seed": 0,
                "window": 20, "rel_improve": 1e-4, "patience": 3},
     "quantize": {"levels": [2, 4, 8]},
     "signal": {"rect": null}
   }
   ```

   - `target.threshold_frac`：支持区判定，`A >= frac*max`；目标为均匀图时设
     `uniform: true` 才会报均匀度。
   - `grid.dx_um` 是全息面像素间距（= 单胞周期）；`n` 是设计区像素数；
     `pad` 是零填充倍数（>=2）。
   - `gs.window`/`rel_improve`/`patience`：平台早停，每 `window` 轮判一次，
     连续 `patience` 个窗口改善 < `rel_improve` 就停；`max_iter` 是硬上限。
   - `signal.rect`: `[x0,x1,y0,y1]`（0–1 归一化），用于把信号区限制在某块；
     默认按目标支持区。
2. **`--dry-run` 先看网格**：确认 `dx_img_um`、支持区占比、`nyquist.ok`。
   这一步不开任何 FFT。
3. **开跑**：`--config ... --out ...`。多 seed 取最优，但 `rmse_across_seeds`
   的极差一并落账——只报最优值是假轮次。
4. **判读数**：`metrics.rmse` 与 `quantized.*.strehl` 是硬指标；
   `strehl/theory_eta_max` 落在 1.00–1.02 是正常（离散直方图不均匀），
   超过 1.05 会进 `warnings`；`strehl > 1` 直接 exit 2（数学上不可能）。
5. **交接**：`quantized_phase.csv`（`x_um,y_um,phase_rad,level` 四列）与
   `library_map.json` 是给装配技能（`fdtd-metasurface-assembly`，未建）的契约；
   本技能**不查单胞库**，库里没有该档是装配侧的 `missing[]`，不许在这硬凑。
   相位热图直接 `figure --kind field --input phase_map.npz`（第一个二维数组是相位）。

## 示例

**用户：** "把这个 128×128 的方框目标做成 8 阶相位版图，波长 0.74 µm，20 µm 后焦面。"

**动作：**

```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py \
  --config _scratch/regress/2026-11-11/holo/holo_frame.json \
  --out /tmp/holo_frame --json
```

**结果：** `n=256 pad=2 dx=0.4 µm -> dx_img=0.0723 µm`；GS 200 轮（4 seed），
RMSE 1.213 → 0.392 逐轮单调；`eta=0.906`、`snr=19.7 dB`；
`L=2/4/8` 的 Strehl = 0.405/0.810/0.950，与 `sinc^2` 比值 1.000/0.999/1.000。
产出 `phase_map.npz` + `quantized_phase_L8.csv` + `holo_metrics.json`。

## 故障排除

| 症状 | 处置 |
|---|---|
| `GSError: 目标图带 alpha 通道` | 导出灰度或 RGB；本技能不猜透明合成规则 |
| `GSError: angular_spectrum 要求 dx <= lambda/2` | 减小 `dx_um` 或换 `fourier`；这不是警告，超过就是混叠 |
| `GSError: 像面像素 ... 超过允许的 ...` | 提高 `pad` 或 `n`；`dx_img_max_um` 由目标最细特征的一半决定 |
| `GSError: 数组 'I' 是空的` | 目标 npz 没写进去；空文件不许当成成功 |
| RMSE 卡在 0.39 不动 | 二值硬边目标本来就难；先看 `rmse_hist.csv` 是否仍单调，再考虑加 `n_seed`，不要改阈值 |
| `strehl/theory_ratio` 略大于 1 | 相位直方图不均匀，属采样；> 1.05 才进 warnings |
| 相位与设计相位差 ~1 rad 但强度对得上 | 正常：单强度面相位不唯一，见 CRITICAL 5 |
| 跑很久不停 | 查 `gs.window/patience` 是否被设成 0 或过大；`max_iter` 是硬上限 |
| `--self-test` 有一条 FAIL | 先修实现，别改期望值；15 条判定里正对照（11）与消融负对照（10b）是硬门槛 |

## 按需加载

- 不读任何文件即可自检：`python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --self-test`
  （15 行判定，含 Parseval、delta、透镜焦点位置、量化上限、pad 隔离、
  越采样拒绝、空数组、复数白名单、GS 收敛 + 消融负对照、正对照）。
- 读 `../fdtd-lumerical-figure/SKILL.md` **当要把相位版图或收敛曲线出成图** 时——
  本技能不内嵌 plt。
