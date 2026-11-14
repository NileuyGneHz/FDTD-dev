# P01 复现过程 · skills 精进问题清单（2026-11-09）

> 用途：给 Nileuy 逐条精进 skills 的**工单**。每条都来自本次复现**实际踩到并有证据**的现象，
> 不是推测。每条给出「建议改动点」和一条可执行的**验收判据（负对照自测题）**。
> **本轮未修改任何 skill** —— 按你的要求，精进由你执行，我只把问题和证据摊开。
>
> 与 `repro_report_2026-11-09.md` §6 的区别：那份是按「信息缺失 / 依赖不可用 / 运行结果偏差 /
> skills 能力不足 / 其他阻塞」分类的**汇报**；这份是按「改动优先级」排序的**施工清单**。
>
> **人裁决（2026-11-09，Q4 已关闭）**：接受 Lumerical ~0.82 为复现基准，显式标注求解器口径差异。
> 因此「本机无 CST 2009」不再算阻塞；剩下的是**把这个裁决写进验收策略与报告模板**（见 G-13）。

## 0. 排序依据

本次**没有「算错数值」类问题**（四条独立 Lumerical 结果在 6 µm 处极差 0.0027，两次独立运行逐位一致）。
所以按项目铁律往下推一层：先修**会让人拿到假绿灯 / 漏用现有能力**的（P0），
再修**需要新增能力**的（P1），最后修**工程化体验**（P2）。

| 档 | 条数 | 含义 |
|---|---|---|
| **P0** | 5 | 误导性绿灯、官方能力被文档埋没、已验证知识没落地 → 影响判断，先修 |
| **P1** | 4 | 真实能力缺口 → 需要立项，按 Fig.3 / 4 / 5 的结论重要性排 |
| **P2** | 4 | 体积、契约漂移、校验 checklist、状态标记 → 可批量修 |

---

## P0 — 先修（影响判断）

### G-01 · `run_lsf.py` 的 `allow_cases_write` 开关没写进 SKILL.md

| 项 | 内容 |
|---|---|
| 问题现象 | `fdtd-lumerical-headless/SKILL.md` 的「三条安全闸」把 `config.fsp 在 cases/ 内` 写成**无条件 exit 2**，我据此判断「官方 .lsf 唯一入口在本次交付场景不可用」，于是绕过它自己写了 `_scratch/p01_repro/verify_lsf.py`。实际上脚本有官方豁免开关。 |
| 证据 | `skills/fdtd-lumerical-headless/scripts/run_lsf.py:32-36, 198, 212-215, 327`：config 支持 `allow_cases_write=true`；`--help` 也列了它。全库 Grep `allow_cases_write` 只命中该脚本，**SKILL.md 零命中**。上轮汇报 §6-E 的「规则互相打架」结论因此被加重了。 |
| 根因 | 脚本加了开关，SKILL.md 的三条闸表格没同步。属文档滞后，不是能力缺失。 |
| 影响范围 | 任何「在 `cases/` 内对已交付工程跑只读验证脚本」的场景；agent 会放弃官方入口、自造脚本，审计链断掉。 |
| 本次规避 | 一次性脚本 `f.load` + `f.eval(lsf)` + `getv`，能跑通但不在技能覆盖内。 |
| 建议改动点 | `skills/fdtd-lumerical-headless/SKILL.md`「三条安全闸」表格 → 补第 4 行 `allow_cases_write`，并给一个「cases/ 内只读验证」示例 config。 |
| 验收判据（自测题） | 拿 `verify_repro.lsf` + 一份 `{"fsp":"cases/.../P01_Absorber_042_repro.fsp","allow_cases_write":true,"read":["peak_A"]}` 跑 `run_lsf.py --dry-run` 与正式跑，必须 `exit 0` 且读回 `peak_A=0.8069`；把 `allow_cases_write` 删掉必须 `exit 2`。 |
| 优先级 | **P0** |

### G-02 · `build_fsp.py --check` 只查几何，34 项绿灯被当成全量验收

