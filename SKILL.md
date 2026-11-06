---
name: lumerical-fdtd-headless
description: Build and verify Ansys Lumerical FDTD scripts (.lsf) and projects (.fsp) headlessly with lumapi. Use when creating or modifying Lumerical simulation scripts, diagnosing script errors, or automating parameter sweeps. Contains field-tested v251 scripting traps, GPU crashes on non-ASCII paths, CPU/GPU resource switching, and GUI popup workarounds. Eight chapters: environment / sessions / modelling / properties / results / resources / troubleshooting / tools.
agent_created: true
updated: 2026-10-10
---

# Ansys Lumerical FDTD Headless Scripting and Verification (v251 field manual)

> This file answers one question: **when driving Lumerical through `lumapi`, which constructs quietly ruin your work?**
> Every conclusion comes from **measurements on this machine**, is dated, and carries a **control experiment** where possible.
> It is not a paraphrase of the official documentation — where the two conflict, **this file wins** (and the conflict is flagged in the entry).

## How to use this file

| Situation | How to read |
|---|---|
| Short on time / mid-debug | **Read §0 (symptom index) only**, jump by symptom, do not read top to bottom |
| First time in this workspace | Read `agent.md` first (the rules), then come back here on demand (the evidence and fixes) |
| About to write a new script | Read §1.1 (environment) → §2 (session sequence) → §3.1 (recommended style), copy the code blocks |
| Results disagree with the literature | Read §5.2 (the `getindex` frequency trap) → §7.1–7.2 (control-experiment method) |
| The error message makes no sense | §0 index → jump to the matching chapter |

**Division of labour with the other files**

| File | Role |
|---|---|
| `agent.md` | **The rules**: project goal, asset map, iron laws, collaboration conventions |
| `SKILL.md` (this file) | **Evidence and fixes**: measured conclusions + code you can copy directly |
| `packages\PACKAGES.md` | **Task map**: which package this session is about |
| `README.md` | Directory index and getting started (English version: `README.en.md`) |

**Structure**: 8 chapters — environment / sessions / modelling / properties / results / resources / troubleshooting / tools.

## Path conventions (required reading for collaboration)

This repository covers only the `F:\Lumercial_WS\FDTD_WS\` level. Paths in this document fall into three classes:

| Class | Example | Notes |
|---|---|---|
| **In-repo** | `F:\Lumercial_WS\FDTD_WS\packages\P03_HWP_Ding2015\` | Shipped with the repo; every collaborator has it |
| **Local, outside the repo** | `F:\Lumercial_WS\scripts\`, `...\docs\`, `...\projects\`, `...\ANSYS Inc\` | **Not in the repo**; must be prepared separately on another machine. Tool scripts with the `z_*` / `t*` prefixes mostly fall here |
| **Not committed** | `course_media\*.mp4`, `.fsp` files > 100 MB | Excluded for size reasons (see the repo root ignore rules) |

All work inside a package happens under `packages\P0N_<topic>\`; `fsp\` and script filenames **must be pure ASCII** (§6.2).

## 0. Index by symptom (⭐ start here)

If you are short on time, jump by "what you are seeing". Do not read top to bottom.

| What you are seeing | Go to |
|---|---|
| **`run()` returns instantly, no error, nothing was computed** | §2.1 — ⭐⭐⭐⭐⭐ the worst trap |
| **Error says "wrong number of arguments" but your arguments are fine** | §4.1 (`setname` vs `setnamed`) |
| **After `load`ing an already-computed `.fsp`, `set` complains about analysis mode** | §2.2 |
| **Job Manager shows mojibake / Progress 0% / path contains non-ASCII** | §6.2 (the GPU engine rejects non-ASCII paths) |
| **Estimated time remaining is absurdly long (hundreds of hours)** | §6.1 (check mesh size + wavelength units first) |
| **`R > 1` / negative `T` / `A = 1−R−T` exceeds 1 (non-physical)** | §6.3 (GPU divergence) + §6.4 (periodic boundaries) |
| **Material refractive index comes back absurd (TiO₂ → 5.99)** | §5.2 (`getindex` takes frequency, not wavelength) |
| **GUI reports "no active GPU resources"** | §6.3 (`setresource` persists and corrupts the config) |
| **`getnamed(x)` prints what looks like mojibake / `Mesh`-type object cannot be found** | §4.2 (three signatures) |
| **You want to set a rotation angle on a rectangle** | §3.6 (`addrect` rotation is inactive → use `addpoly`) |
| **`addmaterial("Au_Drude")` fails** | §3.7 (the argument is a **model type**, not a material name) |
| **New session reports `Failed to set up Ansys license sharing`** | §1.4 (port TIME_WAIT, just retry) |
| **`FlexNet Licensing error:-97,121` / "The desired vendor daemon is down" / GUI won't launch** | §7.7 (the vendor daemon died; `lmgrd` is still fine — run `lmreread`) |
| **Python side raises `KeyError` on `E["Ex"]`** | §5.1 (the result is a whole array, not a dict) |
| **GUI keeps popping up "Save changes?"** | §7.5 |
| **You want to know whether some tool or method actually works** | §7.1 — the first rule of this project |
| **You want to read the scripts / monitors inside someone else's `.fsp`** | §5.3 (Analysis Groups are readable) |
| **A result is missing from O&S / right-clicking model shows no Visualize** | §5.4 (the result name = `matrixdataset("<name>")` in the root `analysis script`) |
| **Reflectance measurement looks wrong, unclear if it is the code or the physics** | §7.2 (the "gold film only" control) |
| **A long job gets killed halfway / the output file was never written** | §1.5 (use the Bash channel + never print Chinese) |
| **You need to health-check an unfamiliar `.fsp`** | §7.6 |
| **You need to delete files / clean a directory** | §8.5 (Recycle Bin mechanics) |

**The four most expensive lessons (memorise these first)**

1. **Without a control experiment, do not draw a conclusion** (§7.1)
2. **`run()` returning instantly = nothing was computed**; check `layoutmode` + `_p0.log` (§2.1)
3. **Wavelength is in metres; `getindex` takes frequency** (§5.2 / §6.1)
4. **A non-ASCII path always crashes the GPU engine** (§6.2)

## 1. Environment and prerequisites

### 1.1 Prerequisites for headless operation (all three required)

**① License environment variable** (headless requires it explicitly)

```bash
export ANSYSLMD_LICENSE_FILE="1055@localhost"   # the license file says SERVER localhost ... 1055
```

**② Python-side import path**

```python
import sys, os
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
os.environ.setdefault("ANSYSLMD_LICENSE_FILE", "1055@localhost")
import lumapi                      # ships with v251; do NOT write import ansys.lumerical
fdtd = lumapi.FDTD(hide=True)
fdtd.eval(open(lsf_path, encoding="utf-8").read())
fdtd.close()
```

**③ How much the GUI actually conflicts** (corrected by measurement, 2026-09-19): with the GUI process
(`fdtd-solutions.exe`) **already running, headless can still create a session successfully** — this
machine has a 100-seat shared license, so the GUI does not necessarily conflict.
But if you see `Could not connect to Ansys license server`, **the first thing to try is still to close
the GUI and retry**.

The Python environment is `C:\Users\saber\.workbuddy\binaries\python\envs\default`
(**measured 3.13.14**, numpy 2.5.3). ⚠️ System Python 3.14 has no numpy → `import lumapi` crashes outright.

### 1.2 Environment facts at a glance (measured values, do not guess)

| Item | Value |
|---|---|
| Lumerical | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\`, version **2025 R1 (v251)** |
| Python API | `<install>\api\python\lumapi.py`; use **`import lumapi`**, not `import ansys.lumerical` |
| Managed Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default` (3.13.14 + numpy 2.5.3) |
| ❌ System Python | 3.14 has **no numpy** → `import lumapi` crashes outright |
| License | `1055@localhost` (100 shared seats, expires 2035-12-31) |
| headless prerequisite | `export ANSYSLMD_LICENSE_FILE="1055@localhost"` |
| GPU | RTX 3070 Laptop (8 GB) → **real32 single precision**, metals tend to diverge (§6.3) |
| CPU engine | `fdtd-engine-msmpi.exe`; MS-MPI lives at `C:\Program Files\Microsoft MPI\Bin\mpiexec.exe` |
| Single-run duration | 30–60 s for a normal project; thousands of hours when the mesh runs away (see §6.1 for a real case) |

### 1.3 The real lifecycle of a session — measured

**Every `lumapi.FDTD()` starts its own `fdtd-solutions.exe` process and holds 1 license seat.**
Measured (counting `fdtd-solutions.exe` with `tasklist`; baseline 1 = the already-open GUI):

| Operation | Process count | Conclusion |
|---|---|---|
| start | 1 | GUI |
| `a = lumapi.FDTD(hide=True)` | 2 | a new session = a new process, +1 seat |
| `b = lumapi.FDTD(hide=True)` | 3 | **not a singleton**; every instance holds its own seat |
| `a.close()` | 2 | close releases correctly |
| `b.close()` | 1 | back to zero |

#### Does a crash without `close()` leak? → Not permanently, but **never rely on it**

`lumapi.py:1308` defines `__del__` → when Python collects the object it **closes the session
automatically**. So the "variable gets overwritten in a loop" case looks perfectly fine:

```python
for i in range(3):
    fdtd = lumapi.FDTD(hide=True)   # next iteration overwrites fdtd -> refcount 0 -> __del__ cleans up
# measured: the process count stays at 2
```

