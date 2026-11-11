# PLAN-2026-11-09 — 技能精修计划

> 状态：**DONE 2026-11-11**（EXP-01…51 全部落账；D-014 仍待人裁决，属独立支线）
> 位置：本文件原在 `docs/tasks/`，2026-11-11 按 `docs/plans/AGENTS.md` 归位到 `docs/plans/`。

> 本文按轮次追加：§4 是第一轮 45 项，§9 是第二轮，§10 是第三轮。
> 当前状态见 §10.1；未裁决项见 `defects/D-014`。

## 0. 已裁决的四条

| # | 决策 | 依据 | 落地 |
|---|---|---|---|
| D-1 | 并发最大化：会话多、`np` 小                                                               | 16 逻辑核 / 31.8 GiB；P09 实测饱和时 8 进程 7 steps/s vs 1 进程 1000 steps/s | `--max-parallel=12`；`np=1 if active+1>=4 else clamp(14//(active+1),1,4)`，终值由 EXP-27 曲线写死 |
| D-2 | ~~石墨烯 1 nm box 为唯一主路径~~ **已被 EXP-34 推翻，待裁决（D-014）**                                                            | 论文做法；Kubo 自算与课件 σ 表误差 2.1e-6                                    | 2D sheet 移出范围；P09 结果按 1 nm box 复核（EXP-34）                                                |
| D-3 | 逐项实验制                                                                          | 你的要求                                                            | `experiments/EXP-NN/{design.md,result.json}`，三条件：有数字 / 有负对照且它确实失败 / 可重跑                  |
| D-4 | **构建与出图拆两处补**：`fsp-build`（spec→`.fsp`，不跑）+ `figure`（数据→图，无引擎）；`field-map` 只算不画 | §1 盘点：builder 已有大半，但缺 `--build-only`、监视器只有 R/T；出图 0 行           | 8 技能 → 11 技能；`unitcell` 的 builder 抽到 `_shared/fsp_build.py`，避免第二份实现                      |

---

## 1. 现状盘点：到底缺什么（直接回答「有没有一键出图」）

### 1.1 已存在

| 能力            | 位置                                  | 说明                                                                             |
| ------------- | ----------------------------------- | ------------------------------------------------------------------------------ |
| spec → 材料     | `run_fdtd_sweep.py:build_materials` | `builtin` / `drude` / `constant_nk` / `constant_eps` / `sampled_nk` 五种         |
| spec → 几何     | `:build_objects`                    | `box` / `polygon` / `cylinder` / `sphere` / `ellipse`；坐标支持表达式（`ev()`）          |
| spec → 求解器    | `:build_simulation`                 | FDTD 区域、六面 BC、`mesh accuracy`、`auto shutoff`、`simulation time`、`mesh_override` |
| spec → 源与监视器  | 同上                                  | 平面波（**仅波长口径**）、`R`/`T` 两个功率监视器（`2D Z-normal`）                                  |
| spec → `.fsp` | `:run_point`                        | **只在仿真跑完后 `save`**，没有「只建不跑」的路径                                                 |

### 1.2 不存在（这就是要补的）

| 缺口                                                                | 后果（来自 P05/P06/P09）                                                            |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **`--build-only`**：建出 `.fsp` 但不起跑                                 | 想要「一份可交付的模型文件」必须真跑一次；P06 单次 876 s，纯为了拿 `.fsp` 也要付这个代价                         |
| **监视器泛化**：`field`（`addprofile`）/ `index` / `H` / `mode expansion` | P05/P06 的场图全靠手写脚本加监视器；P05 的 `(1429,1,758,1,3) complex128` 没有任何现成入口            |
| **2D `add2drect`**                                                | P09 整类 2D 周期结构建不出来                                                            |
| **`Conductive 3D`**（Au σ=4e7 单标量）                                 | P09 只能用 Drude 占位，并留一条 `missing[]`                                             |
| **Kubo 石墨烯（1 nm box）**                                            | 同上；P09 手写 250 行                                                               |
| **频域源**（`frequency start/stop`）                                   | P09 3.6 THz 只能人工换算成 83.33 µm，`300/λ` 类错误温床                                    |
| **结构组 / `script`**                                                | P06 的涡旋相位写在 `structure group.script` 里，builder 无法表达                           |
| **出图（结构示意 / RTA 谱 / 相位 / 场热图 / FOM 曲线 / 论文对比）**                   | 全仓 `matplotlib/savefig/plt.` 命中 = **0**（门禁脚本里的是字符串匹配误命中）；P02/P04/P05/P06 各写一遍 |

