# Advanced workflows

> Loaded on demand from `field-manual.md`. These are low-frequency procedures: read this file only when the
> task actually matches one of the four workflows below.
>
> Contents: D (batch migration) · E (restructure a long doc) · F (translate a long doc) ·
> G (per-package self-check questions)

---

## Workflow D: batch-migrate a course/paper directory into packages

A complete implementation already exists in `scripts/migrate_classes_to_packages.py`. Key design points:

1. **`LECTURE_TO_PKG` mapping table**: lecture number (`041`) → package ID. The lecture is identified
   from the first three digits of a path part.
2. **`FSP_RENAME` explicit rename table + `safe_name()` generic fallback**:
   - Semantic names (`红外完美吸收器` → `infrared_perfect_absorber`) are hard-coded in the table
   - Fallback rules: spaces → underscores, `&` → `and`, other non-ASCII → `_`
   - ⚠️ **Always unit-test `safe_name()` first**: confirm that pure-ASCII names are not altered
     (`d2_perfectCross` must survive unchanged)
3. **Logs must be renamed alongside the `.fsp`**: `<fsp name>_p0.log` is what `assert_ran()` looks
   for, so renaming an fsp means renaming its log too, or the "did it actually run" check breaks.
4. **Generate `fsp\_rename_map.json` per package** (new name → original name) for manual tracing.
5. **The progress log must print the destination filename**: write `source -> destination`.
   Printing only the source name makes people think the rename did not take effect.
6. **Paper filtering**: exclude lecture handouts by the `ppt` / `上课` keywords. Note that some paper
   filenames **do not contain the word "论文"** (e.g. `Wide-angle, ...pdf`), so "contains 论文"
   cannot be used as the filter condition.

### Four verification steps after migration (all mandatory)

```bash
# 1) unit-test the rename logic (before migrating, run safe_name on samples)
# 2) unit-test paper filtering (print the PAPER/skip verdict for every PDF)
# 3) execute the migration
# 4) confirm what actually landed: ls each package and check filenames;
#    run check_packages.py to confirm ERROR=0
```

**Do not judge success from the log alone** — use `ls` / `find` to look at what actually landed.

### Porting checklist (reusing this skill in another workspace)

1. Copy `scripts/check_packages.py` → change `PKG_ROOT`, `PKG_NAME_RE`, `SUBDIRS`
2. Copy `assets/template/README.md` → rewrite §2's parameter table and §4's pitfalls for the domain
3. Copy `scripts/lumapi_common.py`, or replace it with the equivalent tool for the target domain
4. Follow Workflow A step 1: **audit before touching anything**
5. **Ask the user first** about migration policy: whether large files get copied (could be hundreds
   of MB), whether originals are kept, whether derived files are skipped
6. Migrate with "copy only, never delete", leave a `_rename_map.json` in each package, and a
   migration report at the root

---

## Workflow E: restructure a "patchwork" long document (without losing content)

Pitfall-log documents (like the main `field-manual.md`) tend to grow into an append-only body of
"§一·补一 / §一·补二 …" sections: **the content is all correct, but one topic is scattered across
several places**, and newcomers can only navigate via the index.
The right way to restructure is **machine-assisted relocation, not hand-copying**:

1. **Audit the structure first**: `grep -n "^#\{1,4\} "` lists every heading with its line number,
   giving you the exact line range of each block.
2. **Collect cross-references first**: `grep -o '§[^ ，。；、）)「]*' | sort -u`.
   Measured on this project: references were almost entirely concentrated in the document's own
   index chapter, with only 2–3 in the body — which sharply lowers the risk of restructuring.
   **The more references there are, the more caution is warranted.**
3. **Write a mapping table instead of hand-copying**: the script slices and reassembles using a list
   of `(new heading, old start line, old end line)`, keeping the body **verbatim** and changing only
   heading levels (`###`→`####`) while absorbing the scattered old sub-headings.
4. **Zero-loss check (mandatory)**: extract every line of the old file that is "not a heading, not a
   separator" and assert that each one appears in the new file; every reported difference **must be
   explained individually** (on this project all 8 differences were intentionally fixed references).
