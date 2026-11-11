# EXP-17 linear-x-monitor-recognised

## 假设

P09 的 2D 工程线监视器类型是 Linear X，旧白名单只认 z-normal/power，把 500 点反射谱判成 no_stored_spectra；现在以 getresult 是否成功为准

## 输入

`cases/P09_GrapheneAbsorber_044/model/graphene_perfect_absorber.fsp`

## 负对照

P09 的 2D 工程线监视器类型是 Linear X，旧白名单只认 z-normal/power，把 500 点反射谱判成 no_stored_spectra；现在以 getresult 是否成功为准

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "status": "ok",
  "npts": 500,
  "peak_R": 0.9857
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
