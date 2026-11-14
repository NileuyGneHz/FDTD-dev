---
name: fdtd-lumerical-unitcell-simulation
description: Build, run and sweep a periodic unit-cell FDTD model in Ansys Lumerical from a JSON model spec (geometry objects plus material definitions), then export R/T/A spectra and diagnose why the result disagrees with the publication. Use when reproducing a metasurface or absorber unit cell (cross resonator, nano-brick, patch antenna, MIM stack), when a simulated reflection/absorption spectrum does not match the paper, when a geometry or material sweep is needed, or when a simulation returns non-physical values such as absorption above unity. Consumes the spec produced by fdtd-paper-parameter-extraction; supports box, polygon, cylinder, ellipse, sphere and ring objects, drude, constant_nk, constant_eps, builtin and sampled_nk materials, and both reflection-mode (absorber) and transmission-mode (dielectric metasurface) geometries.
agent_created: true
---

# Lumerical unit-cell simulation

## Where this sits in the pipeline

```
paper PDF  --[fdtd-paper-parameter-extraction]-->  spec_<id>.json  --[this skill]-->  R/T/A + report
```

The spec is the single source of truth for every dimension and material parameter. If a number is
wrong, it is wrong in the spec, not in this script. Do not hard-code geometry here — add an object
to the spec instead.

## When to use

Use this skill when the task is "make the unit cell in this paper and give me the spectrum". Typical
triggers:

- "reproduce Figure N of this paper" for a periodic metasurface / absorber / wave plate unit cell
- a simulated absorption or reflectance curve that is physically plausible but quantitatively off
- `A > 1`, negative `T`, or a reflectance that does not move when the geometry changes
- a parameter sweep over period, feature size, spacer thickness, or material

Do not use it for full devices (lenses, holograms) where the phase profile over many cells is the
object — that needs a supercell model, not a unit cell.

## CRITICAL — the four decisions that decide whether the answer is right

Everything else is mechanical. Get these four wrong and the spectrum still looks like a spectrum.

### 1. Boundary conditions

| x / y boundary | What it actually simulates | Use when |
|---|---|---|
| `Periodic` | the infinite array (the physical object in almost every metasurface paper) | **default** |
| `Bloch` | infinite array with a phase ramp — oblique incidence | non-normal incidence |
| `PML` | **one isolated element** in free space | a single scatterer, never a periodic array |

Measured on the P01 stack (2026-11-03): the identical geometry gave **A = 1.111** (non-physical) with
PML on x/y and **A = 0.808** with `Periodic`. A plane-wave source that spans exactly one period
diffracts into the lateral PML, and the reflected-power monitor then reads a negative flux. If you
see `A > 1`, check this first.

### 2. Materials — the argument is a model type, not a material name

```python
t = f.addmaterial("Plasma")            # not "Au", not "Drude"
f.setmaterial(t, "name", "Au_paper")
f.setmaterial("Au_paper", {"Plasma resonance": 1.3665928e16,   # rad/s = 2*pi*2175 THz
                           "Plasma collision": 4.0840704e13})  # rad/s = 2*pi*6.5 THz
```

Measured on v251: `"Plasma"`, `"Lorentz"`, `"(n,k) Material"`, `"Sampled data"` all work;
`"Drude"` and `"Dispersive"` fail with `Failed to create material of type ...`.

Built-in database materials are assigned to an object by name instead:
`f.setnamed("sub", "material", "Si (Silicon) - Palik")`.

`getindex(material, X)` takes **frequency in Hz** as a column matrix, never a wavelength.

### 3. Monitor placement

For a reflection measurement with the light coming from above:

```
        PML
   z_R  ─────  R monitor      (above the source: only the reflected wave crosses it)
   z_src ────  plane source, direction = "Backward"  (propagates toward −z)
        ...
     structure  (surface at z = 0)
   z_T  ─────  T monitor      (below the ground plane)
        PML
```

- Put `R` **above** the source, not between the source and the structure. Between them the monitor
  sees incident plus reflected flux and the sign depends on the source convention.
- Keep every monitor at least ~0.3 µm away from the nearest PML face.
- For a design with a metallic ground plane, `T` must come out ≈ 0 — a value like `-1e-5` is
  numerical zero. If `T` is a few percent, the ground plane is too thin or too coarsely meshed.

**Transmission devices** (all-dielectric metasurface on glass) invert the geometry: the source sits
below the substrate, propagates `Forward`, and `T` is collected in air above. The `R` monitor then sits
*below the source*, so the reflected wave travels in −z and the monitor returns a **negative** power
value. Its magnitude is the reflectance — the builder negates it for you. Expect `R` of a few percent
and `T` near unity; an all-dielectric metasurface that reports `T = 0.1` is a geometry error, not a
lossy material.

### 4. Convergence — read the engine log, not the plot

Every run writes `<project>_p0.log` next to the `.fsp`. Two lines matter:

```
Starting 20985 total iterations
... Auto Shutoff: 8.80583e-05      <- last value in the file
```

- The run has **converged** only if the final `Auto Shutoff` is below your `auto shutoff min`.
- If the last value is ~1e-2 or larger, the run stopped at the iteration cap and the DFT spectrum is
  **not trustworthy** — no matter how smooth the curve looks.
