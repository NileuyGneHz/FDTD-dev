# case-01 — build a unit cell from a spec and report the spectrum

**Tests**: the happy path. Turns a validated spec into a converged run and a comparable summary.
**Expected duration**: 1–3 minutes on GPU.

## Prompt

> 用 `packages\P01_Absorber_042\scripts\spec_p01.json` 跑一次，
> 告诉我峰值吸收、峰值波长和 FWHM。

## Expected actions

1. Run `validate_spec.py --strict` on the spec. If it fails, stop and report — do not run.
2. `--dry-run` to confirm the point list and output directory.
3. Run `run_fdtd_sweep.py --spec ... --out ...`.
4. **Read `<project>_p0.log`** and confirm the final `Auto Shutoff` is below `auto_shutoff`
   (1e-4 here). Report the observed value.
5. Read `summary.csv` and answer with the three numbers.

## Pass criteria

| # | Check | Expected |
|---|---|---|
| 1 | Spec validated before running | yes |
| 2 | Convergence reported, not assumed | final `Auto Shutoff` stated and below threshold |
| 3 | peak A | 0.80 ± 0.02 (measured 0.8079) |
| 4 | peak wavelength | 5.85 ± 0.15 µm |
| 5 | FWHM | 0.80 ± 0.15 µm |
| 6 | Artifacts | `point_00_base.csv`, `summary.csv`, `.fsp` all present |

## Fail modes

- Answers with numbers but never mentions convergence → **fail**: the number is unverified.
- Reports A ≈ 0.97 because that is what the paper says → **fail**: quoted the target instead of the run.
- Skips validation "because the spec looks fine" → **fail**: that is the step this eval exists for.

## Notes for the grader

Exact values depend on GPU/driver but should be stable to ±0.01. A drift beyond 0.02 means the
mesh or geometry changed — investigate rather than re-baselining the eval.
