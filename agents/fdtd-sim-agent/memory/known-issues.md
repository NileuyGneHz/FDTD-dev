# memory/known-issues.md

Symptom → cause → fix, in the order these actually bite. Every entry has been observed on this
machine; dates are when it was characterised.

---

## 状态标记约定（2026-11-11 新增，见 `agents/AGENTS.md` 约束 6）

每条标题后必须带一个标记，二选一：

- `→ D-xxx`：已复现并定性，权威记录在 `defects/D-xxx.md`，本文件只留症状与速查
- `[未立项]`：只观察到现象、还没开 D 号。这类**只有本文件一处记录**，别指望在 defects 里找到

判据（将来由 `tools/check_docs.py` 机检）：每个 `##` 标题都含上述两种标记之一。

## 索引

| # | 症状速查 | 归属 |
|---|---|---|
| 1 | FlexNet `-97,121` 会话起不来 | `[未立项]` |
| 2 | `A > 1` / 负 `R` / 谱无视几何 | `[未立项]` |
| 3 | 读监视器 `too many values to unpack` | `[未立项]` |
| 4 | 已收敛被误判为发散（正则截断指数） | `[未立项]` |
| 5 | 单次运行 12 分钟（mesh accuracy 8） | `[未立项]` |
| 6 | 参考工程本身不可信 | `→ D-001` |
| 7 | 折射率返回荒谬值（`getindex` 传波长） | `[未立项]` |
| 8 | `addmaterial("Drude")` 失败 | `[未立项]` |
| 9 | 自定义材料静默用了数据库的光学常数 | `[未立项]` |
| 10 | GPU 引擎遇中文路径崩（1113） | `[未立项]`（规则见 `path-conventions.md` §1） |
| 11 | 杂散短波长导致显存爆炸 | `[未立项]` |
| 12 | `run()` 秒回、什么都没算 | `→ D-004` |
| 13 | O&S 结果缺失 / Visualize 变灰 | `[未立项]` |
| 14 | 全介质超表面报 `T ≈ 0.13`（反射几何） | `[未立项]` |
| 15 | 给透射器件报「峰值 A」 | `[未立项]` |
| 16 | "Save changes?" 对话框卡住无头运行 | `→ D-004` |

**统计**：16 条 = 3 条已有 D 号 + 13 条未立项。未立项不等于不重要——它们是**还没定性**的坑，
定性后应开 D 号并把本条收敛成指针。

---

## 1. `FlexNet Licensing error:-97,121` — GUI or headless session will not start `[未立项]`

**Means**: the licence broker is up, the **vendor daemon is dead**. Not a configuration problem.
`lmstat` shows `license server UP` but `ansyslmd: Network connect to THIS_HOST failed (-95,378)`,
and `tasklist` has no `ansyslmd.exe`.

**Fix** (no admin needed):
```bash
"F:/Lumercial/Shared Files/fnp/winx64/lmutil.exe" lmreread -c 1055@localhost
```
Healthy = two UP lines. If that fails:
`net stop "ANSYS, Inc. License Manager CVD"` / `net start ...` (admin).

**Recurs after reboot** when the service starts before the network stack. Prevention: set it to
Automatic (Delayed Start), and never disable the wired Realtek adapter — the hostid
`047c1636fd0f` is bound to its MAC.

---

## 2. `A > 1`, negative `R`, or a spectrum that ignores the geometry `[未立项]`

**Cause**: `PML` on x/y for what is actually a periodic array. PML simulates one isolated element;
the finite-width plane source then diffracts into the lateral PML and the reflectance monitor reads
a negative flux.

**Measured** (P01, identical stack): `Periodic` → A = 0.808; `PML` → **A = 1.111**.

**Fix**: `bc.x = bc.y = Periodic` (or `Bloch` for oblique incidence). Check this before touching
materials or mesh.

---

## 3. `ValueError: too many values to unpack` when reading a monitor `[未立项]`

**Cause**: on v251 `getresult(mon, "T")` returns a **list of dicts**, each carrying `lambda`, `f`, `T`
and a `Lumerical_dataset` block — not a `(x, y)` tuple.

**Fix**:
```python
item = raw[0]
lam = np.asarray(item["lambda"]).flatten()
val = np.asarray(item["T"]).flatten()
```

---

## 4. A converged run misdiagnosed as divergent `[未立项]`

**Cause**: grepping the engine log with `Auto Shutoff: [0-9.]+` truncates `8.80583e-05` to
`8.80583` and reads as "never decayed".

**Fix**: include the exponent — `Auto Shutoff: [0-9.eE+-]+`. This one cost a whole debugging detour.

---

## 5. A single run takes 12 minutes `[未立项]`

**Cause**: `mesh accuracy = 8` on a few-µm cell with 100 nm metal. The course project
`d2_perfectCross.fsp` is set up this way: 77,813 iterations, ~12 min.

**Fix**: `mesh accuracy 4` + a local mesh override of 15–30 nm around the metal/spacer stack.
Measured: 30 s per run, and the answer changed by 0.007 when refined — i.e. the coarse setting was
already converged.

