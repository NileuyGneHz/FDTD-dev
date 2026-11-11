# PLAN-2026-11-11 — 全息相位恢复技能（stage 1.8）

> 状态：**DONE 2026-11-11**（EXP-52…59 全部落账，--self-test 15/15）
> 位置：本文件原在 `docs/tasks/`，2026-11-11 按 `docs/plans/AGENTS.md` 归位到 `docs/plans/`。

> ⚠️ **文件头部残缺**：本文件现存内容从 §2 开始，**§0（现状）与 §1（目标态）从未写入**，
> 且该文件在损坏时尚未入库，无法从 git 恢复。§7 的「执行记录与判据偏差」排在 §2 之前，
> 是后续追加时的顺序错乱。**不补写 §0/§1**——按 `docs/AGENTS.md` 约束 2，
> 缺失的决策记录不应事后编造；需要时由人补。
> 已开 `defects/D-016` 记录本次盘点发现。

---

## 7. 执行记录与判据偏差（2026-11-11）

### 7.1 落地产物

| 项 | 位置 | 判据 |
|---|---|---|
| 唯一实现 | `skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py` | `--self-test` **15/15 pass**（原计划 9 条，见 7.2-①） |
| SKILL.md | `skills/fdtd-holo-phase-retrieval/SKILL.md` | 6 段骨架，CRITICAL 6 条，正文 < 500 行 |
| 登记 | `skills/INDEX.md` stage 1.8；`agents/fdtd-sim-agent/skills.yaml` | K10 + K17 覆盖 |
| 台账 | `experiments/EXP-52…EXP-59` | `check_experiments.py` 全 pass |

端到端实测（`_scratch/regress/2026-11-11/holo/`）：方框目标 n=256/pad=2/dx=0.4 µm，
GS 200 轮 4 seed，RMSE 1.21277 → 0.39234（逐轮单调，最大回升 −5.86e−5），
`eta=0.9056`、`snr=19.66 dB`；量化 Strehl 0.4052/0.8095/0.9497 vs `sinc²` 0.4053/0.8106/0.9496。
透镜目标（角谱，n=128）：300 轮 plateau，强度 RMSE 0.0323、`eta=0.884`，单次 4 seed 约 12 s。

### 7.2 三处判据偏差（都有数字支撑，不是放宽）

① **self-test 从 9 条扩到 15 条**。新增 GS 收敛（10）、消融负对照（10b）、
正对照 FFT/角谱（11、11b）。理由：「收敛」和「目标按振幅归一化」这两条断言，
不设常驻检查就只能靠人记得；实测 10b 的漂移是**精确 0**，11 的 FFT 残差是**精确 0**。

② **EXP-56 的 pad 判据换成 Nyquist 拒绝**。原判据「pad=1 时边缘能量显著高于 pad=2」
不可测：pad=1 时设计窗与周期复制重合，没有「窗外」可统计。真正的失效模式是
**像面欠采样**，于 `make_grids()` 里做成硬拒绝（`dx_img_max_um`），self-test 5b 覆盖。

③ **EXP-58 的单调性判据从 eta 换成 Strehl**。实测同一相位 L=2/4/8：
`eta_support/eta_cont = 0.8316 / 0.8314 / 0.9546`（**非单调**，L=2 反而略高），
`Strehl = 0.4052 / 0.8095 / 0.9497`（单调且贴 `sinc²`）。
结论：eta 是支持区能量占比（对比度），不是量化效率；拿它比 `sinc²` 是分母错。
运行时硬判据因此定为 `strehl ≤ 1`（数学上不可违反），`strehl/sinc² > 1.05` 只进 warnings。

④ **EXP-59 的「相位 RMSE < 0.1 rad」不成立，换成强度口径**。实测透镜目标：
强度 RMSE 0.032（好），但恢复相位与解析透镜相位差 **1.19 rad**——不是 bug，
是单强度面相位不唯一（目标只约束 `|E|`）。该判据若保留，唯一过法是把阈值放到 1.3，
那就是自欺。现判据：正对照（已知相位回灌 RMSE=0）+ 已知可实现目标的强度 RMSE ≤ 0.05。