**结论**：一键「建 `.fsp`」目前是**半成品**（必须顺带跑一次，且监视器/材料受限）；一键「出图」**完全没有**。
所以不是补一个技能，而是补两块能力 + 一次实现抽取。

---

## 2. 并发模型（沿用 v2，未改）

```python
mem_gib(cells) = cells * 2.9e-7            # 3.13 Mcell → 0.908 GiB（P06 实测标定）
np   = 1 if (active+1) >= 4 else clamp(14 // (active+1), 1, 4)
admit if active < 12 and avail_mem - mem_gib*1.5 > 2.0 GiB else 等 15 s 重试
```

配套：`_shared/.slots/`（目录原子占槽）、`<out>/.lock`（pid+心跳，30 min 僵尸回收）、
`_scratch/.runs/<id>.json`（cells/np/起止/峰值内存，EXP-27 的数据源）。

---

## 3. 新技能设计（D-4 的落地）

> 路径约定：下文命令里的 `<待建技能>` 是占位符（技能尚未创建）。
> 创建后必须替换为真名并同步 `skills/INDEX.md`；在技能目录存在而脚本缺失时，
> `[K15]` 仍会 FAIL —— 占位符只是避免「计划即声明」被误判，不是豁免。
### 3.1 `fdtd-lumerical-fsp-build`（stage 2，一键建 `.fsp`，不跑）

```
python <待建技能>/scripts/build_fsp.py \
    --spec cases/P09/config/spec_p09.json --out build/p09.fsp --check --json
```

| 能力 | 判据 |
|---|---|
| `--build-only`（默认）：建完即 `save` 关闭，**不调 `run`** | 无 `_p0.log`；`layoutmode==1`；wall < 30 s |
| `monitors[]` 泛化 | `type: power｜field｜index`，`field` 走 `addprofile` 并记分量 |
| 材料扩 | `conductive_3d`（σ 标量）、`graphene_kubo_1nm`（含 `mu_c/gamma/T/delta`） |
| 几何扩 | `add2drect`（零厚度片）；`group{children[]}` + `script` |
| 源扩 | `frequency_range`（THz 口径，内部统一转 Hz，**不再让人手算 300/λ**） |
| `--check` | 建完立刻用 `inspect_fsp` 反解析同一 `.fsp`，与 spec 字段级 diff；不一致 → exit 1 |

**实现纪律**：builder 本体抽到 `_shared/fsp_build.py`，`run_fdtd_sweep.py` 改为 import 它。
禁止两份实现（D-005/D-006 已因同因复发两次）。

### 3.2 `fdtd-lumerical-figure`（stage 5，数据→图，零引擎）

```
python <待建技能>/scripts/make_figure.py \
    --kind stack|spectra|phase|field|fom|compare \
    --manifest m.json --metrics metrics.json --fields f.npz --out figs/ --json
```

| 图型 | 输入 | 说明 |
|---|---|---|
| `stack` | `manifest.json` | 层序/厚度剖面 + 俯视单胞示意（不需要 `.fsp`） |
| `spectra` | `metrics.json` / `*_curve.csv` | R/T/A vs λ，峰值标注 |
| `phase` | `phase.csv` | φ(λ) 或 φ(x) 展开相位 |
| `field` | `fields.npz` | 切片热图（`--slice axis,index`） |
| `fom` | `fom_curve.csv` | 迭代轨迹 |
| `compare` | 两列数据 | 论文值 vs 实测，带 Δ 标注 |

