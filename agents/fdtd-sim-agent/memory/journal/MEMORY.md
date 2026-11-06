# MEMORY.md — FDTD_WS 项目长期记忆

## 项目
- **目标**：Python 驱动 Ansys Lumerical 2025 R1 (v251) FDTD，复现课题组**超表面系列论文**
  （课程 041–049 每讲 = 一篇论文 + 一套模板工程），做到建模→扫参→判读→出图→归档全自动化。
- **主线**：P03 = Ding 2015 半波片（D1）。
  Figure 1（正入射 R/PCR）已在设计带宽内达标；
  **2026-10-08 起黄老师指定目标改为 Figure 2**（各入射角下的 R_cr 与 PCR，仿真需计入 5 nm Ti 粘附层）。
  D2（周期/完美吸收对照）落在 P01。
- **验收标准**：导师（黄老师）判定，**与论文精确一致**，不是"差不多吻合"。
- **协作形态**（2026-10-01 起）：本仓库供多人/多 agent 协作，GitHub 作备份与同步渠道。

## 工作空间结构（2026-09-30 定案）
- `F:\Lumercial_WS\FDTD_WS\` 是**协作入口**，核心四件：
  `agent.md`（章程/铁律）、`SKILL.md`（踩坑手册，英文）、`README.md`（索引，中文）、
  `README.en.md`（索引，英文）
- **打包机制**：`packages\` 下**一课题一包**（一包 = 一篇论文）
  - 包结构：`README.md` / `paper\` / `fsp\` / `scripts\` / `results\` / `notes\`
  - 入口：`packages\PACKAGES.md`（任务地图），Nileuy 每次指定包 ID
  - 自检：`tools\check_packages.py --pkg P0N`
  - 共享：`_shared\lumapi_common.py`
- 现有 10 包（P01–P10），P03 = Ding2015 半波片 = **D1 主线**

## 项目约定（必须遵守）
1. **新增课题工作一律进对应包内**，不要散落到工作空间根目录
2. **包目录名与 `.fsp` 文件名必须纯 ASCII** —— 中文名会让 GPU 引擎崩溃（错误码 1113）
3. **论文与 fsp 一一对应**，协作前跑自检脚本
4. **与论文对不上的差异必须写进包内 README §5**，不要只留在对话里
5. 单包专用 → 包内 `scripts\`；两包以上共用 → `_shared\`；
   通用大工具 → 留在 `F:\Lumercial_WS\scripts\`（引用不复制）
6. **临时脚本只写在工作空间 `_scratch\`**（2026-10-01 用户新规）——
   不要写 `%TEMP%`/C 盘，也不要写仓库根目录。用完即删，留档进 `_scratch\archive\`
7. **skill 的正文只留一份**：`lumerical-fdtd-headless`（用户级）已改为**薄壳索引**，
   正文唯一来源 = `FDTD_WS\SKILL.md`。不要再把正文复制回 skill 里（会分叉）
8. **每包一份 `paper\自测题_5问.md`**（2026-10-08 起）：固定五问 =
   物理现象 / 公式（含验算）/ 前置基础 / 设计选择 / 仿真 A/B 对照；
   答案须带「要补的基础 + 教材锚点」，文末附基础缺口自查表。
   样板 = `packages\P03_HWP_Ding2015\paper\自测题_5问.md`；新增论文照此补。
   生产流程见项目级 skill `fdtd-package-workspace` Workflow G
9. **skill 一律按官方四段式**（`skill-creator` 规范）：
   `SKILL.md`（YAML: name/description/agent_created）+ `scripts/` + `references/` + `assets/`；
   长流程下沉 `references/`，SKILL.md 只留路由；新建用 `init_skill.py`，交付前跑
   `quick_validate.py`（description **不能含尖括号**）。现有三个：
   `fdtd-package-workspace`（包管理）、`lumerical-unitcell-simulation`（单元胞仿真）、
   用户级 `lumerical-fdtd-headless`（薄壳索引，按设计不扩）
10. **周期单元胞的 x/y 边界必须是 `Periodic`（或 Bloch），不能是 PML** ——
   PML 会退化成"孤立单个元胞"，有限宽平面源向侧向 PML 衍射后 R 会变负、A>1。
   实测同一结构：Periodic → A=0.81，PML → A=1.11（非物理）

## 文档约定（2026-10-01 定案）
- **三份文档分工，不要互相复制正文**：
  `agent.md` = 规矩（目标/资产地图/**十三条铁律 A–M**/协作与仓库纪律）；
  `SKILL.md` = 证据与对策（**八章**：环境/会话/建模/属性/结果/资源/排错/工具，§0 症状索引）；
  `README.md` = 入口索引（面向 GitHub 落地页，只写"读什么/放哪/怎么开始"）
- **语言（2026-10-01 用户要求）**：**skill 一律英文**（根 `SKILL.md` + 项目级 skill 均为英文，
  便于英文 agent 接管）；**README 中英双版**（`README.md` 中文 / `README.en.md` 英文，顶部互加切换链接）；
  其余协作文档（`agent.md`、包内 README）保持中文。
  翻长文档的手法见项目级 skill **工作流 F**（翻正文、冻骨架、分段写、机器校验编号与引用）
- ⚠️ **引擎报错原文不要翻译**（如 `ERROR: 在多字节的目标代码页中…`）—— 那是用户实际会看到的字面量
- **SKILL.md 禁止再追加「·补」式小节**，新增内容归入对应章（见其中 §8.6）
- **重编号后必须全仓清锚点**：`grep -rn "§[一二三四五六七八]" --include=*.md --include=*.py`
  覆盖 `.py` docstring 与 `.workbuddy\skills\` 下的副本；残留必须为 0
- **副本纪律**：`_shared\`/`tools\`/模板 的副本改动后当轮重新同步并 `diff` 确认

## 仓库纪律（协作）
- **不入库**：`course_media\*.mp4`（7.4 GB）、单文件 >100 MB 的 `.fsp`（GitHub 硬限会拒收）；
  入库约 185 MB
- **`.fsp` 是二进制 → 不能 diff/合并**：谁改谁立刻提交；同一工程同一天不要两人并行改
- **`(Agent_ignore)Log.md` 是 Nileuy 个人日志** —— **默认不读、不改**；
  但**当 Nileuy 在对话中显式引用它时**（如 `@(Agent_ignore)Log.md`），
  **本轮授权阅读**（仅读、仍不改），用完即止，不主动续读、不随手更新（2026-10-03 用户明确）

## 环境实测值
| 项 | 值 |
|---|---|
| Lumerical | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\`（2025 R1 / v251） |
| 托管 Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default`（3.13.14 + numpy 2.5.3） |
| ❌ 系统 Python 3.14 | 无 numpy，`import lumapi` 崩 |
| License | `1055@localhost`（100 席）。**两段进程链**：`lmgrd`（broker）+ `ansyslmd`（vendor daemon） |
| License 工具 | `F:\Lumercial\Shared Files\fnp\winx64\lmutil.exe` |
| License 文件 | `F:\Lumercial\Shared Files\Licensing\license_files\ansyslmd.lic` |
| License hostid | 绑**有线 Realtek 网卡** `04-7C-16-36-FD-0F`（≠VMware/Radmin 网卡）；**禁用该网卡会废掉许可** |
| ⚠️ `-97,121` | = vendor daemon 死了而 broker 活着 → `lmutil lmreread -c 1055@localhost`（无需管理员）。详见 `SKILL.md` §7.7 |
| GPU | RTX 3070 Laptop（8 GB，real32 单精度，金属易发散） |

