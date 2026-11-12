---
name: fdtd-lumerical-field-propagate
description: 用角谱法把一个平面上的复场传播到下一个平面，为「单段 FDTD + 自由空间传播」的多层光路（4f 系统、透镜-掩模-透镜、级联超表面）提供可串联的链接器；只做传播，不建模型、不跑仿真、不出图。
---

# 角谱传播（场 → 下一个面）

## 概述

FDTD 只能算有限厚度的一段；4f 这类系统的层间距是 mm 级，网格按 λ/20 走根本铺不开。
本技能补的是「层间那段真空」：把一段 FDTD 的场导出，用角谱传播 `z`，得到下一段的入射面。
**只传播**——透镜相位在 `fdtd-holo-phase-retrieval` / `fdtd-lumerical-field-map`，
出图在 `fdtd-lumerical-figure`，建模在 `fdtd-lumerical-fsp-build`。

输入：`.fsp` 的场监视器，或任意满足契约的 npz；输出：可**再次作为输入**的 npz（可串联）。

## CRITICAL（违反即停止）

1. **`dx > λ/2` 不许传播**。角谱在 Nyquist 之上会把高频折回低频，结果看着像"传播了"，
   其实是混叠。脚本 `exit 2` 并给出需要的 dx。
2. **边缘硬截断的场不要拿去做往返验证**。截断本身含倏逝分量，正向衰减、反向也衰减，
   往返必然不闭合——这是物理，不是 bug。要验往返，用边缘平滑的带限场。
3. **倏逝分支只在正向衰减**；反向用共轭会把它放大，噪声指数增长。距离要自己限制。
4. **不要在这里加相位**（透镜、涡旋、掩模相位）。这里只搬场；加相位会让"传播"变成第二种建模实现。
5. **采样窗 `N·dx` 不够时，场会从一边绕到另一边**。`propagate_metrics.json` 里的
   `max_reliable_distance_um` 是上限，超了要加大 `--n`，不是加大 `--pad` 就完事。

## 核心工作流

1. 拿到入射面场：`--fsp run.fsp --monitor field`（只读开一次会话），或 `--npz dump.npz`。
2. 先 `--dry-run` 看计划：输入、距离、补零后的 N、是否有 mask。
3. 正式跑：`--distance-um Z --out OUT`，得到 `propagated.npz` + `propagate_metrics.json`。
4. 读 metrics：`energy_ratio`（真空应 ≈1，含倏逝时会略小于 1）、`evanescent_fraction`、
   `max_reliable_distance_um`。超上限就加大 `--n` 重跑。
5. 把 `propagated.npz` 喂给下一段（下一段 FDTD 的源，或再传一次）。

## 示例

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# 自检（不读任何文件）
"$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py --self-test

# 从 npz 传播 50 um
"$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py \
    --npz _scratch/lens1_field.npz --distance-um 50 --out _scratch/lens1_at_mask --json

# 4f 第二段：先加孔径，再传播
"$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py \
    --npz _scratch/lens1_at_mask/propagated.npz --mask-npz _scratch/aperture.npz \
    --distance-um 50 --n 2048 --out _scratch/at_lens2
```

## 故障排除

| 症状 | 原因 / 处置 |
|---|---|
| `sampling error: dx ... > lambda/2` | 监视器网格太粗；换监视器或先降采样到 ≥2 点/波长 |
| `energy_ratio` 明显 <1（真空） | 场里有倏逝分量（硬边、亚波长结构）；这是正常衰减，不是算错 |
| 场从边缘绕回、出现鬼影 | 采样窗不够；加大 `--n`，看 `max_reliable_distance_um` |
| `mask 形状 ... 不一致` | mask 必须与场同尺寸；先裁剪/重采样 |
| `--n 小于输入网格` | `--n` 只能补零，不能缩小 |

## 按需加载

- 读 `references/usage.md` **当要串 4f / 多层，或改传播距离与网格时**：4f 配方、
  采样窗公式、偏振分量处理、与 holo 的边界。

## 脚本与退出码

`scripts/propagate_field.py` — `--npz|--fsp --monitor --distance-um --out
[--n --pad --mask-npz --wavelength-um --json --dry-run]`，另有 `--self-test`。
`0` 成功 / `1` 运行失败 / `2` 参数或采样不合法。