- A periodic cell has no lateral loss channel, so the default run time (set by the source pulse) is
  often too short. Set `simulation time` explicitly and re-check the log.

⚠️ When grepping this value, include the exponent: `Auto Shutoff: [0-9.eE+-]+`. A pattern of
`[0-9.]+` truncates `8.80583e-05` to `8.80583` and turns a converged run into a suspicious one.

P01 ships **two** course projects. Do not merge them into a single "0.82"
(`defects/D-001`):

| project | x/y BC | iterations | final Auto Shutoff | threshold | verdict |
|---|---|---|---|---|---|
| `d2_perfectCross.fsp` | PML | 77,813 | `0.046734` | 1e-5 | ❌ hit the time cap, never converged, no stored spectrum |
| `infrared_perfect_absorber.fsp` | Periodic | 7,039 | `8.87508e-06` | 1e-5 | ✅ converged |

The converged course project stores `peak A = 0.8196 @ 6.152 µm`; our own converged build gives
`0.8083 @ 5.85 µm`. At 6 µm they agree to **0.0011**. So ~0.82 is the *stable Lumerical answer*
for this parameter set, not an artefact of an unfinished run. Before citing any reference
project, run `fdtd-lumerical-fsp-introspection` and state which project and which run the number
came from.

## Workflow

> **Before step 1:** if the package ships a reference `.fsp`, calibrate first — run
> `fdtd-lumerical-fsp-introspection` to read its layer positions, BCs, mesh, source and stored
> spectrum, and confirm convergence from `_p0.log`. P01's two course projects were conflated
> precisely because this step was skipped (`defects/D-001`).

1. **Extract the paper's numbers first.** Geometry, layer thicknesses, and the *stated* material
   model with units. A parameter you cannot find is a red flag — mark it, do not invent it.
2. **Write the parameter block into a config JSON** (`cases/P0N_.../config/spec_<id>.json`
   or `projects/R0N_.../config/`).
3. **Dry-run** to confirm the plan: `--dry-run` prints the points without opening a simulation.
4. **Build + run** with `scripts/run_fdtd_sweep.py` (below). It saves the `.fsp` before running so
   the engine log exists.
5. **Audit convergence** from `_p0.log` before believing any number (§4 above).
6. **Refine the mesh once** and confirm the answer moves less than the disagreement with the paper.
   If it does, the mesh is finished; stop refining.
7. **Sweep the one knob that controls the resonance** (spacer thickness, feature length, period) to
   see whether the paper's number is reachable at all with this material set.
8. **Write the report** from `assets/report_template.md`, into the package's `results/`
   (regression output belongs in `_scratch/regress/`, never back into read-only `cases/`).

