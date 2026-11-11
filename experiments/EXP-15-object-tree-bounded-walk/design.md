# EXP-15 object-tree-bounded-walk

## 假设

P06 fig5 的 30x30 组已折叠（只读 number/period），但整轮仍 273 s —— 瓶颈不是递归而是 selectall()+getAllSelectedObjects() 对 4500 个对象建包装。判据 <30 s 未达成，如实记 fail，优化留待后续

## 输入

`cases/P06_Vortex_049/model/fig5.fsp`

## 负对照

P06 fig5 的 30x30 组已折叠（只读 number/period），但整轮仍 273 s —— 瓶颈不是递归而是 selectall()+getAllSelectedObjects() 对 4500 个对象建包装。判据 <30 s 未达成，如实记 fail，优化留待后续

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "wall_s": 273.0,
  "target_s": 30,
  "max_objects": 800,
  "max_depth": 3,
  "group_collapsed": true,
  "leaf_objects": 4500
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
