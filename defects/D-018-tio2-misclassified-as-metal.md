# D-018：`probe_gpu_eligibility` 把 TiO2 误判成金属（词表 `ti` / `titanium` 误伤）

**状态**：`resolved`（2026-11-11）

## 根因

`tools/probe_gpu_eligibility.py` 的 `METAL_WORDS` 里含 `"ti"` 与 `"titanium"`，
而判断方式是「材料名按非字母数字切词后与词表取交集」：

```python
toks = {w.lower() for w in re.split(r"[^A-Za-z0-9]+", nm) if w}
if toks & METAL_WORDS:
    metals.append(nm)
```

`TiO2 (Titanium Dioxide) - Siefke` 切词后含 `ti` 与 `titanium` → 命中词表 → 被判为金属 →
`verdict = gpu_risky` → 默认不走 GPU。

**这是误伤**：TiO2 是全介质超表面的标准材料，正是最该用 GPU 的那类工程。

实测（2026-11-11）：

| 工程 | 修正前 | 修正后 |
|---|---|---|
| `cases/P03_HWP_Ding2015/model/t4_tio2_unitcell.fsp` | `gpu_risky`（金属 `TiO2 (Titanium Dioxide) - Siefke`） | **`gpu`**（3D + 平面波 + 介质） |

## 修复

从 `METAL_WORDS` 删掉 `"ti"` 与 `"titanium"`，并在源码里写明理由：

```python
METAL_WORDS = {"au", "ag", "al", "cu", "ni", "cr", "gold", "silver",
               "aluminum", "aluminium", "copper", "drude",
               "conductive", "pec"}
```

**为什么删了不丢判据**：真正的「强损耗 / 色散金属」仍由两条独立判据抓——

1. `LOSSY_K = 0.5`：虚折射率 > 0.5（这是主判据，不依赖名字）
2. 模型类型含 `drude` / `conductive`

名字词表只是**兜底**。裸钛（Ti）在光学超表面里几乎不用；真用到损耗钛，`k` 值会触发判据 1。

## 验证

```powershell
$PY="C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

# 正例：TiO2 现在应判 gpu
& $PY tools/gpu_guard.py --fsp cases/P03_HWP_Ding2015/model/t4_tio2_unitcell.fsp --dry-run
# 期望：GPU ... - 3D + 平面波源 + 介质/低显存 -> 可走 GPU

# 负例：真金属仍须被抓住（分类没被带偏）
& $PY tools/gpu_guard.py --fsp cases/P01_Absorber_042/model/d2_perfectCross.fsp --dry-run
# 期望：CPU ... - 金属/有损材料 ['user_Au']
& $PY tools/gpu_guard.py --fsp cases/P03_HWP_Ding2015/model/fig1_hwp_paper_materials.fsp --dry-run
# 期望：CPU ... - 金属/有损材料 ['Au_Drude']
& $PY tools/gpu_guard.py --fsp cases/P05_Metalens_048/model/LCP.fsp --dry-run
# 期望：CPU ... - 含 TFSFSource -> GPU 引擎明确不支持（D-011）
```

实测（2026-11-11）：5 个工程的分类结果全部符合预期，TiO2 走 GPU，Au/Drude/TFSF 走 CPU。

## 影响面

`tools/probe_gpu_eligibility.py` 一份。**间接影响**所有按它的 `verdict` 做批次的流程
（`tools/gpu_guard.py`、并行跑批的批次划分）。

历史批次若曾据此把 TiO2 工程排进 CPU 队列，那些工程的机时被浪费了——但不影响任何已出结论
（CPU 结果比 GPU 更可信）。

## 遗留

`METAL_WORDS` 的兜底机制本质上不可靠：任何含金属缩写子串的介质名都可能误伤
（`al` 之于 `Al2O3` 是**正确**命中，但 `ni` 之于 `Niobium` 之类就看运气）。
当前靠 `LOSSY_K` 主判据兜住；若再出现误伤，优先考虑**删掉整个名字词表**、只留
`LOSSY_K` + 模型类型两条判据。