### 7.3 落地时抓到的实现缺陷

`target_amplitude()` 最初把**强度**当振幅返回（漏 `sqrt`）。二值目标（0/1 图）
完全看不出——`sqrt(0)=0, sqrt(1)=1`；只有渐变目标才暴露：透镜目标从 0.032 恶化到 0.597。
抓住它的是**正对照**（解析相位回灌），不是任何曲线形状或目视检查。
现固化为 self-test 11；变异测试：删掉 `np.sqrt` 后该条读 0.311/0.349 并 FAIL。
认 4）。**不许无界循环** |
| **作用范围** | 纯标量衍射、单波长、近轴（FFT 角谱/Fresnel）。偏振复用、多波长、非近轴**显式拒绝**（exit 2 + missing[]） |

---

## 2. 技术方案与模块划分

单一实现脚本 `skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py`（**一份实现原则**，
契约 §4-11），内部按函数分层，不拆多文件（参考 field_map.py 的单文件模式）。
依赖：numpy + matplotlib（已有，零新增）。

```
目标图(png/npz) ──▶ [1] target  ──▶ [2] propagate ──▶ [3] gs_core ──▶ [4] metrics ──▶ holo_metrics.json
                          │              │                │  ▲
                          ▼              │                ▼  │ 反馈
                     预处理/归一          │           [5] quantize ──▶ quantized_phase.csv
                                          │                │
                                          └──── 采样网格定义 ┘
                                                          └─▶ （占位）映射表 → 技能B
```

| # | 模块 | 职责 | 关键输出 |
|---|---|---|---|
| 1 | `load_target()` | 读 png（PIL 退化到 matplotlib.imread）/ npz；灰度化；重采样到 `--grid-n`；**能量归一**到 1 | 目标振幅 `A_t`（非负实数） |
| 2 | `make_grids()` | 统一物理↔像素换算：`dx_um`、`f_um`、`lambda_um` → 全息面/像面网格；零填充因子 `--pad`（默认 2） | grids dict（**唯一**定义分辨率的地方） |
| 3 | `gs_iterate()` | 迭代主循环：随机初相 → FFT 传播 → 像面换振幅 → 反传 → 全息面取相位（+ 可选均匀振幅约束） | `phase`（连续）、`rmse_hist[]`、收敛标志 |
| 4 | `eval_recon()` | 用所得相位正向传播一次，算指标：**衍射效率 η = 信号区能量/出射总能量**、RMSE、信号区 SNR、均匀度（仅对均匀目标） | `holo_metrics.json` |
| 5 | `quantize_phase()` | N 阶量化（`--levels`，2/4/8）；量化后**重估指标**（量化损耗单列）；输出 `quantized_phase.csv`；预留 `library_map` 占位字段（技能B 接口，本技能不实现查库） | 量化相位 + `holo_metrics.json` 追加 `quantized.*` |
| 6 | CLI | `--config --out --dry-run --json --self-test`；退出码 0/1/2；不假设 cwd | — |

与现有技能的关系：

- **不 import `_shared/lumapi_common.py`**——本技能零引擎，故意不碰会话层（与 field_map 的 `--npz` 路径同理）。
- 产出的 `phase_map.npz` 第一个二维数组是连续相位（rad），可被 `figure --kind field` 直接出图
  （写进 INDEX 的 hands_to；若 figure 需要相位色图模式，登记为后续小改，C 档）。
- 量化相位 → 技能B（`fdtd-metasurface-assembly`，未建）的消费格式**本计划只定 schema 不定实现**：
  `{x_um, y_um, phase_rad, level}` 四列 CSV + `meta.json`。

---

## 3. 关键知识点（设计约束的物理根源）

1. **GS 的域切换与约束（「相位/状态切换」）**：全息面只调相位（振幅恒定为 1 或源振幅），
   像面只换振幅（保留传播来的相位）。两个约束交替投影，误差单调不增但**不保证全局最优**。
