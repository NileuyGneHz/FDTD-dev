# EXP-64 — 端到端：Skill A 的 8 阶相位 → 64×64 超表面 `.fsp`

## 假设

`fdtd-holo-phase-retrieval` 产出的 `quantized_phase_L8.csv`（65537 行、256×256 网格）
经降采样到 64×64 + 装配 + `fsp-build` 后，能拿到一个对象数可核、`--check` 全过的 `.fsp`；
build 耗时在可接受范围（≤ 数分钟），且 `layoutmode=1`、无 `_p0.log`（build-only 语义不破）。

## 判据

- 64×64 = 4096 个单元对象 + 衬底等少量静态对象，`--check` `mismatches=0`。
- `layoutmode == 1`、`p0_log == false`、`_p0.log` 文件不存在。
- 单次 build 墙钟时间落账（build-only 的卖点：秒级到分钟级，而不是一次完整机时）。
- 从 256×256 降到 64×64 必须**显式**（`--target-nx/--target-ny` 或降采样步长），
  不许静默抽样：抽样方式写进 spec 的 `meta` 并回读。

## 负对照

不降采样直接 256×256 → 65536 个单元：这一轮**必须**因超过 objects 引擎的安全规模
而报错退出（`_MAX_CELLS_OBJECTS`），而不是跑到一半内存爆掉或建出半成品 `.fsp`。
若它能"成功"跑完，说明规模防线不存在，判据失效（那时需要回头补 group_script）。

## 命令

```bash
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py \
  --phase _scratch/regress/2026-11-11/holo/run1/quantized_phase_L8.csv \
  --library _scratch/regress/2026-11-11/array/library_L8.json \
  --geometry _scratch/regress/2026-11-11/array/geom_64.json \
  --target-nx 64 --target-ny 64 \
  --out _scratch/regress/2026-11-11/array/spec_64.json --json
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec _scratch/regress/2026-11-11/array/spec_64.json \
  --out _scratch/regress/2026-11-11/array/build64 --tag meta64 --check --json
```

## 结论

（执行后补）
