---
name: fdtd-package-workspace
description: Turn a Lumerical/FDTD research workspace into an agent-collaborative "one topic = one package" layout, or create/take over a topic package inside that layout. Use when you need to build a self-contained reproduction folder for a paper (paper + .fsp + scripts + results), maintain the package index, run the packaging self-check, take over a task by package ID, batch-migrate a course/paper directory into packages, generate per-paper self-check questions, or restructure/translate a long pitfall document without losing content or breaking cross-references. Long procedural workflows (migration, doc restructuring, translation, self-check questions) are bundled in references/advanced-workflows.md and loaded on demand. Includes field-tested self-check and session utilities.
agent_created: true
updated: 2026-11-03
---

# FDTD Package Workspace: build the structure, create packages, take over packages

## When to use

- Converting a messy research workspace into a package layout an agent can take over
- Creating a self-contained reproduction package for a new paper (paper + `.fsp` + scripts + results + README)
- Taking over a task by package ID: read index → read package README → self-check → start work
- Diagnosing "incomplete package" (missing paper / non-ASCII filename / unfilled README)

## Core design: one topic = one package

**One package = one paper = one self-contained folder.** Locate tasks by package ID, pass context
through the README, and keep the structure from rotting with a self-check script.

```
<workspace>\
├─ cases\                  ★ renamed from packages\ in TASK-002 (2026-11)
│  ├─ INDEX.md             ★ master case table (agent entry point)
│  ├─ _TEMPLATE\           copy this when creating a package
│  └─ P0N_<short_name>\    one package = one paper
│     ├─ README.md         ★ agent takeover entry point
│     ├─ paper\            paper PDF + reference material
│     ├─ model\            .fsp projects + .lsf sources (filenames MUST be ASCII)
│     ├─ config\           spec_<id>.json / sweep_<id>.json (machine-readable inputs)
│     ├─ results\          data and figures
│     └─ notes\            notes, repro cards, troubleshooting records
├─ library\py\             modules shared across cases
└─ tools\                  repo-level gate scripts
```

> The directory is `cases/` (not `packages/`), the project file dir is `model/` (not `fsp/`),
> and per-case machine inputs live in `config/`. `tools/check_packages.py` is the authority on this
> layout (`SUBDIRS = ["paper", "model", "results", "notes"]`); read it if a doc disagrees.

## CRITICAL — three hard constraints

1. **Package directory names and `.fsp` filenames must be pure ASCII.**
   The GPU solver (`fdtd-engine.exe`) crashes on any non-ASCII path, and the error message comes back
   as mojibake (Windows error code 1113). Spaces are fine; the CPU engine `fdtd-engine-msmpi.exe` does
   not have this problem. → Original projects with Chinese names must be **renamed, with an old→new
   mapping recorded.**
2. **Papers and .fsp files map one-to-one**, verified by the self-check script as a machine check —
   never by human memory.
3. **Any discrepancy against the paper must be written into the package README**, not left sitting
   in a chat log overnight.

## Placement rules

