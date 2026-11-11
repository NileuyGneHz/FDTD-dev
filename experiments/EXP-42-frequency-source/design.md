# EXP-42 — 频域源：3–8 THz 口径建立成功（2D 另记 D-008）

## 改动
source.frequency_range_thz → frequency start/stop（Hz）；不碰 inactive 的 frequency

## 方法
建完读回 frequency start/stop，与目标 3/8 THz 比相对误差

## 实测
```json
{
  "f_start_thz": 3.0,
  "f_stop_thz": 8.0,
  "abs_err_pct": [
    0.0,
    0.0
  ],
  "dimension": "3D",
  "wavelength_range_um": [
    37.474,
    99.931
  ]
}
```

## 负对照
- 做法：dimension=2D 的同一份 spec
- 预期：失败并留下可诊断信息
- 实测：setnamed 'z min bc' → property is inactive（z 是 2D 的不变轴），已记 D-008
- 负对照是否按预期失败：是

## 结论
频率口径 ±0%；但 2D 维度整体不支持，EXP-34/35 因此无法进行。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-40/verify_40_41_42.py
```
