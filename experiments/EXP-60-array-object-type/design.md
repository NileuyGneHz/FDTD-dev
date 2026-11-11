# EXP-60 — `array` 对象类型与三级作用域求值

## 假设

per-cell 变参不需要新求值器：把 `ev(expr, params)` 的作用域从「全局一份」扩成
`全局 params ⊕ {i, j} ⊕ cell_params[行主序]`，即可让同一模板逐格不同。
若这条成立，则只需给 `build_objects()` 加一个分支，`ev()` / `resolve_axes()` /
`build_simulation()` 零改动。

## 判据

3×3 手算阵列（pitch=1 µm，每格 d1/rot 手写），对象名 `{id}_r{i}c{j}`；
`--check` 读回每个对象的位置/尺寸，与手算值逐位相等；
缺某格参数时回落全局 params 且不报错；`cell_params` 行数 ≠ nx*ny 时必须报错。

## 负对照

把 `i` / `j` 从作用域里删掉（模拟"只有全局 params"的旧行为），
模板里的 `i*P` 必须抛 `NameError`/`ValueError` —— 证明格子索引确实来自作用域注入，
而不是碰巧被某个同名全局参数顶上。
另：`cell_params` 少一行时若不报错而是静默补 0，则阵列会静默错位 → 该行为必须被判失败。

## 命令

```bash
python _scratch/regress/2026-11-11/array/probe_array.py --self-test
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec _scratch/regress/2026-11-11/array/spec_3x3.json \
  --out _scratch/regress/2026-11-11/array/build --tag arr3 --check --json
```

## 结论

（执行后补）