| Content | Where it goes |
|---|---|
| Scripts used by a single package | that package's `scripts\` |
| Shared by two or more packages | `library\py\` |
| General-purpose large tools (probes, resource fixes, etc.) | stay in the common `scripts\`, **referenced, not copied** (avoids stale copies) |

> ⚠️ **Stale copies are a pitfall we actually hit** (2026-10-01): `assets/template/README.md` and
> `scripts/lumapi_common.py` each had a copy; the source files had their anchors updated but the
> copies did not follow, so the section numbers they pointed at stopped resolving.
> **Rule**: copies only serve as a "distribution origin"; whenever a source file changes, you
> **must re-sync its copies within the same turn and `diff` to confirm they match**.

---

## Workflow A: convert a workspace from scratch

1. **Audit before touching anything.** Use `Get-ChildItem -Recurse` / `find` to list the actual
   files in full. **Do not trust the path descriptions in the existing README** — in practice,
   wrong paths in READMEs are the norm. Record where the paper PDFs are, where the `.fsp` files are,
   where the scripts are, where the results are.
2. **Build the package inventory**: a paper → package ID mapping. Package IDs use `P0N`; directory
   names append a short English name and the origin (e.g. `P03_HWP_Ding2015`, `P01_Absorber_042`).
3. **Build the skeleton**: copy `assets/template/` (the README template) into every package, and
   create the subdirectories `paper/model/results/notes` plus `config/` (the complete directory
   layout is in `<workspace>\cases\_TEMPLATE\`). Put `.gitkeep` in empty directories so version control
   preserves them.
   ⚠️ `.gitkeep` breaks the "directory is empty" check — the self-check script must exclude
   placeholder files from its file counts.
4. **Write `INDEX.md`**: the master package table (ID / topic / paper / status / main line)
   + naming rules + self-check commands + an **asset location table** (recording where each file
   currently lives).
   - If you decide to **defer migration**: write "not archived, path recorded only" in the table.
   - If migration is **complete**: change the table to "archived" and note that the originals are
     still in place, read-only.
5. **Write each package README** (using the template), filling in at least §0 and §1.
6. **Wire the self-check script — do NOT copy it.** The single implementation is
   `tools/check_packages.py`; `skills/fdtd-package-workspace/scripts/check_packages.py` is a thin
   forwarder to it. The old "copy it and edit the path constants" advice is exactly what produced
   two divergent copies that both went dead after `packages/` → `cases/` (found 2026-11-08:
   the skill copy resolved `<skill>/packages`, which never existed).
7. **Verify by actually running it**: run once to see the baseline; then **deliberately create a
   file with a Chinese name** as a control, and confirm it gets caught (see below).

## Workflow B: create a new package

```bash
cp -r cases/_TEMPLATE cases/P0N_<short_name>
# Fill in README: §0 (goal / acceptance / entry script), §1 (paper), §2 (parameters)
# Archive: paper -> paper\, .fsp/.lsf -> model\, spec -> config\ (ASCII names; record old->new)
py tools/check_packages.py --pkg P0N
```

## Workflow C: take over a package (every collaboration)

1. Read `cases\INDEX.md` → locate the package ID
2. Read that package's `README.md` §0 "Agent quick takeover" → get this session's goal /
   acceptance criteria / entry script
3. Run `py tools/check_packages.py --pkg P0N` to confirm the package is complete
4. Pass the ASCII gate → start work
5. When done, write progress into the package README §5 (discrepancy log) + §6 (supervisor sync)

---

## Self-check script

`scripts/check_packages.py` — **read-only**, modifies nothing.

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" tools/check_packages.py              # all packages
"$PY" tools/check_packages.py --pkg P03    # a single package
"$PY" tools/check_packages.py --json       # JSON output (for agent parsing)
"$PY" tools/check_packages.py --strict     # treat WARN as failure too
```

Checks performed:

| Level | Check |
|---|---|
| ERROR | package directory name does not match `P0N_<short_name>` / README missing / README contains an unfilled placeholder `<...>` / **filename is non-ASCII** |
| WARN | `paper\` is empty / new-package signature / `.fsp` has no same-named `_p0.log` (never actually run?) |
| INFO | file counts per subdirectory, number of .fsp files, package size |

**Verify the script itself is reliable (mandatory, once is enough)**:
deliberately drop in a file with a Chinese name, run the script, and confirm it reports ERROR with
exit code 1 while ASCII files in the same directory are not falsely flagged.
— This is the "to judge whether a tool works, you must first run a control" principle in action.

### Constants to change per environment

Three constants at the top of the script must be changed when porting to a new workspace:

```python
TOOLS_DIR = Path(__file__).resolve().parent
WS_ROOT   = TOOLS_DIR.parent          # workspace root
PKG_ROOT  = WS_ROOT / "packages"      # package directory
PKG_NAME_RE = re.compile(r"^P\d{2}_[A-Za-z0-9_]+$")   # package naming rule
SUBDIRS = ["paper", "fsp", "scripts", "results", "notes"]
```

If a project needs **certain subdirectories to exist unconditionally** (e.g. "every package must
have `paper\` and `fsp\`"), just promote the corresponding check from WARN to ERROR.

---

## Package README template

`assets/template/README.md`, seven sections (§0–§6); **§0 is the interface for the agent**:

| Section | Content | Audience |
|---|---|---|
| §0 Agent quick takeover | package ID / status / **this session's goal** / **acceptance criteria** / entry script / mandatory pre-work | agent |
| §1 Paper | title / authors / journal / DOI / local files / list of figures to reproduce | human + agent |
| §2 Key parameters | the paper's parameter table, copied verbatim (**the material data source must be stated**) | agent |
| §3 File inventory | item-by-item description of paper / fsp / scripts / results / notes | agent |
| §4 Pitfalls specific to this package | only what is unique to this topic; general pitfalls point at the main SKILL.md | agent |
| §5 Reproduction progress and discrepancy log | paper value vs my result vs difference vs judgement | human + supervisor |
| §6 Sync with supervisor | dates reported / open questions / deliverables | human |

---

## Session utilities (FDTD context)

`scripts/lumapi_common.py` — turns field-tested FDTD pitfalls into functions, so each package does
not have to rewrite them.

```python
import sys
sys.path.insert(0, r"<workspace>\library\py")
from lumapi_common import setup_env, verify_and_run, assert_ran, ascii_gate, n_at

