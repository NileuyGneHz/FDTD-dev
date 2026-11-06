# FDTD_WS — 超表面 FDTD 复现工作空间

> **Ansys Lumerical 2025 R1 (v251)** ｜ Python 驱动（`lumapi`）｜ headless 仿真
> 用途：复现课题组的超表面（metasurface）系列论文，做成「建模 → 扫参 → 判读 → 出图 → 归档」的可复现闭环
> 协作方式：**一课题一包**，每次协作前指定包 ID（如"这次做 P03"）
> 建立 2026-09-27 ｜ 校订 2026-10-01（`SKILL.md` 结构重排 + 协作文档补齐）

---

## 先读什么（按顺序）

| 顺序 | 文件 | 作用 |
|---|---|---|
| 1 | **`packages\PACKAGES.md`** | **任务地图**：10 个包分别是什么 —— 每次协作的第一步 |
| 2 | **`packages\P0N_*\README.md`** | 该包的 §0「Agent 快速接管」：本次目标 / 验收标准 / 入口脚本 |
| 3 | **`agent.md`** | **规矩**：项目目标、资产地图、十三条铁律、协作与仓库纪律 |
| 4 | **`SKILL.md`** | **证据与对策**：v251 实测的坑 + 可直接照抄的代码（§0 按症状索引） |
| 5 | 本文件 | 入口索引：结构、用途、上手命令 |

---

## 快速开始

```bash
export PATH="/usr/bin:/bin:$PATH"          # 本机 Bash 工具 PATH 会丢，先补回来
cd "F:/Lumercial_WS/FDTD_WS"

PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# 1) 包结构自检（论文齐否 / .fsp 是否纯 ASCII / README 是否填完）
"$PY" tools/check_packages.py                # 全部包
"$PY" tools/check_packages.py --pkg P03      # 单个包

# 2) 提交前体积体检（>100 MB 的文件会被 GitHub 直接拒收）
"$PY" tools/check_git_limits.py
```

跑仿真时优先用共享封装（已把会话的坑封好）：

```python
import sys
sys.path.insert(0, r"F:\Lumercial_WS\FDTD_WS\_shared")
from lumapi_common import setup_env, verify_and_run, ascii_gate, n_at

setup_env()
f = verify_and_run(fsp)          # save → load → run → 三判据，一步到位
try:
    ...
finally:
    f.close()
```

---

## 仓库结构

```
FDTD_WS\
├─ README.md              ← 本文件（中文）
├─ README.en.md           英文版（English）
├─ agent.md               协作章程（规矩）
├─ SKILL.md               踩坑手册（八章，按症状索引）
├─ packages\            ★ 任务打包区（一课题一包）
│  ├─ PACKAGES.md           ★ 任务地图
│  ├─ _TEMPLATE\            新包模板（复制它来建包）
│  └─ P01..P10\             10 个课题包
│     ├─ README.md           ★ 接管入口
│     ├─ paper\              论文 PDF
│     ├─ fsp\                .fsp 工程（纯 ASCII 名）+ 同名 _p0.log
│     ├─ scripts\            本包专用脚本
│     ├─ results\            数据与图
│     └─ notes\              笔记与排查记录
├─ _shared\               跨包共享工具（lumapi_common.py）
├─ skills\                可复用技能库（标准四段式：SKILL.md + scripts + references + assets）
│  ├─ paper-fdtd-parameter-extraction\   论文 → 参数规格 spec.json
│  ├─ lumerical-unitcell-simulation\     spec.json → 建模/扫参/出谱
│  └─ fdtd-package-workspace\            包结构与自检
├─ agents\                agent 定义（角色 / 工具 / 技能 / 记忆 / 评测）
│  └─ fdtd-sim-agent\     AGENT.md + agent.yaml + tools.yaml + skills.yaml + memory\ + evals\
├─ tools\                 仓库级脚本（自检 / 体检 / 迁移）
├─ course_media\          课程视频索引（*.mp4 不入库）
├─ .gitattributes         文本/二进制与换行规则
└─ _scratch\              临时脚本区（不入库）
```

### 各目录的用途与归属

