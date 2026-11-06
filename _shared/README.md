# _shared — 跨包共享工具

> 只放**两个以上包**会用到的东西。单包专用的脚本留在该包 `scripts\` 内。

---

## 文件

### `lumapi_common.py` ★

FDTD 会话与校验的共享工具。把 `SKILL.md` §8.4 的实测片段固化，避免每包重写。

```python
import sys
sys.path.insert(0, r"F:\Lumercial_WS\FDTD_WS\_shared")
from lumapi_common import setup_env, open_fdtd, ascii_gate, assert_ran, verify_and_run

setup_env()                                  # 设置 license + import lumapi
f = open_fdtd()                              # 带重试的会话工厂
try:
    f.load(fsp); f.switchtolayout()
    ...
finally:
    f.close()
```

| 函数 | 作用 | 依据 |
|---|---|---|
| `setup_env()` | 设 license + sys.path，import lumapi | SKILL.md §1.1 |
| `open_fdtd()` | 会话工厂，带端口 TIME_WAIT 重试 | §1.4 |
| `n_sessions()` | 数 fdtd-solutions.exe 进程 = 占用席位数 | §1.3 |
| `ascii_gate(p)` | 路径 ASCII 闸门（GPU 引擎硬要求） | §6.2 |
| `assert_ran(f, fsp)` | **三判据**确认"真的算了" | §2.1 |
| `mesh_report(log)` | 抽网格/内存/迭代数，判断规模健康 | §6.1 |
| `n_at(f, mat, λ)` | 查折射率，**内部把波长换成频率** | §5.2 |
| `check_material(...)` | 带期望值的材料校验 | §5.2 |
| `verify_and_run(fsp)` | 完整序列：save→关→load→run→三判据 | §2.1 |

**自测**：`python lumapi_common.py` → 会真启一个会话再关掉，验证环境。

---

## 不放这里的东西

以下通用工具留在 `F:\Lumercial_WS\scripts\`，**引用而不复制**（避免多份副本不同步）：

| 脚本 | 用途 |
|---|---|
| `z_fix_gpu_res.py cpu\|gpu` | GPU/CPU 资源一键恢复 |
| `lumapi_probe.py` | `.fsp` 对象树探查 |
| `fsp_strings.py` | `.fsp` 二进制字符串抽取 |
| `z_ascii_work.py` | 中文路径 → ASCII 目录 |
| `d2_lib.py` | 吸收类（042/D2）共享模块 |
| `gs_cgh.py` / `gs_demo.py` | GS 相位恢复（纯 Python） |
