# D-013：`sampled data` 材质收的是复介电常数，builder 灌的是 (n,k)

**状态**：`resolved`（2026-11-10，EXP-48）——在写缺陷之前已实测确认，见下

## 现象

`build_materials` 的两个分支（`sampled_nk`、`graphene_kubo_1nm`）都执行
`np.column_stack([freq, n + 1j*k])`。用 P09 的 1 nm 石墨烯实测：

| 量 | 解析值（`graphene_nk`） | 引擎 `getindex` 读回 |
|---|---|---|
| n @3.6 THz | 1.83e-35 | 5.05 |
| k @3.6 THz | 51.10 | 5.05 |

`(5.05+5.05i)² = 51i`，而解析的 ε 就是 `1 + iσ/(ε0ωΔ) ≈ 2611i`。
也就是说引擎把喂进去的 `n+ik` **当成 ε 用了**。

## 判定（两次对照，不是推断）

1. `(n,k) Material` 常数材料设 `n=2, k=0` → `getindex` 返回 **2.0**。所以
   `getindex` 返回的是 n，不是 ε。
2. `Sampled data` 灌 `4 + 0i` → `getindex` 返回 **2.0** = √4。若按 (n,k) 解释应为 4。

结论：v251 的 `Sampled data` 材质，`sampled data` 属性收的是 **复介电常数 ε(f)**；
GUI 里的「导入 n,k」是界面替你换算的，LSF 属性不换算。

## 影响面

- `graphene_kubo_1nm`：石墨烯的有效 ε 被开方 → 吸收弱 51 倍。P09 的 1 nm box 模型
  因此完全没有第一模（A 在 3.6 THz 只有 0.010，峰跑到 7.59 THz）。
- `sampled_nk`：任何用它的 spec 色散都错。当前仓库里只有
  `_scratch/p09-20261108/config/spec_p09.json`（3D 旧版，未用于最终结论）在用。
- 生产 case（P01/P02/P05/P06/P07）用的是 `builtin` / `drude` / `conductive_3d` /
  `constant_nk`，**不受影响**。

## 为什么 EXP-41 没抓到

EXP-41 的判据是「读回 `type = Sampled 3D data`、`sampled data` 形状 `(points, 2)`」，
即**形状与类型**。这次的问题在**数值语义**上：`setnamed` 成功、`getnamed` 形状一致，
但物理量完全不同。这是「假轮次」的第三种形态——不是参数不在因果链上，而是
**参数的物理含义被换了单位**。判据必须包含「用 engine 的 `getindex` 反查一个已知点」。

## 修复

见 `experiments/EXP-48-sampled-data-is-epsilon/`。
