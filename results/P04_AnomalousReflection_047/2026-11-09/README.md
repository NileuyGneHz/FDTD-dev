# results/P04_AnomalousReflection_047/ — 复现数据与交付工程

**状态：已复现（Sun et al., Nano Lett. 2012, 12, 6223）。** 全部数据由本轮 GPU FDTD 7 轮实跑生成，
无解析式冒充。结论与验收见 `docs/P04_AnomalousReflection_047/repro_report.md`。

## 1. 工程文件

| 文件 | layoutmode | 说明 |
|---|---|---|
| `P04_AnomalousReflection_047_repro.fsp` | **0**（已求解） | 30.4 MB，`R` 监视器结果已内置，`getresult('R','E')` 可直接读 → `(5013,1,1,1,3)` |
| `P04_AnomalousReflection_047_buildonly.fsp` | 1 | 490 KB，含 `field` / `field_big` / `R` 三个监视器，`dt = 0.99`，打开后需自己 Run |
| `run_thi00_gpu/run_thi00_gpu_output.h5` | — | **已求解版的结果文件，不可删** |

> ⚠️ **`.fsp` 以相对 basename 引用结果文件**（`run_thi00_gpu/run_thi00_gpu_output.h5`）。
> 搬运时**必须把 `.fsp` 与 `run_thi00_gpu/` 目录一起搬**；单拷 `.fsp` 会出现
> `Can not find result 'E' in the result provider 'R'`——这不是文件坏了。

## 2. 数据文件

| 文件 | 内容 |
|---|---|
| `farfield_angle_850nm.png` / `_thi00.csv` / `_summary.json` | **课程口径**：`R` 监视器 Ey → `czt`，θr ∈ [35°, 89°]，300 点（等价 `draw_fig2c.lsf`）。峰 **45.114°**；Lumerical `czt` 与独立 Python DFT **零误差一致** |
| `farfield_fullangle_850nm.png` / `_thi00.csv` / `_summary.json` | **全角**：−89…89°，复场 DFT，0.025° 网格。峰 **45.07°**；镜面 0° 邻域仅 0.084% |
| `farfield_fullangle_all_incidences.png` / `.csv` | **五点入射角**合并曲线（θi = −20/−10/0/+10/+20°） |
| `incidence_scan_summary.json` | θr–θi 数值表 + 式(2) 对照 + 能量占比 |
| `efficiency_summary.json` | η = 77.4%，吸收 22.6%，R_flat = 0.978（平整 Au 参考标定） |
| `flat_reference_spectrum_thi00.csv` | 平整镜面参考（关掉 `structure group`）的角谱，峰在 **0.000°**，供效率标定审计 |
| `sw_field_ey_xz_theta_i_+20deg.png` / `.csv` / `sw_field_summary.json` | θi = +20° 的 x–z 场图（论文 Fig.3d）；束缚模 1/e 衰减 **411 nm**（理论 421 nm） |
| `logs/*_p0.log` | **7 份求解日志原文**（判据证据）。每份都应含 `Detected GPU 0`、`Using datatype: real32`、`Completed <n> iterations`、`Early termination … autoshutoff criteria are satisfied`，且 `diverging` 出现 0 次 |

## 3. 关键数字一览

| 量 | 本工程 | 论文 |
|---|---|---|
| 正入射异常反射角 θr | **45.07°**（全角）／45.11°（czt 课程口径） | 45.5°（理论 45.1°） |
| 相位梯度 ξ/k₀ | 0.7083 | 0.708 |
| 临界角 θic | 16.96° | ≈17° |
| θi = +20° | 远场峰消失（残余为 x-PML 侧壁伪影） | 峰消失 |
| 转换效率 η | 77.4%（吸收 22.6%） | >80%（吸收 ~20%） |
| 镜面级 | 0.084% | 被抑制 |
| 束缚表面波衰减长度 | 411 nm（kx = 1.05 k₀） | 论文给 kx ≈ 2π/811 nm⁻¹ |

## 4. 复算命令

```bash
cd F:/Lumercial_WS/FDTD_WS/_scratch/tmp_p04repro_run   # 本轮工作目录（已随会话清理）
"F:/Lumercial_WS/ANSYS Inc/v251/Lumerical/bin/fdtd-engine.exe" -gpu -t 8 <工程>.fsp
```

判据三条（缺一不可）：`_p0.log` 里有 `Detected GPU 0` + `Using datatype: real32`；
有 `Completed <n> iterations` 且 `Early termination … autoshutoff criteria are satisfied`
（**这句是正常收敛，不是发散**）；`lumapi` 回读 `layoutmode == 0`。
