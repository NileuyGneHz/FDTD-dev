---
name: fdtd-lumerical-phase-retrieval
description: Extract the transmitted field phase of a periodic unit cell in Ansys Lumerical FDTD and compute the phase difference between two polarizations, as required for wave plates, polarization rotators and phase-gradient metasurfaces. Use when a figure plots transmission phase, when verifying that a half-wave plate really delivers a pi phase difference (transmission alone cannot show this), when a birefringent response must be quantified, or when a power-only reproduction has to be extended to a phase claim. Handles the field monitor, the zeroth-order plane average, and the two-polarization differential that cancels propagation phase.
agent_created: true
---

# Phase retrieval for a unit cell

Power and phase are different experiments. `fdtd-lumerical-unitcell-simulation` answers "how much light
gets through"; this skill answers "with what phase". A device can show `T ≈ 1` on both axes and have a
phase difference of zero — which is a transparent slab, not a half-wave plate. Never infer a phase
claim from a transmission curve.

## Prerequisite

The model must already be described by a validated spec (schema v1.0, produced by
`fdtd-paper-parameter-extraction`). This skill **imports the builder** from
`fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py` rather than duplicating it — one
implementation, one place to fix. Do not fork the builder.

## Method, and why each step is necessary

1. **2D DFT field monitor on the transmission plane.** `addprofile(name=...)` creates a `DFTMonitor`
   with `output Ex/Ey/Ez` already enabled. (`adddftmonitor()` returns `None` on v251 — do not use it.)
2. **Plane-average the co-polarised component.** At normal incidence every non-zero diffraction order
   is evanescent below the plane, so the spatial average over the period *is* the zeroth-order
   transmitted amplitude. Sampling a single point instead picks up near-field ripple from the pillar.
3. **Run once per polarization, then subtract.** `Δφ = arg(E_x) − arg(E_y)` at the *same plane*. Both
   runs share source, substrate and propagation distance, so the common phase cancels exactly —
   **no bare-substrate reference run is required.** This is the whole reason the method is cheap.
4. **Wrap to (−π, π].** Then state the convention. A jump of exactly 2π is an artefact of wrapping,
   not a physical feature.

## Workflow

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-phase-retrieval/scripts/run_phase_sweep.py \
      --spec cases/P0N_.../config/spec_<id>.json --pol 0 90 \
      --out cases/P0N_.../results/phase_<id>
```

Output `phase.csv`: `lam_um, phase_deg_<pol>..., dphi_deg, T_<pol>...`

Then check the three validity conditions below before writing any conclusion.

## CRITICAL — validity checks (all three, every time)

| # | Check | Fail looks like |
|---|---|---|
| 1 | `|E_zeroth|²` is consistent with the power monitor's `T` (same order of magnitude, same trend) | amplitude and T disagree → the monitor is not on the transmission plane, or the plane average is picking up a diffraction order |
| 2 | `T` from the two runs is comparable | one run is at a resonance minimum → the "phase difference" compares two different regimes and means nothing |
| 3 | Δφ is stable under mesh refinement | Δφ moves by more than ~0.1π when the mesh is refined → the phase is mesh-limited; phase converges slower than power |

A half-wave plate target is `Δφ ≈ 180°`; a quarter-wave plate `≈ 90°`. Report the mean over the
design band **and** the extremes, not a single wavelength.

## Troubleshooting — traps measured on this machine

- **`adddftmonitor()` returns `None`** and every subsequent `setnamed` fails with
  `Unsupported data type`. Use `addprofile(name=...)`.
- **`addprofile` creates a `DFTMonitor`**, not a separate type. Its results are `E` (shape
  `(nx, ny, 1, nfreq, 3)`) plus `lambda` and `f`. `getresult(m, "E")` returns a **list of dicts** —
  the same shape trap as the power monitors.
- **`getresult(m, "Ex")` also exists** and returns `(nx, ny, 1, nfreq)` if only one component is
  needed.
- **`f.close()` on an unsaved session pops a modal "save changes?" dialog** that hangs a headless run.
  Always `f.save(path)` before `close()`, with `path` inside `_scratch\` or the package's `results\`.
- **Absolute phase is meaningless without a reference**; only differences are physical. Do not report
  `phase_deg_0` as "the phase of the device" — it contains the source phase and the propagation to
  the monitor plane.

## Examples

**Half-wave plate check.** Spec `P02`, target `Δφ = 180°` at 1.55 µm.

1. `run_phase_sweep.py --pol 0 90` → `phase.csv`.
2. Confirm `|E_zeroth|²` tracks `T` from the same run (check 1), and `T` is comparable on both axes (check 2).
3. Report `dphi_deg = 178° ± 3°` over 1.50–1.60 µm. **Never** report `phase_deg_0` alone — it carries
   the source phase and the propagation to the monitor plane.

**Expected non-result.** `T = 0.96 / 0.95` but `dphi = 4°` → the two axes are in phase; this is a
transparent slab, not a wave plate. Stop and say so.

## References（load on demand）

- Load `references/phase-conventions.md` **before writing or defending any phase number** — sign
  conventions, wrapping, what π and π/2 mean physically, and how to report so someone can reproduce it.
- `scripts/run_phase_sweep.py` — the extractor; imports the builder from the unit-cell skill.
