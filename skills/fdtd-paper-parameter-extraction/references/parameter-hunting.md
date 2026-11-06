# Where FDTD parameters hide in a paper

A paper never presents its simulation inputs in one place. They are scattered across the caption,
Methods, a parameter table, and the supplementary information — and the fastest path is to hunt in a
fixed order rather than read top to bottom.

## The hunting order

1. **Figure caption of the target panel.** Geometry almost always lives here: period, feature sizes,
   layer thicknesses, sometimes the material model. This is the highest-density block in the paper.
2. **The sentence introducing the figure.** Often carries the one number the caption omits
   ("optimized for a 6 µm resonance", "the spacer was swept from 50 to 250 nm").
3. **Methods / Experimental section.** Material models, deposition thicknesses, measurement angles.
   Note that **fabrication thicknesses and simulated thicknesses sometimes differ** — record both.
4. **A parameter table**, if one exists. Check it against the caption; when they disagree, the caption
   is usually the simulated value and the table the fabricated one.
5. **Supplementary information.** Sweep ranges, optimisation history, the value the authors *chose*
   versus the value they *report*. This is where "we swept the spacer and picked 185 nm" hides.
6. **References for material data.** "Au was modelled by a Drude model [27]" — you need [27] to know
   whether the quoted ωp is in rad/s or Hz.

## The checklist

Copy this into the spec as you go. Anything you cannot fill goes into `missing`, not into a guess.

### Geometry
- [ ] lattice type and period (one number for square, two for rectangular)
- [ ] every feature dimension, **and which surface it is measured from**
- [ ] layer thicknesses in stack order, top to bottom
- [ ] rotation angle and rotation axis, if any
- [ ] supercell composition (how many distinct elements per period)

### Materials
- [ ] metal model: Drude / Lorentz / tabulated, with **units**
- [ ] dielectric: constant `n`, constant `ε`, or dispersive table; loss tangent vs `k`
- [ ] substrate: material and thickness
- [ ] adhesion layers (Ti, Cr) — papers often mention them only in the figure caption

### Simulation
- [ ] dimension (2D vs 3D) — a 2D paper cannot be compared with a 3D model
- [ ] boundary conditions (if unstated, assume periodic for an array and say so in `assumptions`)
- [ ] incidence angle and polarization
- [ ] wavelength range of the reported spectrum
- [ ] what exactly is plotted: simulated, measured, or both

### Targets
- [ ] the headline number and the wavelength where it occurs
- [ ] a secondary number (FWHM, bandwidth, efficiency) — one number is too easy to hit by accident

## Unit traps, in the order they bite

| Paper writes | You must write | Failure if wrong |
|---|---|---|
| ωp = 2π × 2175 THz | `1.3666e16` rad/s | metal 40× too reflective, absorption collapses |
| ωp = 6.5 eV | `6.5 × 1.519e15` rad/s | same |
| t = 185 nm | `1.85e-7` m | a 185 m thick layer; the solver refuses or gives nonsense |
| ε = 2.28, tanδ = 0.04 | `n = 1.5105, k = 0.0302` | using ε''=0.04 directly halves the loss |
| "6 µm" in a figure axis | `6.0e-6` m | 6 m wavelength; no resonance anywhere |

**Sanity check before running**: convert every number back to the unit the paper used and compare
with the sentence you took it from. Ten seconds, catches most of these.

## Telling the material models apart

- "modelled as a Drude model with ωp = …, ωd = …" → `kind: drude`. Two numbers, analytic.
- "optical constants taken from Palik / Johnson & Christy" → `kind: sampled_nk`. A table, not a formula.
  Do **not** substitute a Drude fit for tabulated data or vice versa: on the same device this has been
  measured to move a polarisation-conversion ratio from 72% to 95%.
- "ε = 2.28 + 0.09i" → `kind: constant_eps`, then convert to `n, k`.
- "lossless dielectric with n = 1.45" → `kind: constant_nk` with `k = 0`. Write the `k = 0` explicitly;
  a forgotten imaginary part is invisible in the spec and fatal in the result.

## When a parameter is missing

Three options, in this order:

1. **Find it elsewhere in the paper** — SI, another figure, a cited reference.
2. **Show it does not matter.** Change it by ±50% and confirm the target metric moves less than the
   tolerance. Then record it in `assumptions` with the evidence. Example: substrate thickness behind a
   metallic ground plane.
3. **Put it in `missing` and ask.** Never silently pick the value that makes the curve match — that is
   fitting, and it destroys the diagnostic value of the reproduction.

## Cross-check the extracted numbers before building

Two independent reads of the same number:

- the caption's dimension vs the schematic's labels (a label may show the half-length)
- the simulated value vs the fabricated value (they legitimately differ; record both)
- the target wavelength vs the period (a period larger than the wavelength means grating orders are
  in play — check that the paper's claim is consistent with that)

If two sources disagree and you cannot resolve which is the simulated one, put both in `assumptions`
and flag it. A reproduction built on an unresolved ambiguity is not a reproduction.
