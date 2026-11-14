# D-020：`angle_sweep.py --json` 在 Windows 捕获管道里因中文输出崩溃

**状态**：`resolved`（2026-11-13，入口处把 stdout/stderr 重配为 UTF-8）

## 根因

`angle_sweep.py` 的 `plan` / `collect` 用 `json.dumps(..., ensure_ascii=False)` 打印中文
warning 与指标。Windows 上 Python 的 stdout 是管道时默认走 `cp1252`（本机实测），
`print()` 遇到中文即抛：

```text
ERROR: 'charmap' codec can't encode characters in position 386-388: character maps to <undefined>
```

DSH 的 `pwsh` 工具正是用管道捕获输出，所以**技能在 agent 里第一次调用就 exit 2**；
人直接在中文控制台跑可能看不到，属于「本机看着好、agent 一跑就死」的宿主差异。

## 修复

`scripts/angle_sweep.py` 的 `if __name__ == "__main__":` 入口增加：

```python
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
```

`sys.dont_write_bytecode = True` 已在文件顶部，不需要额外处理 `.pyc`。

## 验证

```powershell
$PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
$S="skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py"

# 修复前：不设 PYTHONIOENCODING 时，plan --json 抛 UnicodeEncodeError、exit 2
# 修复后：同一个命令 exit 0，中文 warning 正常输出
& $PY $S plan --spec <spec.json> --angles 0,30 --pol 0 --mode bfast `
  --out <dir> --dry-run --json

& $PY $S collect --plan <dir>/angle_sweep_plan.json --run-dir <dir>/run `
  --out <dir>/angle_matrix.csv --json

& $PY $S --self-test
# 期望 50/50 assertions passed
```

实测（2026-11-13）：`plan --dry-run --json` 与 `collect --json` 在**不设**
`PYTHONIOENCODING` 的情况下均 exit 0；`--self-test` 50/50；`check_skill_contract.py`
WARN 0 / FAIL 0。

## 影响面

- 所有通过 DSH / PowerShell 管道调用 `angle_sweep.py` 的场景；`plan` 的中文
  `warnings` 与 `collect` 的中文 metrics 是触发点。
- 不影响 `.fsp` 构建与仿真本身；只影响 CLI 的 JSON/人类输出。

## 同类风险

其他技能脚本若也 `ensure_ascii=False` 打印中文且没有 `reconfigure`，在 DSH 管道里会同样崩。
判据：`grep -L "reconfigure" skills/*/scripts/*.py`，再逐个用管道跑 `--help` / `--json`。
2026-11-13 扫描：10 个技能脚本同时含 `ensure_ascii=False` 且无 `reconfigure`
（`gs_retrieval` / `design_loop` / `field_map` / `propagate_field` / `make_figure` /
`build_fsp` / `session_control` / `run_fdtd_sweep` / `assemble_spec` / `validate_spec`）。
本次只修了 `angle_sweep.py`，没有逐个改——这是已知的横向风险，不是「已全部解决」。
