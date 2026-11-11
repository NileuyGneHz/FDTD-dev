# EXP-47 — inspect_fsp 在 4500 对象工程上 273 s → < 30 s

## 假设

`inspect_fsp.py` 的耗时不在递归本身，而在**为每个对象建 Python 包装**：
`selectall()` + `getAllSelectedObjects()` 给 4500 个对象各建一个 `SimObject`
（~0.06 s/个），`read_obj` 里对巨型组调 `getChildren()` 再一次付同样的账。
D-007 只点了第一处，两处都要量。

## 输入

`cases/P06_Vortex_049/model/fig5.fsp`（4500 叶子、30×30 structure group）

## 方法

1. 探针 `probe_timing.py` 把整轮拆成：`load` / `selectall` / 顶层 `children` /
   巨型组 `getChildren` / 树遍历后 `getresult`，逐项记墙钟。
2. 监视器发现改为**只读顶层**（顶层 7 个对象，代价与模型规模无关），
   并验证「先树遍历、后 getresult」是否仍能读到数据
   （现有代码注释声称顺序不可反，要拿数推翻或确认）。
3. 巨型组的「折叠」判断移到 `getChildren()` **之前**：`number`/`period` 已经在
   props 里，没必要先建 4500 个包装再发现该折叠。

## 判据

| 指标 | 期望 |
|---|---|
| `fig5.fsp` 整轮墙钟 | `< 30 s`（原 273 s） |
| 监视器集合 | 与 selectall 慢路径**逐名相同**（不是「数量相同」） |
| `spectra_status` | 仍为 `ok`，峰值/派生量与改前一致 |
| P01 / P05 / P07 / P09 的派生指标 | 逐位不变（P01 `peak_A=0.8196016`） |

## 负对照

- 做法 A：把某个监视器**放进 group** 再建工程 → 若新路径只读顶层，必须
  **明确报告「该组未展开，其中的监视器未计入」**，不能静默少一个。
  这是本次改动唯一的新增失真风险，必须被看见。
- 做法 B：拿掉 `getresult` 前的树遍历 → 期望 `spectra_status` 变 `ok`；
  若顺序真的不能反，改成「树在 getresult 之后」也必须仍 ok。
- 两条都必须「按预期失败/放行」并留数。

## 可重跑命令

```bash
python _scratch/regress/2026-11-10/EXP-47/probe_timing.py
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config _scratch/regress/2026-11-09/EXP-13/cfg_p06.json --out /tmp/p06_new
python _scratch/regress/2026-11-10/EXP-47/neg_controls.py
```

## 实测：D-007 的根因写错了

```json
{
  "load_s": 0.76,
  "selectall_s": 0.02,
  "selectall_n": 7,
  "root_children_s": 0.06,
  "getchildren_s_on_array_group": 255.79,
  "getchildren_children": 4500,
  "monitors_match_old_vs_new": true,
  "total_s": 262.87
}
```

D-007 写的是「瓶颈在 `enumerate_monitors()` 的 `selectall()+getAllSelectedObjects()`
（0.06 s/个 × 4500）」。实测：`selectall` 只选中 **7** 个对象、耗时 **0.02 s**。
真正的 255.8 s 花在 `read_obj` 里对那个 30×30 组的 **`getChildren()`**：4500 个子对象，
每个 0.057 s。而旧代码先 `getChildren()` 再判断「该折叠」，这 255 s 建出来的包装
在下一行就被丢掉了。

`lumapi` 的 `getChildren()` 内部就是 `select(children)+getAllSelectedObjects()`，
所以三种替代路径都试过并失败：`select('group::*')`、`selectpartial('*')`、
`getnamed(group,'children')`——组内对象在引擎里只有这一条出口。

## 什么时候可以不展开（判据来自实测，不是猜）

| 工程 | 组属性 | number | 实际子对象 | 展开耗时 |
|---|---|---|---|---|
| P05 RCP | number，**无** period | 21 | 21 | 1.3 s |
| P06 fig5 | number + **period** | 30 | 4500 | 255.8 s |

带 `period` 的是周期阵列，子对象数 ≈ number² × 每胞对象数；不带的组，子对象数 = number。
所以：**有 `period` 或 number>256 → 跳过展开并标 `duplicates_unchecked`**；
其余照旧展开，同名检测照旧生效。

## 负对照

- A：P06 阵列组 → `children_collapsed` + `duplicates_unchecked` +
  `children_are_array` + `n_children_declared=30`（实测：全部为真）
- B：P05 组 → `duplicate_name=['rectangle']`、`n_children=21`、
  **不**带 `duplicates_unchecked`（实测：一致，EXP-14 证据保住）
- C：阵列组的 `getChildren` 调用次数 → 实测 **0**
- 负对照是否按预期失败：是（3/3）

## 结论

- fig5：273 s → **1.7 s**（进程整体 7.9 s），判据 <30 s 达成。
- P01 / P05 / P06 / P09 的 `spectra.json` 与 `diff.json` **逐字节相同**，
  P01 `peak_A=0.8196016447349421` 不变。
- 树输出：P01 0 差异、P05 0 差异、P06 8 处差异，全部是
  「把没查说出来」——`duplicate_*` 换成 `duplicates_unchecked` / `children_are_array`，
  `n_children=4500` 换成 `n_children_declared=30`。
- 这一轮真正的教训不是「优化」，而是**上一轮把 273 s 归错了因**：
  归因错误导致第一轮去读属性表、去加 `--max-objects`，都没用。

