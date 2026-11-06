# Model spec schema (v1.0)

The single contract between **extraction** (`fdtd-paper-parameter-extraction`) and **building**
(`fdtd-lumerical-unitcell-simulation`). One JSON file describes everything needed to rebuild a unit cell:
geometry, materials, solver settings, and the numbers the paper reports.

All lengths are in **metres**, all angles in **degrees**, all frequencies in **rad/s** unless a field
says otherwise. No exceptions — mixed units are the most common cause of a spectrum that is off by
10× or 1000×.

## Top level

```json
{
  "schema_version": "1.0",
  "meta": { ... },
  "parameters": { ... },
  "lattice": { ... },
  "materials": { ... },
  "objects": [ ... ],
  "simulation": { ... },
  "targets": [ ... ],
  "assumptions": [ ... ],
  "missing": [ ... ]
}
```

| Key | Required | Purpose |
|---|---|---|
| `meta` | yes | provenance: which paper, which figure, which pages |
| `parameters` | yes | named scalars the geometry refers to by name |
| `lattice` | yes | periodicity — decides the boundary conditions |
| `materials` | yes | material definitions keyed by name |
| `objects` | yes | the geometry, ordered by mesh order |
| `simulation` | yes | solver region, source, monitors |
| `targets` | yes | what the paper claims — the test to pass |
| `assumptions` | no | every value you inferred rather than read |
| `missing` | no | parameters the paper never states — the questions to ask |

## `meta`

```json
{
  "package": "P01",
  "paper": {
    "title": "Infrared Spatial and Frequency Selective Metamaterial with Near-Unity Absorbance",
    "authors": "Liu, Starr, Starr, Padilla",
    "journal": "Phys. Rev. Lett.", "volume": "104", "page": "207403", "year": 2010,
    "doi": "10.1103/PhysRevLett.104.207403"
  },
  "target_figure": "Fig. 2(a)",
  "source_pages": [1, 2],
  "extracted_by": "agent",
  "extracted_on": "2026-11-03"
}
```

`source_pages` matters: when a number later looks wrong, you need to know which page to re-read.

## `parameters`

Named scalars. **Any value used more than once lives here** — never repeat a number in two objects,
or a sweep will change one and not the other.

```json
"parameters": {
  "a":  2.0e-6,
  "l":  1.7e-6,
  "w":  4.0e-7,
  "tm": 1.0e-7,
  "ts": 1.85e-7,
  "t_sub": 2.0e-9
}
```

Values may also be expressions over other parameters, e.g. `"z_cross": "tm/2"`. Keep expression
chains short — one level deep is readable, three is a debugging trap.

## `lattice`

```json
"lattice": {
  "type": "square",
  "period_x": "a",
  "period_y": "a",
  "supercell": { "nx": 1, "ny": 1 }
}
```

`type`: `square` | `rectangular` | `hexagonal`. `supercell` > 1 means the model contains several
unit cells (gradient metasurfaces, phase-gradient supercells); the builder multiplies the simulation
region by `nx`/`ny` but keeps the object coordinates as given.

## `materials`

Four kinds are supported. Every entry must carry `cite` — where in the paper the values came from.

```json
"materials": {
  "Au":    {"kind": "drude", "wp": 1.3665928e16, "wc": 4.0840704e13, "unit": "rad/s", "cite": "Methods"},
  "Al2O3": {"kind": "constant_nk", "n": 1.5105, "k": 0.0302, "cite": "Methods"},
  "Si":    {"kind": "builtin", "name": "Si (Silicon) - Palik", "cite": "Methods"},
  "Gr":    {"kind": "sampled_nk", "data": [[4e-7, 3.0, 0.1], [5e-7, 2.9, 0.12]], "cite": "Fig. S3"}
}
```

| kind | fields | note |
|---|---|---|
| `drude` | `wp`, `wc` | angular frequencies, rad/s. `wp = 2π·f_p` if the paper quotes f in Hz |
| `constant_nk` | `n`, `k` | lossless if `k` omitted |
| `constant_eps` | `eps_real`, `eps_imag` | when the paper gives ε and tanδ, convert: `k = n·tanδ/2` |
| `builtin` | `name` | must match the Lumerical database exactly, including the suffix |
| `sampled_nk` | `data` | rows of `[wavelength_m, n, k]` |

**Unit trap.** Papers usually quote `ω_p` in **eV** or in **Hz**. `2π × 2175 THz` = `1.3666e16 rad/s`.
Writing `2.175e15` (Hz) into a field that expects rad/s makes the metal ~40× too reflective and the
absorption collapses. Check with `getindex` against a value the paper quotes, if it quotes one.

## `objects`

Each object is built by evaluating its string fields against `parameters`. Numbers pass through
unchanged.