2. **采样与混叠（「碰撞检测」的物理版）**：
   - 像面采样间隔由全息面总跨度与波长、距离决定（`dx_img = λ·f/(N·dx_holo)`），
     目标图必须重采样到这个网格，**不许两套网格各自定义**（模块 2 单一真相源）。
   - 零填充不足 → 循环卷积混叠，边缘出现鬼影。`--pad≥2`，且 pad 区计入能量分母要排除。
   - 输入合法性检查（真·碰撞检测）：目标图含负值/全零、`lambda_um≤0`、grid 非 2 的幂警告，
     一律 exit 2 不猜。
3. **相位量化的理论账（「数值平衡」）**：N 阶量化衍射效率上限 `(sin(π/N)/(π/N))²`：
   2 阶 40.5%、4 阶 81.1%、8 阶 95.0%。**实测 η 超过上限 = 实现有 bug**（多半是分母放错了），
   写进 self-test 断言。
4. **散斑不是噪声**：相干重建的 speckle 是固有的，SNR 定义必须基于信号区整体，
   不许用「平滑后对比」糊掉（与验收口径 D-012 同类教训：指标变好不代表物理变好）。
5. **复数 dtype 纪律（D-015）**：npz 的 dump/读回统一 `dtype.kind in "fiubc"` 白名单；
   相位数组是实数，但传播中间量全是 complex128——**数组为空必须报错**，不许写出看似成功的空 npz。
6. **可视化同步（「动画与特效」）**：本技能**只算不画**（同 field_map 的分工）。
   唯一例外：`--save-debug-frames` 落 `rmse_hist.csv` + 每 50 轮的重建快照 npz，
   供 figure 技能事后出收敛曲线。**不内嵌任何 plt 调用**。
7. **多种子方差即指标**：`n_seed` 次独立运行的 η 均值±极差都要进 `holo_metrics.json`；
   只报最优值是「假轮次第三种形态」（文案与语义相反）。

---

## 4. 实现步骤与优先级

按 §2 的 8 步走，每步配实验：

| 优先级 | 步骤 | 实验登记 | 验收判据 |
|---|---|---|---|
| P0 | EXP-52：schema 先行——`--config` 的 JSON schema + `holo_metrics.json` 字段表，写进 `design.md` | 字段被下游（figure、技能B 占位）点名 |
| P0 | EXP-53：模块 1+2（target/grids）+ `--dry-run` | dry-run 打印网格与采样参数、不开任何数组计算；非法输入 exit 2 |
| P0 | EXP-54：`--self-test` 9 条解析真值（零引擎可跑）：① Parseval 能量守恒；② 平面相位→像面单点；③ 透镜相位→焦斑位置误差 < 1 像素；④ 量化效率不超理论上限；⑤ pad=2 时边缘能量 < 0.1%；⑥ 量化恒等（levels=2 输出只有两档）；⑦ 网格对称性；⑧ 空数组报错；⑨ 复数 dtype 白名单 | 9/9 过 |
| P1 | EXP-55：gs_core 迭代 + 收敛控制 | RMSE 单调不增（允许 1e-12 数值抖动）；早停触发有日志 |
| P1 | EXP-56：负对照——故意不换像面振幅（退化成纯传播），RMSE 必须**不收敛**；负对照二——`pad=1` 时边缘能量显著高于 pad=2 | 两个负对照都「确实失败」，否则判据无效 |
| P1 | EXP-57：metrics + 多种子（n_seed=8 跑「双缝」目标） | η 均值/极差入 json；η ≤ 理论上限 |
| P2 | EXP-58：quantize 模块 + 2/4/8 阶对同一目标 | 量化损耗随 N 单调下降；`quantized.eta` 有数字 |
| P2 | EXP-59：端到端真值——**解析相位回灌正对照**（RMSE 必须为 0）+ 用它生成「已知可实现」的目标，GS 重建强度 RMSE ≤ 0.05 | 正对照 0（FFT）/0.004（角谱）；lens 目标实测 0.032 |
| P2 | SKILL.md 六段骨架（≤500 行；CRITICAL≤6 条）+ INDEX 行 + `skills.yaml` 编排 + `skills-wire.py --apply` + **用户级 junction**（§7 Node 命令） | `check_skill_contract.py` + `skills-doctor.py` 双 ALL GREEN |
| P3 | 新会话验证发现 + journal 一笔 | 新会话 `Skill("fdtd-holo-phase-retrieval")` 可触发 |

