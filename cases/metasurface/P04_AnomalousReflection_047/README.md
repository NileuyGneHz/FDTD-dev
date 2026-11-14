# P04 — 异常反射

---

## 0. Agent 快速接管（每次协作必读）

| 项 | 值 |
|---|---|
| **包 ID** | `P04` |
| **任务状态** | 未开始 |
| **本次目标** | 复现梯度超表面的异常反射角与效率 |
| **验收标准** | 反射角符合广义 Snell 定律，效率与论文吻合 |
| **入口脚本** | `—（课件内）` |
| **预计耗时** | 单次仿真 35–60 s |

### 开工前必做

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" "F:\Lumercial_WS\FDTD_WS\tools\check_packages.py" --pkg P04
```

---

## 1. 论文

| 项 | 内容 |
|---|---|
| 标题 | *High-Efficiency Broadband Anomalous Reflection by Gradient Meta-Surfaces* |
| 期刊 | 课程 047 讲配套论文 |
| DOI | `见论文 PDF` |
| 本地文件 | `paper\` ✅ 已归档 |
| 课程出处 | `F:\Lumercial_WS\Classes\FDTD\课件\047第七讲 异常反射\` |

**要复现的目标**：

| 目标 | 论文位置 | 状态 |
|---|---|---|
| 待填 | 待填 | ❌ 未开始 |

---

## 2. 关键参数（填论文值）

> ⚠️ 材料数据源必须写明是哪一套。四套 TiO₂ 差 ~15%，混用结果对不上。

| 参数 | 值 | 来源 |
|---|---|---|
| 设计波长 | 待填 | 论文 |
| 周期 / 高度 | 待填 | 论文 |
| 结构材料 | 待填 | 论文 Methods |
| 基底 | 待填 | 论文 Methods |
| 网格 | 待填 | 经验值 |
| 边界条件 | 待填 | 论文 |

---

## 3. 文件清单（2026-09-30 已归档）

### `paper\` — 论文

| 文件 | 说明 |
|---|---|
| `7论文-High-Efficiency_Broadband_Anomalous_Reflection_by_Gradient_Meta-Surfaces.pdf` | 论文原文 |

### `fsp\` — 仿真工程（ASCII 文件名）

| 文件 | 说明 |
|---|---|
| `fig1bc.fsp` | 仿真工程 |
| `fig2c_and_3.fsp` | 仿真工程（原 `fig2c&3.fsp`，已改名） |
| `fig2c_and_3_method2.fsp` | 仿真工程（原 `fig2c&3_method2.fsp`，已改名） |
| `fig4.fsp` | 仿真工程 |
| `fig4_method2.fsp` | 仿真工程 |
| `fig5e.fsp` | 仿真工程 |
| `fig5e_method2.fsp` | 仿真工程 |

### `scripts\` — 本包专用脚本

| 文件 | 说明 |
|---|---|
| `draw_fig1bc.lsf` | 课程配套绘图脚本 |
| `draw_fig2c.lsf` | 课程配套绘图脚本 |
| `draw_fig2c_method2.lsf` | 课程配套绘图脚本 |
| `draw_fig4.lsf` | 课程配套绘图脚本 |
| `draw_fig4_method2.lsf` | 课程配套绘图脚本 |
| `draw_fig5e.lsf` | 课程配套绘图脚本 |
| `draw_fig5e_method2.lsf` | 课程配套绘图脚本 |

### `results\` — 数据与图

| 文件 | 内容 |
|---|---|
| — | 待跑仿真后生成 |

### `notes\` — 笔记

| 文件 | 说明 |
|---|---|
| — | 暂无 |

## 4. 本包特有的坑

涉及 czt / 远场 / 角度扫描。

（通用坑见 `..\..\SKILL.md`）

---

## 5. 复现进度与差异记录

| 图号 | 论文值 | 我的结果 | 差异 | 判断 |
|---|---|---|---|---|
| 待填 | — | — | — | — |

---

## 6. 与导师的同步

| 项 | 内容 |
|---|---|
| 已向导师汇报 | 待确认 |
| 待确认问题 | — |
| 交付物 | — |
