# repro_p03 — P03 监视器结果

| 文件 | 内容 |
|---|---|
| `p03_monitors.csv` | 101 个波长点 × 全部监视器列（R_co、R_cr、PCR、Δφ、R_u、R_v、相位） |
| `pol0.csv` | 单偏振原始导出（与主表同内容） |
| `pol0_fields.npz` | 平面平均复场 `Ex/Ey/Ez`、`R/T`、`lam_um` |
| `run_pol0_p0.log` | 引擎日志（收敛判据：末值 8.82e-6，Completed，无 diverging） |
| `fig_p03_monitors.png` | 四联图：R_co/R_cr、PCR、u/v 幅度、u/v 相位差 |
| `repro_report.md` | 论文对照、偏差诊断、复跑命令 |
| `summary.json` | 机器可读汇总 |

## 定义

- `R_co = |Ex|² / R_total` 归一化后的同偏振反射；`R_cr = |Ey|² / R_total`。
- `PCR = R_cr/(R_co+R_cr)`。
- `r_u = J_xx + J_yx`，`r_v = J_xx − J_yx`（45° 砖），`Δφ_uv = arg(r_u) − arg(r_v)`，按 mod 360 报告。
- 绝对相位没有物理意义；只报 u/v 相位差。

## 注意

`model/p03_hwp.fsp` 是 build-only（`layoutmode=1`，无存谱，477 KB）。
带监视器数据的 run `.fsp` 会膨胀到 109 MB（超过单文件 100 MB 入库红线），已删除；
监视器数据以 CSV/NPZ 交付，`.fsp` 保持可重跑的模型态。
