# memory/materials.md

Material models that have been built and measured in this workspace. When a paper disagrees with a
simulation, the material model is the first thing to suspect — it has been the largest single error
source in every reproduction so far.

## Naming rule (learned the hard way, 2026-11-03)

**Never name a custom material `Au`, `Al2O3`, `Si`, `SiO2`, `TiO2`.** Those names exist in the built-in
database. Lumerical accepts the name in some calls and resolves to the *database* entry in others, so
the model silently uses the wrong optical constants. Suffix custom materials: `Au_paper`,
`Al2O3_paper`, `SiO2_paper`.

## Gold

Two legitimate ways, and they are **not interchangeable**:

| Route | How | When |
|---|---|---|
| analytic Drude | `addmaterial("Plasma")`, set `Plasma resonance` = ωp, `Plasma collision` = ωc, both in **rad/s** | the paper states ωp/ωc |
| tabulated | `addmaterial("Sampled data")`, feed `[freq_Hz, complex ε]` | the paper cites Palik / Johnson–Christy |

Measured case (P03, Ding 2015 half-wave plate): same geometry, Palik instead of the paper's Drude →
polarisation conversion ratio **72%** instead of **95%**. The material model, not the mesh, was the
whole gap.

Drude values in use:

| Device | ωp | ωc | Source |
|---|---|---|---|
| P01 IR absorber | 2π × 2175 THz = 1.3666e16 rad/s | 2π × 6.5 THz = 4.0841e13 rad/s | Liu 2010, Methods (cites Ordal) |
| P03 half-wave plate | 1.37e16 rad/s | 1.224e14 rad/s | Ding 2015, Methods |

Sanity check after building: `getindex("Au_paper", [[c/6e-6]])` gives `n ≈ 2.8 + 43i`. The imaginary
part is what governs absorption and matches a hand calculation to ~0.3%; the real part is
ill-conditioned (ε is large and negative, so a 0.5% change in ε′ moves n′ tenfold). **Do not rescale
ωp to "fix" n′** — it wrecks the absorption.

## Alumina (Al₂O₃)

Papers usually state `ε = 2.28` and `tanδ = 0.04`. Convert before entering it as `(n,k)`:

```
k = n · tanδ / 2 = 1.5105 × 0.04 / 2 = 0.0302
n = √2.28 = 1.5105
```

Writing `k = 0.04` directly halves the loss and the absorption peak drops by ~10 points.
In a MIM absorber this layer carries *most* of the dissipation (Liu 2010: an order of magnitude more
than the gold), so getting `k` right matters more than getting the metal right.

## Silicon

`Si (Silicon) - Palik` is in the database — assign by name, never build it. Note the exact suffix:
`"Si (Silicon) - Palik"`, not `"Si"`.

## TiO₂

Four database variants exist and differ by ~15% in the visible; mixing them between runs invalidates
any comparison. `TiO2 (Titanium Dioxide) - Siefke` gives n@532 nm = 2.45 and is the one used in the
P03 side experiments (t4/t14 series).

Trap: `getindex()` takes **frequency in Hz**, not wavelength. Passing 532 (meaning nm) returned
n = 5.99 instead of 2.45 — the error is large but not absurd-looking, which is what makes it dangerous.

## Graphene

Modelled as a 2D surface conductivity, not a bulk `(n,k)`:

- Kubo formula → `σ_s(ω, μ_c, Γ, T)`
- convert to an equivalent thin-film permittivity with `ε_eq = 1 + iσ_s/(ω ε0 t)`, choosing `t` ≈ 0.34 nm
- the chemical potential `μ_c` is the tuning knob in P09 (50–200 meV)

Do not enter graphene as a bulk Drude metal; the thickness is arbitrary and the result becomes a free
parameter.

## Model-name reference (measured on v251)

| `addmaterial()` argument | Result |
|---|---|
| `"Plasma"` | ✅ Drude-type; properties `Plasma resonance`, `Plasma collision` |
| `"Lorentz"` | ✅ |
| `"(n,k) Material"` | ✅ properties `Refractive Index`, `Imaginary Refractive Index` |
| `"Sampled data"` | ✅ properties `sampled data`, `max coefficients` |
| `"Drude"` | ❌ `Failed to create material of type Drude.` |
| `"Dispersive"` | ❌ fails |
