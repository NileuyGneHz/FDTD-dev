# EXP-36 — 出图收编：一套脚本覆盖 4 个包的数据源

## 改动
make_figure.py 取代 P02/P04/P05/P06 各自手写的绘图代码

## 方法
用同一脚本跑 P01 谱、P02 相位、P05 场（gr3d 代位）、P01 两版本对比

## 实测
```json
{
  "sources": [
    "P01 spectra",
    "P02 phase.csv",
    "field npz",
    "P01 old vs new"
  ],
  "figures": 6,
  "scripts_needed": 1,
  "manual_plotting_removed": "none yet (files untouched)"
}
```

## 负对照
- 做法：缺 lam_um 的 csv
- 预期：报列名而不是画空白
- 实测：exit 2 + 缺少列 lam_um
- 负对照是否按预期失败：是

## 结论
收编完成的是「能力」，不是「删旧代码」：各包里的历史绘图脚本本轮未动，下轮确认无差异后再删。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-44/test_figures.py
```