| 项 | 内容 |
|---|---|
| 问题现象 | 我在派生 spec 里新增了 `E_spacer`(field) / `nidx_spacer`(index) 两个监视器、把 `monitors` 从 dict 改成 list，`--check` 依然 `checked=34, mismatches=0`。绿灯只证明「几何数字没抄错」，不证明材料、边界、源、监视器、收敛设置与论文一致。 |
| 证据 | `skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py:65-98` `expected_properties()`：只收 objects 的 center/span/radius/height + `FDTD x/y span` + `mesh accuracy` + `dimension`。`P01_Absorber_042_repro_build.json` 的 `check.checked=34`。另：`validate_spec.py --strict` 也报 `0 error(s), 0 warning(s)`，但它只做结构与量纲 plausibility。 |
| 根因 | `--check` 的设计意图是「抓文件与 spec 不一致」，但 SKILL.md 把它写成「交付前最小验证链」，读者自然理解成全量验收；且**不输出未检查项**。 |
| 影响范围 | 所有 build-only 交付。项目记忆里已有「ALL GREEN 只证明扫描范围内没问题」的教训，这次是同一类病灶第 4 次。 |
| 本次规避 | 另跑 `inspect_fsp.py` 反解析 + `--only-check` + 手动读 `verification.json` 补齐。 |
| 建议改动点 | ① `expected_properties()` 纳入 `materials`（`getmaterial` 数值）、`bc`、`source.wavelength_range/npts/polarization`、`monitors` 类型与 z、`auto shutoff min`、`simulation time`、`mesh_override`；② manifest 增加 `not_checked[]` 字段，把没查的项显式列出。 |
| 验收判据（自测题） | 把 `Al2O3_paper.k` 从 0.0302 改成 0.0332（+10%）或从 spec 删掉 `E_spacer`，重跑 `--check` **必须 exit 1** 并打印 `object/property/expected/actual`；当前两处改动都是 exit 0。 |
| 优先级 | **P0** |

### G-03 · `inspect_fsp.py` 把 index 监视器当成功率监视器，误报 `Can not find result 'T'`

| 项 | 内容 |
|---|---|
| 问题现象 | 反解析交付工程时输出 2 条 issues：`非功率监视器 ['nidx_spacer'] 不产生 R/T 谱` 与 `功率监视器读取失败：{'nidx_spacer': "Can not find result 'T' in the result provider 'nidx_spacer'"}`。第一条是正确排除，第二条说明**同一个对象又被塞进了功率监视器读取分支**。 |
| 证据 | `_scratch/p01_repro/inspect/` 的 stdout：`status_counts={"ok":1}`、`spectra_status="ok"`、谱完整读回（peak A 0.80694）——工程没坏，是工具自相矛盾的告警。 |
| 根因 | 按类型排除逻辑只排除了 `field`，没排除 `index`；或排除后的对象仍进入 `getresult(name,"T")`。 |
| 影响范围 | 任何带 index / 非功率监视器的工程；人会先怀疑工程坏了，或学会忽略 issues（项目记忆：「门禁若把合法引用和幽灵入口判成同一种错，人会先学会忽略告警」）。 |
| 本次规避 | 在汇报里手工标注「issues 属工具误报，非工程损坏」。 |
| 建议改动点 | `skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py`：功率谱读取改成显式白名单（只取 `DFTMonitor` / power 类型），读之前先枚举可用 result 名。 |
| 验收判据（自测题） | 对带 `E_spacer`(field) + `nidx_spacer`(index) + `R`/`T`(power) 的交付工程跑反解析，`issues` 必须为空、`spectra_status=ok`、4 个监视器全部列出；再故意把 `R` 监视器删掉，必须报「缺功率监视器」而不是静默 ok。 |
| 优先级 | **P0** |

### G-04 · `reference_spec` 自我比对产生「无信息量绿灯」

