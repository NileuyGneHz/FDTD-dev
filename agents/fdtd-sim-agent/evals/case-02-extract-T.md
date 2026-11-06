# case-02 — extract T from an existing run without re-running it

**Tests**: correct result extraction. The monitor API returns a list of dicts on v251; a naive
`lam, T = f.getresult(...)` raises `too many values to unpack`. This case also checks that the agent
verifies `T ≈ 0` instead of assuming it.

## Prompt

> 这个工程跑过了：`packages\P01_Absorber_042\results\repro_p01\point_00_base.fsp`。
> 不要重跑，直接给我峰值处的 R 和 T，并说明 T 是否合理。

## Expected actions

1. Load the `.fsp`, read results **without** calling `run()`.
2. Use the dict-list form:
   ```python
   item = f.getresult("T", "T")[0]
   lam, val = np.asarray(item["lambda"]), np.asarray(item["T"])
   ```
3. Report `R` and `T` at the absorption peak.
4. Judge `T`: for a design with a 100 nm gold ground plane, `T` should be numerical zero
   (~1e-5 or smaller, sign irrelevant). State why.

## Pass criteria

| # | Check | Expected |
|---|---|---|
| 1 | Did not re-run the simulation | no new `_p0.log` timestamp, no new `.fsp` |
| 2 | Extracted via the dict form | no `ValueError` |
| 3 | `R` at peak | 0.19 ± 0.02 |
| 4 | `T` at peak | |T| < 1e-3 |
| 5 | Interpretation | "T ≈ 0 confirms the ground plane is opaque at 6 µm" |

## Fail modes

- Crashes on unpacking and then reports "the results file is corrupted" → **fail**: it is an API
  shape issue, not corrupt data.
- Re-runs the simulation "to be safe" → **fail**: the prompt explicitly said not to, and a 30 s run
  is not the point of the test.
- Says T = −1.26e-5 is "negative, so unphysical" → **fail**: that is numerical zero; the sign carries
  no meaning at that magnitude.

## Variant (harder)

Ask for the same numbers from a `.fsp` that was **saved before** the run (so it contains no results).
Correct behaviour: recognise that the file has no results and say so, rather than reporting zeros.
