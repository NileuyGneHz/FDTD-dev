# EXP-53 — 目标加载与网格定义 + dry-run

## 假设
物理↔像素换算只能有一处定义（`make_grids`）。dry-run 必须在任何 FFT 之前 return，
否则「只看计划」也要付一次全量计算。

## 判据
方框目标 n=256/pad=2/dx=0.4/λ=0.74/z=20 → `dx_img = λz/(N dx) = 0.07227 µm`；
支持区占比 0.09399；dry-run 打印 grid + target + nyquist，不做传播。

## 负对照
三份坏输入必须 exit 2：带 alpha 的 png、含负值的强度图、空 npz。
静默丢弃 alpha 或把空数组当成功，都是「看起来成功」的假账。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/holo_frame.json --dry-run
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/alpha.json --dry-run
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/neg.json --dry-run
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/empty.json --dry-run
```

## 结论
dry-run 输出 `dx_img_um=0.07227`、`support_fraction=0.09399`、`nyquist.ok=true`；
三份坏输入全部 exit 2（alpha 通道 / 负值 / 空数组各有专门文案）。
