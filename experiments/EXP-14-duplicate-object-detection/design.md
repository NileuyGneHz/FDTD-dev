# EXP-14 duplicate-object-detection

## 假设

P05 的 group 内 21 个同名 rectangle：旧版逐条写进 manifest（unique x=1 的假记录）；现在标 duplicate_name 并只留一条

## 输入

`cases/P05_Metalens_048/model/RCP.fsp`

## 负对照

P05 的 group 内 21 个同名 rectangle：旧版逐条写进 manifest（unique x=1 的假记录）；现在标 duplicate_name 并只留一条

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "duplicate_name": true,
  "n_children": 21,
  "duplicate_names": [
    "rectangle"
  ],
  "children_kept": 0
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
