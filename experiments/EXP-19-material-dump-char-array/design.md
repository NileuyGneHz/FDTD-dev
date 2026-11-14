# EXP-19 material-dump-char-array

## 假设

getmaterial() 返回字符数组未 join 时整张表丢失；现在 user_Au 带 type=Conductive 3D、σ=4e7，user_Gra2 标 Sampled 2D data

## 输入

`cases/metasurface/P09_GrapheneAbsorber_044/model/graphene_perfect_absorber.fsp`

## 负对照

getmaterial() 返回字符数组未 join 时整张表丢失；现在 user_Au 带 type=Conductive 3D、σ=4e7，user_Gra2 标 Sampled 2D data

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "materials": [
    "user_Au",
    "user_Gra2"
  ],
  "au_type": "Conductive 3D",
  "au_sigma": 40000000.0,
  "gra_type": "Sampled 2D data"
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
