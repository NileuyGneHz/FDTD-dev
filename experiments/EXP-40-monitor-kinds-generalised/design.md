# EXP-40 — 监视器泛化：power / field / index 三类都能建、都能读

## 改动
build_simulation 支持 monitors[]（power→addpower、field→addprofile、index→addindex），并兼容旧式 dict 写法

## 方法
同一 spec 建三个监视器，跑一次后逐个 getresult

## 实测
```json
{
  "power_R_points": 51,
  "field_E_points": 19683,
  "field_grid": [
    81,
    81
  ],
  "index_points": 6561,
  "all_non_empty": true,
  "layoutmode": 0.0,
  "p0_completed": true
}
```

## 负对照
- 做法：只给 power 监视器的旧 spec（P01）
- 预期：产物少 field/index 两类，但不报错
- 实测：P01 build 仍只有 R / T 两个监视器（EXP-38 manifest monitors 一致），无异常
- 负对照是否按预期失败：是

## 结论
三类监视器的 getresult 键各不相同：power 给 lambda/f/T，field 给单数组 E，index 给 index_x/y/z。写死 'T' 的地方必须按 kind 分支。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-40/verify_40_41_42.py
```
