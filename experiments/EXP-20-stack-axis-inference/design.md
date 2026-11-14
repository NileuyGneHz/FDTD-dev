# EXP-20 stack-axis-inference

## 假设

P09 是 2D 工程（堆栈沿 y），旧逻辑只按 z 取位置 → derived=null；现在据 dimension / injection axis 推轴

## 输入

`cases/metasurface/P09_GrapheneAbsorber_044/model/graphene_perfect_absorber.fsp`

## 负对照

P09 是 2D 工程（堆栈沿 y），旧逻辑只按 z 取位置 → derived=null；现在据 dimension / injection axis 推轴

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "fdtd_dimension": "2D",
  "axis_used": "y"
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
