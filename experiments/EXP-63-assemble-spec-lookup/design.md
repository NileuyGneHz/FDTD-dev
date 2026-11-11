# EXP-63 — `assemble_spec.py` 的查表装配（零引擎）

## 假设

「相位档位 → 单元几何参数」是一次纯查表：`quantized_phase.csv` 第 4 列 level
在 `library_map.json` 里查得一组 params，填进 array 的 `cell_params`。
装配正确性可以完全脱机验证（不开 lumapi）。

## 判据

- 3×3 合成相位（level 序列已知）→ 装配出的 `cell_params` 长度 = 9、行主序为
  `(i,j)` 升序、每格 params 与 library 该 level 全等。
- `library_map` 缺某一档 → 必须报错并**列出缺失的 level 与该 level 出现次数**，
  不许静默跳过（EXP-49 同病灶：文案与语义相反）。
- CSV 行数 ≠ nx*ny → 报错并打印 CSV 前三行帮助定位。
- 相位 CSV 的 `x_um/y_um` 与 `grid.pitch`/`origin` 推出的坐标必须一致
  （容差 1e-6 µm），不一致报错——这是"行主序/坐标约定"的双向检查。

## 负对照

把查表实现成「取 library 第一条」的哑实现（忽略 level），
判据① 必须失败：装出来的 9 格全是同一组 params。
若哑实现也能过，说明判据①只验了"有 9 条"，没验"每条对不对"。

## 命令

```bash
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py --self-test
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py \
  --phase _scratch/regress/2026-11-11/array/phase_3x3.csv \
  --library _scratch/regress/2026-11-11/array/library_3x3.json \
  --geometry _scratch/regress/2026-11-11/array/geom_3x3.json \
  --out _scratch/regress/2026-11-11/array/spec_3x3.json --json
```

## 结论

（执行后补）
