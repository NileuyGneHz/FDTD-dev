# D-007 inspect_fsp 在超大结构组上仍要 273 s（EXP-15 判 fail）

**状态**：`resolved`（2026-11-10，EXP-47）——273 s → 1.7 s

## 根因（订正：第一版归因是错的）

~~定位：瓶颈不在递归，而在 `enumerate_monitors()` —— `selectall()` +
`getAllSelectedObjects()` 会为全部 4500 个对象建 Python 包装，约 0.06 s/个。~~

**这段是错的。** EXP-47 逐段计时（`_scratch/regress/2026-11-10/EXP-47/probe_timing.json`）：

| 步骤 | 墙钟 |
|---|---|
| `load` | 0.76 s |
| `selectall()` + `getAllSelectedObjects()` | **0.02 s**，只选中 **7** 个对象 |
| 顶层 `getChildren()` | 0.06 s |
| **30×30 组的 `getChildren()`** | **255.79 s**（4500 个子对象，0.057 s/个） |

真正的原因在 `read_obj` 里：它**先** `getChildren()`、**后**判断「该折叠」，
于是 255 s 建出来的 4500 个包装在下一行就被丢掉了。旧描述把「对象多所以慢」
归到了错的那一处——按错的归因去做优化（去属性表读取、加 `--max-objects`）
自然一个都不管用。

第一版描述里那句「叶子对象数从 4500 降到 7」也是错的：叶子从来没有被读出来过，
`n_children=4500` 只是计数。

尝试过的无效优化：
- 去掉每个对象一次 `getnamed(name)` 属性表查询 → 273 s 不变（说明开销不在属性表）；
- `--max-objects 800 --max-depth 3` → 273 s（说明不在读取，而在选择）。

## 修复（待做）

不要用 `selectall()` 枚举监视器。可选路径：
1. 先用 `getObjectById("::model")` 拿到树，**只遍历顶层子对象**取 type，再对 type 命中
   monitor 的对象单独 `getresult`；顶层只有 7 个对象，代价与模型规模无关。
2. 或 `f.getnamed("::model")` 的属性表里解析子对象名（一次调用）。

判据不变：`fig5.fsp` 单工程 < 30 s，且 `spectra_status` 与本次一致（`ok` / 5 个监视器）。

## 验证

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config _scratch/regress/2026-11-09/EXP-13/cfg_p06.json --out /tmp/p06
# 期望 wall < 30 s
```

## 影响面

只影响「超大结构组」工程的耗时，不影响结果正确性：
P01/P05/P07/P09 的派生指标在本轮修改后逐位不变（P01 `peak_A=0.8196016`）。

## 修复（2026-11-10）

`read_obj` 把折叠判断移到 `getChildren()` **之前**，并区分「该不该付枚举的钱」：

| 组 | 判据 | 行为 | 实测 |
|---|---|---|---|
| P05 RCP（21 个同名 rectangle） | number，**无** period | 展开 → 同名检测 | 1.3 s，`duplicate_name=['rectangle']` 保留 |
| P06 fig5（30×30 阵列） | number + **period** | 跳过展开 | 255.8 s → 0 s |

带 `period` 的组是周期阵列，子对象数 ≈ number² × 每胞对象数；不带的组子对象数 = number。
跳过时**必须**写 `duplicates_unchecked: true` + `children_are_array` +
`children_skipped_reason`：否则「没有 `duplicate_name`」会被读成「查过且没有」，
这正是本轮最容易引入的新失真。

判据：fig5 整轮 **1.7 s**（进程 7.9 s），< 30 s；
P01 / P05 / P06 / P09 的 `spectra.json`、`diff.json` 逐字节相同；
P01 `peak_A=0.8196016447349421` 不变；树输出 P01/P05 各 0 差异、
P06 8 处差异全部是「把没查说出来」。

## 试过但不可行的路径（省得再试）

`lumapi` 的 `getChildren()` 内部就是 `select(children)` + `getAllSelectedObjects()`，
所以组内对象只有这一条出口。以下全部在 v251 上实测失败或返回 0：
`select('group::*')` / `select('::model::group::*')` / `selectpartial('*')` /
`selectinside` / `selectallinside` / `getnamed(group,'children')`。
