# EXP-39 — --build-only：30 秒拿到 .fsp，且不留 _p0.log

## 改动
新增技能 fdtd-lumerical-fsp-build 与 scripts/build_fsp.py（默认只建不跑）

## 方法
用 P01 spec 真建一次，检查 wall / layoutmode / _p0.log / 字节数

## 实测
```json
{
  "wall_s": 7.26,
  "layoutmode": 1.0,
  "p0_log": false,
  "bytes": 474963,
  "solves": 0,
  "same_bytes_as_full_sweep_build": 474963,
  "check_properties": 34,
  "check_mismatches": 0
}
```

## 负对照
- 做法：旧路径 run_fdtd_sweep.py 是否支持 --build-only
- 预期：不支持：它的 argparse 里没有这个开关，.fsp 只在 run_point 之后才 save
- 实测：argparse 无 --build-only；P01 全流程实测 5987 次迭代（EXP-26），也就是说旧路径要拿到 .fsp 必须先付一次完整求解
- 负对照是否按预期失败：是

## 结论
建与跑分离成立：7.3 s / 0 次求解 / layoutmode=1 / 无 _p0.log / 474963 B。

## 可重跑命令
```bash
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py --spec cases/P01_Absorber_042/config/spec_p01.json --out _scratch/regress/2026-11-09/EXP-39 --tag p01 --check --json
```