**顺序理由**：schema 与 self-test 先于迭代核心——先把「什么算对」钉死，再写算法，
否则又会得到「当时管用、原因不明」的脚本（契约 §1 判定顺序）。

### 压缩档（时间不够怎么砍）

| 场景 | 可以省 | 绝对不能省 |
|---|---|---|
| 只有半天 | EXP-58/59 推迟（登记 `deferred` + flag） | self-test 9 条 + 两个负对照 |
| 急着要相位版图 | debug frames、多 seeds（n_seed=1） | RMSE 平台期早停（无界循环是红线） |
| 完全没时间 | **不开工** | 只写本 PLAN + 占位 INDEX 行都不许（K17 会红） |

---

## 5. 技术难点与应对

| # | 难点 | 应对 |
|---|---|---|
| 1 | GS 停滞在局部最优，η 上不去 | 多种子取优（已内建）；留 `--method gs\|wgs` 扩展口，加权 GS 只在 gs 不达标时启用（避免过度设计） |
| 2 | 物理↔像素换算错一位，全盘皆错且不报错 | 模块 2 单一真相源 + self-test ③（透镜相位焦斑位置误差 < 1 像素）作为回归锚 |
| 3 | 量化后与 P05 类单胞库对不上（库里没有该相位档） | 本技能只输出 `level` 与占位 schema；「缺档」是技能B 的 `missing[]`，不许在这里硬凑 |
| 4 | 与 stage 4 技能语义混淆（agent 调错） | 命名 `holo-` 前缀 + 两技能 SKILL.md 互写「别用」边界 + INDEX 边界列 |
| 5 | 用户给彩色/带 alpha 的目标图 | 灰度化规则写死（ITU-R 601-2），alpha 通道拒绝并提示（exit 2），不静默丢弃 |
| 6 | 大网格（N≥1024）迭代慢 | FFT 是 O(N²logN)，200 轮秒级；真慢先查 pad 因子，不许砍网格精度 |
| 7 | 「指标好看但物理错」复发 | EXP-56 的两个负对照是硬门槛；η 超理论上限直接判 FAIL 而非报喜 |

### 会踩的坑（本项目已实测过的同类）

- **改完技能当前会话调不到**：project 级是会话快照；必须挂用户级 junction（§7 Node 命令），
  且 `~/.workbuddy/skills` 条目数 == INDEX 技能数（11→12）。
- **frontmatter 别用 `description: >` 单行折叠以外的花样**；文件不许带 BOM（headless 踩过）。
- **INDEX.md 改完必须 `yaml.safe_load` 相关门禁全过**（D-011：行首 `*` 让整份 yaml 不可解析而正则全绿）。
- **stage 1.8 含数字 → 必须进 `agents/fdtd-sim-agent/skills.yaml`**（K17），漏了编排链静默断。
- **`.npz` 写出前查空数组**（D-015）；读回用 `"fiubc"`。
- 路径纯 ASCII；脚本输入全来自 `--config`，输出全写 `--out`（契约 §4-5）。

---

## 6. 本计划不做的事（防范围蔓延）

1. 不建阵列、不查单胞库（技能B 的地盘）。
2. 不做近远场变换验证 FDTD 结果（技能C 的地盘）。
3. 不支持偏振复用 / 多波长 / 非近轴（输入检查直接拒绝）。
4. 不内嵌绘图（figure 技能的地盘，`--save-debug-frames` 只落数据）。
5. 不改 stage 4 `fdtd-lumerical-phase-retrieval` 的任何实现（只在其 SKILL.md 加一行互斥指引，A 档）。