## 本机 shell 环境陷阱（会反复遇到）
- **Bash 工具 PATH 默认丢失**（`ls`/`dirname`/`head` not found）→ 命令前加
  `export PATH="/usr/bin:/bin:$PATH"` 即可恢复
- **PowerShell 工具 stdout 不回显** → 写文件后用 Read 工具读
- **PowerShell 后台任务约 2 min 被中断** → 长任务改用 Bash + `run_in_background`

## WhaleNote.md —— 超表面答疑速查（2026-10-08 新增，长期有效）
- 位置：`F:\Lumercial_WS\FDTD_WS\WhaleNote.md`（工作空间根目录，与 `README.md` 同级）
- **用途**：Nileuy 随时抛超表面物理名词/公式/概念 → 鲸鱼**详尽解答** →
  每条末尾压成 **150–350 字高浓缩小结** 追加进该文件，供他日后回顾。
- **纪律**：只答疑，**不改工程/脚本**；需要落盘时只写该文件（外加工作区记忆）。
  追加式，**不覆盖、不删旧条目**；新条目同步登记到文首「索引」表（# / 条目 / 类型 / 日期）。
- **条目统一结构**：① 直觉解释（C++ / 日常类比）② 物理量定义与公式
  ③ 与仿真参数的对应 ④ 小结（≤350 字）⑤ 基础缺口与教材锚点。
- **回答口径**：结论先行 → 公式具体（给符号、单位、数字）→ 几何类概念配内联示意图；
  涉及论文数字时**回原文核对**，不得凭记忆复述；数值结论尽量实机验算（临时脚本进 `_scratch\`）。
- 与 `packages\P0N_*\paper\自测题_5问.md` 互补：后者**出题测水平**，WhaleNote **被动答疑沉淀**。
