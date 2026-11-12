# 用法：4f 串联、采样窗、偏振与边界

## 1. 数据契约

| 方向 | 键 | 类型 / 约束 |
|---|---|---|
| 输入 | `E` | complex，`(nx,ny)` 或 `(nx,ny,3)`；方阵像素 |
| 输入 | `x_um`、`y_um` | 一维、等间距；`dx == dy` |
| 输入 | `wavelength_um`（或 `lambda_um`） | 标量；可被 `--wavelength-um` 覆盖 |
| 输入（可选） | `mask`（经 `--mask-npz`） | `(nx,ny)`，非零处通过 |
| 输出 | `propagated.npz` | 同上键 + `distance_um`；**可直接作为下一次输入** |
| 输出 | `propagate_metrics.json` | 能量、倏逝占比、采样上限、告警 |

单位：npz 里一律 µm，脚本内部转 m 再喂 `library/py/angular_spectrum.py`。

## 2. 4f 串联配方（透镜-掩模-透镜）

```
[FDTD lens1] --E(x,y)@z1--> propagate(f1) --> [mask] --> propagate(f2) --> [FDTD lens2 / 像面]
```

1. **lens1**：用 `fsp-build` 建有限口径 + PML，`field` 监视器拍住出射面；
   跑完用 `--fsp` 直接读，或用 `session-control --format npz` 导出。
2. **传播 f1**：`--distance-um f1`。检查 `energy_ratio`（纯传播应 ≈1；有硬边会略低）
   与 `max_reliable_distance_um`（必须 > f1，否则加大 `--n`）。
3. **掩模**：把掩模存成 npz 的 `mask`（0/1 或 0…1），用 `--mask-npz`。
   若掩模是纯相位，先乘 `exp(iφ)` 再存成复场，不要塞进 amplitude mask。
4. **传播 f2**：读上一步的 `propagated.npz` 当输入，重复 2。
5. **第二片透镜**：把 `propagated.npz` 的场作为 lens2 入射条件（或作为其源场的抽样目标）；
   本技能不负责把它写回 `.fsp`。

每一段都留 `propagate_metrics.json`，报告里逐段贴 `energy_ratio`，不要只贴最终图。

## 3. 采样窗：两个不同的上限

- **传播距离上限**（防 FFT 绕回）：`z_max ≈ N·dx²/λ`。
- **窗口要装得下衍射展宽**：`N·dx ≳ D + 2·λ·z/D`（D 为口径），否则边缘绕回。
  两条都要看：`z_max` 过了但窗口不够，照样出鬼影。

实践值（λ=1.55 µm）：

| 口径 D | 距离 z | 最小 N（dx=0.5 µm） |
|---|---|---|
| 100 µm | 1 mm | 4096 |
| 200 µm | 2 mm | 8192 |

N 翻倍 ⇒ 内存 ×4；先粗算再开跑。

## 4. 偏振

`E` 为三分量时逐分量独立传播——这是**逐分量近似**，不是严格矢量衍射。
它在 NA ≲ 0.5 时够用；大角度会聚（NA>0.7）时 `Ez` 与横场耦合不能忽略，
此时应在单胞阶段把偏振效应吃掉，或改用严格矢量方法。SKILL 里已把这条列为边界。

## 5. 与 `fdtd-holo-phase-retrieval` 的边界

- holo 的 `propagate()` 是 **GS 迭代内部**的传播器，输入是 `grid` dict，没有 I/O；
- 本技能是**数据链接器**，输入是文件，输出是文件，带采样检查与 metrics；
- 两者数值必须逐点一致（EXP-68 断言 <1e-12）。holo 暂未改为 import 本模块，
  避免动一个已绿的技能；哪天要动，只改它 `propagate` 的内部实现即可。

## 6. 常见误用

| 误用 | 后果 |
|---|---|
| 拿硬边孔径做往返验证 | 往返不闭合，误判"实现有 bug"（其实是倏逝不酉） |
| 加大 `--pad` 却不看 `max_reliable_distance_um` | 窗口变大但距离仍可能超上限；两个数一起看 |
| 把透镜相位塞进传播器 | 出现第二份"建模实现"，与本仓库的单实现原则冲突 |
| 用传播结果替代 FDTD 的强散射区 | 标量近似在金属/高对比结构内不成立 |
