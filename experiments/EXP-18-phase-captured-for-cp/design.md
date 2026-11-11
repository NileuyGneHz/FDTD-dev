# EXP-18 phase-captured-for-cp

## 假设

圆偏振由两个正交 TFSF 源 ±90° 凑出；旧 CORE_PROPS 没有 phase，RCP/LCP 两工程 manifest 一模一样，判不出旋向

## 输入

`cases/P05_Metalens_048/model/RCP.fsp`

## 负对照

圆偏振由两个正交 TFSF 源 ±90° 凑出；旧 CORE_PROPS 没有 phase，RCP/LCP 两工程 manifest 一模一样，判不出旋向

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "sources": [
    "source",
    "source_1"
  ],
  "phase_values": [
    0.0,
    -90.0
  ]
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
