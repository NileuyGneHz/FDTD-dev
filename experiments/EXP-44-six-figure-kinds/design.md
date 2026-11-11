# EXP-44 — 六类图各出一张，缺必需列报列名

## 改动
新增技能 fdtd-lumerical-figure 与 scripts/make_figure.py（stack/spectra/phase/field/fom/compare）

## 方法
用真实产物各跑一遍（P01 spec、11-09 谱、P02 phase.csv、gr3d 场 npz、三配置 FOM、两条谱）

## 实测
```json
{
  "kinds_ok": 6,
  "bytes": {
    "stack": 21820,
    "spectra": 61416,
    "phase": 42471,
    "field": 51822,
    "fom": 53716,
    "compare": 59363
  },
  "all_non_empty": true,
  "missing_column_exit": 2,
  "missing_column_draws_nothing": true,
  "missing_column_message": "缺少列 lam_um；实际列 = A, R, T"
}
```

## 负对照
- 做法：删掉 csv 的 lam_um 列
- 预期：exit 2、报出列名、不写文件
- 实测：exit 2，输出「缺少列 lam_um；实际列 = A, R, T」，未生成 png
- 负对照是否按预期失败：是

## 结论
删 T 列不算错（反射式器件没有 T），删 lam_um 才算——判据要分清必需与可选。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-44/test_figures.py
```
