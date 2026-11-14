# LD-004 FDTD R/T 归一化：监视器法线设反

**状态**：`resolved`

## 现象

`_scratch/fdtd_probe/RT_spectrum.csv` 的 21 个点全部异常：

| 波长 nm | T | R | A |
|---|---|---|---|
| 1200.00 | 0.559271 | **1.000000** | −0.559271 |
| 1358.49 | −0.716012 | **1.000000** | 0.716012 |
| 1384.62 | 2.768298 | **1.000000** | −2.768298 |
| 1800.00 | 1.257678 | **1.000000** | −0.242322 |

三个症状：R 恒等于 1、T 超出 [0,1]、A 出现负值。

## 根因

**监视器的 `monitor type` 设成了 `2D X-normal`**（法线沿 x），而传播轴是 y。
X-normal 的监视器在 y 方向横跨整个仿真区（含 PML），`src_mon` / `ref_mon` / `trn_mon`
三者覆盖同一片区域，读到完全相同的场：

```
src_mon  center@lam0 = 3.37453874e-10-7.91322265e-10j
ref_mon  center@lam0 = 3.37453874e-10-7.91322265e-10j   ← 逐位相同
```

于是 `R = P_ref / P_src ≡ 1`，而 T 变成无意义的商。

**次要根因（同轮一并修复）**：`ref_mon` 距源只有 0.05 µm，落进源的近场，
即使方向正确，真空下 R 也会读成 0.50（应为 0）。

## 修复

1. `setnamed(mon, "monitor type", "2D Y-normal")` —— 法线沿传播轴。
2. `ref_mon` 移到 y=0.30 µm（距源 0.15 µm）。
3. 归一化**不需要** analysis group：裸 `addpower` 在 Y-normal 下自带归一化的 `"T"` 结果。
4. 符号：`T = -T[trn]`、`R = 1 + T[ref]`（光沿 −y，法线 +y）。

修复后模板：`_scratch/fdtd_template.py`（含七个坑的注释）。

## 验证

```powershell
& 'C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe' `
  F:\Lumercial_WS\LC_EE_ws\_scratch\fdtd_proof.py
```

五个算例全部符合预期（exit 0）：

| 算例 | T | R | 判定 |
|---|---|---|---|
| main（Si 砖 + SiO₂） | [0.0049, 0.9672] | [0.0332, 0.9969] | T+R∈[0.9982, 1.0019] ✅ |
| vacuum（无结构） | 1.0000 | −0.0000 | 正对照 ✅ |
| **xnormal（复现 bug）** | [−0.0000, 0.0000] | **1.0000** | 负对照：复现原症状 ✅ |
| nearsrc（ref 贴源） | [0.8970, 0.9994] | [0.4361, 0.5554] | 负对照：R 被污染 ✅ |
| metal（金背板） | [0.0000, 0.0001] | 中位数 0.974 | 负对照：不透明 ✅ |

## 影响面

- LC_EE_ws 的 `fdtd_proof.py`、`fdtd_probe/*.fsp`
- 任何照抄"2D X-normal"的 2D 模型
- FDTD_WS 不受影响：`fsp_build.py` 按传播轴拼 `2D %s-normal`，本来就对

