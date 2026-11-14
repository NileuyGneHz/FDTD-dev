# EXP-38 — builder 抽取到 _shared/fsp_build.py，字段级零差异

## 改动
ev / resolve_material / build_materials / build_objects / check_monitor_gap / build_simulation 迁到 _shared/fsp_build.py（切片搬运，非手抄）；run_fdtd_sweep.py 改成 import，451 -> 209 行

## 方法
抽取前后各用同一 spec（P01）构建 .fsp，再用 inspect_fsp(full_props) 逐字段比对

## 实测
```json
{
  "objects_before": 11,
  "objects_after": 11,
  "field_level_diffs": 0,
  "materials_equal": true,
  "fsp_bytes_before": 474963,
  "fsp_bytes_after": 474963,
  "sweep_lines_before": 451,
  "sweep_lines_after": 209,
  "sweep_still_contains_builder_body": false,
  "build_wall_s": 6.5,
  "layoutmode_built": 1.0,
  "p0_log_absent_when_not_run": true
}
```

## 负对照
- 做法：把 _shared/fsp_build.py 移走后经 run_fdtd_sweep 导入
- 预期：ImportError（不允许静默回落到隐藏副本）
- 实测：ImportError: _shared/fsp_build.py not found
- 负对照是否按预期失败：是

## 结论
结构判据成立；但抽取时把 DEFAULT_ENV / open_session 一并切走，CLI 立刻 NameError —— 探针绕过 CLI 所以没抓到。已修，并把「必须跑 CLI」写入判据。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-38/build_probe.py --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json --out _scratch/regress/2026-11-09/EXP-38/after --impl shared
python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json --out _scratch/regress/2026-11-09/EXP-26/run --dry-run
```
