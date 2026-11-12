# TASK-002 P03 半波片复现（Fig.1b/1c + Fig.3b）

> 状态：done
> 负责人：agent
> 关联项目：R03_HWP_Ding2015
> 最后更新：2026-11-12

## 0. 一句话

用论文的 Au Drude + SiO₂ n=1.45 参数建 600 nm 单胞，CPU 跑 x 偏振反射，
从场监视器分离 R_co/R_cr/PCR，并由 `r_u=J_xx+J_yx`、`r_v=J_xx−J_yx` 得 u/v 相位差。

## 1. 完成定义（DoD）

- [x] spec 通过 `validate_spec.py --strict`
- [x] `.fsp` 通过 `build_fsp.py --check`（0 mismatch）
- [x] CPU 运行收敛（Auto Shutoff 8.82e-6 < 1e-5，无 diverging）
- [x] 交付 `p03_monitors.csv` / `pol0_fields.npz` / `fig_p03_monitors.png`
- [x] `repro_report.md` 写偏差诊断
- [x] journal 交接

## 2. 结果

| 量 | 结果 |
|---|---|
| R_co 均值 | 1.31%（max 3.05%） |
| R_cr 均值 | 90.31%（min 81.01%） |
| PCR 均值 / 最小 | 98.58% / 96.68% |
| PCR>95% 带宽 | 790–1660 nm（论文 805–1672 nm） |
| Δφ_uv 均值 | 181.7° ± 13.5°（cos −0.972） |
| 收敛 | 8.82e-6，Completed，无 diverging |

## 3. 产物

- `projects/R03_HWP_Ding2015/model/p03_hwp.fsp`
- `projects/R03_HWP_Ding2015/results/repro_p03/`
- `projects/R03_HWP_Ding2015/notes/physics_terms_and_formulas.md`

## 4. 边界

- 未做 Fig.2（斜入射）、Fig.4–6（超胞/场分布）。
- 20 nm 粗化对照失败（R_co max 56%、PCR min 30%）；5 nm 细化启动后 2% 主动终止，
  **未完成 5 nm 收敛证明**；10 nm 达到 auto-shutoff。
- Ti 粘附层未计入（Fig.1 未明说；Fig.2 才明确计入）。
