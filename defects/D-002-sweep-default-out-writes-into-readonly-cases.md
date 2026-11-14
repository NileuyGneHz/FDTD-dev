# D-002 `run_fdtd_sweep.py` 默认输出目录会写进只读的 `cases/`
**状态**：`resolved`（默认输出改到 --out，见正文验证段）
## 根因

`skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py` 的 `main()`：

```python
out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)),
                                   (spec.get("meta", {}).get("package", "spec") + "_out"))
```

`spec_<id>.json` 按归档契约常驻 `cases/P0N_<topic>/config/`。未显式给 `--out` 时，
输出（`point_*.fsp`、`point_*.csv`、`summary.csv`）会落到 `cases/.../config/P01_out/`，
违反 `cases/AGENTS.md` 的「只读」与 `AGENTS.md` §5「产出只落单元内」。
`.fsp` 是二进制且可能几十 MB，误写进只读参照系后很难察觉。

2026-11-07 实测 dry-run：

```
$ python ... run_fdtd_sweep.py --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json --dry-run
out_dir  : F:\Lumercial_WS\FDTD_WS\cases\metasurface\P01_Absorber_042\config\P01_out
```

## 修复

本次**不改脚本默认值**（属 C 档脚本变更，按 `skill-change-contract.md` §3 需要
改前改后同输入数值对比 + 2 个 case 回归，不应夹在文档订正里做）。采取两步：

1. **A 档文档订正**：`fdtd-lumerical-unitcell-simulation/SKILL.md` 的脚本段明确
   「必须显式 `--out`；spec 来自 `cases/` 时不得省略」，并给出合规命令示例。
2. 新增的 `fdtd-lumerical-fsp-introspection/SKILL.md` 在 CRITICAL 里写明
   「只读加载参考 `.fsp`，任何产物只写 `--out`，回归一律 `_scratch/regress/`」。

后续若要改默认输出位置，走 C 档：改前改后同 spec 逐行对比 `summary.csv`，
并在 1 个吸收器 case + 1 个超表面 case 上回归。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS

# ① 复现症状（不写盘）
"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json --dry-run
# 期望输出含 cases/metasurface/P01_Absorber_042/config/P01_out —— 证明默认路径确实指向只读区

# ② 合规用法
"$PY" skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/regress/p01-20261107/baseline --dry-run
# 期望 out_dir = _scratch/regress/p01-20261107/baseline

# ③ 确认没有污染 cases/
find cases -type d -name "*_out"
# 期望：无输出
```

## 影响面

所有以 `cases/` 内 spec 为输入、又省略 `--out` 的回归 / 复现任务。
`cases/` 只读是硬约束，这条默认路径是一个「静默违规」入口。
