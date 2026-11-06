# Lumerical v251 API reference (measured on this machine)

Scope: only what has been **read back from a working project or executed successfully** with
`lumapi` on Ansys Lumerical 2025 R1 (v251, build 8.33.3999). Anything not listed here was not
verified — check the official docs rather than guessing.

Measured 2026-11-03 against `packages\P01_Absorber_042\fsp\d2_perfectCross.fsp`.

## 1. Session setup (order matters)

```python
import sys, os
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
os.environ.setdefault("ANSYSLMD_LICENSE_FILE", "1055@localhost")
import lumapi
f = lumapi.FDTD(hide=True)
```

- `import lumapi` — **not** `import ansys.lumerical`.
- If the GUI is open, the headless session competes for the same seat; close the GUI first.
- `f.close()` releases the seat — call it in a `finally:` block, or the next run hits a stale seat.

## 2. Reading an existing `.fsp`

```python
f.load(path)
root = f.getObjectById("::model")     # the only reliable entry point
for child in root.getChildren():      # recurse to walk the tree
    print(child, f.getnamed(child, "type"))
```

- `getobjectlist()` returns only `['::model::']` — it does **not** expand the subtree.
- `getnamed(name, prop)` is safe for both numbers and strings; it raises `LumApiError` for an
  unknown property name.
- `.fsp` is a private binary. Never try to parse it as text; go through `lumapi`.

## 3. Property names by object type (all measured)

### `FDTD` (solver region)

| Property | Notes |
|---|---|
| `dimension` | `"3D"` / `"2D"` |
| `x span`, `y span`, `z span` | plus `x`, `y`, `z` centres |
| `x min bc`, `x max bc`, `y min bc`, `y max bc`, `z min bc`, `z max bc` | `"PML"` / `"Periodic"` / `"Bloch"` / `"Metal"` / `"Symmetric"` / `"Anti-Symmetric"` |
| `mesh accuracy` | 1–8. **8 is not "best practice"** — it is extremely expensive; 3–4 plus a local mesh override is the sane default |
| `mesh cells per wavelength` | only used when `define x/y/z mesh by = "mesh cells per wavelength"` |
| `auto shutoff min` | default 1e-5; the run stops when the field decays below it |
| `use auto shutoff` | `1` by default |
| `pml layers`, `pml type`, `pml profile` | PML tuning; leave alone unless diagnosing reflections |
| `angle theta`, `angle phi` | incidence angles (degrees) |

### `Rectangle` (geometry)

| Property | Notes |
|---|---|
| `x`, `y`, `z` | **centre** coordinates |
| `x span`, `y span`, `z span` | full extents, not half-widths |
| `z min`, `z max` | read-only derived values |
| `material` | material name as a string |
| `mesh order` | lower number wins in an overlap; pair with `override mesh order from material database = 1` |
| `override mesh order from material database` | must be `1` for the `mesh order` above to take effect |

### `PlaneSource` (plane wave)

| Property | Notes |
|---|---|
| `injection axis` | `"z"` |
| `direction` | `"Backward"` = propagates toward −z (downward; use for reflection setups) |
| `x`, `y`, `z`, `x span`, `y span` | source plane position and size |
| `amplitude` | set to `1` so that measured power can be read directly as a ratio |
| `polarization angle` | degrees, measured from the x axis |
| `override global source settings` | `1` when you want to set the wavelength range on the source itself |
| `wavelength start`, `wavelength stop` | metres |

### `DFTMonitor` (created by `addpower`)

| Property | Notes |
|---|---|
| `monitor type` | `"2D Z-normal"` for a plane cross-section normal to z |
| `x`, `y`, `z`, `x span`, `y span` | monitor plane |
| `override global monitor settings` | `1` to set the spectral sampling per monitor |
| `use source limits` | `0` to decouple from the source range |
| `wavelength center`, `wavelength span` | metres |
| `frequency points` | number of samples |
| `use wavelength spacing` | `1` = uniform in wavelength instead of frequency |

## 4. Materials

`addmaterial()` takes a **model type**, not a material name. Measured on v251:

| Argument | Result |
|---|---|
| `"Plasma"` | ✅ works — the Drude-type model; properties `Plasma resonance`, `Plasma collision` |
| `"Lorentz"` | ✅ works |
| `"(n,k) Material"` | ✅ works — properties `Refractive Index`, `Imaginary Refractive Index` |
| `"Sampled data"` | ✅ works — properties `sampled data`, `max coefficients` |
| `"Drude"` | ❌ `Failed to create material of type Drude.` |
| `"Dispersive"` | ❌ `Failed to create material of type Dispersive.` |

Standard pattern — create, rename, then set:

```python
t = f.addmaterial("(n,k) Material")          # returns a temporary name like "New material 3"
f.setmaterial(t, "name", "Al2O3_paper")
f.setmaterial("Al2O3_paper", {"Refractive Index": 1.5105,
                              "Imaginary Refractive Index": 0.0302})
```

**Drude metal via `Plasma`.** Pass angular frequencies in rad/s — that is what the stored model
uses. For Au with ωp = 2π×2175 THz and ωc = 2π×6.5 THz:

```python
t = f.addmaterial("Plasma")
f.setmaterial(t, "name", "Au_paper")
f.setmaterial("Au_paper", {"Plasma resonance": 1.3665928e16,     # 2*pi*2175e12
                           "Plasma collision": 4.0840704e13})    # 2*pi*6.5e12
```

Unit sanity check: at 6 µm this returns `n ≈ 2.80 + 43.25i`. The imaginary part is the one that
governs absorption and it matches hand-calculated √(ε) to ~0.3%; the real part is numerically
ill-conditioned because ε is large and negative (a ±0.5% change in ε_real moves n_real by 10×).
Do not "fix" n_real by rescaling ωp — that would wreck the absorption.

**Built-in library materials** are assigned by name on the object, not created:

```python
f.setnamed("Si_sub", "material", "Si (Silicon) - Palik")
```

**`getindex()` takes frequency in Hz, not wavelength** — pass a column matrix:

```python
f.getindex("Au_paper", np.array([[299792458.0 / 6.0e-6]]))   # -> [[n + ik]]
```

## 5. Reading results

```python
lam, R = f.getresult("R", "T")    # monitor named "R" -> (wavelengths [m], power ratio)
```

- The `"T"` result of a power monitor is the **power through the monitor normalised to the source**.
  It is *not* the letter of the monitor name — a monitor called `R` also returns its `"T"` result.
- No extra normalisation is needed **provided** `source amplitude = 1` and the monitor sits on the
  far side of the source from the structure (see the reflection rule in `SKILL.md`).
- Convert to micrometres explicitly (`* 1e6`) before plotting or comparing with a paper.

## 6. Traps measured on this machine

1. **`x`/`y` boundaries decide what you are simulating.** `PML` on x/y means a single isolated
   element; `Periodic` means an infinite array. For a metasurface paper the array is the physical
   object — check this before comparing with published spectra.
2. **A monitor sitting inside the PML records garbage.** Keep at least ~0.3 µm of propagation
   distance between a monitor and the nearest PML face.
3. **`mesh accuracy = 8`** on a 2 µm cell with 100 nm metal takes minutes per run and buys almost
   nothing over accuracy 4 + a 15–25 nm local override around the metal/spacer stack.
4. **Structures larger than the simulation region get clipped, not warned about.** A 5 µm rectangle
   in a 2 µm cell is fine — but it means the drawing no longer represents the array period.
5. **Two `lmgrd` processes can coexist** and only one owns port 1055; a licence failure that looks
   like "server down" is usually the *vendor daemon* (see workspace `SKILL.md` §7.7).
