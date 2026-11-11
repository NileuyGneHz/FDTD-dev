# EXP-56 — 两个负对照（收敛 + 采样）

## 假设
「GS 会收敛」与「网格够密」这两句话，必须各有一个能证伪它们的对照。
（pad 判据由「窗外能量」改为 Nyquist 硬拒绝，理由见 PLAN §7.2-②。）

## 判据
① `image_constraint=False` 时 RMSE 漂移 0.0；
② `pad=1` 且目标要求 `dx_img ≤ 0.05 µm` 时，解出的 0.0723 µm 超限 → exit 2。

## 负对照
两条本身就是负对照：① 去掉像面约束必须**不**收敛；② 欠采样必须**被拒**而不是
算出一组看着合理的数。任一「通过」都说明判据失效。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --self-test          # 10b / 5b 两行
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/bad/coarse.json --dry-run
```

## 结论
消融漂移 0.0；欠采样 config 报
`像面像素 0.07227 um 超过允许的 0.001 um`，exit 2。
