# Phase conventions and how to report a phase result

Phase is where results most often look meaningful and are not. This file fixes the conventions so a
number produced here can be checked by someone else.

## What is being measured

For a periodic cell under normal incidence, the quantity of interest is the **complex transmission
coefficient of the zeroth order**:

```
t(λ) = E_transmitted,zeroth(λ) / E_incident(λ)
```

- `|t|` is the amplitude; `|t|²` should agree with the power monitor's `T`.
- `arg(t)` is the **phase delay** imparted by the structure.

The zeroth order is obtained by **averaging the complex field over the unit-cell plane**. At normal
incidence every non-zero diffraction order is evanescent, so the plane average contains only the
propagating zeroth order. Sampling a single point instead picks up near-field ripple from the
structure and gives a phase that depends on where you put the monitor.

## Only differences are physical

`arg(t)` as computed includes:

1. the source's own phase,
2. the propagation phase from the source plane to the monitor plane,
3. the structure's phase delay.

Terms 1 and 2 are identical for two runs that share the same geometry and monitor plane, so their
difference cancels them exactly:

```
Δφ = arg(t_x) − arg(t_y)
```

**This is why no bare-substrate reference run is needed.** If you ever do need absolute phase (for
example to compare two different structures), you must run a reference and subtract — and say so.

## Sign convention

`arg()` of the complex DFT result follows the solver's time-harmonic convention. A global sign flip
of every phase is a convention change, not a physical error. What is invariant is:

- `cos(Δφ)` — the physically meaningful quantity for a retarder,
- `|Δφ|`.

Report `cos(Δφ)` alongside the angle for exactly this reason.

## The 180° branch-cut trap (measured, P02, 2026-11-04)

A half-wave plate sits at **exactly** 180°, which is the wrap boundary. The signed difference then
flips between `+179.7°` and `−179.8°` from sample to sample, and the naive mean collapses:

```
signed mean   = −62.3°     <- meaningless
mod-360 mean  = 179.x°     <- correct
```

**Rule**: always report the value **modulo 360 in [0, 360)** for a retarder target, and never average
the signed value across a branch cut. A signed mean near 0° with a wide spread is the signature of
this artefact, not of a device that does nothing.

## Criteria

| Device | Criterion | Equivalent |
|---|---|---|
| half-wave plate | Δφ = π | `cos Δφ = −1` |
| quarter-wave plate | Δφ = π/2 | `cos Δφ = 0` |
| full-wave / transparent | Δφ = 0 | `cos Δφ = +1` |

Report, per quantity:

1. the **mean over the stated design band** (e.g. C+L: 1530–1625 nm),
2. the **extremes** over that band,
3. `cos(Δφ)` mean,
4. the band you used, explicitly. "Constant π over a broad band" is not a number; "180 ± 3° over
   1530–1625 nm" is.

## Cross-checks before believing a phase curve

| Check | Passes when | If it fails |
|---|---|---|
| amplitude vs power | `|t|² ≈ T` within a few percent | monitor not on the transmission plane, or the plane average is not zeroth order |
| both polarizations transmitting | `T` comparable for both runs | one run sits at a resonance minimum; the "phase difference" then compares two different regimes |
| mesh stability | Δφ moves by less than ~0.1π when the mesh is refined | phase converges more slowly than power; refine before reporting |
| smoothness | Δφ varies smoothly with λ apart from 2π wraps | a discontinuity that is not a wrap means an order crossing or a bad average |
