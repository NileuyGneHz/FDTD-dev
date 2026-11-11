# EXP-58 — N 阶量化与 sinc² 上限

## 假设
量化效率是相位误差的 Strehl `|<exp(i dphi)>|²`，其渐近上限为 `sinc²(π/N)`。
单调性只对 Strehl 成立，对「支持区能量比」不成立。

## 判据
同一相位 L=2/4/8：Strehl = 0.4052 / 0.8095 / 0.9497，上限 0.4053 / 0.8106 / 0.9496，
比值 1.000 / 0.999 / 1.000；单调递增。

## 负对照
改用 `eta_support/eta_cont`：0.8316 / 0.8314 / 0.9546 —— L=2 反而高于 L=4，
**非单调**；拿它比 sinc² 会得出「L=2 效率 83%」的假结论。该口径必须被否掉。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/holo_frame.json --out _scratch/regress/2026-11-11/holo/run1
```

## 结论
Strehl 单调且贴上限；eta 比非单调，故运行时硬判据用 `strehl ≤ 1`，不用 eta。
