# EXP-02 lumapi_common 必须只有一份实现，技能内只能是转发壳

## 假设

两份逐字节副本会在改名后静默分叉（D-005/D-006 同类）。改成壳之后，删掉唯一实现必须直接 ImportError，而不是回退到隐藏副本。

## 输入

`_shared/lumapi_common.py`（唯一实现）+ `skills/fdtd-package-workspace/scripts/lumapi_common.py`（壳）

## 对照与负对照

正：通过技能路径 `import lumapi_common`，7 个函数全部可调用、`n_sessions()` 返回 0；负：把 `_shared/lumapi_common.py` 改名后必须 `ImportError`。

## 判据

`grep -c '^def open_fdtd'`：shared=1、壳=0；导入后 `callable(open_fdtd)`；负对照抛 ImportError。

## 重跑命令

```bash
"$PY" -c "import sys; sys.path.insert(0, r'skills/fdtd-package-workspace/scripts'); import lumapi_common as m; print(callable(m.open_fdtd), m.n_sessions())"
```