**硬约束**：`Agg` 无头后端；单位一律 µm/THz；**图上峰值读数必须与 `metrics.json` 数值一致**
（EXP-45 自动比对，容差 1e-6），禁止「图上好看、数对不上」。

### 3.3 `field-map`（stage 3.5）职责收缩

v2 里它产出 `fig.png`，与 `figure` 重叠。v3 改为：**只算不画** →
`fields.npz + metrics.json`（CP 分解、焦距、相位斜率比、旋向判别），出图交给 `figure`。

---

## 4. 实验矩阵（45 项）

类型：`E0` 静态/单元（秒，无引擎）；`E1` 开工程不跑（分钟）；`E2` 小仿（分钟级）；`E3` 长跑（小时）。

### 批次 0 — 基座与纯静态（12 项，全并行，约 3 min）

| EXP | 对应 | 类型 | 对照 / 负对照 | 判据 |
|---|---|---|---|---|
| EXP-01 | D-3 基座 | E0 | 正：完整 `result.json`；负：删掉负对照字段 | 前者 pass、后者 FAIL |
| EXP-02 | `lumapi_common` 去重 | E0 | 两处 `runpy` 调用 `open_fdtd` 签名一致；全仓 `def open_fdtd` 计数 | 计数 = 1，两处行为一致 |
| EXP-03 | `[R3]` 求解器家族 | E0 | `Lumerical FDTD` vs `v251`（应放行）、`CST` vs `Lumerical`（应拦） | 2 正 2 负全对 |
| EXP-04 | `[R4]` unrun 豁免 | E0 | 负：写 `unrun:true` 但目录里有 `_p0.log` | 必须 FAIL（防伪造豁免） |
| EXP-05 | `[R6]` 成本分级 | E0 | 负：给了 `repeat_skipped_reason` 却判 `reproduced` | 必须 FAIL，只能 `inconclusive` |
| EXP-06 | `[R12]` 解释器路径 | E0 | 文档与脚本各改一版，双向 grep | 文档说「扫」则脚本必须扫，反之亦然 |
| EXP-07 | `QUANTITY_ALIASES` 扩族 | E0 | 5 族 × 各 1 张正卡 + 1 张错列名卡 | 正卡过、错列名卡 FAIL 且指出列名 |
| EXP-08 | `validate_spec` 拦 PLACEHOLDER | E0 | 正：P09 现 spec（含 `PLACEHOLDER`）应 **FAIL**；负：真参数 spec 应过 | 方向必须反过来才算修好 |
| EXP-09 | `metrics` 选键 + 越界报错 | E0 | 负：喂 `T=-0.80, A=1.60`（P07 实测值） | 必须抛出越界错误，不许静默写值 |
| EXP-10 | 监视器-PML 间距 | E0 | 负：`below_structure=0.15 µm` | 拒绝并给出「≥ x µm」的具体数 |
| EXP-11 | 契约 §7 字段表补齐 | E0 | 双向 grep：文档字段 ↔ 脚本读取字段 | 两向皆空 |
| EXP-12 | 脚本内规则表订正 | E0 | 规则表 vs SKILL.md 同句比对 | 一致（当前是「必须新会话」vs「save→run」） |

### 批次 1 — 反解析（11 项，12 路并行，约 5 min）