| 目录 | 用途 | 谁写入 | 命名规则 |
|---|---|---|---|
| `packages\P0N_*\` | 一课题一包；论文 + 工程 + 脚本 + 结果自包含 | 所有人 | `P<两位序号>_<PascalCase课题>_<课程讲次>` |
| `packages\P0N_*\fsp\` | 仿真工程与引擎日志 | 改工程的人 | **纯 ASCII**、小写下划线；日志与 `.fsp` **同名** + `_p0.log` |
| `packages\P0N_*\scripts\` | **仅本包用**的脚本 | 本包负责人 | `t<n>_<主题>.py` 或 `<动词>_<对象>.py` |
| `packages\P0N_*\results\` | 数据与图（csv/png） | 跑仿真的人 | `<脚本名>_<图号>_<内容>.csv` |
| `packages\P0N_*\notes\` | 笔记、排查记录 | 所有人 | 自由，建议带日期 |
| `_shared\` | **两包以上**共用 | 需要复用的人 | 模块名小写下划线 |
| `tools\` | **仓库级**工具（自检/体检/迁移） | 需要维护仓库的人 | 动词开头 |
| `course_media\` | 课程视频索引（只有 README，mp4 不入库） | 只读 | `L<讲次>_<主题>.mp4` |

**新文件该放哪（决策）**：

1. 只服务**一个包** → 该包 `scripts\` / `results\` / `notes\`
2. **两个以上包**要用 → `_shared\`
3. 仓库级体检 / 管理工具 → `tools\`
4. 论文与工程 → 对应包的 `paper\` / `fsp\`
5. 课程原始资料原件 → **留在仓库外** `F:\Lumercial_WS\Classes\FDTD\`（只读）
6. 一次性草稿 → 包内 `notes\`，不要放仓库根目录

> 空目录靠 `.gitkeep` 占位保留，**别删**。

---

## 10 个课题包

导师给的课程 041–049，每讲 = 一篇论文 + 一套模板工程。

| 包 | 课题 | 讲次 | 论文 | `.fsp` | 状态 |
|---|---|---|---|---|---|
| P01 | 红外完美吸收器 | 042 | ✅ | 2 | 已跑通 |
| P02 | 偏振转换 | 045 | ✅ | 4 | 素材就位 |
| **P03** | **等离激元半波片（Ding 2015）** | — | ⚠️ 精读版 | 4 | **进行中（主线）** |
| P04 | 异常反射 | 047 | ✅ | 7 | 素材就位 |
| P05 | 圆偏振超透镜 | 048 | ✅ | 4 | 素材就位 |
| P06 | 涡旋光产生 | 049 | ✅ | 11 | 素材就位 |
| P07 | 破缺对称 | 041 | ✅ | 3 | 素材就位 |
| P08 | 宽带可见光吸收器 | 043 | ✅ | 4 | 素材就位 |
| P09 | 石墨烯完美吸收器 | 044 | ✅ | 3 | 素材就位 |
| P10 | 二次谐波产生 | 046 | ✅ | 3 | 素材就位 |

> 学习主线：**041 → 045 → 047 → 048 → 049** 是通往超表面全息的路径。
> 各包详细的目标 / 参数 / 进度见 `packages\P0N_*\README.md`。

---

## 协作流程

1. 你指定包：**"这次做 P03"**
2. 读 `packages\PACKAGES.md` 定位包 → 读包内 `README.md` **§0** 拿目标与验收标准
3. 跑自检 `tools\check_packages.py --pkg P03`
4. 开工（遵守 `agent.md` §4 铁律；通用坑查 `SKILL.md`）
5. 完工：结果进包内 `results\`，进度与差异写回包内 `README.md` **§5**
6. 提交：小步提交，提交信息写清「哪个包 + 改了什么 + 结论」

---

## 四条最贵的坑（先背下来，完整版见 `SKILL.md` §0）

1. **没跑对照组，不要下结论**（`SKILL.md` §7.1 —— 本项目第一条规矩）
2. **`run()` 秒回 = 没算**：headless 新建会话必须先 `save` → 新会话 `load` → 再 `run`；
   判据是 `layoutmode == 0` + 存在 `_p0.log` + 日志含 `Completed`（§2.1）
3. **波长单位是米，`getindex()` 收频率不是波长**（§5.2 / §6.1）
4. **非 ASCII 路径 GPU 引擎必崩**（报错是乱码，错误码 1113）（§6.2）

---

## 仓库纪律（协作必读）

| 规矩 | 原因 |
|---|---|
| **不要提交 mp4 / >100 MB 的 `.fsp`** | GitHub 单文件硬限 100 MB，超了直接拒收；混进历史后清理要重写历史 |
| **`.fsp` 不能 diff / 不能合并** | 二进制。谁改谁立刻提交；同一工程同一天不要两人并行改；要并行就另存 `<name>_v2.fsp` |
| **改了工程或结论，同步改包内 README** | 只改代码不改文档，下一个人会踩同样的坑 |
| **包目录名与 `.fsp` 名纯 ASCII** | GPU 引擎硬要求，中文名必崩 |
| **`(Agent_ignore)Log.md` 不要读、不要改** | Nileuy 的个人日志 |

**入库策略**：课程视频（7.4 GB）与 >100 MB 的工程不入库；其余论文、脚本、结果、文档全部入库。
排除后仓库约 **185 MB**，在 GitHub 建议范围（< 1 GB）内。

---

## 环境速查

| 项 | 值 |
|---|---|
| Lumerical | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\`（2025 R1 / v251） |
| Python API | `<安装>\api\python\lumapi.py`（`import lumapi`） |
| 托管 Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default`（3.13.14 + numpy 2.5.3） |
| ❌ 系统 Python 3.14 | 无 numpy，`import lumapi` 直接崩 |
| License | `1055@localhost`（100 席，2035-12-31 到期） |
| GPU | RTX 3070 Laptop 8 GB（real32 单精度，金属易发散） |

> 详见 `agent.md` §3 与 `SKILL.md` §1。

---

## 路径约定（协作必读）

本仓库只覆盖 `F:\Lumercial_WS\FDTD_WS\` 这一层。文档里的路径分三类：

| 类型 | 例子 | 说明 |
|---|---|---|
| **仓库内** | `packages\P03_HWP_Ding2015\` | 随仓库分发，任何协作者都有 |
| **本机外部** | `F:\Lumercial_WS\scripts\`、`...\docs\`、`...\Classes\FDTD\`、`...\ANSYS Inc\` | **不在仓库里**，换机器需自行准备 |
| **不入库** | `course_media\*.mp4`、大 `.fsp` | 体积原因排除 |

---

## 已知缺口

| 缺口 | 说明 |
|---|---|
| **P03 缺论文原文 PDF** | 现为精读版；DOI `10.1021/acsnano.5b00218`，需索取或自行下载 |
| **8 个包的 `results\` 为空** | 只有课程原始工程，尚未自己跑过 |
| **文档引用了仓库外路径** | 克隆到别的机器时 `scripts\` / `docs\` 不存在（见上「路径约定」） |
| **Lumerical 与 license 不在仓库内** | 商业软件，属正常 |
