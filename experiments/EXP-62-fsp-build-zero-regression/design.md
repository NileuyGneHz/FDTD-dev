# EXP-62 — 改 `_shared` 的零破坏回归（双调用方）

## 假设

给 `_shared/fsp_build.py` 加 `array` 分支不改动任何既有 type 的代码路径，
因此 P01 这类不含 array 的 spec 重建结果与改动前**逐位一致**。
`run_fdtd_sweep.py` 与本技能 import 同一份实现，二者都应能让 P01 spec 通过。

## 判据

- P01 spec 在改动前后各建一次，两次 `--check` 的 `checked` 数与 `mismatches`
  完全相同（都是 0），且 `_build.json` 里 `span_range` / `monitors` 数值逐位相等。
- `python -c "import sys; sys.path.insert(0,'_shared'); import fsp_build"`
  在 `run_fdtd_sweep.py` 的 import 上下文可用（它 import 的名字集合仍全部存在）。
- `tools/check_scripts.py` 仍通过（包内无 `.py` 的约束不受影响）。

## 负对照

把 `ev()` 对 `i`/`j` 的处理改成「全局无条件注入 `i=0, j=0`」（一种常见的偷懒实现），
P01 的表达式里若真出现 `i` 就会静默取 0 —— 用一条 P01 变体（把 `l` 写成 `l + i*0`）
证明它不会有差异，而**真正的负对照是**：在旧 spec 上注入一个与全局参数同名的 `i`，
两者必须产生不同结果，证明「注入」这件事本身有副作用风险，所以只在 array 分支内注入。

## 命令

```bash
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/regress/2026-11-11/array/p01 --tag p01_after --check --json
python tools/check_scripts.py
```

## 结论

（执行后补）
