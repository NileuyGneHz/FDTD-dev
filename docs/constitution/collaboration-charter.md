---
title: "agent.md — Lumerical FDTD 工作空间协作章程"
summary: "AI agent 与人类协作者接入本工作空间时的第一份必读文件：项目目标、资产地图、十三条铁律、协作与仓库纪律"
read_when:
  - 任何会话开始，尤其是首次进入 F:\Lumercial_WS\FDTD_WS
  - 执行任何仿真 / 改脚本 / 改 .fsp / 提交 git 之前
updated: 2026-10-01
---

# agent.md — 协作章程

> **读者**：接入本工作空间的 **AI agent 与人类协作者**。首次进入请通读，之后按需查。
> 这份文件回答四件事：**我们在做什么 / 东西在哪 / 什么绝对不能做 / 怎么配合**。
> 踩坑证据与可照抄的代码在 `SKILL.md`（八章：环境 / 会话 / 建模 / 属性 / 结果 / 资源 / 排错 / 工具），
> 目录与上手索引在 `README.md`（英文版 `README.en.md`）。

---

## 0. 一句话

**产品方针**：人先定大致方向，再定所需材料与几何结构（可多轮调整，也可逆向工程）；
agent 用 **Lumerical FDTD** 在人锁定的参数空间内调参，直到产出达标结果。
论文复现是校准模型、建立可信度的手段，**不是终点**。

Nileuy（此用户）仍在打基础，在建模与调参过程中需要对**重要的物理名词与物理公式进行较为详尽的解释**，
确保学到知识，而不是只拿到一个能跑的结果。

技术栈：**Python 驱动 Ansys Lumerical 2025 R1 (v251) FDTD**，
把「**建模 → 扫参 → 判读 → 出图 → 归档**」做成 headless 闭环。

**当前主线（复现模式）**：`P03` = **Ding 2015 等离激元半波片 Figure 1**
（单元胞扫描 → 相位库 → GS 相位恢复 → 全息出图）。它是模型校准任务，不改变上面的产品方针。

**验收标准由导师（黄老师）判定：与论文结果精确一致，不是"差不多吻合"。**

---

## 0.5 ⭐ 接手第一步：定位本次要做的包

**本工作空间采用「一课题一包」。开始任何工作前，先读包索引：**

```
F:\Lumercial_WS\FDTD_WS\packages\PACKAGES.md      ← 任务地图（先读这个）
```

Nileuy 会在每次协作开始时指定包 ID（如"**这次做 P03**"）。流程：

1. 读 `packages\PACKAGES.md` → 找到对应包 → 点进该包 `README.md`
2. 读该包 `README.md` 的 **§0 Agent 快速接管** → 拿到本次目标 / 验收标准 / 入口脚本
3. 跑自检：`tools\check_packages.py --pkg P0N`
4. 过 ASCII 闸门（§4-B）→ 开工；完工后把进度写回包内 `README.md` **§5**

