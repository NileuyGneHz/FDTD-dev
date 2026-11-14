# D-022 四个技能脚本对非法 JSON 抛裸 traceback

**状态**：`resolved`

## 现象

给下列脚本喂空 JSON 文件或语法错误的 JSON，会抛未捕获的
`json.decoder.JSONDecodeError` 并打印完整 Python traceback，**exit 1**：

| 脚本 | 修复前 |
|---|---|
| `fdtd-lumerical-fsp-build/scripts/build_fsp.py` | traceback，exit 1 |
| `fdtd-paper-parameter-extraction/scripts/validate_spec.py` | traceback，exit 1 |
| `fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py` | traceback，exit 1 |
| `fdtd-lumerical-phase-retrieval/scripts/run_phase_sweep.py` | traceback，exit 1 |

## 根因

`json.load(fh)` / `json.loads(...)` 直接暴露在 `main()` 里，没有 `try`。
**"输入文件坏了" 被呈现成 "脚本崩了"**——使用者第一反应是去查代码，而不是查输入。

同类脚本（`assemble_spec.py`、`angle_sweep.py`、`inspect_fsp.py`）本来就返回 exit 2
且打印可读错误，说明这不是设计意图，是遗漏。

## 修复

四处统一加：

```python
try:
    ... json.load / json.loads ...
except FileNotFoundError:
    print("ERROR spec not found: %s" % path)          # 或 stderr
    return 2
except json.JSONDecodeError as exc:
    print("ERROR spec is not valid JSON: %s  (%s)" % (path, exc))
    return 2
except OSError as exc:
    print("ERROR cannot read spec: %s  (%s)" % (path, exc))
    return 2
```

退出码 2 = 参数/输入错误，与这些脚本既有的 `--out` 缺失、spec 不存在一致。

## 验证

```powershell
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
$e="_scratch/edge/empty.json"    # 空文件

& $PY skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py --spec $e --out _scratch/edge/o3
# -> ERROR spec is not valid JSON: ...  (Expecting value: line 1 column 1 (char 0))   exit 2

& $PY skills/fdtd-paper-parameter-extraction/scripts/validate_spec.py $e
# -> 同上，exit 2

& $PY skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec $e --out x
& $PY skills/fdtd-lumerical-phase-retrieval/scripts/run_phase_sweep.py --spec $e --out x
# -> 同上，exit 2，无 traceback
```

**回归**：正常 spec 仍 exit 0（`validate_spec` 报 `spec is structurally valid`；
`build_fsp --dry-run` exit 0；`run_fdtd_sweep --dry-run` exit 0）。

## 影响面

- 四个技能的所有 `--spec` 入口
- 不影响 `--self-test` 与正常输入路径
- 全部门禁（8 项）与三个技能的 self-test 复跑全绿
