# EXP-55 — GS 迭代与收敛控制

## 假设
GS 的两个约束（全息面—像面）是投影，误差应单调非增；早停不得无界循环，
也不得在 window+patience 轮就触发（原实现有此缺陷，已修为每 window 判一次）。

## 判据
方框目标（fourier，512²，4 seed，200 轮）：RMSE 1.21277 → 0.39234，逐轮最大回升
−5.86e−5（即恒降）；透镜目标（角谱，256²）：300 轮 plateau，RMSE 0.0323。

## 负对照
去掉像面振幅约束（`image_constraint=False`）：往返成为恒等映射，40 轮 RMSE 漂移
必须精确为 0。若它还在下降，说明「收敛」来自别的东西（比如初始化）。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/holo_frame.json --out _scratch/regress/2026-11-11/holo/run1 --save-debug-frames
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/holo_p05_lens.json \
  --out _scratch/regress/2026-11-11/holo/run_p05 --max-iter 600
```

## 结论
两条都收敛且单调；消融负对照漂移 0.0（self-test 10b）。