| 项 | 内容 |
|---|---|
| 问题现象 | 我给 `inspect_fsp.py` 的 `reference_spec` 就是**生成该工程的** `spec_repro_p01.json`，于是 `all_settings_match=true` / `all_materials_match=true` 是同义反复，却被输出成「校准通过」。 |
| 证据 | `_scratch/p01_repro/inspect/` stdout：`diff.settings_mismatches=[]`、`all_settings_match=true`、`all_materials_match=true`，同时 `functional_layers_match=null`（见 G-06）。 |
| 根因 | 工具不区分「独立参照系」与「工程自身的输入」；SKILL.md 只说「可选 `reference_spec`」，没说必须来自独立来源。 |
| 影响范围 | 所有用自建 spec 做 diff 的复现；绿灯会把「我照着自己抄了一遍」误报成「与参考工程一致」。 |
| 本次规避 | 另外用课程工程 `infrared_perfect_absorber.fsp` 的已存谱数值做人工对照（0.8196 / 0.7174）。 |
| 建议改动点 | ① `inspect_fsp.py` 增加 `self_reference` 检测（比对 spec sha 与 `*_build.json` 的 `spec_sha256`，或检查 spec 路径是否在同目录），命中时把 diff 标 `informational` 并给 WARN；② SKILL.md 写死「`reference_spec` 必须来自独立来源」。 |
| 验收判据（自测题） | 用工程自身 spec 跑 diff → 输出 `self_reference=true` 且 diff 不参与「校准通过」判定；换 `cases/metasurface/P01_Absorber_042/config/spec_p01.json`（独立基线）→ 输出 `self_reference=false`。 |
| 优先级 | **P0** |

### G-05 · 已验证的引擎行为只留在日志，没进 SKILL.md → 同一坑重复踩

| 项 | 内容 |
|---|---|
| 问题现象 | 本轮实测证伪了我上一轮的判断（详见 §1 更正）：`run_fdtd_sweep.py` 产出的 .fsp **确实含已存谱**。而 `.workbuddy/memory/2026-11-09.md` 17:20 段早就记着 **EXP-22「run 后不 save 不丢数据」**，但这条结论只留在日志，没进 `fdtd-lumerical-headless/SKILL.md`、没进 `references/lumerical_api_ref.md`、没进任何 checklist，所以我又推了一遍错误结论。 |
| 证据 | `_scratch/p01_repro/probe_sweep_fsp.py` 输出：`bytes=83725458`、`layoutmode=0.0`、`has_stored_R_result=True`。项目日志 2026-11-09 17:20：「run 后不 save 不丢数据（EXP-22）→ P06 那条建议作废」。 |
| 根因 | 「实验结论 → 技能正文」没有强制落地环节。项目有 `check_experiments.py` 管实验台账，但没有「verdict=pass 的结论必须挂到某个 SKILL.md 段落」的门禁（repro-card 的 `training_items` 是手工填 `landed`）。 |
| 影响范围 | 所有跨会话复现；知识存在但检索不到，等于不存在。 |
| 本次规避 | 本轮补做实测证伪，并把更正写进本清单与 memory。 |
| 建议改动点 | ① 把 EXP-22 结论写进 `fdtd-lumerical-headless/SKILL.md` CRITICAL 段（「工程 `save()` 过之后，`run()` 结束引擎会把结果写回该 .fsp，不需再 `save()`；未 `save()` 过才静默失效」）；② `tools/check_experiments.py` 或 `check_skill_contract.py` 增加「`training_items.landed=true` 的 `target_path` 必须含该结论关键词」的弱校验。 |
| 验收判据（自测题） | 在 `headless/SKILL.md` Grep `EXP-22` 或「自动写回」必须命中；把 `save()` 从建模脚本里删掉跑一次，必须仍报 `layoutmode=1` + 无 `_p0.log`（负对照保留原结论）。 |
| 优先级 | **P0** |

---

## P1 — 真实能力缺口（需立项）

### G-06 · 层位 diff 对含 `lattice` 键的 spec 恒返回 `unsupported_spec_shape`

| 项 | 内容 |
|---|---|
| 问题现象 | `inspect_fsp.py` 的 diff 返回 `{"status":"unsupported_spec_shape","unsupported_reasons":["spec 含 lattice 键（超胞/晶格形状，扁平层位模型不适用）"]}`，`functional_layers_match=null`；但同一份输出里 `all_settings_match=true`、`all_materials_match=true`。 |
| 证据 | `_scratch/p01_repro/inspect/` stdout。`lattice` 是 model-spec schema 的**必备字段**（P01 原 spec 就有），所以该 diff 在 P01 上永远不可用。 |
| 根因 | 把「有 lattice」当成「超胞/非扁平」的判据，误伤所有普通周期单胞。 |
| 影响范围 | `functional_layers_match` 是回答「`ts` 从哪个面量」的判据（SKILL.md §5），该判据在 P01 上失效 → 校准链断一环。 |
| 本次规避 | 层位一致性改由 `build_fsp.py --check`（34 项）+ 课程工程反解析笔记 `repro-2026-11-07-fsp-calibration.md` 人工互证。 |
| 建议改动点 | `inspect_fsp.py`：把触发条件改成 `supercell.nx>1 or ny>1`；或把「结构 diff 未执行」与「设置 diff 通过」拆成独立字段，不要混在 `all_*_match` 里。 |
| 验收判据（自测题） | 用 `cases/metasurface/P01_Absorber_042/config/spec_p01.json` 对 `model/infrared_perfect_absorber.fsp` 跑 `mode=both`，`functional_layers_match` 必须非 null 且为 `true`（`substrate_mismatch` 单列）。 |
| 优先级 | **P1** |

