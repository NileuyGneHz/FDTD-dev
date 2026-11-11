# EXP-52 — config schema 与 metrics 字段表

## 假设
先把「配置里必须有什么、缺了怎么死」写死，再写算法。否则脚本会长成
「当时能跑、原因不明」的样子（契约 §1 的判定顺序）。

## 判据
`resolve_config()` 校验 12 个字段：target.path/key/threshold_frac、grid.n/pad/dx_um/
wavelength_um/distance_um/method、gs.max_iter/n_seed、quantize.levels、signal.rect。
任何一项缺失或越界 → `GSError` + exit 2，不猜默认值。

## 负对照
三份坏 config 必须被拒：缺 `grid.n`、缺 `target.path`、`signal.rect` 的 x0>=x1。
若它们能跑通，schema 就只是文档。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/no_n.json --dry-run
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/no_target.json --dry-run
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/bad_rect.json --dry-run
```

## 结论
三条全部 `GSError` 且 exit 2：`grid 缺字段 'n'` / `target 缺字段 'path'` /
`signal.rect 必须是 [x0,x1,y0,y1] …`。
