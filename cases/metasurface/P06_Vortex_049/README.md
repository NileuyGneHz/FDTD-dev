# P06 — 涡旋光产生

---

## 0. Agent 快速接管（每次协作必读）

| 项 | 值 |
|---|---|
| **包 ID** | `P06` |
| **任务状态** | 未开始 |
| **本次目标** | 产生拓扑荷 l 的涡旋光束 |
| **验收标准** | 远场相位呈 2πl 螺旋，中心有暗核 |
| **入口脚本** | `—（课件内）` |
| **预计耗时** | 单次仿真 35–60 s |

### 开工前必做

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" "F:\Lumercial_WS\FDTD_WS\tools\check_packages.py" --pkg P06
```

---

## 1. 论文

| 项 | 内容 |
|---|---|
| 标题 | *Light Propagation with Phase Discontinuities: Generalized Laws of Reflection and Refraction* |
| 期刊 | 课程 049 讲配套论文 |
| DOI | `见论文 PDF` |
| 本地文件 | `paper\` ✅ 已归档 |
| 课程出处 | `F:\Lumercial_WS\Classes\FDTD\课件\049第九讲 涡旋光产生\` |

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
| `9论文-Light_Propagation_with_Phase_Discontinuities___Generalized_Laws_of_Reflection_and_Refraction.pdf` | 论文原文 |

### `fsp\` — 仿真工程（ASCII 文件名）

| 文件 | 说明 |
|---|---|
| `fig2a.fsp` | 仿真工程 |
| `fig2de.fsp` | 仿真工程 |
| `fig2g-1.fsp` | 仿真工程 |
| `fig2g-2.fsp` | 仿真工程 |
| `fig2g-3.fsp` | 仿真工程 |
| `fig2g-4.fsp` | 仿真工程 |
| `fig2g-5.fsp` | 仿真工程 |
| `fig2g-6.fsp` | 仿真工程 |
| `fig2g-7.fsp` | 仿真工程 |
| `fig2g-8.fsp` | 仿真工程 |
| `fig5.fsp` | 仿真工程 |

### `scripts\` — 本包专用脚本

| 文件 | 说明 |
|---|---|
| `draw_fig2a.lsf` | 课程配套绘图脚本 |
| `draw_fig2e.lsf` | 课程配套绘图脚本 |
| `draw_fig2g.lsf` | 课程配套绘图脚本 |
| `draw_fig3c.lsf` | 课程配套绘图脚本 |
| `fig2g_modify_run.lsf` | 课程配套绘图脚本 |

### `results\` — 数据与图

| 文件 | 内容 |
|---|---|
| — | 待跑仿真后生成 |

### `notes\` — 笔记

| 文件 | 说明 |
|---|---|
| — | 暂无 |

## 4. 本包特有的坑

**终点目标**：相位调控的最终综合应用。

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