5. **Zero out the side effects**: after renumbering, `grep` the whole repo for old anchors (including
   `.py` docstrings, `_shared\`, and the copies under `skills\`), fix them all and re-sync
   the copies; **the number of leftover old-style anchors must be 0**.
6. **Archiving discipline**: once the chapter scheme is settled, write it into the "maintenance
   conventions" at the end of the document and **stop appending "·补"-style sections**.

> Key mindset: **content is a non-renewable asset; structure is a renewable artifact.**
> Restructuring touches structure only — no field-tested conclusion is allowed to vanish in
> the process.

---

## Workflow F: translate a long doc into another language (without breaking anchors)

Same risk profile as Workflow E, plus one extra hazard: a translation invites you to "improve"
sentences, and any change to a heading silently breaks every reference to it.

**Golden rule: translate the prose, freeze the skeleton.** Section numbers, heading text used as an
anchor, code blocks, measured dates, numbers and filenames are data — they are translated *never*
or *only with the original retained*.

1. **Record the skeleton before you start.** Dump the heading list and the reference list:
   `grep -n "^#\{1,4\} "`, then `grep -o '§[0-9]\+\(\.[0-9]\+\)\?' | sort -u`.
   Keep the original heading list as the expected value for the parity check in step 5.
2. **Write in passes, not one shot.** A 1300-line file translated in a single write is unreviewable
   and any tool truncation loses the tail silently. Write pass 1 ending in a unique marker
   (e.g. `<!-- PART2 -->`), then **Edit** that marker into pass 2 + the next marker, and so on.
   This keeps every pass reviewable and makes resuming after an interruption trivial.
3. **Translate prose only.** Keep, verbatim: section numbers, `§x.y` references, code, error
   messages actually emitted by the tool (**do not translate an error string — the user will see it
   in the original language**), CLI flags, paths, filenames, and every number/date.
4. **Preserve the notation system.** If the document uses ✅/❌/⚠️/⭐ as semantic markers, keep them —
   they are part of the format contract, not decoration.
5. **Machine parity check (mandatory).** Assert, against the recorded skeleton:
   - subsection count is identical, and the *number list* is identical
   - every `§x.y` reference still resolves to a real heading
   - the symptom/index table's targets all still exist
   Before/after file sizes and line counts are a weak signal; the number list is the strong one.
6. **Also check the cross-document links.** Any index/map file that lists documents
   (`README.md`, the collaboration charter, the package `README.md`) must be updated for the new file
   and for the changed language, or the map goes stale immediately.
7. **When fixing a dangling reference, say so.** If the source had a broken reference
   (e.g. a "see (2)" pointing at nothing), translate it into a **valid** one and flag the change
   in the report — do not silently reproduce a broken reference and do not silently rewrite it.

**Do not translate** the bundled `assets/` and `scripts/` when translating a skill:
a translated copy of a script or template diverges from its source (see the stale-copy pitfall in
"Placement rules") and creates permanent sync debt.

## Workflow G: per-package self-check questions ("5 questions per paper")

**When to use:** a package has its paper PDF archived and the user wants study/self-check material
for it — typically after they report "I can't answer the questions you gave me". The deliverable is
one `paper\自测题_5问.md` per package, sitting next to the PDF.

**Why this shape.** A student who has been reproducing papers by following videos has learned
*operations*, not *physics*. The point of the questions is to force the three-layer unwrap:
phenomenon → model assumptions → numerical realisation. Every question therefore ends with the
prerequisite physics it exercises, not just an answer.

### Pipeline

1. **Extract the text once, for every paper** (never let a subagent invent numbers):
   ```python
   import pymupdf, glob, os
   for src in sorted(glob.glob(r"...\packages\P*\paper\*.pdf")):
       doc = pymupdf.open(src)
       body = "\n".join(f"\n===== PAGE {i+1} =====\n{p.get_text('text')}"
                        for i, p in enumerate(doc))
       open(os.path.join(OUT, os.path.basename(src) + ".txt"), "w", encoding="utf-8").write(body)
   ```
   Write the dumps under `_scratch\` (never `%TEMP%`), archive them under `_scratch\archive\<date>_pdf_extract\`.
   Use the managed venv interpreter — it has `pymupdf`; the managed *base* interpreter does not.
   Watch two traps: (a) a package may hold **two** PDFs (original + a Chinese annotated copy), so key
   the output by source filename, not by package ID; (b) `print("chars=", len(txt))` per page is the
   scan-detector — a page with ~tens of characters has no text layer.

2. **Write one exemplar yourself, then parallelise.** Write the first package's file by hand; it
   becomes the style contract. Then hand the remaining packages to N subagents, 2–3 packages each,
   in a single message so they run concurrently. Each subagent brief must contain: the exemplar
   path to read first, the extracted-text path(s), the output path, the fixed 5-question template,
   the language, and "every number must be traceable to the paper — fabricate nothing".

3. **Fixed template (5 questions, same five slots in every file):**
   - **Q1 phenomenon** — the core effect, explained *without formulas* as a causal chain.
   - **Q2 formula** — the paper's central defining/theoretical expression; explain every symbol's
     physical meaning; **numerically verify** it against the paper's own numbers when possible.
   - **Q3 prerequisite** — where a foundational concept used by the paper comes from (Drude/Lorentz,
     Fano, Mie, Jones matrix, Bloch periodic BC, Kubo, χ² tensor …).
   - **Q4 design choice** — why that parameter/structure value; what breaks if changed.
   - **Q5 simulation A/B** — an executable controlled experiment: independent variable, frozen
     quantities, output metric and how it is collapsed to a comparable number, and **≥2 independent
     criteria to separate physical effect from numerical error**.
   Each answer carries `> 要补的基础：` and `> 教材锚点：` (concrete book + chapter). End the file
   with a 基础缺口自查表 (question → missing foundation → where to study).

4. **Verify the subagents — do not trust their summaries.** After they return:
   ```bash
   grep -c '^### Q' file.md; grep -c '^### A' file.md      # must both be 5
   ```
   then **grep each cited number back into the extracted source text**. Agents transcribe well but
   they also occasionally "tidy" a value; the cheapest guard is a keyword sweep over the source for
   every figure they quote.

5. **Update the maps.** `packages\PACKAGES.md` (the per-package inventory row + a short note that
   every package now carries `自测题_5问.md`), and the package `README.md` if its paper list or
   target figure changed.

### Two reporting duties that ride along

- **If the adviser's target figure differs from what the package README claims, say so loudly.**
  A package can be mid-way through Figure 1 while the new instruction is Figure 2; that is a change
  of goal, not a detail. Diff the figure captions and rewrite §0/§1 of the package README.
- **A simulator cannot reproduce an experimental figure panel** (SEM micrographs, measurement
  set-ups). Mark those panels as "experiment only — cite the original" instead of leaving them as
  "not started", or the progress table will never reach a truthful state.


