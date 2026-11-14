# D-021 `make_figure.py` 的 `eval` 可执行任意代码

**状态**：`resolved`

## 根因

`skills/fdtd-lumerical-figure/scripts/make_figure.py` 的 `fig_stack()` 用：

```python
z0 = float(eval(str(centre[2]), {}, payload.get("parameters") or {}))
```

**空 dict 作为 globals 不会屏蔽 `__builtins__`**——Python 会自动注入它。所以
`centre[2]` 写成 `"__import__('os').getcwd()"` 就能执行任意代码。

实测（本机）：

```python
eval("__import__('os').getcwd()", {}, {})   # -> 'F:\Lumercial_WS\FDTD_WS'   ← 可执行
eval("__import__('os').getcwd()", {"__builtins__": {}}, {})  # -> NameError  ← 被拦
```

这是**唯一**一处危险写法：其余三个技能（`fsp_build` / `inspect_fsp` / `validate_spec`）
都用 `{"__builtins__": {}}` + 字符白名单，是对的。

**威胁模型**：spec 来自论文抽取或用户提供，属于**不可信输入**。一个恶意/手误的
spec JSON 在 `--kind stack` 下即可执行任意命令。

## 修复

新增 `_safe_eval()`，与 `fsp_build.py` 的写法对齐：

```python
_SAFE_EXPR = re.compile(r"[0-9a-zA-Z_.+\-*/() ]+")

def _safe_eval(expr, params: dict) -> float:
    s = str(expr)
    if not _SAFE_EXPR.fullmatch(s):
        raise FigureError("不支持的表达式字符：%r" % s)
    ...
    return float(eval(s, {"__builtins__": {}}, scope))  # noqa: S307
```

同时把 `except Exception` 收窄为 `except FigureError`（只有「缺 z」才跳过）。

## 验证

```powershell
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# 正常 spec 仍能画
& $PY skills/fdtd-lumerical-figure/scripts/make_figure.py --kind stack `
    --input cases/P01_Absorber_042/config/spec_p01.json `
    --out _scratch/figtest/p01_stack.png --json
# -> {"layers": 5, "z_min_m": -2.285e-06, "z_max_m": 1e-07, "bytes": 21820}

# 注入负对照
& $PY skills/fdtd-lumerical-figure/scripts/make_figure.py --kind stack `
    --input _scratch/figtest/evil_spec.json --out _scratch/figtest/evil.png
# -> ERROR objects[] 里没有带 z span 的对象，无法画侧视层图（exit 2，不生成文件）
```

注入被拦在**字符白名单**这一层：`__import__(...)` 含引号和括号外的非法字符，直接
`FigureError`；即使侥幸通过白名单，`__builtins__={}` 也保证 `__import__` 未定义。

## 影响面

- `fdtd-lumerical-figure` 的 `--kind stack`
- 任何把 spec JSON 当不可信输入的调用方
- 未影响 `spectra` / `phase` / `field` / `fom` / `compare`（不经过 `_safe_eval`）
