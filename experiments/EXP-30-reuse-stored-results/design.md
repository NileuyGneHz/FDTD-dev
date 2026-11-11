# EXP-30 — layoutmode=0 且无参数时复用已存结果，不重跑

## 改动
run_one 增加 reused_stored 分支；--force / 有 params 时仍重算

## 方法
对 P01 参考工程（layoutmode=0、有谱）跑 Reproduce 空参数

## 实测
```json
{
  "reused_stored": 1,
  "layoutmode_at_load": 0.0,
  "elapsed_s": 6.6,
  "previous_cost_s": 4200,
  "speedup": 636,
  "assert_ran": "not run: reused stored results"
}
```

## 负对照
- 做法：cfg 里加 force=true
- 预期：进入 save+run 分支，不标 reused
- 实测：dry-run 的 reuse_if_stored 随 force 变为 false；实跑走 verify_and_run 分支
- 负对照是否按预期失败：是

## 结论
P05 四次 70 min 的重复求解可省；判据是 layoutmode=0，不是文件名或时间戳。

## 可重跑命令
```bash
python skills/fdtd-lumerical-session-control/scripts/session_control.py --config _scratch/regress/2026-11-09/sc_reuse_npz.json --out _scratch/regress/2026-11-09/EXP-30/out --json
```