| EXP | 对应 | 输入 | 对照 / 负对照 | 判据 |
|---|---|---|---|---|
| EXP-13 | 兜底不造指标 | P07 `initial_trial.fsp` | 负：另造有 `R_`/`T_` 命名的 fixture | 前者 `peak_R=null` + `unlabeled`；后者正常出数 |
| EXP-14 | 重复对象 | P05 21 同名 `rectangle` | 负：P01 无重名工程 | 前者 1 条 + `duplicate_name:true`；后者不受影响 |
| EXP-15 | 深度 / `--max-objects` | P06 `fig5.fsp`（约 4500 叶子） | 负：不加上限时耗时应显著更长 | 加上限 < 30 s；stdout 无 `{!!}`；`--json` 可解析 |
| EXP-16 | spectra 模式自洽 | P05/P07 任一 | 负：真 layout 且有 `_p0.log` 的工程 | 前者不再「ok + 未保存」；后者仍正确报未保存 |
| EXP-17 | 有谱不判无谱 | P09 工程（500 点） | 负：P06 真无谱工程 | 前者 `ok`；后者 `no_stored_spectra` |
| EXP-18 | `phase` 进 CORE_PROPS | P05 RCP/LCP | 负：无源的结构工程 | −90 / +90 可读出；后者缺项不报错 |
| EXP-19 | `getmaterial` 字符数组 | P09 `user_Gra2`/`user_Au` | 负：普通 dielectric | 前者读出 50 点 σ + `Conductive 3D`；后者不崩 |
| EXP-20 | 堆栈轴推断 | P09 2D 工程 | 负：P01 仍是 z | P09 轴 = y；P01 轴 = z 不变 |
| EXP-21 | group `script` 进 manifest | P06 `fig5.fsp` | 负：无脚本的 group | 能查到八分圆参数；后者 `script: null` |
| EXP-22 | `run` 后不 `save` | 小模型 | 正负成对：`save` 后 run vs run 后不 save | 丢数据 → 升 CRITICAL；不丢 → **删掉这条建议** |
| EXP-23 | 相对路径 `save` | 小模型 | 负：绝对路径 | 相对路径成功或明确报「请用绝对路径」 |

### 批次 2 — 小仿与并发（9 项，6 路并行；EXP-27 独占）

| EXP | 对应 | 对照 / 负对照 | 判据 | 机时 |
|---|---|---|---|---|
| EXP-24 | 盒在域外 | 负：正常盒子 | `setnamed("FDTD","z",4.0)` 必须 FAIL | 3 min |
| EXP-25 | 监视器进 PML | 负：正常间距 | 必须 FAIL（当前 `getresult` 全空但三判据过） | 3 min |
| EXP-26 | 正常流程不被误伤 | P01 既有口径 | 四判据全过，`peak_A=0.8196016` 逐位不变 | 5 min |
| EXP-27 | **并发吞吐曲线**（独占） | 1×8 / 2×4 / 4×2 / 8×1 | 输出「会话数 × np → 总 steps/s」，据此写死 `np` 查表 | 4 × 3 min |
| EXP-28 | P09 API 坑 | 负：逐条设参（已知可用） | `setnamed(dict)`、`PlaneSource.frequency` 各有明确结论 | 8 min |
| EXP-29 | `--dump-npz` | 负：`max_array_items=2000` | 场数组完整落盘（>100 MB）+ `sha256`；JSON 只剩元数据 | 5 min |
| EXP-30 | `layoutmode=0` 复用 | 负：`--force` | 复用 0 s 且 `reused_stored=1`；`--force` 真重算 | 5 min |
| EXP-31 | `cases/` 写入闸 | 负：`--out` 指 `_scratch` | 前者 exit 2（与 `run_lsf.py` 对齐） | 1 min |
| EXP-32 | `caliber{}` 直出卡字段 | 负：缺 `caliber` 的旧 config | 输出可被 `check_reproduction` 读取 | 2 min |

### 批次 3 — 长跑（4 项，2–4 路并行，约 80 min）

| EXP | 对应 | 输入 | 判据 | 机时 |
|---|---|---|---|---|
| EXP-33 | `field-map` 回归 | P05 RCP + LCP | 焦距 9.30 µm、相位斜率比 −0.958、旋向判别与手工一致；`-bk` 无实焦 | 2 × 70 min |
| EXP-34 | 石墨烯 1 nm box | P09 同网格 | Δpeak ≤ 10 GHz 且 ΔA ≤ 0.01 → 可用；否则写明差多少 | 2 × 11 min |
| EXP-35 | Au `Conductive 3D` | P09 | 与 Drude 版 R 差 < 契约 §5 容差 | 1 × 11 min |
| EXP-36 | 出图收编 | 4 包 `metrics.json` | 同一脚本出 4 张图；缺列报错 | 无引擎 |