### G-07 · sweep 只能扫 `parameters`，不能扫仿真设置

| 项 | 内容 |
|---|---|
| 问题现象 | 想检查 A@10 µm（论文 p.2）就必须把源的 `wavelength_range` 从 4–8.5 µm 改到 3–12 µm；但 `run_fdtd_sweep.py` 的 sweep 只对 `spec["parameters"]` 做 `update`，改不了 `simulation.*`。结果 A@10 µm **不可测**，C4 只覆盖一半。 |
| 证据 | `skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py:153-157` `expand()`、`:209-212` `params.update(over)`；`verification.json` 的 `A_at_10um: null`。 |
| 根因 | sweep 空间被定义为「几何参数」，而数值设置（λ 范围 / mesh accuracy / polarization / shutoff）同样是复现里要扫的维度。 |
| 影响范围 | 所有需要「数值收敛对照」「宽谱对照」「偏振对照」的复现；目前只能手改 spec 再跑，破坏可重放性。 |
| 本次规避 | 在 spec 里把「扩到 3–12 µm 重跑」列为待确认 Q3′，未擅自改基线。 |
| 建议改动点 | sweep 支持 dotted path（如 `"simulation.source.wavelength_range": [[3e-6,12e-6],[4e-6,8.5e-6]]`）或加 CLI `--wavelength-range`；`params.update` 处改为按路径写回 deepcopy 的 spec。 |
| 验收判据（自测题） | 一条 `--sweep-json` 同时扫 `ts` 与 `simulation.source.wavelength_range`，输出两点 CSV 的 `lam_um` 上下界必须不同，且 `summary.csv` 两行都收敛。 |
| 优先级 | **P1** |

### G-08 · 无 per-layer 损耗密度、无复 S 参数反演 → Fig.3 / Fig.4 不可复现

| 项 | 内容 |
|---|---|
| 问题现象 | 论文 Fig.3 用反演 S 参数给出 ε₁/μ₁ 在 ω₀ 同时过零、一正一负；Fig.4 给出 6 µm 处逐层 W/m³，结论是 Al₂O₃ 介质损耗比金属欧姆损耗大一个数量级。现有技能链两个都做不了：`R`/`T` 功率监视器只给 `\|S\|²`，`fdtd-lumerical-phase-retrieval` 只做周期单胞的透射相位差 φx−φy，不做 Smith 反演；`_shared/fsp_build.py` 的监视器 `kind` 只有 `power/field/index`。 |
| 证据 | `repro_report_2026-11-09.md` §4 C6/C7 标 `⛔/🟡`；`spec_repro_p01.json` 的 `conclusions` 相应条目；`_shared/fsp_build.py:350-391`。 |
| 根因 | 能力边界，非 bug。 |
| 影响范围 | 论文 4 条物理结论中 2 条（P6、P7）只能定性讲，不能定量验收。 |
| 本次规避 | 加 `E_spacer`/`nidx_spacer` 给场局域的**定性**证据，并在汇报里明确标「不可定量」。 |
| 建议改动点 | ① 监视器 `kind` 增 `pabs`（或分析组算 `Pabs = -0.5*ω*ε0*ε''|E|²` 分体积分）；② 立项「S 参数反演」独立技能，或明确写进 `unitcell-simulation` 的非目标。二者择一，别留模糊。 |
| 验收判据（自测题） | 对 P01 交付工程能输出 `loss_Al2O3 / (loss_cross + loss_ground)` 的数量级，且该比值 > 5；把 Al₂O₃ 的 `k` 设为 0 时该比值必须显著下降（负对照）。 |
| 优先级 | **P1** |

