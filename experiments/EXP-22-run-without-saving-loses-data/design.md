# EXP-22 — 「run 之后不 save 会丢数据」——未复现，建议作废

## 改动
无代码改动。这是对 P06 报告结论的复核；按计划停止条件，反证成立即删掉该建议。

## 方法
同一 tiny 模型跑两次：A 保存后 run、close 不再 save；B 保存后 run、close 前再 save。两者都在新会话 reload，比较 layoutmode 与 getresult

## 实测
```json
{
  "A_no_resave_layoutmode": 0.0,
  "A_no_resave_points": 5,
  "A_no_resave_min": -0.06865909296620877,
  "A_no_resave_max": -0.006105445579138593,
  "B_resave_layoutmode": 0.0,
  "B_resave_points": 5,
  "B_resave_min": -0.06865909296620877,
  "B_resave_max": -0.006105445579138593,
  "identical": true,
  "verdict_on_claim": "refuted"
}
```

## 负对照
- 做法：B（close 前再 save 一次）
- 预期：若 A 真丢数据，B 必须留下数据，两者应不同
- 实测：两者逐位相同（n=5, min/max 一致）-> A 没有丢数据
- 负对照是否按预期失败：是

## 结论
P06 的「run 后不 save 会丢数据」在本机 v251 上不成立：引擎 close 时把结果写回了工程。原报告可能是在 save 之前就 close、或读的是另一个文件。**不写进 CRITICAL**；真正的风险是 EXP-24/25 那两类「有数据但非物理」。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-22/probe_false_pass.py
```
