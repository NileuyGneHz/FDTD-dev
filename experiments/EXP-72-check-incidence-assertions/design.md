# EXP-72 — `--check` 补 source/BC 双向断言

## 假设

改完 builder 后，`build_fsp.py --check` 仍只断言几何 span/center/radius + mesh accuracy。
「角度写错了 check 全绿」是典型的**单向门禁盲区**（D-011 同类）：它只验「写了的对不对」，
不验「该写的有没有写」。必须让 `--check` 读回 `source.angle theta`、
`source.plane wave type`、倾斜面 BC、`pml layers`、`bfast alpha`。

BC 与 plane wave type 是**字符串枚举**，而 `run_check()` 里一律 `float(...)`；直接加断言会
全部误报成 `missing`（K11 同类：拿 A 的属性判 B）。所以同时扩展 `run_check()` 支持字符串比较。

## 判据

1. 正对照：P08 spec（θ=30）对 `p08_30.fsp` → `mismatches=0`，断言数比改前多 6 条。
2. N3：把 spec 改成 θ=35 但**不重建** `.fsp` → exit 1，且报错指名
   `source.angle theta expected=35 actual=30`。
3. 反向对照：把 `.fsp` 的 source angle 改成 35（保存为新文件），用**原 spec** → 同样红。
4. N2：带结果的课程工程直接 `setnamed` 报 `use switchtolayout first`。
5. 零破坏：P01 legacy spec 的断言集不变（34/0）。

## 负对照

N3 与反向对照任一变绿都算失败 —— 那说明断言没覆盖角度，或者字符串比较被静默跳过。

## 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
B="skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py"
S="_scratch/regress/2026-11-13/oblique"
"$PY" "$B" --only-check "$S/EXP-71/p08/p08_30.fsp" --spec "$S/spec_p08.json" --json
"$PY" "$B" --only-check "$S/EXP-71/p08/p08_30.fsp" --spec "$S/spec_p08_mut35.json" --json; echo $?
"$PY" "$B" --only-check "$S/EXP-72/p08_fsp_mut35.fsp" --spec "$S/spec_p08.json" --json; echo $?
"$PY" "$B" --only-check "$S/EXP-71/p01/p01.fsp" \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json --json
```

## 实测结果

| 用例 | 结果 |
|---|---|
| 正对照（spec 30 / fsp 30） | `checked=33, mismatches=0, exit 0` |
| N3（spec 35 / fsp 30） | `checked=33, mismatches=1, exit 1`，报 `source.angle theta expected=35.0 actual=30.0` |
| 反向（spec 30 / fsp 35） | `checked=33, mismatches=1, exit 1`，报 `expected=30.0 actual=35.0` |
| P01 legacy 零破坏 | `checked=34, mismatches=0`（与改前一致） |
| N2 analysis mode | `you cannot modify ... use switchtolayout first`；`switchtolayout()` 后可写 45° |

新增 6 条断言：`source.angle theta`、`source.plane wave type`（字符串）、
`FDTD.x min bc` / `x max bc`（字符串）、`FDTD.pml layers`、`FDTD.bfast alpha`。
`angle phi` **故意不查**——2D 下该属性 inactive，builder 从未写过（诚实降级，不假装全查）。
