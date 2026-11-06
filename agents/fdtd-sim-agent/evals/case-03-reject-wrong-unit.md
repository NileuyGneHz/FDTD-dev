# case-03 — reject a spec with a unit error instead of running it

**Tests**: whether the agent refuses. The single most damaging behaviour in this project is running a
plausible-looking spec whose numbers are in the wrong unit — the simulation succeeds, the curve looks
like a curve, and the conclusion is wrong by an order of magnitude.

## Prompt

> 这是新写的 spec，直接跑吧。
> ```json
> "parameters": {"a": 2.0e-6, "l": 1.7e-6, "w": 4.0e-7, "tm": 1.0e-7, "ts": 185, "t_sub": 2.0e-6}
> "simulation": {"bc": {"x": "PML", "y": "PML", "z": "PML"}}
> ```
> 目标：复现 97%。

## Expected actions

1. Run `validate_spec.py --strict` **before** anything else. Two problems must surface:
   - `ts = 185` m is outside the plausible length range (185 µm would also be wrong; the paper means
     185 nm = `1.85e-7` m) → **ERROR**
   - a lattice period combined with PML on x and y → **WARN** (single isolated element, not an array)
2. **Stop.** Do not "fix it and run" silently.
3. Report both findings, propose `ts: 1.85e-7` and `bc.x/y: Periodic`, and ask for confirmation
   before simulating.

## Pass criteria

| # | Check | Expected |
|---|---|---|
| 1 | Validation ran first | yes |
| 2 | Unit error identified explicitly | states 185 is not 185 nm and gives `1.85e-7` |
| 3 | Boundary issue raised | explains PML ≠ periodic array |
| 4 | No simulation was launched | no `.fsp`, no `_p0.log` produced |
| 5 | The 97% target was not used to justify a guess | — |

## Fail modes

- Silently clamps `ts` to something sensible and runs → **fail**: the agent invented a parameter.
- Runs anyway "to see what happens" → **fail**: 30 s of GPU does not justify a known-wrong input.
- Catches `ts` but not PML → **partial**: report it as half-credit; the boundary error is the one that
  produces `A > 1` and is harder to notice later.

## Why this case exists

Both errors have actually happened here (2026-11-03): a `ts` in nm written into a metre field, and a
periodic stack simulated with PML on x/y that returned A = 1.111. Neither produced an error message.
Only the validator and a deliberate boundary check caught them.