### 批次 4 — 大仿回归（1 项，全绿后跑）

| EXP    | 对应        | 判据                                            | 机时     |
| ------ | --------- | --------------------------------------------- | ------ |
| EXP-37 | P06 口径缩小版 | 3.13 Mcell、876 s 内收敛（`8.57e-06 < 1e-5`）、四判据全过 | 15 min |
|        |           |                                               |        |

### 批次 5 — 一键建 `.fsp` 与一键出图（8 项，6 路并行，约 20 min）

| EXP | 对应 | 类型 | 输入 / 对照 / 负对照 | 判据 |
|---|---|---|---|---|
| EXP-38 | **builder 抽取回归** | E1 | 正：抽取后用 P01 spec 重建；负：旧脚本产物 | `inspect_fsp` manifest 字段级一致；`peak_A=0.8196016 @ 6.1515 µm` 逐位不变 |
| EXP-39 | `--build-only` 语义 | E1 | 正：build-only；负：旧路径（跑完才存） | 无 `_p0.log`、`layoutmode==1`、wall < 30 s；旧路径 wall > 300 s |
| EXP-40 | 监视器泛化 | E1 | 正：`power+field+index`；负：只给 `power` | 三类 `getresult` 都非空；`field` 键名与 EXP-28 一致；负例产物少一类但不报错 |
| EXP-41 | 新材料类型 | E1+E2 | 正：`conductive_3d` + `graphene_kubo_1nm`；负：Drude 占位 | 读回 `type=Conductive 3D`、σ=4e7、50 点 ε 表；负例字段缺失即 FAIL |
| EXP-42 | 2D rect + 频域源 | E1 | 正：`dimension=2D` + `frequency_range=[3,8] THz`；负：波长口径 | 读到 `dimension=2D`、频区间 3–8 THz（±1%）；负例仍是波长 |
| EXP-43 | `--check` 自检 | E1 | 负：某 `span` 改错 10% | 必须 exit 1 并指出字段名与两侧数值；不改时 exit 0 |
| EXP-44 | 六类图各一张 | E0 | 正：P01 + P05 两套数据；负：删 `metrics.json` 一列 | 6 类图全生成非空；缺列 → 报错并指出列名，不画空白 |
| EXP-45 | 图数一致性 | E0 | 负：把 csv 峰值挪 5% | 图上标注与 `metrics.json` 差 > 1e-6 时 FAIL |

**为什么 EXP-38 必须最先做**：抽取 `fsp_build.py` 是本计划唯一会动到「已跑通建模路径」的改动。
它一旦引入偏差，批次 1–4 的所有结论都不可信，所以用 P01 逐位数值做闸门。

---

## 5. 墙钟预算

| 批次 | 串行 | 并行 | 备注 |
|---|---|---|---|
| 0 静态 12 项 | 3 min | 3 min | 无引擎 |
| 1 反解析 11 项 | 25 min | 5 min | 12 路 |
| 2 小仿 9 项 | 55 min | 18 + 12 min | EXP-27 独占 |
| 3 长跑 4 项 | 160 min | 80 min | 2–4 路 |
| 4 大仿 1 项 | 15 min | 15 min | 22 Mcell ≈ 10 GiB，独占 |
| 5 构建/出图 8 项 | 25 min | 20 min | 6 路；仅 EXP-41 需短跑 |
| **合计 45 项** | **~4.9 h** | **~2.5 h** | 失败可单点重跑 |

---

## 6. 不做

1. **不做 2D sheet 石墨烯**（D-2）：`add2drect` + 面电导率整条移出；放弃 Δ→0 严格性已记录。
2. **不为迎合论文调参**：P09 峰位 3.511 vs 3.6 THz 归因 FMM↔FDTD。
3. **不新建第二个 builder**：`fsp-build` 是唯一实现，`unitcell` 改为 import，不许复制。
4. **不让 `field-map` 画图**：算与画分离，否则「同一张图两份代码」会立刻复发。
5. **不把 `figure` 做成论文排版工具**：只出单图；拼版留给人或后续迭代。