**包结构**（`packages\P0N_<课题>\`）：

```
P0N_<课题>\
├─ README.md     ★ 接管入口（§0 接管信息 / §1 论文 / §2 参数 / §3 文件 / §4 本包坑 / §5 进度 / §6 导师同步）
├─ paper\        论文 PDF 与参考资料
├─ fsp\          .fsp 工程（必须 ASCII 文件名）+ 同名 _p0.log
├─ scripts\      本包专用脚本
├─ results\      数据与图
└─ notes\        笔记与排查记录
```

**约束**：

- **包目录名与 `.fsp` 文件名必须纯 ASCII**（中文名 → GPU 引擎崩，§4-B）
- **论文与 fsp 一一对应**，用 `tools\check_packages.py` 机器校验
- 单包专用的放包内；**两包以上共用**的放 `library\py\`；仓库级工具放 `tools\`
- 新建包：复制 `packages\_TEMPLATE\` → 改名 → 填 README（模板里已写好各节该填什么）

---

## 1. 项目性质与角色

| 项 | 内容 |
|---|---|
| 身份 | 广西大学 计算机学院 通信工程 2025 级本科生（Nileuy / saber） |
| 定位 | 在导师课题组内做超表面 FDTD 设计与验证：人定方向与结构，agent 负责数值闭环 |
| 协作形态 | 本仓库供**多人 / 多 agent 协作**用；GitHub 作为备份与同步渠道 |
| 交付节奏 | 周期性向导师提交 **（Agent_Ignore）log.md 进度小结**；之后导师会下发论文培养独立方向 |
| 当前阶段 | 10 个包骨架 + 素材已就位；P01 / P03 已跑通，其余待实跑（§7） |

---

## 2. 资产地图

### 2.1 仓库内（随 git 分发；仓库根 = `F:\Lumercial_WS\FDTD_WS\`）

```
FDTD_WS\
├─ agent.md              ★ 本文件（规矩）
├─ SKILL.md              ★ 踩坑手册（证据与对策，八章，按症状索引）
├─ README.md             目录索引 + 快速开始
├─ packages\          ★ 任务打包区（一课题一包）
│  ├─ PACKAGES.md         ★ 任务地图（协作入口）
│  ├─ _TEMPLATE\          新包模板
│  └─ P01..P10\           10 个课题包（paper / fsp / scripts / results / notes）
├─ library\py\           跨包共享模块（lumapi_common.py + fsp_build.py）
├─ tools\                自检与体检脚本（check_packages.py 等）
├─ _scratch\             临时脚本区（一次性探查/验证脚本，不进库；见 N 条）
├─ course_media\         课程视频索引（*.mp4 体积过大，不入库）
├─ .gitignore            入库 / 不入库规则
└─ .gitattributes        文本/二进制与换行规则
```

**入库策略（重要）**：

| 内容 | 体积（实测） | 是否入库 | 说明 |
|---|---|---|---|
| 课程视频（11 个 mp4） | 7.4 GB | ❌ | 单文件最大 1.07 GB，GitHub 直接拒收 |
| `.fsp` 工程（45 个） | 496 MB | 部分 | 单文件 >100 MB 的（如 331.8 MB 的 `infrared_perfect_absorber.fsp`）不入库 |
| 论文 PDF（10 份） | 19 MB | ✅ | 每个包 `paper\` 一份 |
| 脚本 / 文档 / 结果 | < 2 MB | ✅ | — |

> 排除这些之后，仓库约 **185 MB**，在 GitHub 建议范围（< 1 GB）内。
> **规矩**：不要试图把视频或 >100 MB 的工程塞进 git —— 一旦进了历史，清理要重写提交历史。

### 2.2 本机外部（**不在仓库里**，换机器需自行准备）

| 路径 | 内容 | 备注 |
|---|---|---|
| `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\` | Lumerical 安装 | 商业软件，`api\python\lumapi.py` 在此 |
| `F:\Lumercial_WS\Classes\FDTD\` | 导师给的课程原件（课件 / 论文 / 模板 .fsp / mp4） | **只读**，包内素材是从这里复制的 |
| `F:\Lumercial_WS\scripts\` | 通用脚本库（`py.bat`、`z_fix_gpu_res.py`、`lumapi_probe.py`、`fsp_strings.py` …） | 被本仓库文档引用，但不在仓库内 |
| `F:\Lumercial_WS\docs\` | 文档总库（指令清单、排查记录、GS 算法讲解） | 同上 |
| `F:\Lumercial_WS\projects\` | 旧的散置工程目录（`d2\`、`L042\`） | ASCII 路径，可直接跑 |
| `C:\Users\saber\.workbuddy\binaries\python\envs\default` | 托管 Python | 见 §3 |

> ⚠️ 仓库内的文档会引用这些路径。**克隆到别的机器时它们不存在** —— 这是已知的移植性缺口，
> 需要哪份工具就单独拷过去（优先拷 `scripts\` 下的 `z_*` / `lumapi_probe.py` / `fsp_strings.py`）。

### 2.3 关键脚本速查

| 脚本 | 位置 | 用途 |
|---|---|---|
| `check_packages.py` | `tools\`（仓库内） | ★ 包结构自检：论文齐否 / `.fsp` 是否纯 ASCII / README 是否填完 |
| `migrate_classes_to_packages.py` | `tools\`（仓库内） | 课程素材 → 包内的搬迁脚本（含中文名转 ASCII 映射，可复用） |
| `lumapi_common.py` | `library\py\`（仓库内） | ★ 会话/校验封装：`setup_env` `open_fdtd` `verify_and_run` `ascii_gate` `n_at` |
| `py.bat` | 外部 `scripts\` | 启动器，自动选托管 Python |
| `z_fix_gpu_res.py` | 外部 `scripts\` | ★ GPU/CPU 资源一键恢复（幂等 + 备份 + 回读校验） |
| `lumapi_probe.py` / `fsp_strings.py` | 外部 `scripts\` | 对象树探查 / `.fsp` 二进制字符串抽取（材料名唯一获取途径） |
| `z_ascii_work.py` | 外部 `scripts\` | 把中文路径课件整体复制到 ASCII 目录 |

---

## 3. 环境事实（不要靠猜，这些都是实测值）

| 项 | 值 |
|---|---|
| Lumerical | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\`，版本 **2025 R1 (v251)** |
| Python API | `<安装>\api\python\lumapi.py`（**`import lumapi`，不要写 `import ansys.lumerical`**） |
| 托管 Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default`（3.13.14 + numpy 2.5.3） |
| ❌ 系统 Python | 3.14 **无 numpy** → `import lumapi` 直接崩 |
| License | `1055@localhost`（100 席共享，2035-12-31 到期） |
| Headless 前置 | `export ANSYSLMD_LICENSE_FILE="1055@localhost"` |
| GPU | NVIDIA RTX 3070 Laptop（8 GB）→ **real32 单精度**，金属易发散 |
| CPU 引擎 | `fdtd-engine-msmpi.exe`；MS-MPI 在 `C:\Program Files\Microsoft MPI\Bin\mpiexec.exe` |