**But as soon as you hold several references at once (which is exactly what batch/parallel sweeps do),
the seats really do pile up:**

```python
held = []
for i in range(3):
    s = lumapi.FDTD(hide=True)
    held.append(s)                  # hold the reference, blocking collection
# measured: 3 -> 4 -> 5   <- three seats consumed
```

#### Three hard conclusions that follow

1. The point of `try/finally` + `close()` is **not "leak prevention"** (the GC usually covers that),
   it is **deterministic release** — not depending on GC timing or the interpreter's exit path.
2. **The genuinely dangerous case is batch/parallel**: while holding N sessions at once, one missed
   `close()` costs you a seat, and once the 100 seats are gone nothing will start. In a sweep loop
   `close()` must live in `finally`.
3. ❌ **Do not verify leakage by "run the script, then check tasklist"** — by then the GC has already
   cleaned up, and you will wrongly conclude "no problem". Print the count **while the script is alive**.

#### A ready-made session counter (for verification)

```python
import subprocess

def n_sessions() -> int:
    out = subprocess.run(["tasklist"], capture_output=True,
                         text=True, errors="replace").stdout
    return sum(1 for l in out.splitlines() if "fdtd-solutions" in l.lower())
```

### 1.4 Session creation needs a retry (ansyscl port TIME_WAIT)

When you create and close headless sessions rapidly, `lumapi.FDTD()` throws:
```
Failed to set up Ansys license sharing. ANSYSLI exited or could not read server port ...
```
The real cause, visible in the log (`%TEMP%\.ansys\ansyscl.<...>.log`), is:
```
ERROR  Could not bind socket on port 58657.
       1) The OS has not cleared this port since its last use.
```
— The Ansys licensing interconnect daemon runs with `-nodaemon` and **exits when the client exits**;
a fast restart collides with the port's TIME_WAIT. **This is a transient failure; just retry**:

```python
def open_fdtd_retry(n=8, delay=6):
    for i in range(n):
        try:
            return lumapi.FDTD(hide=True)
        except Exception as e:
            hint = "port TIME_WAIT" if "bind socket" in str(e) else "other"
            print("  [session retry %d/%d] %s" % (i+1, n, hint)); time.sleep(delay)
    raise RuntimeError("session creation failed repeatedly")
```
Related practice: **`time.sleep(4)` between variants**, and have one script run all variants in a single
pass rather than starting and stopping repeatedly.

**⚠️ Do not conclude from this that the license is broken**: in this instance `lmutil lmstat` showed
100 seats with 0 in use — entirely healthy. The "check licenses" text in the error is misleading.

### 1.5 Long jobs go through the Bash channel; never print Chinese from the script

- **A PowerShell background job gets interrupted after about 2 min**, taking the `fdtd-engine` child
  process down with it. Symptoms: the log stops halfway, Python does not even get to write its final
  output file, `exit code 1`.
- ✅ Use the **Bash tool + `run_in_background`** instead: measured to run a full 3–10 min reliably
  (a 9.5 min run succeeded).
- ✅ A Python script should **write results to a UTF-8 file only and never `print()` Chinese**
  (encoding blows up on redirection).
- The three-part test for "did it actually compute": `layoutmode == 0`, `<project>_p0.log` exists,
  and the log contains `Completed N iterations`.

## 2. The correct simulation session sequence (the most expensive trap)

### 2.1 `run()` silently does nothing **in a newly created session** (the worst one)

**Symptom**: after building objects in a freshly created headless session, calling `f.run()` directly
**throws nothing, returns immediately, and computes nothing**. Every monitor then fails to produce
results:

```
lumapi.LumApiError: Can not find result 'E' in the result provider 'Rm'
```

`f.run()` returns `None`, with no error at all — **a textbook silent failure**.

#### How to tell (one-line diagnosis)

```python
f.eval("lm = layoutmode;")
print(f.getv("lm"))     # 1.0 = still in layout (nothing computed!) 0.0 = results exist
```

Combine with `nsim`: if it is still `0.0` afterwards, the simulation never ran.

#### Control experiment (within a single session, strictly verified)

| Sequence | `layoutmode` after run | Results available? |
|---|---|---|
| new session → `build` → `run` | **1.0** | ❌ No |
| new session → `build` → `save` → **new session load** → `run` | **0.0** | ✅ Yes |
| new session → `load` an existing `.fsp` → `run` | **0.0** | ✅ Yes |

#### ✅ The fix (you must copy this sequence)

```python
def run_sim(fdtd, fsp_path):
    fdtd.save(fsp_path)      # 1) write to disk
    fdtd.close()             # 2) close the old session
    f2 = lumapi.FDTD(hide=True)
    f2.load(fsp_path)        # 3) load -> enters a computable state
    f2.eval("switchtolayout;")
    f2.run()                 # 4) this time it really computes
    return f2
```

**One line to remember**: **in headless, a newly created session must go through save → load once
before `run` takes effect.**

#### Associated facts

- Changing **any** structural parameter pushes the session back into layout mode (`layoutmode = 1`):
  `you cannot modify most simulation objects while in analysis mode, use switchtolayout`
  → so in a "change parameter → run" loop, watch the mode after every change.
- **`run` itself has been verified fine**: `load`ing an existing `.fsp` and running immediately is
  normal (measured against `TiO2_nanobrick_unitcell.fsp`: `layoutmode=0.0` and the `T` result read
  back correctly).

### 2.2 After `load`ing an already-computed `.fsp` you **cannot `set` directly**

The **first wall** you hit when modifying someone else's project (or your own from a previous run):

```python
f = lumapi.FDTD(hide=True)
f.load(r"...\D1.fsp")
f.setnamed("source", "wavelength start", 800e-9)
#  => LumApiError: 'you cannot modify most simulation objects while in
#     analysis mode, use switchtolayout first or modify only the
#     analysis parameters of analysis groups'
```

**Cause**: if the `.fsp` was saved in an already-computed state (analysis mode), the structural,
source and monitor parameters are **all read-only**. Only an Analysis Group's analysis parameters
are exempt.

**Fix (copy this, three steps)**:

```python
f.load(path)
f.switchtolayout()          # ★ switch back to layout before changing anything
f.setnamed(...); f.setnamed(...)
f.save(path)                # what gets saved is the layout state
```

**How to tell**: `f.getnamed("FDTD","mesh accuracy")` reads a value fine but **any `set` raises the
message above** → that is analysis mode. Another way: `f.eval("lm = layoutmode;")` then `f.getv("lm")`
(1=layout / 0=analysis).

⚠️ Related: §2.1's "Associated facts" states that **changing any structural parameter returns the
session to layout mode** — that says "change it and you are in layout", **which is not the same as
"you may change anything freely while in layout"**. Both facts matter.

### 2.3 The standard verification loop (follow this order)

1. **Write the script** → run it as one block with `fdtd.eval(file_content)`, **not** as
   `fdtd.eval("one line at a time")`. Errors from evaluating strings directly are extremely
   misleading (see §2.1, the worst trap in the whole document).
2. **Read back and verify**: have the script print key parameters with `? "..."`, then read them back
   from the Python side with `fdtd.getv("varname")` to confirm.
3. **Locate errors**: when a block fails, bisect it (comment out the second half and re-run); do not guess.
4. To save time, run with **run_in_background** — a single simulation takes about 35–60 s.

### 2.4 The recommended session sequence (copy this, do not invent your own)

```python
def run_sim(fsp_path):
    f = open_fdtd()
    try:
        f.load(fsp_path)
        f.switchtolayout()          # ★ switch back to layout before changing parameters
        f.setnamed(...)             # change parameters (always use setnamed)
        f.save(fsp_path)
    finally:
        f.close()                   # deterministic release, not relying on the GC

    f2 = open_fdtd()
    try:
        f2.load(fsp_path)           # ★ load -> enters a computable state
        f2.eval("switchtolayout;")
        f2.run()                    # this time it really computes
        assert_ran(f2, fsp_path)
        return f2
    except BaseException:
        f2.close(); raise
```

## 3. Modelling and object manipulation

### 3.1 Recommended Python-side style: always use `setnamed`

**Prefer `setnamed` / `getnamed`; do not use `select` + `set`.** Confirmed by measurement:

```python
fdtd.addfdtd(dimension="3D", x=0, y=0, z=0,
             x_span=2e-6, y_span=2e-6, z_span=2e-6)   # keyword args to create an object: OK
fdtd.addrect(name="brick", x=0, y=0, z=0,
             x_span=120e-9, y_span=60e-9, z_span=600e-9)

fdtd.setnamed("FDTD", "mesh accuracy", 3)              # ✅ works without select
print(fdtd.getnamed("FDTD", "mesh accuracy"))          # ✅ reads back 3.0 for verification

fdtd.setnamed("brick", "x span", 150e-9)               # ✅ property names with spaces work too
```

#### ✅ `addrect(material=...)` keyword works (measured 2026-09-24, correcting a wrong call)

`addrect(name="brick", ..., material="TiO2 (Titanium Dioxide) - Siefke")`
**works perfectly**; the material name reads back identical.

⚠️ Do not conclude from `addfdtd(name=...)` reporting inactive that "no `add*` accepts keywords" —
**each `add*` has a different property table** and must be tested individually. Writing it in two steps
(`addrect` then `setnamed`) also works and is equivalent, but **one step is cleaner**.

### 3.2 The precise definition of "current object" (clarified by control experiment)

Older notes only said "it errors without select" — **that is not accurate**. The actual behaviour
depends on *who the current object is*:

> **`set` acts on the "current object". The current object is only changed by two things:
> ① calling `select(name)`; ② **creating an object** through the Python API (`addXxx()`), which makes
> the new object current. `setnamed` / `getnamed` do **not** change the current object.**

Control experiment (a brand-new session each time):

| Sequence | Bare `set("mesh accuracy", …)` | Reason |
|---|---|---|
| brand-new session, **no object created** | ❌ errors | no current object |
| `addfdtd(...)` → bare set | ✅ **succeeds** | `addfdtd` made FDTD the current object |
| `addrect(...)` → bare set of an FDTD property | ❌ errors | the current object is the rectangle, which has no such property |
| `setnamed("rectangle", …)` → bare set | ❌ errors | setnamed **does not change** the current object |
| `addfdtd(...)` + `select("FDTD")` → bare set | ✅ succeeds | the old official style |

The error text (note the extra space): `in set, the requested property 'mesh accuracy'  was not found`

**Why still always use `setnamed`**: a bare `set` depends on **global state that is invisible in the
code** (whoever was created or selected last). Its working right now is pure luck; insert one
`addrect` in between and everything collapses. `setnamed` puts the object name in the arguments, so
**reading the code tells you what is being modified** — a maintainability problem, not a
"does it run" problem.

### 3.3 A simulation can only have 1 FDTD solver region

```python
fdtd.addfdtd(dimension="3D", x_span=250e-9, y_span=250e-9, z_span=2e-6)
fdtd.addfdtd(dimension="3D", x_span=100e-9, y_span=100e-9, z_span=1e-6)
# → lumapi.LumApiError: 'Only 1 FDTD solver object is supported in the global object tree.'
```

So calling a wrapper like `build_region()` **a second time in the same session always throws**
(it throws; it does not fail silently). In a sweep, "re-build for every parameter point" without
clearing first will hit this.

**But you do not need to restart the session for it** — after deleting the old object the same session
can continue building (measured 2026-09-22):

