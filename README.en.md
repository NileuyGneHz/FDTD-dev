# FDTD_WS — Metasurface FDTD Reproduction Workspace

> **Ansys Lumerical 2025 R1 (v251)** | Python-driven (`lumapi`) | headless simulation
> Purpose: reproduce the research group's metasurface paper series as a reproducible loop of
> "model → sweep → interpret → plot → archive"
> Collaboration model: **one topic = one package**; specify the package ID before each session
> (e.g. "this time we do P03")
> Created 2026-09-27 | Revised 2026-10-01 (SKILL.md restructure + collaboration docs completed)

**Language:** [中文](README.md) | **English**

---

## What to read first (in order)

| Order | File | Role |
|---|---|---|
| 1 | **`packages\PACKAGES.md`** | **Task map**: what the 10 packages are — step one of every session |
| 2 | **`packages\P0N_*\README.md`** | That package's §0 "Agent quick takeover": this session's goal / acceptance criteria / entry script |
| 3 | **`agent.md`** | **The rules**: project goal, asset map, thirteen iron laws, collaboration and repository discipline |
| 4 | **`SKILL.md`** | **Evidence and fixes**: v251 measured pitfalls + code you can copy directly (§0 is a symptom index) |
| 5 | This file | Entry index: structure, purpose, getting-started commands |

---

## Quick start

```bash
export PATH="/usr/bin:/bin:$PATH"          # the local Bash tool loses PATH; restore it first
cd "F:/Lumercial_WS/FDTD_WS"

PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# 1) package structure self-check (papers present? / .fsp pure ASCII? / README filled in?)
"$PY" tools/check_packages.py                # all packages
"$PY" tools/check_packages.py --pkg P03      # a single package

# 2) pre-commit size check (files >100 MB are rejected outright by GitHub)
"$PY" tools/check_git_limits.py
```

When running simulations, prefer the shared wrapper (the session traps are already handled):

```python
import sys
sys.path.insert(0, r"F:\Lumercial_WS\FDTD_WS\_shared")
from lumapi_common import setup_env, verify_and_run, ascii_gate, n_at

setup_env()
f = verify_and_run(fsp)          # save -> load -> run -> three checks, in one call
try:
    ...
finally:
    f.close()
```

---

## Repository structure

```
FDTD_WS\
├─ README.md              <- this file (Chinese)
├─ README.en.md           <- English version
├─ agent.md               collaboration charter (the rules)
├─ SKILL.md               pitfall manual (eight chapters, symptom-indexed)
├─ packages\            ★ task packaging area (one topic = one package)
│  ├─ PACKAGES.md           ★ task map
│  ├─ _TEMPLATE\            new-package template (copy it to create a package)
│  └─ P01..P10\             10 topic packages
│     ├─ README.md           ★ takeover entry point
│     ├─ paper\              paper PDFs
│     ├─ fsp\                .fsp projects (pure ASCII names) + same-named _p0.log
│     ├─ scripts\            scripts specific to this package
│     ├─ results\            data and figures
│     └─ notes\              notes and troubleshooting records
├─ _shared\               tools shared across packages (lumapi_common.py)
├─ tools\                 repo-level scripts (self-check / size check / migration)
├─ course_media\          course video index (*.mp4 not committed)
├─ .gitattributes         text/binary and line-ending rules
├─ skills\                reusable skill library (SKILL.md + scripts + references + assets)
├─ agents\                agent definitions (role / tools / skills / memory / evals)
└─ _scratch\              throwaway scripts (not committed)
```

### Purpose and ownership of each directory