---

## 4. 铁律（违反会浪费几小时到几天）

### A. 判断任何工具/方法是否有效 → **必须先跑对照组**

这是本项目用血换来的第一条规矩。实测教训：`Testproject.fsp` 是纯材料库（无几何体），
探查器读出"只有 1 个节点"，差点误判工具坏了去修；拿 `blaze_grating.fsp` 对照 → 12 个节点，工具正常。

> **没有对照实验，你会花两小时去修一个没坏的东西。**

反射测量同理：先搭"**只有 150 nm 金膜**"的镜子参照（已知 `|Ex|≈1, |Ey|=0, R≤1`），
才能把"归一化错"和"物理对"分开。本次正是靠它把排查范围从 4 个假设收敛到 2 个。

### B. 路径必须纯 ASCII → **GPU 引擎硬要求**（2×2 对照实测）

目录名或文件名只要含非 ASCII 字符，GPU 引擎**必崩**，且报错是乱码（错误码 1113）。
空格无关。CPU 引擎 `fdtd-engine-msmpi.exe` 没这个问题。
→ **不管走哪条路，跑之前把 `.fsp` 放到纯 ASCII 路径**（包内 `fsp\` 天然满足）。

### C. headless 新建会话 → **必须先 `save` → 新会话 `load` 一轮，`run` 才生效**

新建会话里建完对象直接 `f.run()` 会**静默失效**：不抛异常、0.2 s 返回、什么都没算。
判据三件套：`layoutmode == 0`、存在 `<工程名>_p0.log`、日志含 `Completed N iterations`。

### D. 改参数前先 `switchtolayout()`

`load` 一个"已算过"的 `.fsp` 后，结构/源/监视器参数**全部只读**，
`setnamed` 会报 `you cannot modify most simulation objects while in analysis mode`。

### E. 一律用 `setnamed` / `getnamed`，不用 `select` + `set`

裸 `set` 依赖"当前对象"这个**代码里看不见的全局状态**，中间插一行 `addrect` 就全线崩。
带 d 的是 "**d**esignated"——你在参数里指认了对象。⚠️ `setname`/`getname`（无 d）**真实存在**，
误写不会报 `NameError`，而是抛语义完全不搭的 `LumApiError`。

### F. `getindex()` 的参数是**频率（Hz）**，不是波长

传 `532e-9` 会被当成 `5.32e-7 Hz` → Lumerical 外推 → **TiO₂ 返回 5.99（正确是 2.45）**。
两种写法都不报错。**唯一可靠的发现途径是拿文献值对照。**

### G. 耗时的根因几乎总是**网格规模**，不是 CPU/GPU 不行

先读 `_p0.log` 里的 `Simulation size in gridpoints`。
最高频的数错是**波长单位写成米**：近红外 800 nm 写 `8e-7`，写成 `1e-7` 就是 100 nm（紫外）→ 网格爆炸 616 倍。

### H. `setresource(...)` 会**持久化**改坏全局配置

它改的不是本次会话，而是 `%APPDATA%\Lumerical\FDTD Solutions.ini` 的 `[jobmanager]` 段。
曾因此让 GUI 报 "no active GPU resources"。
→ **改过资源，离开前必须改回原值并回读确认**（用 `z_fix_gpu_res.py`）。

### I. 长任务走 **Bash + `run_in_background`**，不要用 PowerShell 后台

PowerShell 后台任务约 2 min 被中断，连带杀掉 `fdtd-engine` 子进程。
Python 脚本**只往 UTF-8 文件写结果，不要 `print()` 中文**（重定向时编码翻车）。

### J. `.fsp` 原文件只读

只在 **ASCII 副本**上 run；原文件仅用于 dump / diff。

### K. 一课题一包，论文与 fsp 一一对应

- 所有课题工作**必须在对应包内进行**（`packages\P0N_*\`），不要散落到工作空间根目录。
- 包目录名与 `.fsp` 文件名**纯 ASCII**（见 B 条）。
- 协作前跑 `tools\check_packages.py`；完工后把进度写进包内 `README.md` **§5**。
- 与论文对不上的差异**必须记进包内 README §5**，不要只留在对话里过夜。

### L. `.fsp` 是二进制 → **无法 diff / 无法合并**

两个协作者同时改同一个 `.fsp`，git 只会说 "binary files differ"，**没有可用的合并手段**。

- 规矩：**谁改谁立刻提交并写清改了什么**；同一工程**同一天不要两人并行改**。
- 需要并行对比 → 各自另存为 `<name>_v2.fsp`（ASCII 命名），事后再人工比对关键参数。
- 好处：参数与结论都落在包内 README，**工程文件反而可以随时重算**。

### M. 大文件不进版本库

课程视频（7.4 GB）与单文件 >100 MB 的 `.fsp` **一律排除**：GitHub 单文件硬限 100 MB，
超了会**直接拒绝推送**；而一旦混进历史，清理需要重写历史。

- 提交前先看 `git status` 里有没有 mp4 / 大 fsp。
- 这些资产的备份走网盘或 Git LFS，不走普通 git。

### N. 临时脚本只写在工作空间内

一次性脚本（探查 / 验证 / 搬迁 / 试验）**一律写到 `F:\Lumercial_WS\FDTD_WS\_scratch\`**，
**不要写到 `%TEMP%`（C 盘）或仓库根目录**。

- 理由（2026-10-01 教训）：写在 `%TEMP%` 的脚本会散落、难找、脱离仓库管理，
  且会话结束后无人清理 —— 累积成 C 盘垃圾。
- `_scratch\` 是**唯一允许"脏"的目录**，其余目录必须保持整洁。
- 用完即删；要留档就移入 `_scratch\archive\` 并在 `_scratch\README.md` 登记一行。
- 有复用价值时**提升**为正式脚本：单包 → 包内 `scripts\`；跨包 → `library\py\`；
  通用大工具 → 外部 `F:\Lumercial_WS\scripts\`（引用不复制）。
- `.gitignore` 已排除 `_scratch/*`，仅保留其中的 `README.md`。

---

## 5. 标准工作循环

```
1  定位    读 packages\PACKAGES.md 找本次的包 → 读包内 README §0 拿目标与验收标准
2  自检    tools\check_packages.py --pkg P0N（论文齐否 / fsp 是否 ASCII / README 是否填完）
3  读工程  用 lumapi_probe.py / fsp_strings.py 摸清陌生工程（对象树 + 材料 + 属性）
4  对照    找一份"同构且已知正确"的工程，做三方属性 diff（原始 / 已知正确 / 我的改法）
5  副本    只在纯 ASCII 路径上操作（包内 fsp\），原文件保持只读（J 条）
6  建模    一律 setnamed 建对象；改参数前 switchtolayout()（D / E 条）
7  跑      save → 关会话 → 新会话 load → switchtolayout → run（C 条）
8  验证    assert_ran() 三判据：layoutmode==0 + _p0.log + Completed iterations
9  判读    结果与论文/文献值比对（不看材料名，看数值）；差异写进包内 README §5
10 出图    写 csv/png 到包内 results\；不 print 中文（I 条）
11 归档    脚本 → 包内 scripts\；共享工具 → library\py\；进度 → 包内 README §5
12 提交    小步提交，提交信息写清"哪个包 + 改了什么 + 结论"（§6.3）
```

**共享工具**（`library\py\lumapi_common.py`）已封装第 6–8 步的坑，优先用它：

```python
import sys
sys.path.insert(0, r"F:\Lumercial_WS\FDTD_WS\library\py")
from lumapi_common import setup_env, verify_and_run, ascii_gate, n_at

setup_env()
f = verify_and_run(fsp)       # save→load→run→三判据，一步到位
try:
    ...                        # 取结果
finally:
    f.close()
```

---

## 6. 协作约定

### 6.1 沟通（对人）

- **技术术语与命令用英文，解释与讨论用中文。**
- 结论先行，随后展开细节；**要具体**（给命令、给路径、给数字），不要泛泛而谈。
- 用**编号式步骤**（1. 2. 3.），不要散文式建议。
- 结构化表达优先：**表格对比 / 优先级 bullets / 代码块**。
- 输出中**不使用 emoji**（🔧 仅限身份文件）。

### 6.2 Nileuy 明确要过的

- 给计划必须附两张表：**「压缩档」**（没时间怎么砍）和**「会踩的坑」**。
- 学新东西不要"读教材/看视频课"，要**逼自己动手**的机制（抄 → 改 → 重写、故意制造报错）。
- 需要判断他的水平时**出题测**并**采信自评**，**绝不用 AI 自己生成的文件推断**。
- 收尾常要 "please give me a script" → 产出**符合项目规范、可直接落地**的生产级脚本，不是临时片段。

### 6.3 仓库纪律（协作新增）

1. **先看差异再提交**：`git status` / `git diff --stat`。确认没有 mp4、没有 >100 MB 的 `.fsp`（M 条）。
2. **小步提交**，一条提交只做一件事。提交信息格式：
   `<类型>(<包ID>): <做了什么>`
   - `feat(P03): 加入 t16 相位扫描脚本`
   - `fix(P01): 修正 FDTD 区域中心偏移导致的源 span 派生错误`
   - `docs(P03): 更新 §5 进度与论文差异`
   - `chore: 归档 045 讲模板工程`
3. **改了工程/结论 → 同步改包内 README**（§2 参数 / §5 进度）。只改代码不改文档，下一个人会踩同样的坑。
4. **不要提交**：`.fsp` 的临时副本、引擎中间文件、本机绝对路径截图、个人笔记。
5. **`(Agent_ignore)Log.md` 是 Nileuy 的个人日志** —— AI agent **不要读取**，也不要改动。

### 6.4 硬边界

- **不美化现实**。判断错了当场改，并且**改文件**，不粉饰。
- 他可能把文件名拼错（如 `t4_unicell.py` vs `t4_unitcell.py`）→ 主动建议 Tab 补全。
- 推断内容必须**明确标注"推断"**。
- 外部动作（发邮件、汇报导师、发布、推送到远端）保守，**先问**；
  内部动作（读、整理、跑本地仿真）大胆。

---

## 7. 当前状态、待办与未解问题

### 7.1 各包状态（2026-10-01 实测）

| 包 | 课题（课程讲） | 论文 | `.fsp` | 脚本 | 结果 | 状态 |
|---|---|---|---|---|---|---|
| P01 | 红外完美吸收器 (042) | ✅ | 2 | 0 | 0 | 已跑通（CPU 对照） |
| P02 | 偏振转换 (045) | ✅ | 4 | 3 | 0 | 素材就位，待跑 |
| **P03** | **半波片 Ding2015（★D1 主线）** | ⚠️ 精读版 | 4 | 6 | 8 | **进行中** |
| P04 | 异常反射 (047) | ✅ | 7 | 7 | 0 | 素材就位，待跑 |
| P05 | 超透镜 (048) | ✅ | 4 | 2 | 0 | 素材就位，待跑 |
| P06 | 涡旋光 (049) | ✅ | 11 | 5 | 0 | 素材就位，待跑 |
| P07 | 破缺对称 (041) | ✅ | 3 | 0 | 0 | 素材就位，待跑 |
| P08 | 宽带吸收 (043) | ✅ | 4 | 0 | 0 | 素材就位，待跑 |
| P09 | 石墨烯吸收 (044) | ✅ | 3 | 0 | 0 | 素材就位，待跑 |
| P10 | 二次谐波 (046) | ✅ | 3 | 0 | 0 | 素材就位，待跑 |

> **8 个包的 `results\` 还是空的** —— 它们只有课程原始工程，尚未自己跑过。
> 指定某个包开工时，跑出来的结果就进对应包的 `results\`。

### 7.2 进行中

- **P03 / D1**：复现 Ding 2015 Figure 1（单元胞 HWP → 相位库 → 全息出图）
- **D2**（周期 / 完美吸收对照）落在 **P01**：周期边界路线仍给出非物理读数
  （`T = −0.73 ~ −0.31` 负值，`A = 1−R−T` 冲到 1.5）
  → **当前策略：退回 PML 路线**，先拿到能对得上的结果
- GPU 的 real32 单精度 + Drude 金属发散问题（`dt stability factor` 0.99→0.95 是已验证有效的一招）

### 7.3 未攻克

| 问题 | 状态 |
|---|---|
| Analysis Group **内部叶子对象**（Rectangle/Mesh/Monitor）拿不到 | ⚠️ 未解决（组对象本身可递归，见 `SKILL.md` §5.3） |
| `getfdtdindex` 签名（实测需要 ≥4 个参数） | ⚠️ 未查明 |
| headless `f.run()` 是否也怕中文路径 | ⚠️ 无结论（被 "run 静默失效" 抢先，需重做对照） |
| P03 缺论文**原文 PDF** | ⚠️ 现为精读版；DOI `10.1021/acsnano.5b00218`，需索取或自行下载 |
| 仓库移植性：文档引用了仓库外路径（§2.2） | ⚠️ 已知缺口，未处理 |

---

## 8. 索引

| 想查什么 | 看哪 |
|---|---|
| **本次做哪个包 / 包总表** | `packages\PACKAGES.md`（任务地图） |
| **某课题的目标 / 参数 / 进度** | `packages\P0N_<课题>\README.md` |
| **踩坑速查 / 脚本语法 / 报错对策** | **`SKILL.md`**（八章，§0 按症状索引） |
| 目录结构 / 快速开始 | `README.md`（中文）/ `README.en.md`（English） |
| 共享工具用法 | `library\py\README.md` |
| 包结构自检 | `tools\check_packages.py --pkg P0N` |
| 新建一个包 | `packages\_TEMPLATE\README.md`（复制整个 `_TEMPLATE\`） |
| 改文件名 / 迁移素材 | `tools\migrate_classes_to_packages.py`（含改名映射表，可复用） |
| 环境与前置条件 | `SKILL.md` §1 |
| 会话序列（run 静默失效等） | `SKILL.md` §2 |
| 材料 / 建模 API | `SKILL.md` §3 |
| 折射率 / 结果提取 | `SKILL.md` §5 |
| 网格 / 资源 / 边界条件 | `SKILL.md` §6 |
| 验证方法（对照组） | `SKILL.md` §7 |

---

## 9. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-30 | 建立工作空间章程；确立"一课题一包"；归档课程素材（9 篇论文 / 45 个 `.fsp` / 11 个视频） |
| 2026-10-01 | `SKILL.md` 由"补 N 式"重排为八章（正文零丢失，机器校验）；本章程补齐协作与仓库纪律（铁律 A–M） |