| Operation | Measured result |
|---|---|
| `fdtd.select("FDTD"); fdtd.delete()` | ✅ deleting a single object works (`delete` = LSF's `delete;`, acting on the selection) |
| `addfdtd(...)` after clearing | ✅ works; the name is still `::model::FDTD` → **a sweep can reuse the same session** |
| `fdtd.deleteall()` | ⚠️ **unstable**: sometimes fine, sometimes throws `'in getid, no items are currently selected'` (depending on the selection state), but the objects **are still deleted** → do not use it to judge success or failure; wrap it in `try/except` |

⭐ **When the object tree is empty, `getObjectById("::model")` throws `LumApiError`** — so any code
that "reads the object tree" must be wrapped in `try/except`, or reading after deleting everything
will crash. (This is a real case of "property reads must be wrapped in exception handling"; it works
well as a teaching example.)

### 3.4 The return value of `add*()` is a `SimObject` (do not hard-code object names)

```python
r = fdtd.addfdtd(dimension="3D", x_span=250e-9)   # returns <lumapi.SimObject>
r._id.name                 # '::model::FDTD'   ← full path
r.dimension                # '3D'
r.x_span                   # 2.5e-07 (underscores map to "x span" automatically; both read and write)
```

So "create an object, then modify its properties" needs no object name at all.
Every `add*` in `fdtd.__dict__` is **generated dynamically at runtime** (`appCallWithConstructor` in
`lumapi.py`); that is also why `dir(fdtd)` lists 583 commands — they are not hand-written methods but
automatic wrappers around LSF commands.

**Attribute-style access** (nicer to read):

```python
obj = fdtd.getObjectById("::model::brick")   # full path
obj = fdtd.getObjectById("brick")            # ✅ short names work too, resolved to ::model::brick
obj.x                                   # plain attributes via dot access
getattr(obj, "x span")                  # attributes with spaces via getattr
obj.y = 99e-9                           # writes work as well
```

### 3.5 Attribute-style access == `setnamed` (equivalence verified)

`SimObject` overloads `__getattr__`/`__setattr__` and **converts underscores to spaces automatically**,
so `obj.mesh_accuracy`, `obj["mesh accuracy"]` and `getnamed("obj","mesh accuracy")` are the same thing:

```python
o = fdtd.getObjectById("::model::FDTD")
o.mesh_accuracy                 # read → 2.0 (the default really is 2)
o.mesh_accuracy = 4             # write
fdtd.getnamed("FDTD", "mesh accuracy")   # → 4.0  ✅ the setnamed side reads the same value
```

**`dir(obj)` returns the object's complete property-name list** (with the original spaces) → this is
**the easiest way to enumerate settable properties**, much cleaner than `select(); ?set;`:

```python
[a for a in dir(o) if "span" in a]
# → ['x span', 'y span', 'z span', 'global monitor wavelength span', ...]
```

Other measured details:

- An object's **full path** is the private attribute `obj._id.name` (e.g. `'::model::FDTD'`); there is
  also `_id.index`. **There is no public `getName()`/`getPath()`** — calling one raises
  `AttributeError: 'SimObject' object has no attribute 'getName'`
- `getnamed` / `getattr` return a **float** (`3` → `3.0`). `== 3` still holds, but it prints as `3.0`
- Position keywords like `x=0, y=0, z=0` passed by the user **are accepted normally** and read back as `0.0`

**Conclusion**: `setnamed(object, property, value)` sidesteps the number-one trap of "`set` only acts
on the current selection" in one move, and should be used **universally** in training and library code.
`select` + `set` is only the only option when you must write a LSF script (`.lsf`).

`setnamed` / `getnamed` / `getObjectById` / `getObjectBySelection` / `getAllSelectedObjects`
all appear in `dir(fdtd)` and carry official docstrings, so `help()` works directly.

### 3.6 `addrect`'s `rotation 1/2/3` is inactive → use `addpoly`

(Measured 2026-09-24, hit while reproducing the paper's 45° gold brick)

`addrect`'s property table **does list** `rotation 1/2/3` and reads back `0.0`,
but any `set` reports:

```
in setnamed, the requested property 'rotation 1' is inactive
```

**Both `Rectangle` and `structure group` are inactive** → the "set a rotation angle on a rectangle"
route is a dead end.

#### ✅ The only clean way: `addpoly` + compute the rotated vertices yourself

```python
import numpy as np, math

def rotated_rect_vertices(l1, l2, theta_deg):
    th = math.radians(theta_deg); c, s = math.cos(th), math.sin(th)
    pts = []
    for u, v in [(+l1/2, +l2/2), (-l1/2, +l2/2), (-l1/2, -l2/2), (+l1/2, -l2/2)]:
        pts.append((u*c - v*s, u*s + v*c))
    pts.append(pts[0])                    # close the loop
    return np.array(pts, dtype=float)     # ★ must be an (N,2) 2-D matrix

f.addpoly(name="brick")
f.setnamed("brick", "vertices", rotated_rect_vertices(390e-9, 165e-9, 45))
f.setnamed("brick", "z", 150e-9)
f.setnamed("brick", "z span", 80e-9)
```

#### ⚠️ The `vertices` data-format trap (three shapes, only one works)

| What you pass | Result |
|---|---|
| a Python `list` | ❌ `wrong type for the property 'vertices'  Expected type is: Matrix` |
| a numpy **1-D** `(10,)` flattened array | ❌ `not acceptable ... incorrect dimensions` |
| a numpy **2-D** `(5, 2)` array | ✅ works |

**You must pass an `(N, 2)` 2-D numpy array**, repeating the first point at the end to close the shape.
`addpoly` has 30 properties (fewer than rect, missing `x/y span`, plus `vertices`).

### 3.7 Custom materials: `addmaterial("<model type>")`

**The single most important thing to understand**: `addmaterial()`'s argument is a **model type**,
not a material name!
```
addmaterial("Au_Drude")      -> ❌ 'Failed to create material of type Au_Drude.'
addmaterial("Sampled data")  -> ✅ returns a temporary name (e.g. 'New material 1'); rename with setmaterial
```

#### ✅ Recipe A: constant-index, lossless dielectric (e.g. the paper's SiO₂ n=1.45)
```python
t = f.addmaterial("(n,k) Material")
f.setmaterial(t, "name", "SiO2_paper")
f.setmaterial("SiO2_paper", {"Refractive Index": 1.45,        # a dict can set several properties at once
                             "Imaginary Refractive Index": 0.0})
# measured: reads back n@532nm = 1.4500 + 0.0000i  ✅
```

#### ✅ Recipe B: analytic Drude metal (e.g. the paper's Au)
**Do not** gamble on the built-in Drude model's unit conventions; **compute the complex permittivity
yourself and feed it as sampled data — the result is fully under your control**.
```python
C0 = 299792458.0
WP, WD, EPS_INF = 1.37e16, 1.224e14, 1.0     # paper: Au Drude (rad/s)

def drude_eps(lam_m):
    w = 2*np.pi*C0/lam_m
    return EPS_INF - WP**2 / (w**2 + 1j*WD*w)   # exp(-iωt) convention, Im>0 = loss

lams = np.linspace(400e-9, 2500e-9, 400)        # ★ cover the simulation band with margin
eps  = drude_eps(lams)
t = f.addmaterial("Sampled data")
f.setmaterial(t, "name", "Au_Drude")
f.setmaterial("Au_Drude", "max coefficients", 6)
f.setmaterial("Au_Drude", "sampled data", np.column_stack([C0/lams, eps]))
#                ↑ first column must be **frequency (Hz)**, second column the **complex permittivity**;
#                  a complex numpy array can be passed directly
```
**Measured verification** (mandatory): at `@1000nm` it reads back `0.2379 + 7.1925i`, versus the hand
calculation `eps=-51.676+3.423i → n=0.2379+7.1925i` — **0.00% deviation**; point-by-point agreement at
800/1000/1200/1600 nm.

#### ⚠️ Three things you must know
1. **`getindex` returns the "raw data", not the value the solver actually uses.**
   FDTD additionally performs a rational-function fit (`getfdtdindex` reflects the fit, but measured it
   requires **≥4 arguments** and its signature is not yet determined). → If you suspect the fit has
   drifted, raise `max coefficients` (6→12→25) and see whether the result changes.
2. **Custom materials are saved inside the `.fsp`** (measured: after save → load in a new session the
   material is still there with unchanged values) → **the save/load workflow does not need to rebuild
   materials**. To be safe you may still probe once after loading (does `getindex` succeed) before
   deciding whether to rebuild.
3. **Material names must be exact**; a wrong name makes the error **list every valid material name**
   → usable as a way to "enumerate the material library".

## 4. Property read/write

### 4.1 `setname` / `getname` **really exist** (the nastiest class of trap)

**This is the nastiest class of trap hit on this machine; memorise it.**

`dir(fdtd)` measured (filtering for entries containing `name`):

```
['currentfilename','currentscriptname','filebasename',
 'getname','getnamed','getnamednumber','querynamed','setname','setnamed']
```

`setname` and `getname` — **the two without the `d` genuinely exist** — so writing them as if they
were typos for `setnamed`/`getnamed` does **not** give you a clean `NameError`; it throws a completely
unrelated `LumApiError`:

| Mistake (missing `d`) | Measured error | What the error implies |
|---|---|---|
| `fdtd.setname("FDTD","mesh accuracy",3)` | `LumApiError: 'wrong number of arguments passed to setname'` | "wrong argument count" — **it never mentions you called the wrong function** |
| `fdtd.getname("FDTD","x span")` | `LumApiError: 'getname method does not accept arguments'` | same |

The real semantics:

| Function | Signature | Purpose |
|---|---|---|
| `setname(new_name)` | 1 arg | rename the **current object** |
| `getname()` | 0 args | get the **current object's name** |
| `setnamed(obj, prop, value)` | 3 args | set obj's prop to value ✅ |
| `getnamed(obj, prop)` | 2 args | get obj's prop value ✅ |

**Memory hook**: the one with the **d** is "**d**esignated" — you **designate** the object in the
arguments. The ones without a d always act on the "current object" and only deal with its **name**.

⚠️ A general troubleshooting principle follows: **when an error says "wrong number of arguments",
suspect the function name first; do not rush to change the arguments.**

### 4.2 `getnamed`'s three signatures — do not mix them up

| Form | Returns | Use |
|---|---|---|
| `getnamed(name)` | **a string** (property names separated by `\n`) | get the "property list" ← **not a dict!** |
| `getnamed(name, prop)` | a single property value | get a value (most common; `getnamed("FDTD","x span")` always works) |
| `getattr(obj, prop)` | a single property value | for objects obtained from `getObjectById` / `getChildren()` |

⚠️ Traps:
- `getnamed(name)` returns a **long string**, which looks like mojibake or gets truncated when printed.
  Parse it correctly: `[x.strip() for x in s.split("\n") if x.strip()]`.
- **For `Mesh` / `PlaneSource` / `DFTMonitor`, `getnamed(objectname)` reports
  `no items matching the name 'xxx' can be found`** → use `dir(obj)` + `getattr` instead.
  (`Rectangle` / `FDTD` / `Analysis Group` work fine with `getnamed`.)

### 4.3 `getv()` cannot read a variable that was never created

```python
fdtd.getv("layoutmode")
# → lumapi.LumApiError: 'Failed to get variable'
```

**Real cause**: `getv(name)` can only read **script variables already created on the LSF side**; it
cannot read a system state quantity directly.

```python
fdtd.eval("lm = layoutmode;")   # ← assign first to create the variable
lm = fdtd.getv("lm")            # ← then read ✅
```

General rule: **to read any system quantity, first `eval("x = <system quantity>;")`, then `getv("x")`.**

### 4.4 A plane-wave source's x/y span is a **derived property** and can be stretched past the period by a centre offset

Measured (`d2_perfectCross.fsp`, 2026-09-30):

- The source's `x span` = **`2 * max(|FDTD x min|, |FDTD x max|)`** (same for y), derived automatically
  from the FDTD region.
- This project's FDTD centre is offset (`x = −6.227 nm`, `y = −59.43 nm`) → the source span is stretched
  to **2.0125 × 2.1189 µm**, while the period is only 2 µm.
- `setnamed("source","x span", 2e-6)` **reads back as 2e-6 in the current session** (you think it
  worked), but **after save and reload it reverts to 2.0125e-6** — derived properties are recomputed on
  save/reload.
- ✅ Fix: **set the FDTD's `x` / `y` to 0**, then save + reload to verify.
  The course's original 042 has its FDTD centre at 0, which is why its source span is exactly 2×2 µm —
  this is precisely why "two projects with apparently identical configuration give one normal and one
  abnormal result".
- Consequence: the source extends beyond the simulation region → wrong injected power → every monitor
  reading is garbage.

## 5. Results and data extraction

### 5.1 Result-array key names (easy to get wrong)

When reading complex amplitudes from an `addprofile` point monitor, **there is no `E["Ex"]` key on the
Python side**:

```python
E = fdtd.getresult("R_pt", "E")
E.keys()          # ['lambda','f','x','y','z','E','Lumerical_dataset']
E["E"].shape      # (1, 1, 1, N_freq, 3)
#                    x  y  z   ↑frequency   ↑last index = [Ex, Ey, Ez]

comp = np.array(E["E"])[0, 0, 0]   # (N, 3)
ex, ey = comp[:, 0], comp[:, 1]    # ← extract components this way
```

⚠️ Do not write `E["Ex"]` → `KeyError`.
(For comparison: on the LSF side `getresult("R_pt")` does **list** the `Ex`/`Ey`/`Ez` field names —
that is the LSF dataset view; the Python side receives a single array.)

**A general way to discover available keys** (saves time):
```python
E = fdtd.getresult("monitorName", "E")
print(list(E.keys()))
for k in E.keys():
    print(k, np.array(E[k]).shape)
```

### 5.2 `getindex()`'s argument is **frequency (Hz)**, not wavelength

The sneakiest trap when looking up a material's refractive index: **neither form errors, and both
"successfully return a number"**.

```python
C0 = 299792458.0

fdtd.getindex("TiO2 (Titanium Dioxide) - Siefke", 532e-9)      # → 5.99   ❌ absurd
fdtd.getindex("TiO2 (Titanium Dioxide) - Siefke", C0 / 532e-9) # → 2.45   ✅ correct
```

**Real cause**: `getindex` takes **frequency**. Passing `532e-9` is interpreted as **5.32e-7 Hz** —
tens of orders of magnitude below the material data's lower bound → Lumerical **extrapolates** a ghost
value. Passing something on the order of a wavelength, like 1.4e-6, extrapolates just the same.

**The only reliable way to catch it**: **compare against a literature value**.
(TiO₂ thin film n@550nm ≈ 2.41, source refractiveindex.info / Siefke 2016; if it disagrees, this is
the trap.)

#### Call forms
- The frequency argument must be a **matrix**: `f.getindex(mat_name, np.array([[freq]]))` → returns `[[n+ik]]`
- The material name must be the **full library name** (e.g. `"TiO2 (Titanium Dioxide) - Siefke"`);
  the abbreviation `"TiO2 - Siefke"` is rejected and **all valid material names are listed** (that
  error message is itself useful)
- When the material name is inexact, the error prints **every available material** → usable as a way to
  "enumerate the material library"

#### Four measured TiO₂ datasets (400–700 nm, values are n)
| Material | 400 | 450 | 532 | 600 | 700 |
|---|---|---|---|---|---|
| Siefke | 2.68 | 2.55 | **2.45** | 2.40 | 2.37 |
| Devore | 2.97 | 2.81 | 2.67 | 2.60 | 2.55 |
| Kischkat | 2.70 | 2.66 | 2.61 | 2.58 | 2.55 |
| Sarkar | 2.34 | 2.25 | 2.17 | 2.14 | 2.11 |

The four datasets differ by **~15%** → **do not mix material data sources**; confirm with the other
party which one was chosen.

### 5.3 An Analysis Group's script and internal monitors **are both readable**

Older notes said "objects inside an Analysis Group cannot be reached (`getChildren()` excludes them,
`groupscope()` fails)" — **that is not accurate**. Measured:

```python
ag = f.getObjectById("abs_cross")
ag.type                                # 'Analysis Group'
ag.enabled                             # 0.0 / 1.0  ← whether this analysis group takes part in the simulation
ag.x_span, ag.z_span                   # the group's own input properties (the ones in the GUI)
ag.getChildren()                       # ✅ returns internal children: field(DFT monitor) / index(IndexMonitor)
getattr(ag, "analysis script")         # ✅ the complete script source (str)
getattr(ag, "setup script")            # ✅
[n for n in dir(ag.results) ...]       # ✅ the result names this group declares, e.g. Pabs / Pabs_total
```

`getChildren()` **fails on leaf objects** (Rectangle / Mesh / Monitor), reporting
`The group scope can not be set properly.`; **group objects are in fact the only ones that recurse**.
→ To "read someone else's .fsp" you no longer have to guess the script with `fsp_strings.py` —
**read `.analysis script` directly**.
(Analysis group scripts are usually standard Lumerical library scripts; in this case
"Power absorbed (advanced)" and "Current charge density".)

#### Key lines of the standard library absorption group (Power absorbed (advanced)) — copy these when writing your own

```
Pabs_x = 0.5*eps0*W*(abs(Ex)^2*imag(eps_x));   # W = 2*pi*f；eps comes from the internal index monitor
Pabs = interp(Pabs_x,x+dx,...) + interp(Pabs_y,...) + interp(Pabs_z,...);  # per-component, then interpolate
SP   = sourcepower(f);  Pabs = Pabs/SP;        # normalise → dimensionless (absorbed power per m³ / source power)
Pabs_total = integrate2(Pabs,1:3,x,y,z);       # volume integral → absorbed fraction of that volume (function of f)
```

⚠️ When the group property **`z span = 0` the interior degenerates to a single xy plane** (measured:
the z dimension of the internal J has shape 1), and `integrate2(Pabs,1:3,...)`'s volume integral
**is physically meaningless** (it yields garbage of order 1e48).
Before using it, check that the x/y/z spans match the intended structure.
⚠️ When an analysis group has `enabled = 0` it **does not run at all**, and its results cannot be
retrieved anywhere (it reports
`Can not find result 'Pabs_total' in the result provider 'xxx'`).

### 5.4 The A in O&S's "model script" comes from the **analysis script** on the `::model` root

(Control experiments 2026-09-30 / 10-01: `wide_angle.fsp` vs `wd_BFASK.fsp`)

**Background**: the "model" in FDTD's **Optimization & Sweep (O&S)** is the **root `::model` of the
object tree**. It carries two script properties:

```python
root = f.getObjectById("::model")
root["setup script"]      # runs before the simulation: defines the parameterised model
root["analysis script"]   # runs afterwards: computes results — the <name> in matrixdataset("<name>") is the result name seen in O&S
```

**The criterion**: what O&S can show and whether right-clicking model offers Visualize depends on
**whether the root carries a matching result dataset**:

```python
[n for n in dir(root.results) if not n.startswith("_")]
# wide_angle.fsp  -> ['A']   ← a result named "A" exists → O&S lists A and Visualize is available
# wd_BFASK.fsp    -> ['']    ← no results at all → no A in O&S, right-click model has no Visualize
```

**Item-by-item comparison (measured)**:

| Item | `wide_angle.fsp` (has A) | `wd_BFASK.fsp` (no A) |
|---|---|---|
| root `setup script` | empty | ❌ the whole "compute A" block was put here (**wrong slot**) |
| root `analysis script` | computes A, outputs `matrixdataset("A")` | computes A, but outputs `matrixdataset("Absorption")` ← **the name was changed** |
| root `results` | `['A']` | `['']` (empty) |
| is there an `A` object in the tree | no | an extra `A` **Analysis Group** (redundant) |

**Conclusion**: the result name = the name in `matrixdataset("<name>")` inside the `analysis script`.
Putting the code that computes A into the **`setup script`** is wrong — setup runs before the
simulation and its output is not collected as a result; it must go into the **`analysis script`**, and
the dataset name must match the result name you expect.

⚠️ **Two incidental traps (measured this time)**:

1. That redundant `A` **Analysis Group** makes `runanalysis` **fail entirely**:
   `in runanalysis: one or more analysis objects encountered errors`;
   **delete it and `runanalysis` immediately recovers**.
   Real cause: the `getresult("R","T")` inside the analysis group is constrained by **group scope** and
   cannot find monitors outside the group.
2. `runanalysis()` does **not** execute the analysis script on the root `::model`
   (measured: after deleting the A group `runanalysis` succeeded, but the root `results` stayed empty).
   → the root script is triggered by **running O&S** (`runsweep`), **not** by `runanalysis`.

**Unverified boundary** (flagged per the §8.6 convention):
- *"Running O&S once re-binds `A` back onto the root"* — **not directly reproduced**.
  In headless, `addsweep` + `runsweep` did start a 30-point sweep (4 points completed), but in the
  per-point `.fsp` the root `results` stayed empty; my reading is that the sweep's result registration
  was not configured. **This conclusion awaits confirmation in the GUI**; do not treat it as
  established fact.

## 6. Resources, performance and boundary conditions

### 6.1 "Time remaining is unusually long" → check the mesh size first

**Iron law: the root cause of long runtimes is almost always mesh size, not an inadequate CPU/GPU.**

#### Three-step triage (under 1 minute every time)

**Step 1: read four numbers from the log.**

Search `*_p0.log` for these lines:

| Log line | Meaning | Healthy range |
|---|---|---|
| `Simulation size in gridpoints: A x B x C` | **mesh size (the primary scene)** | 10⁵ – 10⁶ |
| `Estimate of memory required: X GiB` | memory requirement | < 80% of VRAM/RAM |
| `Starting N total iterations` | total iterations | 10⁴ – 10⁵ |
| `Max time remaining` | estimated time remaining | minutes |

**Step 2: back out the mesh step and cross-check via two independent paths.**

```python
# Path A: back out from dt (in the log, "Elapsed simulation time" with only 1 step = dt)
dz = dt * 2 * c        # c = 299792458

# Path B: compute directly from the mesh dimensions
dz = z_span / C        # C comes from "A x B x C"
```

If both paths agree → the mesh really is that fine, **this is not an estimation error**.

**Step 3: check λ_min (the shortest wavelength).**

Lumerical uses `λ_min` to pick the mesh density automatically: `dz ≈ λ_min / cells_per_wl / n`.
So **a wrong wavelength range cascades into the mesh, dt and iteration count**.

| mesh accuracy | cells per wavelength | relative cost |
|---|---|---|
| 1 | 10 | 1× |
| 2 (default) | 14 | ~2× |
| 3 | 18 | ~3.5× |
| 4 | 22 | ~6× |
| 5 | 26 | ~10× |
| 6 | 30 | ~15× |

#### ★ The most frequent numerical mistake: wavelength is in metres

| Target | Correct | Wrong |
|---|---|---|
| Near-IR 800 nm | `800e-9` or `8e-7` | ~~`8e-9`~~, ~~`800e-12`~~ |
| Visible 532 nm | `532e-9` or `5.32e-7` | ~~`532e-6`~~ |
| UV mis-entry | — | `1e-7` (=100 nm! the classic "100nm" slip) |

**Self-check mnemonic**: right after writing it, multiply by 10⁹ in your head to get nm and check the
order of magnitude.

#### ★ Do not raise metal accuracy via the global mesh accuracy

Each +1 on `mesh accuracy` multiplies the grid count by roughly 1.5–2 and memory by roughly 3–8.
The correct approach for metal structures (skin depth ~25 nm):

```
addmesh a local mesh override region covering the metal layer
  -> "dx"/"dy"/"dz" = 2–5 nm
  -> keep the rest of the domain on the coarse ma=2 grid
```

**Global ma is only a floor for the whole domain; local accuracy belongs to the override region.**

#### Real case (2026-09-27, D1.fsp)

| Item | Wrong config | Correct config |
|---|---|---|
| `wavelength start` | `1e-7` (100 nm, UV!) | `8e-7` (800 nm) |
| `wavelength stop` | `9e-7` | `1.6e-6` |
| `mesh accuracy` | `6` | `2` |

Consequence: mesh `254×245×1038` (6.46×10⁷ gridpoints), peak memory 11.1 GiB (the card has only 8 GB),
dt = 3.9×10⁻¹⁸ s, 52.7 s for a single step, estimated **2939 hours**.
Compare a normal project: `41×71×36` (1.05×10⁵ gridpoints), 0.125 GiB, **49.7 s for 8580 steps**.
**A 616× difference in problem size.**

#### Additional GPU warning (metals + single precision)

When this line appears in the log, be wary of GPU solver stability:

```
WARNING: 0 < permittivity < 1, EM fields may diverge if timestep for GPU simulation is too large!
```

This is the **divergence risk** of dispersive metals under GPU single precision. Two possible fixes:
- `dt stability factor` 0.99 → **0.95** (trade speed for stability)
- or **switch to CPU multiprocessing** (`-t 8` / `num cpu=8`) to get it running, then move back to GPU for speed

### 6.2 The GPU engine **cannot handle non-ASCII paths** (2×2 control)

**Symptom**: Job Manager reports `Job Error`, Progress stuck at **0%**, and the Job Details popup shows
a string of **mojibake**.

The engine log (`<project>_p0.log`) holds the original text on its last line:

```
ERROR: 在多字节的目标代码页中，没有此 Unicode 字符可以映射到的字符。
```
(the message is Chinese: "in the multi-byte target code page, no mapping exists for this Unicode character")

= Windows error code **1113 `ERROR_NO_UNICODE_TRANSLATION`**.
The mojibake in the Job Manager popup **is this Chinese message rendered with the wrong encoding** (the
`Enemal` at the start of the popup's `Enemal(process 0)` is the hostname).
→ **Always trust `_p0.log`, never the Job Manager popup.**

**Where it crashes in the log** (crucial — instantly recognisable):

```
Starting 77813 total iterations
Detected GPU 0: NVIDIA GeForce RTX 3070 Laptop GPU (...)
Using datatype: real32
ERROR: 在多字节的目标代码页中，...          <-- right here
```

That is: **modelling and initialisation all succeed, and the crash happens at the instant the problem is
handed to the GPU kernel**. So the first 70 lines of the log are perfectly normal and the mesh size is
normal too — **only the last line blows up**.

#### Control experiment (the same `.fsp`, the same `-gpu -t 8`)

| Directory | Filename | Result |
|---|---|---|
| ASCII | ASCII | ✅ completes |
| Chinese | ASCII | ❌ crashes |
| Chinese (with spaces) | ASCII | ❌ crashes |
| ASCII (with spaces) | ASCII | ✅ completes |
| ASCII | **Chinese** | ❌ crashes |
| Chinese | ASCII (**switched to the `fdtd-engine-msmpi.exe` CPU engine**) | ✅ completes (but ~14× slower) |

**Conclusion**:
- **Spaces are irrelevant** (an ASCII path with spaces works fine).
- **If the path contains any non-ASCII character — directory name or filename, either counts — the GPU
  engine always crashes.**
- The CPU engine `fdtd-engine-msmpi.exe` does **not** have this problem, which is the sole evidence that
  "the fault lies in this particular binary".

#### ✅ The fix (copy this)

Before running, **copy the `.fsp` to a pure-ASCII path**, then `load`/`run`, or hand it to the Job Manager.

```python
try:
    path.encode("ascii")        # a path that will crash throws here
except UnicodeEncodeError:
    print("path contains non-ASCII -> the GPU engine will always crash")
```

Ready-made tool: `F:\Lumercial_WS\scripts\z_ascii_work.py` (copies an entire Chinese-named course
directory to `F:\Lumercial_WS\projects\L0NN\`, automatically renames Chinese filenames to
`p01`/`p02`…, and generates `_name_map.json` + a `README.md` old→new table).

#### ⚠️ Two honest boundaries

1. **"Does headless `f.run()` also fear Chinese paths?" — unproven.** I tried an ASCII and a Chinese case;
   both returned in 0.2 s with `layoutmode` still 1.0 and **neither produced a `_p0.log`**
   (= the engine never started), so that control run was pre-empted by "`run()` silently does nothing",
   and the experiment is **inconclusive**. Circumstantial evidence: the earlier 042 scripts
   (`z_042_abs_run*.py`) all copied the source to `F:\Lumercial_WS\results\042_abs_*.fsp` (ASCII)
   before `load`ing. To be safe: **whichever route you take, use an ASCII path.**
2. **The criterion should be upgraded**: besides `layoutmode` (1.0 = not computed / 0.0 = computed),
   also confirm **whether `<project>_p0.log` was created**.
   `run()` returning instantly + no `_p0.log` = the engine was never launched at all (independent of path).

### 6.3 Controlling CPU / GPU from a script (including the `setresource` trap)

The `FDTD` object has **no** `use gpu` property (`setnamed` reports `was not found`).
Resources go through a separate API, accessing solver `'FDTD'`'s resource entries **by index**:

```python
f.eval("xv = getresource('FDTD',1,'device type');"); f.getv("xv")   # read
f.eval("setresource('FDTD',2,'active',false);")                     # disable one resource
```

Readable fields (`f.eval("xr = getresource('FDTD',1);"); f.getv("xr")` lists them all):
`active, name, hostname, processes, threads, capacity, device type,`
`mpi * / solver * / scheduler command / submission script / additional environment variables`

Two measured resources on this machine:

| # | processes | threads | Notes |
|---|---|---|---|
| 1 | 8 | 1 | CPU multiprocessing (matches the log line `processors are distributed as: 2x2x2`) |
| 2 | 1 | 8 | selected automatically → **uses the GPU** (log: `Detected GPU 0 ... Using datatype: real32`) |

**Why this must be managed**: the GPU is `real32` single precision, and with a Drude metal
(0<Re ε<1) the log shows
`WARNING: 0 < permittivity < 1, EM fields may diverge ...`,
and measured it **diverges after 404 steps with `ERROR: Early termination of simulation, the
electromagnetic fields are diverging.`** → all monitor results turn into 0/garbage.
**This is an "error that does not report as an error"**: seeing only `R = 0.0000` makes it very easy to
misdiagnose a wrong structure or normalisation, when in fact the simulation never succeeded.

**The only verified effective measure**: `dt stability factor` 0.99 → **0.95**
(measured: turned a 404-step divergence into a completed 8777-step run; but real32 precision remains
questionable, and non-physical values — layer absorption summing above 1 — did occur).

#### ⭐⭐⭐⭐⭐ `setresource` **persistently** corrupts the global resource config → the GUI pops up "no active GPU resources" (corrected 2026-09-30)

**Remember this first**: `setresource(...)` changes **not this session** but the global resource
configuration file:

```
C:\Users\<user>\AppData\Roaming\Lumerical\FDTD Solutions.ini   →  the [jobmanager] section
```

Key entries (plain text, directly readable/editable; **back up first**):

```
[jobmanager]
FDTD\GPU-mode=true|false      # master switch: do FDTD jobs use the GPU, or the selected CPU engine below
FDTD\SelectedCPUEngine=0      # when GPU-mode=false, which engine to use (0 = the first one)
FDTD_v2=<engines><engine>…</engine><engine>…</engine></engines>   # the XML for each resource
```

The engine XML fields are exactly those read by `getresource`:
`<nProc>` `<nThread>` `<active>` `<DeviceType>` `<bypassLocalMpi>` `<runType>` `<exePath>`.

The two resources on this machine (**original values**, once corrupted and then restored):

| # | DeviceType | nProc | nThread | exe | runType |
|---|---|---|---|---|---|
| 1 | CPU | 8 | 1 | `fdtd-engine-msmpi.exe` | Remote: Microsoft MPI |
| 2 | GPU | 1 | 8 | `fdtd-engine.exe` | Local Computer |

**The trap we hit (do not repeat)**: to force CPU execution, a script did
`setresource('FDTD',2,'device type','CPU')` + `setresource('FDTD',2,'active',false)`
and **never restored it**. Both resources became CPU type → clicking Run in the GUI immediately popped up:

> There are no active GPU resources in the Resource Configuration utility.

Because `FDTD\GPU-mode` was still `true` (jobs want a GPU) while no active GPU resource existed.
`setresource('FDTD',1,'mpi bypass on localhost',true)` persists the same way, and additionally crushed
resource #1's
`nProc` from 8 down to 1.

→ **Rule: if you change resources with `setresource`, you must restore the original values before
leaving and read them back to confirm.**
One-shot restore/switch script: `F:\Lumercial_WS\scripts\z_fix_gpu_res.py cpu|gpu`
(automatic backup + read-back verification, idempotent).

#### ✅ Running double-precision CPU headless: genuinely viable (measured 2026-09-30)

The previous edition's note that "switching to CPU headless fails silently" was a **misdiagnosis**.
The real cause was not MS-MPI failing to launch, but that **`GPU-mode` was still on**: jobs wanted a
GPU → no active GPU entry → `run()` became a no-op
(returned in 0.3 s, `layoutmode` stayed 1.0, **with no error**). In the GUI this shows as the popup above.

The correct procedure (both steps required):

1. `FDTD\GPU-mode=false`;
2. confirm `FDTD\SelectedCPUEngine=0` points at the `CPU / Remote: Microsoft MPI / nProc=8` engine
   (MS-MPI is installed on this machine: `C:\Program Files\Microsoft MPI\Bin\mpiexec.exe`).

**Verification (line-for-line identical to the control)**: running the course's original 042 project
headless produced a log identical to the author's own reference log:

| Item | Author's reference log | My CPU run |
|---|---|---|
| number of processors | 8 | 8 |
| processors are distributed as | 2x2x2 | 2x2x2 |
| Simulation size in gridpoints | 44 x 44 x 48 | 44 x 44 x 48 |
| Starting N total iterations | 21971 | 21971 |
| finishing | Completed 7039 iterations, 3.203782e-13s | same |

Runtime **31.9 s**, no `real32`, no diverging, and the physics is self-consistent
(`A=1-R-T` peaks at 0.820 @ 6.152 µm).
→ **headless CPU is fully usable**; there is no need to depend on the GUI, nor to force the GPU for
accuracy reasons.

#### The corresponding GUI entry (official documentation)

**The Resource Configuration window is on FDTD's `File` tab** (`File → Resource Configuration`).
Key points: make sure a GPU resource is in the list and `active`; `Device Type` can be `CPU` / `GPU` /
`GPU Custom` / `GPU N`. Script equivalent: `setresource("FDTD", 2, "device type", "GPU")`.

### 6.4 Periodic boundaries vs PML: not a change you can make "in passing"

For the same project, switching x/y from PML to Periodic **invalidates the whole R/T readout**:
measured `T = −0.73 ~ −0.31` (**negative**), with `A = 1−R−T` reaching 1.5.

**Criterion: when `R + |T| ≈ 1`, the T monitor is reading "−absorption", not transmission.**

To use periodic boundaries, first satisfy all of these hard conditions:
① FDTD `x = y = 0`; ② every "full-layer" structure (dielectric layer / backplane / substrate) has
x/y span = the period; ③ the source span therefore automatically equals the period (see §6.4 point (2));
④ monitor span ≤ the period.

Measured on this machine: even with ①–④ all satisfied, that project still gave non-physical readings →
**there is a further unexplained factor**; in that case **fall back to the PML route first** and get a
result that agrees.

The iron law is unchanged: **verify on a control structure whose answer is already known**. This
project's control = the course's original infrared absorber project (x/y = PML, CPU 8 processes,
44×44×48). In-repo copy: `packages\P01_Absorber_042\fsp\infrared_perfect_absorber.fsp`
(the original Chinese-named file lives outside the repo under `Classes\FDTD\课件\042*`):
measured **T ≈ −9e−5 (≈0), A = 0.8196 @ 6.152 µm**.

## 7. Verification methods and troubleshooting

### 7.1 Iron law: to judge whether a tool works, **run a control first**

A real lesson: `Testproject.fsp` is a **pure material-library project** (no geometry), and the probe read
**only 1 node**. I nearly misdiagnosed it as a broken tool and went off to fix it. Using
`blaze_grating.fsp` as a control → it read **12 nodes**, proving the tool was fine.

**Without a control experiment, you will spend two hours fixing something that is not broken.**

### 7.2 The standard control for reflection measurement: a "gold film only" reference structure

When measuring "structure reflectance", since you do not know what to expect, an odd value leaves you
unable to tell whether the **code is wrong** or the **physics is right**. The solution: **build a
reference structure whose answer is known**.

| Case | Structure | Known answer | Measured (this machine) | Conclusion |
|---|---|---|---|---|
| **mirror** | only a 150 nm gold film (a single mirror) | \|Ex\|≈1, \|Ey\|=0, R≤1 and flat | \|Ex\|=0.985, \|Ey\|=0.000, R=0.959–0.976, **0/201 points with R>1** | ✅ the normalisation chain is correct |
| full | the paper's complete three-layer structure | unknown (that is what we are measuring) | 73/141 points with R>1 | ❌ the problem is on the structure side |

**The value of this method**: it pins down "normalisation / source setup / monitor orientation / units"
in one shot. This time it was precisely what cleared normalisation of suspicion and narrowed the
investigation **from 4 hypotheses down to 2**.

**Corollary (reusable)**: if the reference structure is clean while the complete structure shows
non-physical values, **the problem must be in something specific to the target structure** — in this
case the 45°-rotated gold brick (mesh resolution / material fit).

### 7.3 Do not place monitors near the PML

The PML defaults to `pml layers = 8` with `auto scale pml parameters = 1` (thickness scales with the
mesh), and it eats a ring of space at both ends of the solver region. Here the solver region spans
z = −260→1100 nm, and moving the monitor to z=1040 nm **dropped it straight into the top PML**, making
results worse than before (points with R>1 went from 80 to 100).

**Fix**: **keep both the monitor and the structure at least a few hundred nm away from the PML.**
Better to widen the solver region's z span (the only cost is more gridpoints) than to have the monitor
hugging the PML. Conversely: **before moving a monitor, compute how far it is from the PML** — do not
move it blindly.

### 7.4 Measured v251 script traps (sorted by how often they bite)

| Trap | Symptom | Fix |
|---|---|---|
| **Passing wavelength instead of frequency to `getindex`** | no error, absurd value returned (TiO₂ → n=5.99) | pass Hz: `C0/lambda`; **check against a literature value** |
| **Reading `getv("layoutmode")` directly** | `LumApiError: 'Failed to get variable'` | `eval("lm = layoutmode;")` first, then `getv("lm")` |
| **`addfdtd(name="FDTD", ...)`** | `In 'addfdtd', 'name' property is inactive` | do not pass `name=` (the default name already is FDTD) |
| **Inexact material name** | error says value not acceptable | the error **lists every valid material name** → usable for enumeration |
| **Confusing `setname`/`getname` with `setnamed`/`getnamed`** | `LumApiError: 'wrong number of arguments passed to setname'` (**not** a NameError) | use only the `d` versions; see §4.1 |
| **Property names are case-insensitive** (measured 2026-09-24) | `"Mesh Accuracy"` and `"mesh accuracy"` **both work**; reads back `4.0` | ⚠️ **this is not a bug, do not "fix" it**; lowercase is merely a style preference |
| **`set` only acts on the current selection** | modifying an FDTD solver property errors with `the requested property '...' was not found` | ⭐ **prefer `setnamed("FDTD","mesh accuracy",3)`, no select needed at all**; only the old style needs `select("FDTD");` first |
| **The FDTD solver region cannot be renamed** | `set("name","FDTD")` → `the requested property 'name' is inactive` | delete it; the default name already is `"FDTD"` |
| **Dependent properties are inactive unless the master property is on** | `wavelength start/stop` gives the same inactive error | first `set("override global source settings",1)` |
| **`try/catch` is unavailable** | a syntax error even by itself, failing even when merely defined and never run | do not use it; rely on read-back verification at the end |
| **`save()` + `?` wrapped in a multi-line `if/else` blows up** | the whole block fails within 1 s with `Failed to evaluate code` | use comment switches instead of conditional blocks. Note that **a simple `if/else` itself is fine**; do not misjudge it as "else unsupported" |
| **`global monitor sample spacing` is a string** | passing a number has no effect; the value is `"uniform"` | control the sample count with `global monitor frequency points` |
| **Only 5 frequency points by default** | the sampling misses the design wavelength | set the monitor's wavelength grid explicitly, and **linearly interpolate to λ0** on extraction so results are decoupled from the grid |
| **Point monitor complex amplitude** | `\|E\|` carries a normalisation-baseline problem when you need phase/amplitude | with the source inside glass and the monitor in air, `T ≈ \|E\|²/n_substrate` |

**A general way to investigate inactive properties**: `select("objectname");` then `?set;` to print the
complete property table.

### 7.5 The root cause of the GUI repeatedly popping up "Save changes?"

**Symptom**: the GUI repeatedly asks you to save, and each answer creates another same-sized `.fsp` copy.

**Root cause**: if the script starts with `deleteall;`, it **clears the project currently open in the
GUI** and marks it "modified"; if the script only saves once at the end → any mid-way error leaves the
project permanently in the "modified" state.
Separately, `pwd=` in `FDTD Solutions.ini` is the working directory, and it shares a directory with the
script's output, so the two interfere easily.

**Fix**:

- When delivering a script you **must document the `deleteall` risk in the file header**, and recommend
  running it headless through Python
- Before running a script in the GUI, first `File → New` for a **blank** project; answer **Don't Save**
  to every popup
- Promote the save path to a variable at the top of the file for easy control

**To judge whether a batch of `.fsp` files are duplicate copies of the same project**: compare file
sizes. Saving the same project repeatedly under different names changes the size by only a few hundred
bytes (metadata); `stat -c '%y %s %n'` compares them quickly.

### 7.6 The shortest path to health-check an unfamiliar `.fsp`

1. Full dump (object tree + every property of every object);
2. `getindex(material, f)` to **look up the material's optical constants** and compare with the
   paper/literature values (do not trust the material name);
3. Find a project that is "isomorphic but known correct" and do a **three-way property diff**
   (original / known correct / my modification);
4. Only run on an **ASCII copy**; the original file is read-only.

### 7.7 `FlexNet Licensing error:-97,121` — the vendor daemon is down (GUI won't start)

**Symptom.** Launching the Lumerical GUI or any licensed module fails with:

```
Error: Failed to checkout feature 'lumerical_gui'
The desired vendor daemon is down.
Check the lmgrd log file, or try lmreread.
Vendor:Host: localhost
License path: 1055@localhost;
FlexNet Licensing error:-97,121
```

**What it actually means.** The license server is a two-process chain: `lmgrd` (the broker) plus
`ansyslmd` (the vendor daemon, which is the process that actually holds the `lumerical_*` features).
**-97 is not "the license server is down" — it is "the broker is up, the vendor daemon is dead."**
Do not touch the license file or reconfigure the client: nothing about the configuration is wrong.

**Diagnose (read-only, confirms the split within seconds):**

```bash
LM="F:/Lumercial/Shared Files/fnp/winx64/lmutil.exe"
"$LM" lmstat -c 1055@localhost -a | head -12
```

Healthy output looks like this; the two `UP` lines are the whole story:

```
 localhost: license server UP v11.19.5
Vendor daemon status (on <HOSTNAME>):
  ansyslmd: UP v11.19.5
```

Broken output (measured 2026-10-10) — note `lmgrd` is still `UP` while the vendor daemon is gone:

```
 localhost: license server UP v11.19.5
Vendor daemon status (on Enemal):
  ansyslmd: Network connect to THIS_HOST failed. (-95,378)
```

Cross-check with the process table: `tasklist | grep -iE "lmgrd|ansyslm"`. In the broken state
`lmgrd.exe` is present but `ansyslmd.exe` is missing. `ansyslmd.exe` **is expected to be a separate
process** — if it is absent, you have found the fault.

**Fix (the vendor daemon is restarted in place — this is what the error text means by `lmreread`):**

```bash
"$LM" lmreread -c 1055@localhost        # expect: "lmreread successful"
"$LM" lmstat  -c 1055@localhost -a | grep -iE "lumerical|ansyslmd"
```

Success looks like `ansyslmd: UP v11.19.5` plus the features being served:

```
Users of lumerical_gui:    (Total of 100 licenses issued;  Total of 0 licenses in use)
Users of lum_fdtd_gui:     (Total of 100 licenses issued;  Total of 0 licenses in use)
Users of lumerical_solve:  (Total of 100 licenses issued;  Total of 0 licenses in use)
```

No admin rights are needed for `lmreread`. If it reports failure, fall back to restarting the
Windows service (this one **does** need an elevated shell):

```
net stop "ANSYS, Inc. License Manager CVD"
net start "ANSYS, Inc. License Manager CVD"
```

**Why it happens (hypothesis, not yet reproduced deliberately).** The hostid in
`F:\Lumercial\Shared Files\Licensing\license_files\ansyslmd.lic` is bound to one specific MAC
address (`SERVER localhost 047c1636fd0f 1055` → this machine's **wired Realtek adapter**,
`04-7C-16-36-FD-0F`). That adapter was observed in the "media disconnected" state. If the adapter is
disabled, the driver is absent at boot, or the service starts before the network stack is ready, the
vendor daemon can fail its hostid check and die while `lmgrd` survives the same check. This is the
standard ANSYS boot-race failure mode.

**Prevention.**
- **Do not disable the wired Realtek Ethernet adapter in Device Manager** — the license is bound to
  its MAC. `VirtualBox/VMware/Radmin VPN` adapters are irrelevant to it.
- Set `ANSYS, Inc. License Manager CVD` to **Automatic (Delayed Start)** so it no longer races the
  network stack at boot.
- Keep a one-line repair at hand — this recurs after reboots.

**Do not "fix" it by re-running the licensing wizard, re-uploading the `.lic`, or changing the
license path.** Those steps rewrite a working configuration and add a second failure mode on top of
a five-second fix.

### 7.8 Reporting a license fault: what to capture

When escalating (to a supervisor or a forum), the useful payload is: the exact client error block,
`lmstat -a` output, `tasklist` filtered on `lmgrd|ansyslm`, the `SERVER` line of the `.lic`, and
`getmac` — that set distinguishes "broker down" from "vendor daemon down" from "hostid mismatch"
without another round trip.

## 8. `.fsp` inspection, tools and maintenance

### 8.1 `.fsp` inspection methods (two routes, both required)

`.fsp` is a private binary format, **impossible to author by hand**, and can only be produced by
scripting. There are two complementary routes for reading it:

#### Route 1: the lumapi object tree (gets you property values)

```python
fdtd.load(path)
root = fdtd.getObjectById("::model")        # ✅ the only reliable entry point
root.getChildren()                          # ✅ recurse to walk the geometry object tree
```

✔️ Obtainable: object names / types / dimensions / materials / monitor types / results list

**APIs measured as ineffective on v251 (do not waste time)**:

| API | Measured behaviour |
|---|---|
| `getobjectlist()` | on the Python side **returns only `['::model::']`**; does not expand the subtree |
| `materialexists(name)` | ★ **returns `0.0` for any input** (even garbage) → not a membership test |
| `exportmaterialdb()` | `Failed to evaluate code`; unavailable on v251 |
| `getindex(m, base)` | cannot take a string; needs a frequency **matrix**: `getindex(matrix_f, sim_mat, base_mat)` |
| `groupscope("::model::groupname")` | **fails** → an Analysis Group's **internal objects** remain unreachable (⚠️ the only gap not yet cracked) |

#### Route 2: string extraction as a fallback (gets you material names / analysis group scripts)

Material names and the plain-text scripts inside Analysis Groups are only reachable this way.
Already built into a tool:
**`F:\Lumercial_WS\scripts\fsp_strings.py`** (narrow-char + UTF-16LE bidirectional extraction + material-name heuristics).

```bash
python scripts/fsp_strings.py <project.fsp> --materials
python scripts/fsp_strings.py <project.fsp> --grep Palik,CRC,E7
```

⚠️ Material names may be **truncated** in the binary (e.g. `E7 - Li` is really `E7 - Liquid Crystal`);
grep by keyword and merge manually — do not use the result as a complete name.

### 8.2 What the official example library contains (do not expect it to be a course)

`<install>\Resources\fdtd-library\`: **129 `.fsp` files**, flat in a single directory, **mostly geometry
primitive demos** (`coated_sphere`/`gear_cyl`/various `*_extpoly`/photonic crystals/waveguides).

Only 5 relate to periodic structures/metasurfaces, but those happen to be the most worth reading first:
`grating_transmission` (closest to the unit-cell paradigm), `grating_s_params`, `blaze_grating`,
`bragg_grating`, `grating_coupler`.
**The real metasurface examples live in the online Application Gallery (optics.ansys.com), not locally.**

### 8.3 Delivered probe tools

- **`F:\Lumercial_WS\scripts\lumapi_probe.py`** — object-tree probing (`--results` / `--all-props` / `--json`)
- **`F:\Lumercial_WS\scripts\fsp_strings.py`** — binary string extraction (`--materials` / `--grep`)

### 8.4 Ready-to-reuse checklist (turning lessons into code)

#### (1) Session factory: session creation must retry

```python
def open_fdtd(n=8, delay=6):
    for i in range(n):
        try:
            return lumapi.FDTD(hide=True)
        except Exception as e:
            hint = "port TIME_WAIT" if "bind socket" in str(e) else str(e)[:80]
            print("  [session retry %d/%d] %s" % (i + 1, n, hint)); time.sleep(delay)
    raise RuntimeError("session creation failed repeatedly")
```

#### (2) The "did it actually compute" three-part test — check after every run

```python
def assert_ran(fdtd, fsp_path, min_iters=1):
    """Only if all three criteria pass did it really compute. Any failure raises; never treat garbage as a result."""
    import os
    # (1) mode: 0.0 = results computed; 1.0 = still in layout (= nothing computed)
    fdtd.eval("lm = layoutmode;")
    lm = fdtd.getv("lm")
    assert lm == 0.0, "layoutmode=%.1f -> run() silently did nothing (check the save->load sequence)" % lm
    # (2) log exists: proves the engine really was launched
    log = os.path.splitext(fsp_path)[0] + "_p0.log"
    assert os.path.exists(log), "no %s -> the engine never started (non-ASCII path?)" % log
    # (3) iteration count: proves it ran to completion
    txt = open(log, encoding="utf-8", errors="replace").read()
    assert "Completed" in txt, "no 'Completed' in the log -> it died midway"
    for line in txt.splitlines():
        if "Simulation size in gridpoints" in line:
            print("  mesh:", line.split(":")[-1].strip())
        if "Diverging" in line or "diverging" in line:
            raise RuntimeError("fields diverged! step down dt stability factor or switch to CPU")
    return True
```

#### (3) Path ASCII gate — pass this before running

```python
def ascii_gate(p):
    """True means safe. False means you must copy to an ASCII path before running."""
    try:
        str(p).encode("ascii"); return True
    except UnicodeEncodeError:
        print("[ASCII gate] path contains non-ASCII -> the GPU engine will always crash:", p)
        return False
```

#### (4) Mesh health check — run this first when "time remaining is unusually long"

```python
def mesh_report(log_path):
    """Extract 4 numbers from _p0.log to judge whether the magnitudes are healthy."""
    keys = ["Simulation size in gridpoints", "Estimate of memory required",
            "Starting", "Max time remaining"]
    for line in open(log_path, encoding="utf-8", errors="replace"):
        if any(k in line for k in keys):
            print("  ", line.strip())
    # healthy ranges: mesh 10^5-10^6 / memory < 80% VRAM / iterations 10^4-10^5 / remaining: minutes
```

#### (5) Property reading: correct use of the three signatures

```python
# (1) property list (returns a long string, not a dict!)
props = fdtd.getnamed("FDTD")
names = [x.strip() for x in props.split("\n") if x.strip()]

# (2) read a single value (most common)
v = fdtd.getnamed("FDTD", "mesh accuracy")

# (3) for Mesh / PlaneSource / DFTMonitor use dir + getattr
#     (for these three, getnamed(objectname) reports 'no items matching the name ... can be found')
o = fdtd.getObjectById("mesh_1")
[m for m in dir(o) if "dx" in m]
getattr(o, "dx")
```

#### (6) Material refractive index self-check (guard against the `getindex` frequency trap)

```python
C0 = 299792458.0

def n_at(fdtd, mat_name, lam_m):
    """Look up n, k for a material at a given wavelength. Converts wavelength to frequency internally."""
    r = fdtd.getindex(mat_name, np.array([[C0 / lam_m]]))   # ★ pass frequency (Hz), and it must be a matrix
    z = complex(np.array(r).ravel()[0])
    return z.real, z.imag

# check: TiO2 - Siefke @532nm should be n≈2.45 (getting 5.99 means you hit the frequency trap)
```

### 8.5 Notes on deleting files

The F: drive is a separate partition and its Recycle Bin lives at `F:\$RECYCLE.BIN\<SID>\`;
**the Windows Recycle Bin does work**. Use
`[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p,'OnlyErrorDialogs','SendToRecycleBin')`
to send a file to the Recycle Bin (`Add-Type` is blocked by security policy, but PowerShell 5.1 ships
that type already, so use it directly).
Note that when a filename contains non-ASCII (e.g. a full-width `？`), do not write a `.ps1` script —
use wildcard matching to work around it.

### 8.6 Version and maintenance

- This file records **measurements on this machine**, not a paraphrase of the official documentation.
  Every entry carries its measurement date.
- When adding a pitfall, **include the date + a control experiment**; anything without a control must be
  labelled "inferred", not written as a conclusion.
- Division of labour with the other files: `agent.md` = the rules, `packages\PACKAGES.md` = the task map,
  `README.md` = the index.
- **Structural convention**: this file is organised into the eight chapters
  "environment / sessions / modelling / properties / results / resources / troubleshooting / tools".
  Put new content in the matching chapter and **stop appending "·补" (patch)-style sections**
  (restructuring is expensive).