## Script: `scripts/run_fdtd_sweep.py`

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
S="skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py"
"$PY" "$S" --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/regress/p01-20261107/baseline --dry-run
"$PY" "$S" --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/regress/p01-20261107/baseline
```

The flag is **`--spec`**, not `--config`. **Always pass `--out` explicitly**: the default output
directory is derived from the spec's location, so a spec inside read-only `cases/` silently
writes into `cases/.../config/P01_out/` (`defects/D-002`). Regression output goes to
`_scratch/regress/`.

- Builds the whole stack from parameters — no template `.fsp` required, nothing hidden.
- Emits one CSV per sweep point (`lam_um,R,T,A`) plus `summary.csv`
  (`peak_A, peak_lam_um, R_at_peak, T_at_peak, fwhm_um`).
- `structure` keys: `a` period, `l` / `w` feature, `tm` metal thickness, `ts` spacer, `t_sub` substrate.
- `simulation` keys: `bc_xy`, `mesh_accuracy`, `mesh_override`, `lam_lo`/`lam_hi`/`npts`,
  `air_above`, `z_below_ground`, `auto_shutoff`, `simulation_time`.
- Read the module docstring before editing: the geometry convention (surface at z = 0) is written
  down there and the monitor placement derives from it.

## Troubleshooting

| Symptom | Most likely cause | Check |
|---|---|---|
| `A > 1`, negative `R` | PML on x/y with a finite-width plane source | set `bc_xy = Periodic` |
| `T` is a few % instead of ~0 | ground plane too thin, or `dz` too coarse through it | metal ≥ 4 skin depths; `dz` ≤ 20 nm |
| peak at the wrong wavelength, shape right | geometry or material differs from the paper | re-read the caption's parameter list |
| peak amplitude too low, shape right | under-coupled: loss too low, or spacer off-resonance | sweep `ts`; re-check the loss tangent |
| spectrum unchanged when geometry changes | monitors outside the region, or results read from a stale run | confirm monitors are inside; re-run |
| answer moves every time you change the mesh | mesh not converged | refine until Δ < 1% between levels |
| last `Auto Shutoff` ≈ 1e-2 | run hit the iteration cap | raise `simulation_time` |
| `n, k` absurd (e.g. 5.99 for TiO₂) | `getindex` called with a wavelength | pass frequency in Hz |

## Examples — P01, Liu et al., PRL 104, 207403 (2010)

Paper: cross resonator / Al₂O₃ 185 nm / Au ground plane; `a=2.0, l=1.7, w=0.4 µm`, metal 0.1 µm;
reported **97% absorption at 6.0 µm**.

**Step 1 — is the numerics converged?**

| Configuration | peak A | peak λ | Converged? |
|---|---|---|---|
| Periodic, mesh acc 4 + override 30/20 nm | **0.808** | 5.85 µm | ✅ `8.8e-5` |
| Periodic, mesh acc 6 + override 15/10 nm | **0.801** | 5.75 µm | ✅ |
| PML on x/y (same everything else) | 1.111 | 8.50 µm | non-physical |
| Course `d2_perfectCross.fsp` (PML, acc 8) | — | — | ❌ never converged (`0.046734`), no stored spectrum |
| Course `infrared_perfect_absorber.fsp` (Periodic, acc 8) | **0.8196** | 6.15 µm | ✅ `8.875e-6` |
| Rebuild using that course project's settings | **0.8177** | 6.15 µm | ✅ `9.53e-6` |

The two converged builds agree to 0.007, so the mesh is finished and ~0.81 is what this parameter
set gives in Lumerical. The course project and the rebuild made from its own settings agree to
**0.0018 at the same peak wavelength**, so the reverse-engineered settings are correct too.
Refining the mesh further cannot close the gap to the paper's 0.97.

**Step 2 — is the paper's number reachable at all?** Sweep the one knob that sets the resonance
condition, the spacer thickness:

| `ts` | 120 nm | 150 nm | **185 nm (paper)** | 220 nm | 250 nm |
|---|---|---|---|---|---|
| peak A | **0.962** | 0.913 | **0.808** | 0.716 | 0.673 |
| peak λ | 5.85 | 5.90 | 5.85 | 5.90 | 6.05 |

**Reading — corrected 2026-11-07 (`defects/D-001`).** The "spacer thickness is measured from a
different surface" hypothesis is **falsified**. Reverse-engineering both course `.fsp` projects
shows Al₂O₃ at `[-185, 0] nm`, ground plane `[-285, -185] nm`, cross `[0, 100] nm` — exactly the
layer positions in our spec. `185 nm` is ground-plane-top → cross-bottom. `getindex` also
reproduces the paper's Drude `(n,k)` to the last digit at 4 / 6 / 8 / 10 µm, so the material
implementation is not the culprit either.

What differs is the **numerical setup**, not the geometry: the course project uses mesh accuracy 8,
a 24 nm override, shutoff 1e-5, 1 ps, and 3.5–11 µm / 100 points. Rebuilding with those settings
reproduces its stored spectrum to 0.0018 (`0.8177` vs `0.8196`, both at 6.152 µm), and all three
independent runs agree at 6 µm to within 0.0027.

The paper's 0.97 comes from **CST Microwave Studio 2009** (the experimental value is also 97%),
not from Lumerical. Report ~0.82 as the Lumerical result and state the solver gap explicitly.

**What not to do**: do not retune `l`, `w`, `a` and `ts` together until the peak reads 0.97 at
6.0 µm — and do not move `ts` to 120 nm just because that produces 0.962. Fitting parameters to
one number yields a model that reproduces one figure and predicts nothing. Change one knob,
state the offset, and say what it means.

## 边界：本技能只出功率，相位交给下一个技能

The builder reports **power only** (`R`, `T`, `A`). For a wave-plate or any phase-engineered device,
transmission alone is not the result — a half-wave plate additionally needs `φx − φy = π`, and a
device can show `T ≈ 1` on both axes while having the wrong phase difference entirely.

**Phase retrieval is implemented — use `fdtd-lumerical-phase-retrieval`** (stage 4,
`fdtd-lumerical-phase-retrieval/scripts/run_phase_sweep.py`), which consumes this skill's spec and
writes `phase.csv` / `dphi_deg`.
Do not re-implement it here, and do not claim a phase figure was reproduced after running only
this builder.

Method that skill uses (for orientation only):

1. Add one E-field monitor (`addprofile`) on the same plane as `T`, covering the same spectral range.
2. Run each polarization separately (the spec already supports sweeping `polarization_deg`).
3. Take `arg(E_x) − arg(E_y)` **at the same plane**: the common propagation phase cancels, so no
   bare-substrate reference run is required.
4. Report the difference modulo 2π and state the convention.

Measured reference point (P02, 2026-11-04): `T(1.56 µm) = 0.959 / 0.980` for the two axes.

## References（load on demand）

- Load `references/lumerical_api_ref.md` **whenever you write or patch `lumapi` code** — it holds the
  measured v251 property names, material model types, result layouts and the API traps.
- Load `assets/report_template.md` **when writing the reproduction report** — one page, with the
  deviation-diagnosis table.

- `scripts/run_fdtd_sweep.py` — the builder/sweeper used above.
- `references/lumerical_api_ref.md` — measured v251 property names, material models, result layouts,
  and API traps. Load it when writing or patching any `lumapi` code.
- `assets/report_template.md` — one-page reproduction report with a deviation-diagnosis table.
