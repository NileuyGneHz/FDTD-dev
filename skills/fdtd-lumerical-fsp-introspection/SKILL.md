---
name: fdtd-lumerical-fsp-introspection
description: >
  把已有 Lumerical FDTD 工程反解析成结构化证据：对象树与层位、自定义材料参数、边界与网格、源与监视器设置、
  工程内已存的 R/T/A 谱与峰值，并可与模型 spec 做层位和数值 diff，用来判定参考工程究竟算了什么、是否收敛。
  当手上有课程或论文附带的 .fsp、要用它校准复现参数、要读陌生工程的对象树、或要核对两个工程为何给出不同结果时使用。
  触发词：参考 FSP、工程反解析、对象树、工程体检、已存谱、层位对照、参考工程校准、收敛判据。
agent_created: true
---

# 参考 `.fsp` 工程反解析与校准

## 概述

复现论文时，包里的 `.fsp` 往往比 README 更接近真相——它记录了**当时真正跑的设置**。
本技能把这些二进制工程读成可 diff 的 JSON：结构、材料、数值设置、已存谱、收敛状态，
再和 spec 对齐。产出 `manifest.json` / `spectra.json` / `diff.json` / `summary.json`。

**它是校准与诊断能力，不是建模能力**：从零建模仍由
`fdtd-lumerical-unitcell-simulation` 负责。没有参考工程时不要加载本技能。

## CRITICAL（违反即停止）

1. **只 `load`，绝不 `save` 回原 `.fsp`**。`cases/` 是只读参照系；重跑参考工程必须先复制到
   `_scratch/regress/` 的纯 ASCII 路径。原地 `save` 会无声污染黄金对照。
2. **`getnamed(name)` 返回的是换行分隔的属性名字符串，不是 dict**；且在
   `Mesh` / `PlaneSource` / `DFTMonitor` 上会抛错。必须 fallback 到 `dir(obj)` + `getattr`，
   否则源和监视器的设置会整段丢失，得到"看起来对"的残缺 manifest。
3. **判收敛看日志末值，不看有没有结果**。`layoutmode` + `_p0.log` 的 `Completed` +
   最后一条 `Auto Shutoff` 小于该工程的 `auto shutoff min`，三条缺一不算。
   grep 正则必须带指数 `[0-9.eE+-]+`，否则 `8.87e-06` 会被截成 `8.87`，把收敛误判成未收敛。
4. **不要把同包里的多个 `.fsp` 当成同一个工程**。P01 的
   `infrared_perfect_absorber.fsp`（Periodic、末值 `8.87508e-06`、收敛）与
   `d2_perfectCross.fsp`（PML、跑满 77813 步、末值 `0.046734`、未收敛）给出相近的 0.82，
   但只有前者可作基准。混用会推出错误结论（`defects/D-001`）。
5. **材料按参数数值匹配，不按名字**。课程工程叫 `user_Au` / `uesr_Al2O3`，
   自建 spec 叫 `Au_paper` / `Al2O3_paper`；按名字比对会全部漏掉并误报"材料不同"。
6. **`--dry-run` 必须在 `lumapi.FDTD()` 之前 return**。每个会话占 1 个许可席位，
   只打印计划却开了会话会白占席位并拖慢后续仿真。

## 核心工作流

1. 写配置 JSON（模板见 `assets/inspect_config.example.json`）：列 `fsp[]`、选 `mode`、
   可选 `reference_spec`。**所有相对路径以仓库根为基准，不依赖 cwd**。
2. `--dry-run` 打印计划并确认：路径全部可达、纯 ASCII、`--out` 不落在 `cases/`。
3. 正式跑 `scripts/inspect_fsp.py --config <json> --out <dir>`，得到四份 JSON。
4. 先看 `summary.json` 的 `layoutmode` 与 `derived`；`layoutmode=1.0` 的工程**没有可信谱**，
   `spectra.json` 里只有一条 `Can not find result` 说明。
5. 有 `reference_spec` 时读 `diff.json`：
   - **`functional_layers_match`** 是回答"ts 从哪个面量"的判据——只比地平面 / 间隔层 /
     谐振器，排除基底（基底在不透明地平面下方，厚度差不影响光学）；
   - `all_layers_match` 是含基底的严格判定；`substrate_mismatch` 单独列出基底差异及其说明；
   - `settings_mismatches` 逐项列出边界 / 网格精度 / 收敛阈值 / 仿真时长 / 波长范围 /
     频点 / 偏振的差异；`all_settings_match` 是它的总开关；
   - `all_materials_match` 按**数值**判定 Drude 与 `(n,k)` 参数是否同源（名字不同不算差异）。
6. **只有 diff 全部通过，才把该工程当"黄金对照"**。任一不通过，先写
   `defects/D-xxx`（根因 / 修复 / 可重跑验证），再决定要不要改建模 spec。
7. 需要数值互证时，把 diff 出的设置写进 spec，用
   `fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --out _scratch/regress/<date>/...`
   重跑，与工程已存谱比较；回归输出一律不得写回 `cases/`。

## 示例

**用户：** "参考 P01 相关的 FSP 文件复现，先搞清楚课程工程到底怎么建的。"

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config skills/fdtd-lumerical-fsp-introspection/assets/inspect_config.example.json \
  --out _scratch/regress/fsp-20261107 --dry-run