**Rule**: refine once, measure the delta, stop. "Higher is better" is not free.

---

## 6. The reference project is not necessarily correct `→ D-001`

`d2_perfectCross.fsp` runs 77,813 iterations and ends with `Auto Shutoff: 0.047` — it **never reached
the 1e-5 criterion**, so its reported 0.82 is not a converged result. Treating it as ground truth
would have sent the diagnosis in the wrong direction.

**Rule**: before using any `.fsp` as a reference, read its `_p0.log` and confirm convergence.

**权威记录**：`defects/D-001-fsp-layer-reference-and-converged-course-project.md`
（该 D 把本条扩展成「把未收敛的历史运行当成参考工程族的代表，并据此臆测 ts 量取面」，
并给出两次反解析的实测证据）。

---

## 7. Refractive index comes back absurd (TiO₂ → 5.99) `[未立项]`

`getindex(material, X)` takes **frequency in Hz**. Passing a wavelength (532, meaning nm) returns
nonsense that still looks like a number.

**Fix**: `getindex(m, np.array([[c / 532e-9]]))`.

---

## 8. `addmaterial("Drude")` fails `[未立项]`

The argument is a **model type**, not a material name. `Plasma`, `Lorentz`, `(n,k) Material`,
`Sampled data` work; `Drude` and `Dispersive` do not exist.

---

## 9. A custom material silently uses the wrong optical constants `[未立项]`

Naming a user-built material `Au` or `Al2O3` collides with the built-in database. Some calls resolve
to the database entry, some to yours.

**Fix**: suffix every custom material (`Au_paper`). See `materials.md`.

---

## 10. GPU engine crashes with a Chinese path `[未立项]`

`.fsp` files and their containing directories must be pure ASCII. Error 1113.
The failure message is often mojibake and does not name the path, which is why it is easy to miss.

**规则化**：这条已上升为规范，见 `docs/constitution/path-conventions.md` §1（纯 ASCII）。
不另开 D 号——它不是缺陷，是硬约束。

---

## 11. Mesh/GPU memory explosion from a stray short wavelength `[未立项]`

A minimum wavelength of 100 nm in a mid-IR model makes `mesh accuracy 6` cut the mesh to ~2.9 nm and
exhausts 8 GB of VRAM. Check the source's wavelength bounds before blaming the mesh setting.

---

## 12. `run()` returns instantly and nothing was computed `→ D-004`

Signature: no error, no `_p0.log`, `layoutmode != 0`. The project was in layout mode.
Three checks: `layoutmode == 0`, `<name>_p0.log` exists, the log contains `Completed`.

**权威记录**：`defects/D-004-run-silent-failure-is-missing-save-not-session.md`
（该 D 纠正了归因：真前提不是「必须在新会话 run」，而是 **`save` 缺失**）。

---

## 13. O&S result missing / "Visualize" greyed out on the model `[未立项]`

The result name comes from `matrixdataset("<name>")` in the **root** `analysis script`, and the code
must be there — putting it in the `setup script` means it never runs. See workspace `SKILL.md` §5.4.

---

## 14. An all-dielectric metasurface reports T ≈ 0.13 `[未立项]`

**Cause**: the model was built in **reflection geometry** — source above the stack, T monitor below
the substrate. For a metasurface on glass the light must enter through the substrate and be collected
in air; otherwise "T" is measuring the evanescent tail under a 1 µm substrate.

**Measured** (P02, 2026-11-04): reflection geometry → T = 0.13; `mode: transmission` → T = 0.96–0.99.

**Related sign trap**: in transmission mode the R monitor sits *below* the source, so the reflected
wave travels in −z and the monitor returns a **negative** power value. Its magnitude is the
reflectance. The builder now negates it, but any hand-written analysis must do the same.

---

## 15. Reporting "peak A" for a transmissive device `[未立项]`

`A = 1 − R − T` is the **absorber** metric. For a window/metasurface the headline is `T`. Reporting
absorption for a device whose whole point is transmission produces a number (0.13) that looks like a
failure and is actually the wrong quantity. The builder now selects the metric from `simulation.mode`.

---

## 16. A "Save changes?" dialog blocks a headless run `→ D-004`

**Symptom**: a modal "save as <name>" / "save changes?" dialog appears during or after a script that
was supposed to be fully headless, and the process hangs or is killed.

**Cause**: `f.close()` on a session whose project was **modified but never saved**. Creating a
monitor, adding an object, or changing a property all count as modification. `hide=True` suppresses
the window, not the prompt.

**Fix**: save first, then close.

```python
f.save(os.path.join(SCRATCH, "probe_%s.fsp" % tag))   # always, even for a throwaway probe
f.close()
```

**Do not** let a probe save into `packages\` — a stray `.fsp` with a generated name pollutes the
package and confuses the next session. Probe output belongs in `_scratch\`.

**If the dialog is already on screen**: cancel it. Nothing needs saving; the session is disposable.

**权威记录**：`defects/D-004-run-silent-failure-is-missing-save-not-session.md`（与第 12 条同源）。
