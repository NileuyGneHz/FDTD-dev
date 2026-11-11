---
name: fdtd-metasurface-assembly
description: >
  把 fdtd-holo-phase-retrieval 产出的量化相位版图（quantized_phase*.csv）+ 单元库
  （library_map.json）装配成 fsp-build 可用的 array spec——零引擎、纯查表，
  不开 lumapi、不跑仿真。支持中心裁剪（保持单元周期）与整数步长两种取窗方式，
  单元库缺档显式报错并给出现次数。触发词：装配超表面、相位转阵列、cell 参数表、
  逐格变参 spec、超表面阵列、assembly、相位 CSV 转 spec。
agent_created: true
---

# fdtd-metasurface-assembly（stage 1.9）

## 1. 什么时候用它

| 想做的事 | 用这个技能 |
|---|---|
| 我有 `quantized_phase*.csv` + 单元库，要一片完整超表面的 spec | ✅ |
| 拿到 spec 想建 `.fsp` | 转 `fdtd-lumerical-fsp-build`（array 类型是它的底层能力） |
| 只要建普通单胞 / 堆栈 | 同上，不需要本技能 |
| 相位版图还没算 | 转 `fdtd-holo-phase-retrieval`（stage 1.8，方向在前） |
| 建完要跑全息重建 / 看远场 | stage 2/3 仿真 + `fdtd-lumerical-field-map` |

**边界**：本技能只做查表装配（相位档位 → 单元几何参数），不开引擎、不反演相位、
不标定单元库。库里没有该档是**装配侧的 missing[]**（Skill A 的契约），本技能会报错
列出缺失 level 与出现次数，不硬凑参数。

## 2. 核心工作流

```bash
# ① 自检（0.2 s，20 条脱机判定）
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py --self-test

# ② 先看规模（不开引擎）
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py \
  --phase quantized_phase_L8.csv --library library_map.json \
  --geometry geom.json --target-nx 64 --target-ny 64 --dry-run --json

# ③ 装配 spec
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py \
  --phase quantized_phase_L8.csv --library library_map.json \
  --geometry geom.json --target-nx 64 --target-ny 64 --mode crop \
  --out spec_meta.json --json

# ④ 建 .fsp（转调 fsp-build，一份实现不复制）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec spec_meta.json --out <单元内 results/> --check --json
```

## 3. CRITICAL（违反即停止）

1. **取窗必须用 `--mode crop`（默认）**。`--mode stride` 会把单元周期放大 stride 倍
   （EXP-64 实测：0.4 µm → 1.6 µm，在 λ=0.74 µm 下是光栅不是超表面）。
   只有"把相位图当连续版图重新粗采样"时才允许 stride。
2. **单元库缺档不许硬凑**。报错会列出缺失 level 与出现次数；补库的来源是
   `fdtd-paper-parameter-extraction` 或查论文，不是这里现场编参数。
3. **规模上限**：objects 引擎警告线 2000 格、硬拒绝线 8192 格（`fsp_build` 常量）。
   64×64=4096 可建（build 383 s、6.9 MB 实测）；更大阵列需要脚本引擎（未实现），
   先降规模。
4. **行主序**：CSV 是 y 外层、x 内层，与 `fsp_build.array_cells` 的 `divmod(idx, nx)`
   一致；显式 `i`/`j` 标注会被 builder 交叉校验，写反直接报错。

## 4. 输入契约

- `--phase`：Skill A 的 `quantized_phase*.csv`，四列 `x_um,y_um,phase_rad,level`。
  要求均匀网格、无重复坐标；`phase_rad` 不进 spec（几何参数才是引擎要的）。
- `--library`：`library_map.json`，`{"levels": N, "cells": [{"level": k,
  "params": {...}}, ...]}`；`params` 的键就是 `element` 模板里引用的表达式名
  （如 `d1`/`d2`/`rot`）。
- `--geometry`：模板对象（`element` + `element_material`）、材料表、`parameters`
  公共参数、可选 `sub_object`、完整 `simulation` 段。

## 5. 输出

`spec_meta.json`：标准 fsp-build spec，其中 `objects` 里含一个 `type: "array"` 对象
（`cell_params` 逐格参数，长度 = nx*ny）；`meta.assembled_from` 记录相位 CSV、单元库、
源网格、取窗方式与 stride——**抽样方式永远写进产物**，不允许静默。

## 6. 已知边界（不假装支持）

- 只支持降规模（crop / 整数 stride），不支持插值放大。
- 非均匀网格、重复坐标、非整除 stride 全部报错。
- 每格只变几何参数；材料逐格变化显式拒绝（array 共用一种材料，见 fsp-build SKILL.md）。
- ellipse 单元建成 polygon 后引擎侧没有可读的 x/y/x span 属性，`--check` 对它只断言
  z / z span（诚实降级，EXP-64）；box 模板的逐格尺寸断言是全量的。

## 7. Examples

```bash
python skills/fdtd-metasurface-assembly/scripts/assemble_spec.py \
  --phase _scratch/regress/2026-11-11/holo/run1/quantized_phase_L8.csv \
  --library _scratch/regress/2026-11-11/array/library_L8.json \
  --geometry _scratch/regress/2026-11-11/array/geom_64.json \
  --target-nx 64 --target-ny 64 --mode crop \
  --out _scratch/regress/2026-11-11/array/spec_64.json --json
# nx=64 ny=64 cells=4096 pitch=0.4 µm stride=[1,1] levels_used=0..7
```

## 8. References / 按需加载

| 文件 | 什么时候读 |
|---|---|
| `skills/fdtd-lumerical-fsp-build/SKILL.md` §array | 要手写 array spec / 改 check 行为时 |
| `_shared/fsp_build.py`（`array_cells` / `array_plan`） | 要理解行主序与作用域注入时 |
| `skills/fdtd-holo-phase-retrieval/SKILL.md` | 要重新生成相位 CSV 时 |

## 9. 相关文件

| 文件 | 用途 |
|---|---|
| `scripts/assemble_spec.py` | 本技能唯一入口（装配 + --self-test） |
| `experiments/EXP-60…65` | array 类型、逐格 check、零破坏回归、查表装配、端到端、门禁 |
| `_scratch/regress/2026-11-11/array/` | 回归产物（3×3 正负对照、64×64 端到端） |
