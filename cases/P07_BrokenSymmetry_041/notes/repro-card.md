# P07 复现卡（2026-11-08）

> 结构化索引；长表格、几何核对与排除推理在同目录 `repro-2026-11-08-p07.md`。
> 一句话结论：**平台电平复现，两个 Fano 谷没复现**；本包没有一个「既有破缺对称几何、又有可信谱」的参考工程。

```repro-card
{
  "case": "P07",
  "mode": "reproduce",
  "date": "2026-11-08",
  "target": {
    "quantity": "peak_reflectance",
    "value": 0.95,
    "wavelength_um": 1.0,
    "source": "Fig. S7(a) plateau R~0.95 over 900-955 nm; the two Fano dips (R~0.47 @ ~965 nm, R~0.20 @ ~1057 nm) are the real acceptance test",
    "definition": "R = 反射功率监视器（2D Z-normal 面）通量积分 / 源功率，正入射、无偏振旋转；判据取 900-955 nm 平台（不是单点 R(1.0 um)），两个 Fano 谷的位置与深度另记",
    "solver": "FDTD Solutions (Lumerical)",
    "unmeasured_reason": null,
    "measured_columns": ["R"]
  },
  "actual_solver": "Lumerical FDTD v251",
  "locked": ["materials", "layer_stack", "topology", "geometry"],
  "numerics_aligned_from": "cases/P07_BrokenSymmetry_041/model/first_model_mesh_refined.fsp",
  "truth_sources": [
    {
      "path": "model/first_model_mesh_refined.fsp",
      "role": "reference",
      "converged": true,
      "shutoff": 9.80606e-06,
      "threshold": 1e-05,
      "p0_log": "model/first_model_mesh_refined_p0.log",
      "note": "acc 6, Periodic/Periodic/PML, 0.9-1.1 um. Geometry is TWO IDENTICAL 360x140x250 nm boxes = a plain bar, NOT the paper's L. Stored peak R 0.9721 @ 1025.6 nm."
    },
    {
      "path": "model/first_model_minimal.fsp",
      "role": "reference",
      "converged": true,
      "shutoff": 9.53498e-06,
      "threshold": 1e-05,
      "p0_log": "",
      "note": "acc 2, same (bar) geometry. Stored peak R 0.9687 @ 1029.6 nm. No _p0.log archived in the package; convergence taken from the log tail captured at archive time, so treat as WARN."
    },
    {
      "path": "model/initial_trial.fsp",
      "role": "counterexample",
      "converged": true,
      "shutoff": 9.53498e-06,
      "threshold": 1e-05,
      "p0_log": "model/initial_trial_p0.log",
      "note": "This is the ONLY project with the paper's broken-symmetry L (360x140 + 80x140, bbox 360x280), but source band 0.4-0.7 um / 5 points and x/y BC = PML, so its stored R (peak 0.0074) is meaningless. Not usable as a golden reference."
    }
  ],
  "runs": [
    {
      "name": "run_bar_cheap",
      "out": "_scratch/regress/2026-11-08/P07/run_bar_cheap",
      "p0_log": "_scratch/regress/2026-11-08/P07/run_bar_cheap/point_00_base_p0.log",
      "shutoff_final": 0.00215542,
      "threshold": 1e-05,
      "converged": false,
      "metrics": {"R": 1.0018, "peak_R_lambda_um": 1.017, "R_at_1.00um": 0.965}
    },
    {
      "name": "run_L_cheap",
      "out": "_scratch/regress/2026-11-08/P07/run_L_cheap",
      "p0_log": "_scratch/regress/2026-11-08/P07/run_L_cheap/point_00_base_p0.log",
      "shutoff_final": 0.00409133,
      "threshold": 1e-05,
      "converged": false,
      "metrics": {"R": 1.0952, "peak_R_lambda_um": 0.907, "R_at_1.00um": 0.886}
    },
    {
      "name": "run_L_run2_acc5",
      "out": "_scratch/regress/2026-11-08/P07/run_L_run2",
      "p0_log": "_scratch/regress/2026-11-08/P07/run_L_run2/point_00_base_p0.log",
      "shutoff_final": 0.00260983,
      "threshold": 1e-05,
      "converged": false,
      "metrics": {"R": 1.016, "peak_R_lambda_um": 1.084, "R_at_1.00um": 0.889}
    }
  ],
  "same_input_regression": {
    "baseline": 0.9721,
    "repeat": 0.9687,
    "delta": 0.0034,
    "tolerance": 0.005,
    "source": "the package's two engine runs of the SAME (bar) model at acc 6 vs acc 2; no repeat of our own spec was affordable because the host was 5-6x oversubscribed by parallel agents"
  },
  "excluded": [
    {
      "suspect": "mesh / numerics",
      "verdict": "excluded as the cause of the missing Fano dips: acc 6 and acc 2 give the same stored answer (0.9721 vs 0.9687, delta 0.0034)",
      "evidence": "_scratch/regress/2026-11-08/P07/inspect/spectra.json + compare.csv",
      "rerun": "python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config _scratch/regress/2026-11-08/P07/inspect_config_struct.json --out _scratch/regress/2026-11-08/P07/inspect_struct"
    },
    {
      "suspect": "boundary conditions of the reference projects",
      "verdict": "excluded: Periodic/Periodic/PML in both, and the pad is 550 nm with a 550 nm plane wave - the correct periodic configuration",
      "evidence": "_scratch/regress/2026-11-08/P07/inspect_struct/manifest.json (FDTD x/y/z bc)",
      "rerun": "same introspection command as above"
    },
    {
      "suspect": "the notch (broken symmetry) is missing in the course projects",
      "verdict": "CONFIRMED as the cause of the flat spectrum: in first_model_mesh_refined/minimal the two 'rectangle' objects are field-by-field identical (360x140x250 nm at the same centre), i.e. a plain bar; initial_trial.fsp is the only project holding the paper's L (360x140 + 80x140)",
      "evidence": "_scratch/regress/2026-11-08/P07/inspect_struct/manifest.json (same rect props? True) + inspect_trial/manifest.json (Silicon_1 360x140, Silicon_2 80x140 at x=-140 nm)",
      "rerun": "python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config _scratch/regress/2026-11-08/P07/inspect_config_trial.json --out _scratch/regress/2026-11-08/P07/inspect_trial"
    },
    {
      "suspect": "monitor placed inside the PML (run1)",
      "verdict": "confirmed for run1: below_structure 0.15 um put the T monitor inside the PML, T went to -0.80 and A to 1.60; fixed in run2 (below_structure 1 um), A max falls to 0.478",
      "evidence": "run_bar_cheap/point_00_base.csv (T min -0.796), run_L_run2/point_00_base.csv (T min -0.218)",
      "rerun": "python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec _scratch/regress/2026-11-08/P07/spec_p07_paper_L_run2.json --out _scratch/regress/2026-11-08/P07/run_L_run2"
    },
    {
      "suspect": "substrate BaF2 (n=1.469) vs the paper's SOI / buried oxide",
      "verdict": "NOT EXCLUDED - no SOI-stack run was made; the 50-60 nm offset between our dips and Fig. S7(a) cannot be attributed",
      "evidence": "notes/repro-2026-11-08-p07.md section 5.4",
      "rerun": "none yet"
    }
  ],
  "verdict": {
    "status": "inconclusive",
    "gap": 0.05,
    "explainable_by": null,
    "stop_reason": "Plateau level reproduced (R 0.86-0.95 across 900-1100 nm, same as the two converged course projects), but the paper's two narrow Fano dips (0.47 @ ~965 nm, 0.20 @ ~1057 nm) do not appear: our L builds give 0.868 @ 965 and 0.890 @ 1057 with only broad undulations. All three of our runs hit the 1 ps cap (final Auto Shutoff 2.2e-3 / 4.1e-3 / 2.6e-3 against a 1e-5 threshold), so no spectrum here is quotable; and the package's only broken-symmetry project (initial_trial.fsp) has a source band of 0.4-0.7 um, so there is no converged golden reference for the L at all. Stopped because the host was running 40-48 fdtd-engine processes for 5-6 parallel agents (engine self-reported 0.378 Mnodes/s vs 154 in the reference log), which made a converged acc-6 run a multi-hour job."
  },
  "defects": [],
  "training_items": [
    {
      "id": "R-021",
      "observation": "Naming a package project 'refined'/'minimal' says nothing about its geometry: in P07 both are a plain bar because the second box was duplicated and never moved, while the only correct broken-symmetry L sits in the least official-looking file (initial_trial.fsp). Always diff object properties between projects before choosing a golden reference.",
      "evidence": "_scratch/regress/2026-11-08/P07/inspect_struct/manifest.json vs inspect_trial/manifest.json",
      "destination": "defects",
      "landed": false,
      "target_path": null
    },
    {
      "id": "R-022",
      "observation": "A monitor placed less than ~0.3 um above the PML face reports R>1 and T<0, which silently turns A = 1-R-T into a number above unity (measured: A = 1.5956). Check the sign of T before believing any A.",
      "evidence": "_scratch/regress/2026-11-08/P07/run_bar_cheap/point_00_base.csv",
      "destination": "references",
      "landed": false,
      "target_path": null
    },
    {
      "id": "R-023",
      "observation": "For a dielectric reflector the model-spec schema offers quantity 'peak_reflectance', run_fdtd_sweep.metrics() only reports A (reflection) / T (transmission), and check_reproduction.QUANTITY_ALIASES knows neither reflectance nor fwhm - the chain has no working path for a reflectivity target.",
      "evidence": "skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py:metrics(); tools/check_reproduction.py:QUANTITY_ALIASES",
      "destination": "scripts",
      "landed": false,
      "target_path": null
    }
  ],
  "rerun_commands": [
    "python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config _scratch/regress/2026-11-08/P07/inspect_config_struct.json --out _scratch/regress/2026-11-08/P07/inspect_struct",
    "python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py --spec _scratch/regress/2026-11-08/P07/spec_p07_paper_L_run2.json --out _scratch/regress/2026-11-08/P07/run_L_run2",
    "python _scratch/regress/2026-11-08/P07/compare_p07.py"
  ]
}
```
