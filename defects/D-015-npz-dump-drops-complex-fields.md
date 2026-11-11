# D-015：`format=npz` 的场 dump 会静默丢掉复数字段（E 本身）
**状态**：`resolved`（见正文修复段与 EXP 记录）
- 状态：**已修复**（2026-11-10，EXP-50）
- 发现：2026-11-10，写 `fdtd-lumerical-field-map` 的 `--fsp` 载入路径时
- 影响技能：`fdtd-lumerical-session-control`（`read_monitors`）、
  `fdtd-lumerical-field-map`（`_numeric`，同款过滤条件）

## 症状

对场监视器用 `session_control.py` 的 `format: npz` 落盘，得到的 npz **只有坐标**：

```
npz 里既没有 E，也没有 Ex/Ey/Ez；实际键 = f, lambda, x, y, z
```

而 dump 的台账是「成功」的：`bytes`、`sha256`、`arrays` 都在，没人报错。

## 根因

```python
if a.dtype.kind in "fiub" and a.size:     # f=float, i=int, u=uint, b=bool
    arrs[k] = a
```

`"fiub"` 里**没有 `c`（complex）**。这行过滤的初衷是「排除 `Lumerical_dataset`
之类的对象句柄」，但场监视器的 `E` 恰好是 `complex128`，与句柄一起被丢掉。
真正该排除的是 `dtype.kind == "O"`（object），不是「非实数」。

```python
if not arrs:
    ... # 修复时补的闸
```

## 为什么没被门禁抓到

`check_scripts.py` 检查的是 CLI 契约（`--out`/`--json`/`--dry-run`），
不检查 `read_monitors` 的返回值是否含关键数组；四份复现报告里也没有一条做过
「npz 落盘后回读 E」的断言——P05 的 dump 走的是自己的 `run_dump.py`，
没有经过 `read_monitors`，所以这条路径从未被真实跑过。

这与 EXP-41 的病灶同型：**判据只看「类型/形状/字段存在」，不看「关键物理量在不在」**。

## 修复

1. 两处过滤条件改 `"fiubc"`；
2. `read_monitors` 在写 npz 前加闸：`arrs` 为空直接 `ConfigError`，
   不再写出一个「成功但空」的文件；
3. `field_map._numeric` 同步（它是照抄这段惯用法写出来的）。

## 验证

`_scratch/regress/2026-11-10/EXP-50/run_checks.py --with-fsp` 第 9 条：

| 路径 | z_focus |
|---|---|
| `--npz RCP_field.npz`（他人 dump，含 E） | 9.300 µm |
| `--fsp RCP.fsp --monitor field`（走修复后的载入器） | 9.300 µm |

`|Δz| = 0.0`。修复前 `--fsp` 路径直接抛 `FieldError`（见症状）。
