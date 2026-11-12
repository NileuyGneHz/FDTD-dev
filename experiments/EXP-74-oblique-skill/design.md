# EXP-74 — 新技能 `fdtd-lumerical-oblique-incidence`（stage 2.5，零引擎）

## 假设

角度扫描不需要第二份 builder 或 runner：`run_fdtd_sweep.py --sweep-json` 逐点覆盖
`spec["parameters"]`，而 builder 的所有数值都走 `ev()`。所以只要新技能把角度写成
`parameters.theta` 并产出 `spec_angles.json`，扫描天然免费。

`plan` / `collect` / `--self-test` 全部零引擎；`--dry-run` 必须在写任何文件之前返回。
物理决策全部调用 `library/py/fsp_build.py::resolve_incidence()`，不复制规则。

## 判据

1. `--self-test` 的解析真值全过（Bloch 边界相位 π、漂移 38.682/30/19.471、官方
   100/150 THz 例、BFAST 机时表、`getsourceangle` 恒 30、符号约定不自动取负）。
2. `plan --dry-run` 不写文件、`plan` 产出 `angle_sweep_plan.json` + `spec_angles.json`；
   后者过 `validate_spec.py --strict` 且能被 runner 的 `--dry-run` 展开成 3 个点。
3. `build_fsp.py --check` 对 `spec_angles.json` 建模 `38/0`。
4. N5：三个角度的 CSV 完全相同 → `collect` 检出重复曲线并 exit 1；曲线不同 → exit 0。
5. 唯一脚本 + 一份实现；`scripts/` 下只有 `angle_sweep.py`。

## 负对照

N5 是核心：删掉 `theta` 的扫描参数（所有角度跑成同一条曲线）时 `collect` 必须红。
另外用 `--self-test` 里的负例覆盖：重复角度 / θ≥85 / bloch_single+宽带 / 未知 mode /
A<0 / diverging 日志 / 缺 `_p0.log` 报 N/A。

## 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
A="skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py"
S="_scratch/regress/2026-11-13/oblique"
O="$S/angle_sweep"
"$PY" "$A" --self-test
"$PY" "$A" plan --spec "$S/spec_p08.json" --angles 0,30,60 --pol 90 \
  --mode bfast --out "$O" --dry-run --json
"$PY" "$A" plan --spec "$S/spec_p08.json" --angles 0,30,60 --pol 90 \
  --mode bfast --out "$O" --json
"$PY" skills/fdtd-paper-parameter-extraction/scripts/validate_spec.py \
  "$O/spec_angles.json" --strict
"$PY" "$A" collect --plan "$O/angle_sweep_plan.json" --run-dir "$O/fake_run_dup" \
  --out "$O/angle_matrix_dup.csv" --json; echo $?
```

## 实测结果

| 项 | 结果 |
|---|---|
| `--self-test` | **49/49** |
| `plan --dry-run` | `mode=bfast tilt_axis=x n_points=3 cost=10.5× hash=9c1d2d345242e5e9`，`written=[]` |
| `spec_angles.json` 校验 | `0 error, 0 warning` |
| runner `--dry-run` | 3 点 `{theta:0/30/60, pol:90}` |
| `build_fsp --check` | `checked=38, mismatches=0` |
| N5（三条相同曲线） | `duplicate_curves` 3 对，`ok=false`，**exit 1** |
| 正对照（A=0.9/0.85/0.8） | `rows=15, A_range=[0.8,0.9], ok=true, exit 0` |

## 执行中抓到并修掉的两个真缺陷

1. **driver 指向原 spec**：`make_plan` 最初把 `--spec` 写成输入的 spec 路径，
   但原 spec 没有 `parameters.theta`，照它跑会得到三条完全相同的曲线 —— 正是 N5 要抓的假扫描。
   改成指向 `spec_angles.json`，并把「driver 必须消费 spec_angles.json」写进 `--self-test` 防回归。
2. **`collect` 没查收敛**：初版 `angle_checks()` 只看点数 / A 范围 / 重复曲线，
   完全没读 `_p0.log`。补上每点 `diverging` / `Completed` / 最终 `Auto Shutoff` 检查；
   缺日志时按项目契约记 `N/A + reason`，**不静默当成"已收敛"**。

产物：`SKILL.md`、`scripts/angle_sweep.py`（唯一入口）、`references/angle-physics.md`
（三种口径 / 漂移公式 / 机时表 / v251 属性落点 / 课程工程读回 / 坑表）。
