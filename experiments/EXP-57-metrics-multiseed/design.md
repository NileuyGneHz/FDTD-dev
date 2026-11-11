# EXP-57 — 指标口径与多种子极差

## 假设
同一次运行只能有一个 RMSE；多种子的极差必须落账，只报最优值属假轮次。

## 判据
4 seed 的最终 RMSE ∈ [0.3923, 0.3970]，极差 0.0047；`eta=0.9056`；
`snr_db=19.66`（信号区/非信号区均值比）；相对 L2 = 0.39234。

## 负对照
同一场改用 RMS 口径 `sqrt(mean((|v|-A)^2))` 读 0.19617 —— 与相对 L2 差 2.0 倍
（= sqrt(512²)/sqrt(65536)）。两个口径混用，就会出现「同一次仿真两个结论」。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/holo_frame.json --out _scratch/regress/2026-11-11/holo/run1 --json
```

## 结论
极差 0.0047 已写入 `gs.rmse_across_seeds`；两种口径的差值作为 CRITICAL 4 的依据。
