# EXP-21 group-script-captured

## 假设

P06 的涡旋真值（八个八分圆各一种 V 天线）写在 structure group.script 里；旧版只报「一个 group」，等于没看见

## 输入

`cases/P06_Vortex_049/model/fig5.fsp`

## 负对照

P06 的涡旋真值（八个八分圆各一种 V 天线）写在 structure group.script 里；旧版只报「一个 group」，等于没看见

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "script_chars": 2943,
  "number": 30.0,
  "children_collapsed": true
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
