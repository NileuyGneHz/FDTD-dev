# EXP-48 — `sampled data` 材质改喂复介电常数

## 假设

D-013：v251 的 `Sampled data` 材质 `sampled data` 属性收**复介电常数 ε(f)**，
而 builder 两个分支都喂 `n + ik`。改喂 `ε = (n+ik)²` 后，引擎 `getindex`
反查应与解析 (n,k) 一致；石墨烯的 ε 应回到 ~2611i 而不是 51i。

## 输入

- `_shared/fsp_build.py` 的 `sampled_nk` / `graphene_kubo_1nm` 两个分支
- 判据点：3.6 / 5.0 / 8.0 THz

## 方法

1. 建两个探针材质：`probe_nk`（常数 n=2,k=0.1）、`probe_gra`（Kubo μc=0.1 eV）。
2. 用 `getindex(name, f_Hz)` 反查（**入参是频率 Hz，不是波长**）。
3. 与 `graphene_nk()` 的解析值逐点比。
4. 修好后重建 P09 的 2D 模型并跑一次（15 s），看第一模是否回到 3.6 THz。

## 判据

| 指标 | 期望 |
|---|---|
| `probe_nk` @5 THz | `n=2.0, k=0.1`（±1%） |
| `probe_gra` @3.6 THz | `k≈51.1`（±5%），`n≈0` |
| P09 2D 模型 @3.6 THz | `A` 从 0.010 升到 >0.9，峰位落回 3.5–3.7 THz |

## 负对照

- 做法：**故意**仍喂 `n+ik`（旧代码路径），在同一判据点上反查。
- 预期：`k` 读出 ≈ √51.1 ≈ 7.1 量级、与解析差一个开方关系 → 判据必须判 fail。
- 若旧路径也「通过」，说明判据不区分语义，等于没测。

## 可重跑命令

```bash
python _scratch/regress/2026-11-10/EXP-48/probe_epsilon.py
```
