# memory/project-conventions.md

Durable project rules. Change only when a convention actually changes; this is not a journal.

## Workspace layout (2026-11-03)

```
FDTD_WS\
├── packages\          one topic = one package (= one paper)
├── skills\            reusable skills, standard layout: SKILL.md + scripts/ + references/ + assets/
├── agents\            agent definitions (this one lives in agents\fdtd-sim-agent\)
├── tools\             repo-level scripts (check_packages.py, check_git_limits.py)
├── _shared\           modules used by 2+ packages
├── _scratch\          throwaway. never a deliverable; archive before deleting
├── course_media\      lecture videos (git-ignored, 7.4 GB)
├── agent.md           project charter / iron laws
├── SKILL.md           the measured pitfall manual (8 chapters, English)
└── README.md / README.en.md
```

`skills\` used to be `.workbuddy\skills\`. The rename (2026-11-03) makes the workspace readable by
non-WorkBuddy tools; the side effect is that WorkBuddy no longer auto-discovers project skills from
that path, so they must be loaded explicitly by path.

## Package rules

1. **One package = one paper.** Everything for that paper lives inside it: `paper\ fsp\ scripts\ results\ notes\`.
2. **Package directory and `.fsp` filenames must be pure ASCII.** A Chinese filename crashes the GPU
   engine (error 1113). Rename map in `fsp\_rename_map.json`.
3. **New work never lands in the workspace root.** If it is not paper-specific, it goes to `_shared\`;
   if it is a general tool, to `tools\` or `F:\Lumercial_WS\scripts\`.
4. **Every package carries `paper\自测题_5问.md`** — five fixed question slots per paper.
5. **Every package README follows the same §0–§6 skeleton**; §0 is the agent takeover block and must
   state: package ID, status, this session's target, acceptance criteria, entry script, runtime.

## Documentation split

| File | Role | Language |
|---|---|---|
| `agent.md` | charter: goal, asset map, thirteen iron laws | Chinese |
| `SKILL.md` | evidence and fixes: 8 chapters + §0 symptom index | English |
| `README.md` / `.en.md` | entry index for collaborators | Chinese / English |
| package `README.md` | per-paper state and pitfalls | Chinese |
| skill `SKILL.md` | procedural contract for one capability | English |

Do not copy body text between them — each has exactly one job.

## Convergence / verification conventions

- **No conclusion without a control.** Before claiming a tool or a setting works, run a case with a
  known answer (mirror film for reflection, analytic Drude for `getindex`).
- **Report band-limited statistics, not full-sweep means.** A metasurface is specified over a design
  band; averaging across the out-of-band region makes a good result look bad (P03: 0.155 vs 0.043
  for R_co depending on the window).
- **A difference from the paper goes into the package README §5**, not only into the chat.

## Git

- `.fsp` is binary: commit immediately after editing, never let two people touch the same file on the
  same day.
- Single files above 100 MB are rejected by GitHub. `P01\fsp\infrared_perfect_absorber.fsp` (331 MB)
  is git-ignored for this reason.
- Do not commit: `course_media\*.mp4`, `_scratch\*`, engine caches.

## Personal file

`(Agent_ignore)Log.md` is the user's own study log. **Do not read or modify it by default.** Reading is
authorised for the current turn only when the user explicitly references it.