setup_env()                  # set license + sys.path, import lumapi
f = verify_and_run(fsp)      # save -> close -> new session load -> run -> three checks, in one call
try:
    ...
finally:
    f.close()
```

| Function | Purpose |
|---|---|
| `setup_env()` | set `ANSYSLMD_LICENSE_FILE` + `sys.path`, import lumapi |
| `open_fdtd()` | session factory, with retry on `ansyscl` port TIME_WAIT |
| `n_sessions()` | count `fdtd-solutions.exe` processes = how many license seats are held |
| `ascii_gate(p)` | ASCII gate on a path (hard requirement of the GPU engine) |
| `assert_ran(f, fsp)` | **three checks**: `layoutmode==0` + `_p0.log` exists + log contains `Completed` |
| `mesh_report(log)` | extract mesh / memory / iteration count to judge whether the problem size is healthy |
| `n_at(f, mat, λ)` | look up refractive index, converting wavelength to frequency internally (sidesteps the `getindex` frequency trap) |
| `verify_and_run(fsp)` | full sequence: save → close → new session load → run → three checks |

If the target environment is not FDTD, delete this file and drop this section.

---

## Examples

**User:** "turn this course folder into packages and give me the index."

**Action:** audit the folder with `Get-ChildItem -Recurse` → assign `P0N_<short_name>` IDs → copy
`assets/template/` into each package → create `paper/fsp/scripts/results/notes` → move the PDF and the
matching `.fsp` in, renaming to ASCII and recording the old→new map → regenerate `PACKAGES.md` →
run the self-check.

**Result:** `cases\INDEX.md` lists every package, the self-check reports paper↔`.fsp` as 1:1,
and each package README answers §0–§2 without needing the chat log.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| self-check reports a paper/`.fsp` count mismatch | pairs were split or duplicated | complete the pair, or record the missing one in the package README |
| GPU engine returns 1113 / mojibake | package dir or `.fsp` name is non-ASCII | rename to ASCII and record the old→new mapping |
| README section numbers stop resolving | source file edited, its copy not re-synced | re-sync the copy in the same turn and `diff` it |
| paths in an inherited README do not exist | READMEs are usually stale | audit the disk first; never trust the described paths |
| the same script exists in three packages | copied instead of referenced | keep one copy in `library\py\`, reference it |

## References（load on demand）

Four long, low-frequency procedures live in `references/advanced-workflows.md`. Read that file only
when the task matches one of them; the one-liners below are enough to route.

- **Workflow D — batch-migrate a course/paper directory into packages.** Driven by
  `tools/migrate_classes_to_packages.py` (**repo-level tool, not shipped with this skill** —
  a byte-identical copy used to live in `scripts/` and rotted, see D-006): hard-codes the
  lecture→package map, renames non-ASCII `.fsp` files, and must rename each `_p0.log`
  alongside (otherwise `assert_ran()` breaks). Run it with
  `--src <course dir> --out <workspace root> --dry-run` first; nothing is written in dry-run.
- **Workflow E — restructure a "patchwork" long document** into a clean chapter scheme without
  losing a single line. Machine-assisted relocation, never hand-copying.
- **Workflow F — translate a long document into another language** while freezing section numbers
  and `§x.y` anchors, then machine-verify anchor parity.
- **Workflow G — per-package self-check questions.** Five fixed question slots per paper, written to
  `paper\自测题_5问.md`, with answers plus a "missing foundation → where to study" table.

→ `references/advanced-workflows.md`