### G-09 · `supercell` 不复制 objects、无 variant 机制 → Fig.5 / A/B 对照建不出来

| 项 | 内容 |
|---|---|
| 问题现象 | 论文 Fig.5 的 UCA/UCB 双尺寸子晶格需要「一个胞内两套不同十字」；去地平面 A/B 对照需要「同一 spec 里 disable 一个对象」。两者目前都只能另写整份 spec。 |
| 证据 | `_shared/fsp_build.py:260-275`：`nx/ny` 只用来乘 `FDTD x/y span` 与源 span；`build_objects()`（`:140-242`）完全不感知 supercell。`fdtd-lumerical-fsp-build/SKILL.md` §6 只说「结构组只写 script 与名字，不展开子对象」，**没说 supercell 不复制几何**，容易误用。 |
| 根因 | supercell 被实现为「把求解区放大」，而不是「把单胞阵列化」。 |
| 影响范围 | C5（地平面必要性对照）、C8（空间/频率选择性）两条结论。 |
| 本次规避 | 报告中标为「需另建 spec / 无法复现」，未硬凑。 |
| 建议改动点 | ① 文档先写死边界；② 若要支持，给 `objects[]` 加 `supercell_index`/`cell_xy` 与 `enabled:false`；③ `run_fdtd_sweep.py` 支持 `variants:[{name,disable:[]}]`，一条命令出 A/B 两条 A(λ)。 |
| 验收判据（自测题） | 一条命令同时输出 `with_ground` / `no_ground` 两条谱，`no_ground` 的 `T` 必须显著 > 0 且 `peak_A` 下降；若两者相同 → 说明 variant 没生效（假轮次，参考项目记忆里「source x span 改了但 T 不动」那类）。 |
| 优先级 | **P1** |

---

## P2 — 工程化 / 体验（可批量修）

### G-10 · 保存已存谱的体积代价没有提示，也没有 slim 选项

| 项 | 内容 |
|---|---|
| 问题现象 | 同一工程 build-only 时 **478,368 B**，写入已存谱后 **83,725,405 B**（×175）。项目硬约束是单文件 > 100 MB 不入库；P01 包本身已因 347 MB 课程主工程达 488.8 MB（`notes/repro-card.md` R-007 待办）。 |
| 证据 | 交付目录两个 `.fsp` 的 `ls -la`；`P01_Absorber_042_repro_build.json` 的 `bytes=478368`。体积主要来自 field/index 监视器的频域场数据。 |
| 根因 | 技能文档没写「保存已存谱会让工程涨两个数量级」，也没提供「只留 R/T 谱、丢掉场原始场数据」的开关。 |
| 影响范围 | 所有「打开即有谱」的交付；接近入库红线。 |
| 本次规避 | 额外交付 478 KB `..._buildonly.fsp`，并在报告 Q8 请人定夺入库版本。 |
| 建议改动点 | ① 文档写明体积预期；② 给 `build_fsp.py` / `run_fdtd_sweep.py` 加 `--slim`（关闭 field monitor 的频域场记录，或保存前清掉非功率监视器结果）；③ manifest 增 `has_stored_results` 字段。 |
| 验收判据（自测题） | 用 `--slim` 产出的工程 < 5 MB 且仍能 `getresult("R","T")` / `("T","T")` 读回完整 91 点谱；不带 `--slim` 时应 > 50 MB。 |
| 优先级 | **P2** |

### G-11 · `getresult` 返回布局的契约在两处文档不一致，且没有公共实现

| 项 | 内容 |
|---|---|
| 问题现象 | `headless/SKILL.md` 写「`getresult("m","T")` 返回 **dict**」；`run_fdtd_sweep.py` 的 `read_power()` docstring 写「returns a **list of dicts** carrying lambda/f/T on v251」，代码里两种分支都留着。我实测是 dict。 |
| 证据 | `skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py:74-84`；`headless/SKILL.md`「读回结果的两条硬事实」；`_scratch/p01_repro/run_and_store.py` 与 `verify_lsf.py` 各写了一份读取逻辑。 |
| 根因 | API 契约没定死，各脚本各自兼容，一次性脚本又各抄一份（项目记忆里「一份实现 + 转发壳」的老毛病）。 |
| 影响范围 | 任何新写的读谱脚本；换 v 版本时容易集体失效。 |
| 本次规避 | 两处一次性脚本各写兼容分支。 |
| 建议改动点 | 把 `read_power()` 提到 `_shared/`（与 `fsp_build.py` 同层），两处 import；统一文档口径并附 v251 实测证据。 |
| 验收判据（自测题） | 全库 Grep `getresult(.*"T"` 只剩 `_shared/` 一处实现；把返回包成 `[dict]` 的假数据喂进去，公共函数仍能正确读出 `lambda`/`T`。 |
| 优先级 | **P2** |

