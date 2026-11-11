# EXP-45 — 图上的数必须等于数据里的数（扰动输入，标注跟着动）

## 改动
所有标注值在绘图时从被画数组现算，并回写 meta

## 方法
把 spectra csv 的 A 整体乘 1.05，比较两次 meta 的 peak_value

## 实测
```json
{
  "base_peak": 0.8069379708102874,
  "csv_peak": 0.8069379708102874,
  "consistent": true,
  "perturbed_peak": 0.8472848693508018,
  "expected_perturbed": 0.8472848693508018,
  "follows_data": true
}
```

## 负对照
- 做法：把输入整体乘 1.05
- 预期：若标注是写死的，peak_value 不动
- 实测：0.8069379708 → 0.8472848694，严格跟随
- 负对照是否按预期失败：是

## 结论
这条防的是「图上好看、台账对不上」，与 R13 是同一类病。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-44/test_figures.py
```
