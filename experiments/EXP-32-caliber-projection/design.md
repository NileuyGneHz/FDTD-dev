# EXP-32 — caliber{} 直出 repro-card 兼容字段

## 改动
ledger 增加 caliber 与 repro_card 投影（target/actual_solver/numerics_aligned_from）

## 方法
在 config 里给 caliber，检查 ledger 的两个键

## 实测
```json
{
  "caliber_keys": 5,
  "repro_card_keys": [
    "target",
    "actual_solver",
    "numerics_aligned_from"
  ],
  "target_quantity_readable": "peak_absorption",
  "duplicated_typing": 0
}
```

## 负对照
- 做法：config 不给 caliber
- 预期：caliber=None 且不产出 repro_card，而不是造空壳
- 实测：caliber=None，repro_card 键不出现
- 负对照是否按预期失败：是

## 结论
口径声明只写一次，运行台账直接喂给 check_reproduction。

## 可重跑命令
```bash
python skills/fdtd-lumerical-session-control/scripts/session_control.py --config _scratch/regress/2026-11-09/sc_reuse_npz.json --out _scratch/regress/2026-11-09/EXP-30/out --json
```
