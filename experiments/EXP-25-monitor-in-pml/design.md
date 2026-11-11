# EXP-25 — 监视器压进 PML：getresult 照样返回数据，只有几何闸能拦

## 改动
assert_in_domain()：按 FDTD 盒 ± span/2 与可配置 gap（默认 0.3 µm）判 ok / pml_overlap / outside

## 方法
把监视器 z 从 -1.15 逐点外移到 -1.30 µm（盒半跨 1.2 µm），记录 getresult 与日志

## 实测
```json
{
  "z_-1.15": "n=5, 无告警",
  "z_-1.19": "n=5, 无告警 -> pml_overlap",
  "z_-1.20": "n=5, 无告警（正好在盒边）",
  "z_-1.21": "n=5, 无告警（已在盒外一点点）",
  "z_-1.30": "getresult FAILED + 日志 outside the simulation",
  "first_position_with_empty_result_um": -1.3,
  "positions_that_still_return_data_inside_pml": 4,
  "assert_ran_on_pml_case": "pass（四判据都拦不住）",
  "geometry_gate_on_pml_case": "REJECTED: 监视器与 FDTD 边界不足 0.300 um（或已在盒外）: monR=pml_overlap。P",
  "geometry_gate_on_outside_case": "REJECTED: 监视器与 FDTD 边界不足 0.300 um（或已在盒外）: monR=outside。PML 内"
}
```

## 负对照
- 做法：把同一监视器放回 -0.9 µm（健康位置）
- 预期：几何闸放行
- 实测：pass (1 monitors)
- 负对照是否按预期失败：是

## 结论
P06 说「监视器压进 PML -> getresult 全空」并不准确：PML 内仍返回数据，只是非物理。因此必须靠几何闸在 run 之前拦；getresult 判据对这类问题是盲的。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-25/probe_pml_sweep.py
python _scratch/regress/2026-11-09/EXP-24/test_guards.py
```
