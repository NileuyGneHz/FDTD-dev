# EXP-73 — 物理闸（角度/BC 一致性）与 A 越界检查

## 假设

课程口述给了天然负对照：Bloch + 400–800 nm @30° 时长波吸收翘起来、**700 nm 处 A<0**。
现有 `run_fdtd_sweep.py::metrics()` 只对 R/T 做 `check_physical_range()`，这个错误会**静默过关**。
同时 `validate_spec.py --strict` 会放过「θ=30° + Periodic BC」这种物理错误配置。

修法分两处，都不重复实现物理规则：
- `validate_spec.py` 调用 builder 的 `resolve_incidence()`（单一实现），把决策/异常转成 issues；
  并在 validator 层**更严格**：spec 写 Periodic 而 builder 会按 Bloch 建模 → 直接拒绝（spec 与 .fsp 不一致）。
- `run_fdtd_sweep.py::metrics()` 把 `A` 加进 `check_physical_range()` 的循环。

## 判据

1. N4 三条违规配置全被 `validate_spec.py --strict` 拒绝（exit 1）：
   θ=30 + Periodic BC / Bloch + 宽带 / 2D + φ≠0。
2. 合法 P08 spec 与 P01 legacy spec 都是 `0 error, 0 warning, exit 0`（零破坏）。
3. N7：构造「R/T 都在 [0,1] 但 A<0」的结果，`metrics()` 必须报 **A 越界**而不是别的量
   —— 这条用来证明新增检查是 load-bearing，不是被 R 的越界顺带挡下。

## 负对照

- N4 任一变绿 = 物理闸失效。
- N7 若 `metrics()` 报的是 `R 越界` 或干脆通过，说明 A 检查没生效（假轮次）。

## 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
V="skills/fdtd-paper-parameter-extraction/scripts/validate_spec.py"
S="_scratch/regress/2026-11-13/oblique"
for c in n4_periodic_bc n4_bloch_broadband n4_2d_phi; do
  "$PY" "$V" "$S/EXP-73/$c.json" --strict; echo "$c exit=$?"
done
"$PY" "$V" "$S/spec_p08.json" --strict
"$PY" "$V" cases/metasurface/P01_Absorber_042/config/spec_p01.json
```

## 实测结果

| 用例 | 结果 |
|---|---|
| N4-1 Periodic BC | exit 1，报 `斜入射倾斜面 bc.x='Periodic' 必须写成 'Bloch'` |
| N4-2 Bloch+宽带 | exit 1，报 `bloch_single 只能用于单波长 … 漂移 22.3° > 2.0°` |
| N4-3 2D+φ≠0 | exit 1，报 `angle phi 在 v251 2D 里是 inactive` |
| 合法 P08 / P01 legacy | `0 error(s), 0 warning(s)` / exit 0 |
| N7（R∈[0.1,0.9]、T∈[0,0.3]、A_min=-0.2） | `metrics()` 抛 `A 越界 [-0.200, 0.900]`，load-bearing=PASS |

## 设计取舍

`validate_spec.py` 的 incidence 检查**只在 spec 声明了角度时启用**：旧 spec 完全没有
`incidence` / `angle_theta_deg` 时整块跳过，保证 P01/P02/P03 的校验输出不变。
builder 对 `Periodic` 仍只是 WARN 并改回 Bloch（`wd_BFASK.fsp` 实测可收敛），
但 validator 拒绝它——**闸比执行严**，spec 不允许与实际建模不一致。