### G-12 · 派生 spec 没走校验器；校验器自身也有盲区

| 项 | 内容 |
|---|---|
| 问题现象 | 上轮我**没有**对 `spec_repro_p01.json` 跑 `validate_spec.py --strict`（流程缺口）。本轮补跑得 `0 error(s), 0 warning(s)`，但它既不认识我新增的 `conclusions` / `targets` / 扩展 `monitors` 字段，也不校验「数值是否等于论文」。另外论文 PDF 0.6 MB 超过 `Read` 工具 256 KB 上限，直接读会失败，SKILL.md 没提示要先用 `extract_pdf_text.py` 转储。 |
| 证据 | `validate_spec.py --strict` 输出；`extract_pdf_text.py` 转储 4 页 `text`（`_scratch/p01_repro/paper_text.txt`）；`Read` PDF 报错 `File content (0.6MB) exceeds maximum allowed size (256KB)`。 |
| 根因 | 交付 checklist 里没有「派生 spec 也要 validate」；校验器只做结构与量纲 plausibility。 |
| 影响范围 | 所有从 PDF 起步的复现；参数抄错但量纲合理时，校验器照样全绿。 |
| 本次规避 | 本轮补跑校验器，并在 `parameters_and_physics.md` 里人工逐项标注论文页码。 |
| 建议改动点 | ① `paper-parameter-extraction/SKILL.md` 的「What done looks like」补一条「任何派生 spec 也要 `--strict`」+ PDF 大文件提示；② `validate_spec.py` 输出 `not_validated_fields[]`；③ 可选 `--paper-values <json>` 交叉校验。 |
| 验收判据（自测题） | 把 `a` 从 2.0 µm 改成 2.5 µm，`--strict` 必须报错（当前不会，仍 0 error）；`not_validated_fields` 必须列出 `conclusions`、`monitors`。 |
| 优先级 | **P2** |

### G-13 · 人裁决没有落到验收策略与报告模板里

| 项 | 内容 |
|---|---|
| 问题现象 | Q4 裁决「接受 Lumerical ~0.82 基准 + 标注求解器差异」是**人**下的，但技能链里没有任何地方记录「基准可以不同于论文值」：`targets` 只存论文数字、`report_template.md` 没有「solver gap」栏、`verify_repro.lsf` 原本把 0.97 当硬门禁 → 打开工程跑验证会一直 FAIL。 |
| 证据 | 本轮已改：`spec_repro_p01.json` 增 `meta.human_verdict` / `acceptance_baseline` / `acceptance_tolerance`，`verify_repro.lsf` 把 0.82±0.02 设为门禁、0.97 降为 INFO。改前脚本必然 `FAIL C1`。 |
| 根因 | Reproduce 模式的「目标」被建模成单一论文数值，缺「论文参考值 / 验收基准 / 裁决记录」三态。 |
| 影响范围 | 所有存在求解器口径差异的复现；不记录裁决，下一轮 agent 会重新把 0.97 当门禁、甚至去调参凑数。 |
| 本次规避 | 手工改交付物的 spec 与 lsf（**未改 skill**）。 |
| 建议改动点 | ① `references/model-spec-schema.md` 给 `targets` 加 `acceptance_baseline` / `paper_reference_value` / `human_verdict` 三字段；② `assets/report_template.md` 加「solver gap / 人裁决」栏；③ `check_reproduction.py` 校验「有 `human_verdict` 时门禁不得指向论文值」。 |
| 验收判据（自测题） | 造一份 `paper=0.97, acceptance_baseline=0.82` 的 spec 跑门禁 → 全绿；删掉 `human_verdict` 后仍用 0.82 当门禁 → 必须 WARN/FAIL（防止无授权私改基准）。 |
| 优先级 | **P2**（但建议与 G-02 同批做，两者都在动 `targets`/验收） |

