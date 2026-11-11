---
name: fdtd-paper-parameter-extraction
description: Extract the parameters needed to rebuild a paper's FDTD unit-cell simulation into a validated JSON model spec. Use when starting a reproduction from a PDF, when asked what a paper's simulation settings actually were, when a simulation result disagrees with a publication and the input parameters are suspect, or when a new paper package needs its geometry, material models, solver settings and reported targets captured in machine-readable form. Produces a spec consumed by the fdtd-lumerical-unitcell-simulation skill, plus an explicit list of assumptions and missing parameters.
agent_created: true
---

# Paper to FDTD parameter extraction

## When to use

- "reproduce this paper" — the first task is always to get its numbers out, in a form a script can read
- a reproduction is off and you need to prove the *inputs* are right before blaming the solver
- a new package under `packages\` needs its geometry and material models recorded
- someone asks "what did the paper actually simulate?" and the answer is scattered over four pages

Output is always one file: `spec_<id>.json` conforming to `references/model-spec-schema.md`.
It is the contract with the building skill — nothing downstream should have to re-read the PDF.

## Workflow

1. **Dump the text with page markers.**
   ```bash
   PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
   "$PY" scripts/extract_pdf_text.py paper.pdf --images _scratch/pdf_img
   ```
   The summary table flags pages with no text layer (`SCAN?`) — those must be rendered and read
   visually. Do not assume a scanned Methods section says what you expect.

2. **Hunt in a fixed order**, not front to back: target figure caption → the sentence introducing
   that figure → Methods → parameter table → supplementary → cited material references.
   The full checklist and the reasons for this order are in `references/parameter-hunting.md`.

3. **Copy `assets/spec_template.json`** to `packages\P0N_...\scripts\spec_<id>.json` and fill it.
   Rules that are not negotiable:
   - every length in metres, `ωp`/`ωc` in **rad/s**
   - any value used twice lives in `parameters`, never repeated in two objects
   - every material carries `cite` (page, caption, or "Methods")
   - anything you inferred goes into `assumptions`; anything you could not find goes into `missing`

4. **Validate.**
   ```bash
   "$PY" scripts/validate_spec.py cases/P0N_.../config/spec_<id>.json --strict
   ```
   It checks structure, unit plausibility (a "185" that should be 185 nm fails), material kinds,
   object references, and warns when a lattice period is combined with PML boundaries.

5. **Hand off.** The spec is the input to `fdtd-lumerical-unitcell-simulation`. Do not also hand over a
   prose summary of the parameters — one source of truth or none.

## What "done" looks like

A spec is finished when all of these hold:

- `validate_spec.py --strict` exits 0
- every object's `material` exists in `materials`, and every material has a `cite`
- `targets` contains at least two numbers (the headline value plus one shape metric such as FWHM) —
  a single number is too easy to hit by accident
- `assumptions` explains every value not literally printed in the paper
- `missing` lists the questions worth asking the author, each phrased as a question

## CRITICAL — the three failures this skill exists to prevent

**1. Unit drift.** A plasma frequency quoted as `2π × 2175 THz` written as `2.175e15` instead of
`1.3666e16 rad/s` makes the metal tens of times too reflective; the absorption peak silently
disappears while the spectrum still looks like a spectrum. Same class of error: `185` for 185 nm,
and `ε'' = 0.04` used directly when the paper meant `tanδ = 0.04` (correct: `k = n·tanδ/2 = 0.0302`).

**2. Silent substitution.** Replacing tabulated optical constants (Palik, Johnson–Christy) with a
Drude fit, or the reverse. On one measured device this moved a polarisation-conversion ratio from
72% to 95%. Record which one the paper used; do not "improve" it.

**3. Guessing to close a gap.** When the reproduction is off, the temptation is to nudge a parameter
until the curve matches. That converts a reproduction into a fit and destroys the only thing it was
for. Put the unknown in `missing`, say what you would need to know, and stop.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `validate_spec.py` rejects a length | value written in nm/µm, or a bare `185` | convert to metres; every length in the file is `m` |
| `ωp` looks plausible but the metal is far too reflective | quoted as `2π × f` but written as `f` | store **rad/s**: `2π × 2175 THz = 1.3666e16` |
| `k` disagrees with the paper's loss | paper gives `tanδ`, not `k` | `k = n·tanδ/2` |
| an object's `material` not found | material defined but not added to `materials` | define once, reference by name |
| the spec validates but the result is off | parameter guessed to close a gap | move it to `missing` and stop — do not fit |
| a page has no extractable text (`SCAN?`) | scanned Methods section | render the page and read it visually |

## Examples

**User:** "reproduce the absorber in this PDF."

**Action:** `extract_pdf_text.py` → hunt the caption → copy `assets/spec_template.json` to
`packages\P01_...\scripts\spec_p01.json` → `validate_spec.py --strict`.

**Result:** a spec whose `targets` hold `peak_absorption = 0.97 @ 6.0 µm`, whose `assumptions` record
the one open question (`ts` measured to the mid-plane of the cross, not to the ground-plane top), and
whose `missing` asks that question in a form the author can answer.

## References（load on demand）

- Load `references/model-spec-schema.md` **when filling or reading `spec_<id>.json`** — field-by-field
  contract shared with the building skill.
- Load `references/parameter-hunting.md` **when hunting a parameter or units look wrong** — where each
  parameter hides, the checklist, unit traps, and how to tell Drude from tabulated data.
- Load `assets/spec_template.json` **when starting a new spec** — its object block is a MIM stack that
  can be edited or deleted.
- `scripts/extract_pdf_text.py` — page-marked text dump with scan detection.
- `scripts/validate_spec.py` — structural and physical plausibility checks.
