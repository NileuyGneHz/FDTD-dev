# EXP-43 — --check：spec 改 10% 必须 exit 1 并报两侧数值

## 改动
build_fsp.py --check / --only-check 读回工程逐字段与 spec 比

## 方法
用原 spec 建 P01，再把 spec 里 l 乘 1.1，对同一个 .fsp 做 --only-check

## 实测
```json
{
  "good_exit": 0,
  "good_output": "{\"checked\": 34, \"mismatches\": 0}",
  "bad_exit": 1,
  "bad_output": "{\"checked\": 34, \"mismatches\": 2}",
  "mismatch_fields": [
    "cross_x x span",
    "cross_y y span"
  ],
  "expected_value": 1.87e-06,
  "actual_value": 1.7e-06
}
```

## 负对照
- 做法：原 spec 对同一 .fsp
- 预期：0 mismatch，exit 0
- 实测：checked=34, mismatches=0, exit 0
- 负对照是否按预期失败：是

## 结论
报错必须同时给字段名与两侧数值，否则人无法判断是 spec 错还是文件旧。

## 可重跑命令
```bash
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py --spec _scratch/regress/2026-11-09/EXP-43/spec_bad.json --only-check _scratch/regress/2026-11-09/EXP-39/p01.fsp --out _scratch/regress/2026-11-09/EXP-43 --json
```