---

## §1 本轮更正（**我自己的误判，不是 skill 缺陷**）

> 按 `SOUL.md`「错了就当场改，还要改文件」，这一条单独列出，避免它被误当成 skill 工单。

| 项 | 内容 |
|---|---|
| 上轮错误结论 | 「`run_fdtd_sweep.py` 在 `run()` **之前** `save()`，run 后不再 save → 它产出的 .fsp **无已存谱**，所以必须用一次性脚本 `load→run→save` 补齐。」（`repro_report_2026-11-09.md` §6-D 第二行、Q6 的依据之一） |
| 本轮实测 | `_scratch/p01_repro/probe_sweep_fsp.py`：`_scratch/p01_repro/run/point_00_base.fsp` = **83,725,458 B**、`layoutmode = 0.0`、`has_stored_R_result = True`。**该工程本来就含已存谱。** |
| 真实机制 | 工程只要 `save()` 过（拿到磁盘路径），`run()` 结束引擎会把结果写回该 `.fsp`，**不需要再显式 `save()`**；只有「从未 save 过」才静默失效。这正是 `.workbuddy/memory/2026-11-09.md` 17:20 的 **EXP-22** 结论。 |
| 影响 | ① 我写的 `run_and_store.py` 不是必需（直接把 `point_00_base.fsp` 重命名即可作为交付）；② 但它仍提供了**两次独立运行逐位一致**的同输入回归证据，所以保留、不删；③ 上轮汇报里「技能链路缺口 / 规则互相打架」的措辞过重，已在本清单 G-01、G-05 里给出真实根因。 |
| 已改文件 | `spec_repro_p01.json`（裁决）、`verify_repro.lsf`（验收门禁）、`repro_report_2026-11-09.md`（Q4 / 更正）、`.workbuddy/memory/2026-11-09.md`（更正记录）。**skills 本体仍一字未改。** |

---

## §2 一页速查

| ID | 一句话 | 改动点 | 档 |
|---|---|---|---|
| G-01 | `allow_cases_write` 没写进 SKILL.md，官方入口被误判不可用 | `headless/SKILL.md` | P0 |
| G-02 | `--check` 只查几何，34 项绿灯被当全量验收 | `build_fsp.py:65-98` + manifest | P0 |
| G-03 | index 监视器被当成读 `T`，误报 issues | `inspect_fsp.py` 监视器白名单 | P0 |
| G-04 | 自己当自己的 `reference_spec`，diff 是同义反复 | `inspect_fsp.py` + SKILL.md | P0 |
| G-05 | EXP-22 结论只留在日志，没进技能正文 | `headless/SKILL.md` + 落地门禁 | P0 |
| G-06 | 含 `lattice` 就判 `unsupported_spec_shape`，层位 diff 恒失效 | `inspect_fsp.py` 判据 | P1 |
| G-07 | sweep 只能扫 `parameters`，扫不了 λ 范围/网格/偏振 | `run_fdtd_sweep.py:153-157,209-212` | P1 |
| G-08 | 无 per-layer 损耗 / 无复 S 参数反演 | 新监视器 kind + 新技能或明确非目标 | P1 |
| G-09 | `supercell` 不复制 objects、无 variant / disable | `fsp_build.py` + SKILL.md §6 | P1 |
| G-10 | 478 KB → 83.7 MB 无提示、无 `--slim` | 文档 + CLI + manifest 字段 | P2 |
| G-11 | `getresult` 布局契约两处文档打架，读取逻辑各抄一份 | 提到 `_shared/` | P2 |
| G-12 | 派生 spec 漏跑校验器；校验器不查扩展字段/论文数值 | `validate_spec.py` + SKILL.md | P2 |
| G-13 | 人裁决没进 schema / 报告模板 / 门禁 | schema + `report_template.md` + `check_reproduction.py` | P2 |

**建议开工顺序**：G-05 → G-01（先把已有知识/能力补进文档，成本最低）→ G-02 + G-13（一起动 `targets`/验收，避免两次改同一处）→ G-03 + G-04 + G-06（同一份 `inspect_fsp.py`，一次改完）→ G-07 + G-09（同一份 spec/sweep 结构）→ G-10 + G-11 + G-12（批量工程化）→ G-08（立项）。
