# EXP-26 — P01 正常流程四判据全过（并校准 PHYS_TOL）

## 改动
PHYS_TOL 1e-6 -> 1e-3（EXP-09 引入的守卫误伤正常运行）；抽出纯函数 check_physical_range()

## 方法
用改造后的 run_fdtd_sweep.py 真跑 P01 单点，读 summary.csv 与 _p0.log

## 实测
```json
{
  "peak_A": 0.8069379708102874,
  "peak_lam_um": 5.85,
  "T_at_peak": -1.1315996753131341e-05,
  "fwhm_um": 0.8000000000000007,
  "iterations": 5987,
  "shutoff_final": 8.83863e-05,
  "layoutmode": 0.0,
  "p0_log_bytes": 4181,
  "first_attempt_failed": "ValueError: T 越界 [-0.000, -0.000] with tol=1e-6"
}
```

## 负对照
- 做法：P07 的越界数据 T=-0.80 / A=1.60 用新容差 1e-3 重判
- 预期：必须仍然被拒
- 实测：raise ValueError（差值比噪声大 4 个数量级）
- 负对照是否按预期失败：是

## 结论
守卫本身正确，容差设错了：不透明堆栈 T≡0，DFT 通量噪声 ~1e-5（三个独立来源一致：本次 -1.1e-5、11-03 out_fine -2.13e-5、11-03 out_ts -2.05e-5）。1e-6 会把正常运行判成「监视器压进 PML」。

## 可重跑命令
```bash
python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec cases/P01_Absorber_042/config/spec_p01.json --out _scratch/regress/2026-11-09/EXP-26/run
```