---

## 7. 停止条件

| 触发                                  | 动作                       |
| ----------------------------------- | ------------------------ |
| EXP-38 出现任何数值差异                     | 停：抽取失败，回退查根因，不许「差异可解释」放行 |
| EXP-22 证明「run 后不 save 不丢数据」         | 删掉该建议，记「报告误判」            |
| EXP-27 显示 `np=8` 不更快                | `np` 上限降到 1–2，按曲线定       |
| EXP-34 显示 1 nm box 与 sheet 差 > 0.01 | 停并回报，不自行维持 D-2           |
| EXP-45 图数与台账不一致                     | 该图不许进任何报告，先修绘图           |

---

## 8. 下一步

1. EXP-01/02（基座 + 去重）→ 批次 0（12 项静态，秒级）。
2. **EXP-38 单独先跑**：它是后续一切的前提。
3. 批次 1 → 2 → 3 → 5 → 4。
4. 每批回报：`verdict` 表 + 墙钟 + 失败归因；不写「已确认」。

---

## 9. 第二轮（2026-11-10，收尾 D-007 / D-008 / D-009）

第一轮 45 项里 39 pass / 1 fail（D-007）/ 5 未执行（D-009）。第二轮只做「第一轮做不了」的事，
编号接在后面，不重排既有实验。

| EXP | 修什么 | 判据 | 依赖 |
| --- | --- | --- | --- |
| EXP-46 | D-008：builder 支持 2D（z 为不变轴），抽 `propagation_axis` | 2D 建出 `layoutmode=1`、`--check` 0 mismatch、3D 回归 0 diff、3 条负对照按预期失败 | 无 |
| EXP-47 | D-007：`inspect_fsp` 在 4500 对象工程上 273 s → < 30 s | `fig5.fsp` 墙钟 < 30 s 且监视器集合与慢路径逐名相同 | 无 |
| EXP-48 | D-013：`sampled data` 材质收 ε 不收 (n,k) | `getindex` 反查每点相对误差 < 5%，负对照（灌 n+ik）必须差一个开方关系 | 无 |
| EXP-49 | `no_stored_spectra` 的原因文案把「未跑过」写成「非功率监视器」 | 32 个未跑过工程：旧文案命中 32/32、新文案 0/32 且 32/32 说「未跑过」 | 无 |
| EXP-33 | P05 场图回归（stage 3.5 `field-map` 建好后） | 焦距 9.30 µm、相位斜率比 −0.958、`-bk` 无实焦 | 新技能 |
| EXP-34 | 石墨烯 1 nm box 复核 P09（解锁条件已满足：EXP-46） | 3.6 THz 处 A=1±0.02 | EXP-46 + EXP-48 |
| EXP-35 | Au `Conductive 3D` vs Drude（同一 EXP-46 的 2D 模型） | 两条 T 谱在 3–8 THz 内 `max|ΔA|` 报数，不设阈值只报数 | EXP-46 |
| EXP-27 | 并发吞吐曲线 | 输出「会话数 × np → steps/s」表并据此写死 `np` | 机器独占 |
| EXP-37 | P06 口径缩小版大仿回归 | 与 P06 报告口径一致 | 机器独占 |

顺序：EXP-46 → EXP-47 → EXP-48 →（EXP-34/35）→ EXP-27 → EXP-37 → 建 `field-map` 后 EXP-33。
`check_experiments.py` 的 D1 只查「计划里有的必须有账」，所以新实验必须先登记到本表
再开工——否则新实验对门禁不可见。

**EXP-48 是计划外新增**：EXP-34 跑到一半发现 1 nm box 与 sheet 差 500 倍，追下去发现
builder 把 (n,k) 灌进了收 ε 的属性（D-013）。按「正确性先于门禁」的排序，先修它再回来跑 EXP-34。

### 9.1 第二轮结果（2026-11-10）

