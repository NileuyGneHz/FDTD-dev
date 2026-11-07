# v251 `.fsp` 反解析属性图（实测，2026-09-30 ~ 2026-11-07）

> 本文只记**读别人工程时会被坑到的实测细节**。通用 lumapi 规则见
> `docs/constitution/field-manual.md` 与 `skills/fdtd-lumerical-headless/SKILL.md`。

## 1. 对象树怎么走

```python
f.load(fsp)
root = f.getObjectById("::model")
for child in root.getChildren():        # 顶层对象
    child.name, child.type, child.getChildren()
```

- `getChildren()` **只在容器对象上可用**；对叶子（Rectangle / Mesh / DFTMonitor）会抛
  `The group scope can not be set properly.`，必须 try/except 吞掉后当叶子处理。
- `Analysis Group` 是容器：内部 `field` / `index` 监视器能读到，
  `getattr(ag, "analysis script")` / `"setup script"` 能读到完整脚本源码。
- `::model` 根的 `results` 用 `dir(root.results)` 列出结果名；空列表 `['']` 表示没有结果。
- ⚠️ **遍历对象树会改变 group scope**：一旦调过 `getObjectById("::model")` / `getChildren()`，
  再用全局名字 `getresult("R","T")` 会报 `Can not find object 'R'`。
  2026-11-07 实测：三个工程全部触发。
  → **同一会话里必须「先读已存谱，再遍历对象树」**，或分两次会话各做一半。
  `scripts/inspect_fsp.py` 的 `main()` 已按此顺序固定，不要调换。

## 2. `getnamed` 的三个签名（最容易写错）

| 形式 | 返回 | 用途 |
|---|---|---|
| `getnamed(name)` | **一个字符串**，属性名用 `\n` 分隔 | 取属性名清单，**不是 dict** |
| `getnamed(name, prop)` | 单个属性值 | 最常用 |
| `getattr(obj, prop)` | 单个属性值 | 配合 `dir(obj)` |

解析方式：`[x.strip() for x in s.split("\n") if x.strip()]`。

⚠️ `Mesh` / `PlaneSource` / `DFTMonitor` 上调 `getnamed(name)` 会报
`no items matching the name 'xxx' can be found`。**必须 fallback 到 `dir(obj)` + `getattr`**，
`SimObject` 会自动把下划线转成空格（`obj.x_span` ≡ `obj["x span"]`）。
`Rectangle` / `FDTD` / `Analysis Group` 用 `getnamed` 正常。

## 3. 常用属性名（v251 实测可读）

| 类别 | 属性 |
|---|---|
| 几何 | `x`, `y`, `z`, `x span`, `y span`, `z span`, `x min/max`, `y min/max`, `z min/max`, `radius`, `inner radius` |
| 归属 | `material`, `mesh order`, `index`, `enabled` |
| FDTD 区 | `dimension`, `x min bc`…`z max bc`, `mesh accuracy`, `auto shutoff min`, `simulation time`, `dt stability factor` |
| 源 | `injection axis`, `direction`, `polarization angle`, `amplitude`, `wavelength start`, `wavelength stop`, `override global source settings` |
| 监视器 | `monitor type`, `wavelength center`, `wavelength span`, `frequency points`, `use wavelength spacing`, `use source limits` |
| 局部网格 | `dx`, `dy`, `dz` |
| 材料 | `getmaterial(name, prop)`：`Plasma resonance`, `Plasma collision`, `Refractive Index`, `Imaginary Refractive Index`, `Permittivity`, `mesh order` |

⚠️ 自定义材料名在不同工程里不同（课程工程 `user_Au` / `uesr_Al2O3`，
自建 spec `Au_paper` / `Al2O3_paper`），**按名字匹配一定会漏**。
本技能按**参数数值**匹配材料（见 `scripts/inspect_fsp.py` 的 `build_diff`）。

## 4. 判「算没算」：三判据，缺一不算