| Directory | Purpose | Who writes | Naming rule |
|---|---|---|---|
| `packages\P0N_*\` | one topic = one package; paper + project + scripts + results, self-contained | everyone | `P<two-digit index>_<PascalCaseTopic>_<lecture number>` |
| `packages\P0N_*\fsp\` | simulation projects and engine logs | whoever edits projects | **pure ASCII**, lower_snake_case; log named after the `.fsp` + `_p0.log` |
| `packages\P0N_*\scripts\` | scripts used by **this package only** | this package's owner | `t<n>_<topic>.py` or `<verb>_<object>.py` |
| `packages\P0N_*\results\` | data and figures (csv/png) | whoever runs the simulations | `<script>_<figure>_<content>.csv` |
| `packages\P0N_*\notes\` | notes, troubleshooting records | everyone | free-form; date recommended |
| `_shared\` | shared by **two or more packages** | whoever needs reuse | module name in lower_snake_case |
| `tools\` | **repo-level** tools (self-check / size check / migration) | whoever maintains the repo | starts with a verb |
| `course_media\` | course video index (README only; mp4 not committed) | read-only | `L<lecture>_<topic>.mp4` |

**Where does a new file go (decision tree)?**

1. Serves **one package** → that package's `scripts\` / `results\` / `notes\`
2. Needed by **two or more packages** → `_shared\`
3. Repo-level checks / management tooling → `tools\`
4. Papers and projects → the matching package's `paper\` / `fsp\`
5. Original course material → **stays outside the repo** at `F:\Lumercial_WS\Classes\FDTD\` (read-only)
6. Throwaway drafts → the package's `notes\`, not the repo root

> Empty directories are kept alive by a `.gitkeep` placeholder — **do not delete them**.

---

## The 10 topic packages

The supervisor's course covers lectures 041–049; each lecture = one paper + one set of template projects.

| Package | Topic | Lecture | Paper | `.fsp` | Status |
|---|---|---|---|---|---|
| P01 | Infrared perfect absorber | 042 | ✅ | 2 | running successfully |
| P02 | Polarisation conversion | 045 | ✅ | 4 | material in place |
| **P03** | **Plasmonic half-wave plate (Ding 2015)** | — | ⚠️ close-reading version | 4 | **in progress (main line)** |
| P04 | Anomalous reflection | 047 | ✅ | 7 | material in place |
| P05 | Circular-polarisation metalens | 048 | ✅ | 4 | material in place |
| P06 | Vortex beam generation | 049 | ✅ | 11 | material in place |
| P07 | Broken symmetry | 041 | ✅ | 3 | material in place |
| P08 | Broadband visible absorber | 043 | ✅ | 4 | material in place |
| P09 | Graphene perfect absorber | 044 | ✅ | 3 | material in place |
| P10 | Second-harmonic generation | 046 | ✅ | 3 | material in place |

> Learning path: **041 → 045 → 047 → 048 → 049** is the route to metasurface holography.
> Detailed goals / parameters / progress for each package are in `packages\P0N_*\README.md`.

---

## Collaboration workflow

1. You name the package: **"this time we do P03"**
2. Read `packages\PACKAGES.md` to locate the package → read its `README.md` **§0** for the goal and acceptance criteria
3. Run the self-check `tools\check_packages.py --pkg P03`
4. Start work (follow the `agent.md` §4 iron laws; check `SKILL.md` for general pitfalls)
5. On completion: results go into the package's `results\`, progress and discrepancies are written back into its `README.md` **§5**
6. Commit: small commits; the message states "which package + what changed + the conclusion"

---

## The four most expensive pitfalls (memorise these; the full version is `SKILL.md` §0)

1. **Without a control experiment, do not draw a conclusion** (`SKILL.md` §7.1 — the first rule of this project)
2. **`run()` returning instantly = nothing was computed**: in headless, a newly created session must
   `save` → new session `load` → then `run`; the criteria are `layoutmode == 0` + `_p0.log` exists +
   the log contains `Completed` (§2.1)
3. **Wavelength is in metres, and `getindex()` takes frequency, not wavelength** (§5.2 / §6.1)
4. **A non-ASCII path always crashes the GPU engine** (the error comes back as mojibake, error code 1113) (§6.2)

---

## Repository discipline (required reading for collaboration)

| Rule | Reason |
|---|---|
| **Do not commit mp4 files or `.fsp` files >100 MB** | GitHub's hard limit is 100 MB per file and it rejects anything larger; once it is in history, cleaning it up requires rewriting history |
| **`.fsp` cannot be diffed or merged** | It is binary. Whoever changes it commits immediately; two people must not edit the same project on the same day in parallel; to parallelise, save a separate `<name>_v2.fsp` |
| **If you change a project or a conclusion, update the package README** | Changing code without updating the docs means the next person hits the same pitfall |
| **Package directory names and `.fsp` names must be pure ASCII** | A hard requirement of the GPU engine; Chinese names always crash |
| **Do not read or modify `(Agent_ignore)Log.md`** | It is Nileuy's personal log |

**Commit policy**: course videos (7.4 GB) and projects >100 MB are not committed; everything else —
papers, scripts, results, documents — is. After exclusion the repo is about **185 MB**, within GitHub's
recommended range (< 1 GB).

---

## Environment at a glance

| Item | Value |
|---|---|
| Lumerical | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\` (2025 R1 / v251) |
| Python API | `<install>\api\python\lumapi.py` (`import lumapi`) |
| Managed Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default` (3.13.14 + numpy 2.5.3) |
| ❌ System Python 3.14 | no numpy; `import lumapi` crashes outright |
| License | `1055@localhost` (100 seats, expires 2035-12-31) |
| GPU | RTX 3070 Laptop 8 GB (real32 single precision; metals tend to diverge) |

> Details in `agent.md` §3 and `SKILL.md` §1.

---

## Path conventions (required reading for collaboration)

This repository covers only the `F:\Lumercial_WS\FDTD_WS\` level. Paths in the documentation fall into
three classes:

| Class | Example | Notes |
|---|---|---|
| **In-repo** | `packages\P03_HWP_Ding2015\` | Shipped with the repo; every collaborator has it |
| **Local, outside the repo** | `F:\Lumercial_WS\scripts\`, `...\docs\`, `...\Classes\FDTD\`, `...\ANSYS Inc\` | **Not in the repo**; must be prepared separately on another machine |
| **Not committed** | `course_media\*.mp4`, large `.fsp` files | Excluded for size reasons |

---

## Known gaps

| Gap | Notes |
|---|---|
| **P03 is missing the original paper PDF** | Currently a close-reading version; DOI `10.1021/acsnano.5b00218` — request it or download it |
| **8 packages have an empty `results\`** | They only contain the original course projects; no simulation has been run for them yet |
| **Docs reference paths outside the repo** | On another machine `scripts\` / `docs\` will not exist (see "Path conventions" above) |
| **Lumerical and the license are not in the repo** | Commercial software; this is expected |
