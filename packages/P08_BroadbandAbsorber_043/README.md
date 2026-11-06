# P08 — 宽角度可见光吸收器

---

## 0. Agent 快速接管（每次协作必读）

| 项 | 值 |
|---|---|
| **包 ID** | `P08` |
| **任务状态** | 未开始 |
| **本次目标** | 复现宽带角度不敏感吸收 |
| **验收标准** | 0–60° 入射角度内吸收谱稳定，与论文吻合 |
| **入口脚本** | `—（课件内）` |
| **预计耗时** | 单次仿真 35–60 s |

### 开工前必做

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" "F:\Lumercial_WS\FDTD_WS\tools\check_packages.py" --pkg P08
```

---

## 1. 论文

| 项 | 内容 |
|---|---|
| 标题 | *Wide-angle, polarization-independent ultrathin broadband visible absorbers* |
| 期刊 | 课程 043 讲配套论文 |
| DOI | `见论文 PDF` |
| 本地文件 | `paper\` ✅ 已归档 |
| 课程出处 | `F:\Lumercial_WS\Classes\FDTD\课件\043第三讲 宽角度可见光吸收器\` |

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
| `Wide-angle__polarization-independent_ultrathin_broadband_visible_absorbers.pdf` | 论文原文 |

### `fsp\` — 仿真工程（ASCII 文件名）

| 文件 | 说明 |
|---|---|
| `normal_incidence.fsp` | 仿真工程（原 `正入射.fsp`，已改名） |
| `oblique_BFAST.fsp` | 仿真工程（原 `斜入射BFAST.fsp`，已改名） |
| `oblique_Bloch.fsp` | 仿真工程（原 `斜入射Bloch.fsp`，已改名） |
| `wide_angle.fsp` | 仿真工程（原 `wide angle.fsp`，已改名） |

### `scripts\` — 本包专用脚本

| 文件 | 说明 |
|---|---|

### `results\` — 数据与图

| 文件 | 内容 |
|---|---|
| — | 待跑仿真后生成 |

### `notes\` — 笔记

| 文件 | 说明 |
|---|---|
| — | 暂无 |

## 4. 本包特有的坑

涉及斜入射 BFAST / Bloch 边界。

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