1. `f.eval("lm = layoutmode;")` → `f.getv("lm")`：
   `0.0` = analysis 模式（已算过），`1.0` = 还在 layout（**没有可信结果**）。
   直接 `getv("layoutmode")` 会报 `Failed to get variable`。
2. 同目录存在 `<工程名>_p0.log`。
3. 日志里 `Completed … iterations`，且**最后一条 `Auto Shutoff` 小于该工程的
   `auto shutoff min`**。

⚠️ 抓 `Auto Shutoff` 的正则必须带指数：`[0-9.eE+-]+`。
写成 `[0-9.]+` 会把 `8.87508e-06` 截成 `8.87508`，把收敛误判成没收敛。

P01 实测对照（两个课程工程，别再混为一谈）：

| 工程 | x/y 边界 | 步数 | 末值 `Auto Shutoff` | 阈值 | 判定 |
|---|---|---|---|---|---|
| `infrared_perfect_absorber.fsp` | Periodic | 7039 | `8.87508e-06` | `1e-5` | ✅ 收敛 |
| `d2_perfectCross.fsp` | PML | 77813 | `0.046734` | `1e-5` | ❌ 跑满时间上限未收敛 |

## 5. 派生属性：读到 span 不对时别急着改

`PlaneSource` 的 `x span` / `y span` 是**派生量** = `2*max(|FDTD x min|, |FDTD x max|)`。
`d2_perfectCross.fsp` 的 FDTD 中心偏了 `x=-6.23 nm, y=-59.43 nm`，
源 span 被撑到 `2.0125 × 2.1189 µm`（周期只有 2 µm）。
在当前会话里 `setnamed` 改成 2 µm 能读回 2 µm，但 **save + reload 后会被重算回去**。
正解是把 FDTD 的 `x` / `y` 设回 0。

→ 所以 manifest 里**同时记录 FDTD 中心、FDTD span、源 span**，才是完整证据。

## 6. 结果读取布局

`getresult(monitor, "T")` 在 Python 侧可能是：

- `dict`：`{"lambda": …, "f": …, "T": …}` → 取 `item["lambda"]` 与 `item["T"]`
- `list[dict]`：取 `raw[0]`
- 二维 `ndarray`：前两列是波长与功率

`getresult` 不存在的监视器会抛 `Can not find result 'T' in the result provider 'R'`
（常见于 `layoutmode=1` 的未运行工程），按「无已存谱」记录，**不要当脚本失败**。

能量守恒 `A = 1 - R - T` 只在反射模式成立；`T` 出现 `~ -1e-5` 是数值零。
透射型器件（源在下方、R 监视器在源下方）读到的 R 是负值，需要取反。

## 7. `getindex` 用来核对材料时的坑

- 参数是**频率 Hz**，且必须是矩阵：`f.getindex(name, np.array([[C0/lam]]))`。
- 传波长不报错，会静默外推出鬼值（TiO₂ 得 5.99 而不是 2.45）。
- 校验方式：与论文 Drude 解析值对照。

P01 实测（论文 `wp=2π·2175 THz`, `wc=2π·6.5 THz`）：
`user_Au` 与 `Au_paper` 在 4 / 6 / 8 / 10 µm 的 `(n,k)` 与解析值逐位相同，
6 µm 为 `2.8026 + 43.2457i`。→ 材料实现不是偏差来源。

## 8. 只读纪律

- `cases/` 是只读参照系：**只 `load`，绝不 `save` 回原 `.fsp`**。
  重跑参考工程时必须先复制到 `_scratch/regress/` 的纯 ASCII 路径。
- 路径含非 ASCII → GPU 引擎 Windows 1113 弹乱码，以 `_p0.log` 为准。
- 每个 `lumapi.FDTD()` 占 1 个许可席位，`close()` 必须落在 `finally`。
- `--dry-run` 必须在 `lumapi.FDTD()` **之前** return，否则会白占一个席位。
