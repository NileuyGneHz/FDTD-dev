# Reproduction report — <package ID> <paper short title>

> Fill this in after every reproduction run. Keep it short: one page. The value is in the
> **deviation table**, not in restating the paper.
> Copy this file to `packages\<P0N_...>\results\repro_report.md` and fill it there.

## 1. Identity

| Item | Value |
|---|---|
| Package | `P0N_...` |
| Paper | authors, journal, year, DOI |
| Local PDF | `paper\...pdf` |
| Target figure / panel | e.g. Fig. 2(a) |
| Entry script | `scripts\...py` |
| Project file | `fsp\...fsp` |
| Date / run by | |

## 2. Parameters — paper vs. model

Every row must cite where the number came from. A parameter you could not find in the paper is a
red flag: mark it `NOT IN PAPER` rather than inventing a value.

| Parameter | Symbol | Paper value | Used value | Source (page / caption / Methods) |
|---|---|---|---|---|
| period | a | | | |
| feature size(s) | | | | |
| metal thickness | | | | |
| spacer thickness | | | | |
| substrate | | | | |
| metal model | | | | |
| spacer index | | | | |

## 3. Simulation setup

| Item | Setting | Why |
|---|---|---|
| Dimension | 3D / 2D | |
| x / y boundary | Periodic / PML / Bloch | **must be Periodic for an infinite array** |
| z boundary | PML | |
| Mesh | accuracy + local override | |
| Source | type, direction, range, polarisation | |
| Monitor R | position | |
| Monitor T | position | |
| Auto-shutoff | | |

## 4. Result vs. paper

| Quantity | Paper | Simulation | Δ | Verdict |
|---|---|---|---|---|
| peak absorption | | | | |
| peak wavelength | | | | |
| FWHM | | | | |
| R at peak | | | | |
| T at peak | | | | |

**Verdict legend**: ✅ within stated tolerance · 🔶 directionally right, quantitatively off ·
❌ wrong shape / wrong peak / non-physical (R>1, A<0)

## 5. Deviation diagnosis

For each 🔶 or ❌ row above, work down this list **in order** and record what you ruled out:

1. **Boundary conditions** — is x/y really `Periodic`? PML simulates one isolated element.
2. **Material model** — is the metal's ωp/ωc the paper's, or a database default?
3. **Mesh convergence** — re-run at one higher mesh level; if the answer moves more than the
   disagreement with the paper, the mesh is the problem.
4. **Monitor placement** — inside the PML? too close to the structure? on the wrong side of the source?
5. **Normalisation** — source amplitude = 1? T measured on the far side of the ground plane?
6. **Geometry units** — metres everywhere? (a 2 µm period written as `2` is 2 metres)

| # | Suspect | Ruled in / out | Evidence |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

## 6. Conclusion

- What reproduces, quantitatively:
- What does not, and the best-supported explanation:
- Next action (and which package README section was updated):