```json
"objects": [
  {
    "id": "ground",
    "type": "box",
    "material": "Au",
    "mesh_order": 2,
    "center": ["0", "0", "-(ts + tm/2)"],
    "span":   ["a", "a", "tm"]
  },
  {
    "id": "cross_x",
    "type": "box",
    "material": "Au",
    "mesh_order": 1,
    "center": ["0", "0", "tm/2"],
    "span":   ["l", "w", "tm"]
  },
  {
    "id": "brick",
    "type": "polygon",
    "material": "Au",
    "mesh_order": 1,
    "vertices": [["l/2","w/2"], ["-l/2","w/2"], ["-l/2","-w/2"], ["l/2","-w/2"]],
    "z": "tm/2",
    "z_span": "tm"
  },
  {
    "id": "pillar",
    "type": "cylinder",
    "material": "Si",
    "mesh_order": 1,
    "center": ["0", "0", "h/2"],
    "radius": "r",
    "height": "h"
  }
]
```

| type | required fields |
|---|---|
| `box` | `center` (3), `span` (3) |
| `polygon` | `vertices` (N×2, x/y), `z`, `z_span` — for anything that must be rotated |
| `cylinder` | `center` (3), `radius`, `height` |
| `ellipse` | `center` (3), `axes` (2, **full diameters**), `height`; optional `rotation_deg`, `n_vertices` (default 48) |
| `sphere` | `center` (3), `radius` |
| `ring` | `center` (3), `radius`, `inner_radius`, `height` |

`ellipse` exists because papers quote an elliptical pillar as "a = 285 nm, b = 450 nm" — full axes,
not radii. If a semi-axis interpretation would make the feature larger than the period, the full-axis
reading is the correct one; record that reasoning in `assumptions`.

`mesh_order` — lower wins where objects overlap. Put the finest / most important feature at 1, the
ground plane at 2, the spacer at 3, the substrate at 4. Overlap is otherwise resolved silently and
in the wrong direction.

## `simulation`

```json
"simulation": {
  "mode": "reflection",
  "dimension": "3D",
  "bc": { "x": "Periodic", "y": "Periodic", "z": "PML" },
  "mesh_accuracy": 4,
  "mesh_override": { "dx": 3.0e-8, "dy": 3.0e-8, "dz": 2.0e-8,
                     "z_range": ["-(ts + tm)", "tm + 5e-8"] },
  "auto_shutoff": 1e-4,
  "simulation_time": 5e-12,
  "source": {
    "type": "plane_wave", "direction": "Backward", "polarization_deg": 0,
    "wavelength_range": [4.0e-6, 8.5e-6], "npts": 91, "z": "auto"
  },
  "monitors": {
    "R": { "z": "auto", "span": ["a", "a"] },
    "T": { "z": "auto", "span": ["a", "a"] }
  }
}
```

`mode` decides the whole monitor topology, and getting it wrong produces a plausible but meaningless
spectrum:

| mode | light path | source | R monitor | T monitor |
|---|---|---|---|---|
| `reflection` (default) | enters from air above, reflects off the stack | above, `Backward` | above the source | below the stack |
| `transmission` | enters through the substrate, exits into air | below, `Forward` | below the source | above the stack |

A metal-backed absorber is `reflection`; an all-dielectric metasurface on glass is `transmission`.
`direction` may still be overridden explicitly in `source`.

`bc.x` / `bc.y` = `Periodic` for any infinite array. `PML` there means a single isolated element and
produces non-physical absorption for a periodic design (measured: A = 1.11 vs 0.81 on the same stack).

`z: "auto"` lets the builder place the source and monitors from the stack extent — preferred, because
hand-written monitor heights drift when a layer thickness changes.

## `targets`

```json
"targets": [
  {"quantity": "peak_absorption", "value": 0.97, "at_wavelength": 6.0e-6,
   "tolerance": 0.05, "where": "Fig. 2(a)"},
  {"quantity": "fwhm", "value": 1.0e-6, "tolerance": 0.2e-6, "where": "text"}
]
```

`quantity` values the builder understands: `peak_absorption`, `peak_wavelength`, `fwhm`,
`peak_reflectance`, `peak_transmittance`.

## `assumptions` and `missing`

```json
"assumptions": [
  "Substrate thickness set to 2 µm; the paper does not state it (ground plane makes it irrelevant).",
  "Source spectral range 4–8.5 µm chosen to cover the 6 µm peak; the paper's Fig. 2 spans 3–11 µm."
],
"missing": [
  {"field": "spacer_thickness_reference_surface",
   "question": "Is t = 0.185 µm measured from the top of the ground plane or the mid-plane of the cross?"},
  {"field": "substrate_thickness", "question": "Not stated; assumed thick enough to be opaque."}
]
```

Every entry in `missing` is a question for the author. Do not fill these with guesses and hide them —
the difference is the difference between a reproduction and a fabrication.