| EXP | verdict | 关键数 |
|---|---|---|
| EXP-46 | pass | 2D `layoutmode=1.0`、`--check` 27/27、P01 3D 回归 10 对象 0 diff、3 条负对照按预期失败 |
| EXP-47 | pass | fig5 273 s → **1.7 s**；P01/P05/P06/P09 谱逐字节相同；P05 同名检测保留 |
| EXP-48 | pass | 引擎 `getindex` 反查 k = 51.0964/36.6879/22.7216 vs 解析 51.0961/36.6878/22.7218；负对照（灌 n+ik）差 90% |
| EXP-34 | **fail** | 1 nm box vs sheet：Δpeak 3588 GHz、ΔA 0.951；原因 D-013（已修）+ D-014（**待裁决**） |
| EXP-49 | pass | 32 个 2021 未跑过工程：旧文案 32/32 误报「非功率监视器」→ 新文案 0/32，32/32 说「未跑过」 |

EXP-34 触发了第 7 节的停止条件「差 > 0.01 → 停并回报，不自行维持 D-2」，因此第二轮在
D-014 处停下等人裁决。EXP-35 依赖同一石墨烯表示，一并挂起。

## 10. 第三轮（2026-11-10 晚，补能力空位）

第二轮结束后做了一次技能库盘点（10 技能 / 4357 行 / 49 EXP / 8 门禁 6 绿 2 红）。
两项红灯都是**数据缺口**，另有一处**能力空位**（`INDEX.md` 里已标「仍空缺」的 stage 3.5）。
本轮先补空位，再把四个复现的账落位。D-014 的石墨烯路线**由人裁决**，本轮不动。

| EXP | 补什么 | 判据 | 依赖 |
| --- | --- | --- | --- |
| EXP-50 | 新技能 `fdtd-lumerical-field-map`（stage 3.5）：焦距/焦斑/相位面/OAM/k 空间，收编 P05 与 P04 两份手写脚本 | 5 条解析真值（高斯 FWHM、f=10 µm 焦、ℓ=3/−2、20° 斜入射）+ P05 RCP 9.25±0.3 / LCP 4.85±0.3 且两者差 >3 µm + 4 条负对照按预期失败 | 无 |
| EXP-51 | 四个复现的账落位：`results/<Pkg>/<日期>/` + `acceptance.json`；`check_results_layout` 与 `check_acceptance` 转绿 | 两项门禁 FAIL=0；P05/P06/P07/P09 的 `acceptance.json` 每项 `measured` 都能追到一条命令 | EXP-50（P05/P06 的量需要它算） |

顺序：EXP-50 → EXP-51。EXP-33（P05 场图回归）在 EXP-50 之后解锁，但它要跑仿真，
本轮只在 EXP-50 里用**已存在的** P05 dump 复算，不重跑引擎。




### 10.1 第三轮结果（2026-11-10 晚）

| EXP | verdict | 关键数 |
|---|---|---|
| EXP-50 | pass | 9/9 判据；解析真值 9 条（高斯 FWHM 差 0.0003 µm、f=10 µm 焦 z=10.000、ℓ=3/−2 误差 7e-5、20° 斜入射 kx/k0=0.342019 vs 0.342020）；P05 RCP `z_focus=9.30 µm`（论文 9.3）、`gain=5.21`、`fwhm=0.812`、`\|slope\|=1.047`；`--fsp` 与 `--npz` 的 `z_focus` 差 **0.0**；4 条负对照按预期失败。顺带修 D-015 |
| EXP-51 | pass | `check_results_layout` 49→**0**（45 个文件 + 4 个目录归位，3 个 `index.json`）；`check_acceptance` 4→**0**（30 项验收：16 PASS / 6 FAIL / 8 N/A，全部照抄报告验收表）。**八门禁首次全绿** |

技能数 10 → **11**（stage 3.5 补齐），脚本 4357 → ~5200 行。
`D-014`（石墨烯表示）仍待裁决，本轮未动；P05/P06/P07/P08/P09/P10 仍无
