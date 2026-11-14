# EXP-13 unlabeled-monitor-no-guess

## 假设

P07 initial_trial 的监视器叫 monitor/field/time：旧版兜底把 monitor 当 R，报 peak_R=0.0074 @ 0.4 µm；现在一律 None + unlabeled

## 输入

`cases/metasurface/P07_BrokenSymmetry_041/model/initial_trial.fsp`

## 负对照

P07 initial_trial 的监视器叫 monitor/field/time：旧版兜底把 monitor 当 R，报 peak_R=0.0074 @ 0.4 µm；现在一律 None + unlabeled

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "status": "unlabeled_monitors",
  "R_monitor": null,
  "derived_is_null": true
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
