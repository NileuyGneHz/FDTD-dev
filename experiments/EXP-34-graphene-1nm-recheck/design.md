# EXP-34 — 石墨烯 1 nm box 复核 P09

## 状态
**已执行**（2026-11-10，EXP-46 + EXP-48 解锁后）——判据未达成，按计划停止条件回报

## 输入

- `_scratch/regress/2026-11-10/EXP-46/p09_2d_spec.json`（2D，x=周期，y=传播，石墨烯 1 nm box）
- 基准：`cases/P09_GrapheneAbsorber_044/model/graphene_perfect_absorber.fsp` 的存谱
  （手建，石墨烯用 `Sampled 2D data` 表面电导率）

## 方法

同一几何、同一网格（acc 2）下，只换石墨烯表示：1 nm box vs 2D 面电导率。
跑完取 R/T，A = 1 − R − T，比峰位与峰值。

## 判据

计划批次 3：`Δpeak ≤ 10 GHz 且 ΔA ≤ 0.01 → 可用；否则写明差多少`。

## 实测

| 组 | 石墨烯 | 网格 | A@3.6 THz | 峰位 | 峰值 A | 耗时 |
|---|---|---|---|---|---|---|
| 基准（sheet） | `Sampled 2D data` σ | acc 2 | ≈1.00 | 3.511 THz | 0.99998 | 已存谱 |
| box，**材料错**（D-013 未修） | `Sampled data` 灌 n+ik | acc 2 | 0.034 | 7.120 THz | 0.359 | 15 s |
| box，材料对 | `Sampled data` 灌 ε | acc 2 | **0.009** | 7.100 THz | 0.051 | 13 s |
| box，材料对 + dy=0.1 nm | 同上 | override | 0.010 | 7.594 THz | 0.059 | 20 min（材料仍是错的，见下） |
| box，材料对 + dy=1 nm | 同上 | override | 未完成 | — | — | 49 min 到 **0.68%**，引擎自报 ETA **110 h** |

`Δpeak = 3588 GHz`、`ΔA = 0.951` → **判据不达成**。

两条订正必须一起读：

1. 第二行 box 用的是**未修 D-013** 的材料（n+ik 被引擎当成 ε 再开方），所以 0.034 不是
   「1 nm box 的真实能力」，而是「材料口径错 + 网格不足」的叠加。
2. 修了 D-013 之后（ε 正确，`getindex` 反查 k=51.096 与解析一致），粗网格下 A 反而
   降到 0.009 —— 因为 1 nm 层在 ~200 nm 的网格里被摊薄，等效 σ 只剩 ~1/200。
   这不是材料问题，是离散化问题。

## 负对照

- 做法：把同一条判据套在**修前**（材料错）的工程上。
- 预期：也判 fail（A=0.034、峰 7.12 THz）。
- 实测：fail。说明这条判据能同时抓住「材料口径错」与「离散化不足」两类问题，
  不是只在一种情形下亮红。
- 负对照是否按预期失败：是

## 结论（按计划停止条件：差 > 0.01 → 停并回报，不自行维持 D-2）

**1 nm box 在本项目的 2D 胞里不是面电导率的等价替代**：
- 不解析 1 nm → 层被摊薄，A 掉两个数量级；
- 解析 1 nm（dy ≤ 1 nm）→ 网格 8002×240、dt 被最小格距锁死，本机单线程 ETA 110 h。

两条路都不可用。**D-2（石墨烯一律 1 nm box）需要人重新裁决**，可选：
(a) 回到 `Sampled 2D data` 表面电导率（P09 手建模型已验证能给出 A=1 @3.511 THz）；
(b) 保留 1 nm box 但只在有 GPU/多进程且能接受几十小时机时的场景用；
(c) 用 2D 材料表 + 面对象，但要在 spec 里承认它是「面」而不是「1 nm 厚」。

本轮不替人做这个决定，也不为了让数字好看去调 `d` 或 `W`。

## 可重跑命令

```bash
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py --spec _scratch/regress/2026-11-10/EXP-46/p09_2d_spec.json --out _scratch/regress/2026-11-10/EXP-34/build2 --tag p09_2d_fixed --check
P09_FSP=_scratch/regress/2026-11-10/EXP-34/build2/p09_2d_fixed.fsp python _scratch/regress/2026-11-10/EXP-34/run_p09_2d.py
```