"$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config skills/fdtd-lumerical-fsp-introspection/assets/inspect_config.example.json \
  --out _scratch/regress/fsp-20261107 --json
```

**2026-11-07 P01 实测产出：**

| 工程 | 边界 | 层位 Al₂O₃ / 地 / 十字 (nm) | 收敛 | 已存谱 peak A |
|---|---|---|---|---|
| `infrared_perfect_absorber.fsp` | Periodic | `[-185,0]` / `[-285,-185]` / `[0,100]` | ✅ `8.87508e-06` | **0.8196 @ 6.152 µm** |
| `d2_perfectCross.fsp` | PML | 同上 | ❌ `0.046734` | 无（`layoutmode=1`） |
| `point_00_base.fsp`（自建） | Periodic | 同上 | ✅ `8.8e-05` | 0.8083 @ 5.85 µm |

`functional_layers_match = true` → **185 nm 是「地平面顶面 → 十字底面」**，与自建 spec
完全一致，旧结论里"量取面定义差"的猜测被证伪。
`all_layers_match = false` 只因课程工程的 Si 基底厚 1715 nm、自建 spec 用 2000 nm
（`substrate_mismatch` 单列），在不透明地平面下方不影响结果。
`settings_mismatches` 列出 acc 8 vs 4、shutoff 1e-5 vs 1e-4、1 ps vs 5 ps、
3.5–11 µm/100 pts vs 4–8.5 µm/91 pts、偏振 90° vs 0° —— 这些正是峰位
5.85 µm → 6.15 µm 的来源。

数值互证（把课程设置写进 spec 重跑）：

| 来源 | peak A | peak λ | A@6 µm |
|---|---|---|---|
| 课程工程已存谱 | 0.8196 | 6.152 µm | 0.7174 |
| 反解析设置重跑 | 0.8177 | 6.152 µm | 0.7169 |
| 原 spec 基线重跑 | 0.8069 | 5.85 µm | 0.7147 |

三条在 6 µm 处聚合在 0.0027 内 → Lumerical 在该论文参数下的稳定答案就是 ~0.82，
与论文 CST/实验的 0.97 属求解器口径差异。**不要**调 `ts` 到 120 nm 去凑 0.962，那是拟合。

## 结构组（structure group）怎么读

组内子对象只有一条出口：`obj.getChildren()`，而它内部是
`select(children)+getAllSelectedObjects()`，代价 **0.057 s/子对象**——
30×30 阵列的组要 255 s（`select('group::*')`、`selectpartial('*')`、`selectinside`
在 v251 上都拿不到，别浪费时间）。所以：

| 组的样子 | 行为 | manifest 里会看到 |
|---|---|---|
| 带 `period`（周期阵列，子对象 ≈ number²×每胞） | 不展开 | `children_collapsed` + `children_are_array` + `duplicates_unchecked` + `n_children_declared` |
| `number > 256` | 不展开 | 同上 |
| 其余（如 21 个手工摆的柱） | 展开并查同名 | `children_collapsed` + `n_children` +（有重名时）`duplicate_name` |

**`duplicates_unchecked: true` 的含义是「没查」，不是「查过没有重名」。**
这句话是这块唯一的坑：漏读它会把「未知」当成「干净」。

## 故障排除

| 症状 | 处置 |
|---|---|
| `no items matching the name 'source' can be found` | 对 `PlaneSource`/`Mesh`/`DFTMonitor` 用 `dir(obj)` + `getattr`，见 `references/fsp-property-map.md` §2 |
| `The group scope can not be set properly.` | `getChildren()` 打在叶子对象上了；try/except 后当叶子处理 |
| `Can not find result 'T' in the result provider 'R'` | 工程没跑过（`layoutmode=1`）；记"无已存谱"，不是脚本失败 |
| `Failed to get variable`（读 layoutmode） | 先 `eval("lm = layoutmode;")` 再 `getv("lm")` |
| `getmaterial` 读不到自定义材料 | 材料名大小写/拼写不同（课程里有 `uesr_Al2O3` 这种笔误）；按数值匹配 |
| 源 `x span` 大于周期 | FDTD 中心偏移导致派生属性被撑大；读 FDTD 的 `x`/`y`，见属性图 §5 |
| GPU 报 1113 / 弹窗乱码 | 路径含非 ASCII；`--dry-run` 阶段就会拦下来 |
| 输出里 `diff` 为 `null` | 没给 `reference_spec` 或 `mode=spectra`；改为 `mode=both` 并补配置 |

## 按需加载

- 读 `references/fsp-property-map.md` **当要写/改 lumapi 读取代码、或属性读不出来时** ——
  v251 实测属性表、`getnamed` 三签名、收敛三判据、派生属性、结果布局、只读纪律。
- 读 `assets/inspect_config.example.json` **当要给新包写反解析配置时** ——
  可直接复制，改 `fsp[]` 与 `reference_spec` 两处即可。
- 读 `defects/D-001-fsp-layer-reference-and-converged-course-project.md`
  **当有人再次引用 P01 的 0.82 时** —— 记录两个工程被混为一谈的代价。

## 脚本与退出码

`scripts/inspect_fsp.py` — `--config --out --dry-run --json`；
`0` 全部成功 / `1` 至少一个工程读取失败 / `2` 配置或参数错误。
`--json` 把 `summary.json` 同时打到 stdout，便于流水线串接。
