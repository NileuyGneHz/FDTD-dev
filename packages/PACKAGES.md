# PACKAGES.md — 打包索引（Agent 协作入口）

> **这份文件是本工作空间的任务地图。**
> 每次协作开始时，先读这里定位本次要做的包，再进包内读 `README.md`。
>
> 规则写在 `..\agent.md`，踩坑记录在 `..\SKILL.md`。

---

## 怎么用（给 Nileuy）

1. 说一句「**这次做 P03**」或「这次做 Ding2015 半波片」——agent 会读本表定位。
2. Agent 进包后读该包 `README.md` 的 **§0 Agent 快速接管**，拿到本次目标、验收标准、入口脚本。
3. 开工前 agent 会跑 `tools\check_packages.py` 自检 + ASCII 闸门。

**新建一个包**：复制 `_TEMPLATE\` → 改名 → 填 README。填完跑自检。

---

## 包总表

| 包 ID | 主题 | 论文 | 状态 | 主线 |
|---|---|---|---|---|
| [P01](P01_Absorber_042/README.md) | 红外完美吸收器 | 042: *Infrared Spatial and Frequency Selective Metamaterial with Near-Unity Absorbance* | 已复现（`ts` 待确认） | — |
| [P02](P02_PolarizationControl_045/README.md) | 偏振转换 | 045: *Broadband highly-efficient dielectric metadevices for polarization control* | Fig.3(a) 已复现（相位待做） | — |
| [**P03**](P03_HWP_Ding2015/README.md) | **等离激元半波片 / Figure 1** | **Ding 2015, ACS Nano** | **★ 进行中** | **★ D1 主线** |
| [P04](P04_AnomalousReflection_047/README.md) | 异常反射 | 047: *High-Efficiency Broadband Anomalous Reflection by Gradient Meta-Surfaces* | 未开始 | — |
| [P05](P05_Metalens_048/README.md) | 圆偏振超透镜 | 048: *Dual-polarity plasmonic metalens for visible light* | 未开始 | — |
| [P06](P06_Vortex_049/README.md) | 涡旋光产生 | 049: *Light Propagation with Phase Discontinuities* | 未开始 | 终点目标 |
| [P07](P07_BrokenSymmetry_041/README.md) | 破缺对称介质谐振器 | 041: *Broken Symmetry Dielectric Resonators for High...* | 未开始 | — |
| [P08](P08_BroadbandAbsorber_043/README.md) | 宽角度可见光吸收器 | 043: *Wide-angle, polarization-independent ultrathin broadband visible absorbers* | 未开始 | — |
| [P09](P09_GrapheneAbsorber_044/README.md) | 石墨烯完美吸收器 | 044: *A perfect absorber made of a graphene micro-ribbon...* | 未开始 | — |
| [P10](P10_SHG_046/README.md) | 二次谐波产生 | 046: *Second-Harmonic Generation from Magnetic Metamaterials* | 未开始 | — |

**状态图例**：`未开始` / `进行中` / `已跑通` / `已交付`

**学习路线**（导师建议）：041 → 045 → 047 → 048 → 049

---

## 目录规范

```
packages\
├─ PACKAGES.md          本文件
├─ _TEMPLATE\           新建包时复制这个
└─ P0N_<课题>\          一包 = 一篇论文
   ├─ README.md         ★ agent 接管入口
   ├─ paper\            论文 PDF + 参考资料 + `自测题_5问.md`
   ├─ fsp\              .fsp 工程（ASCII 文件名）
   ├─ scripts\          本包专用脚本
   ├─ results\          数据与图
   └─ notes\            笔记与排查记录
```

### 每包一份自测材料（2026-10-08 起）

10 个包的 `paper\` 下各有一份 **`自测题_5问.md`**：5 道题 + 参考答案 + 基础缺口自查表。
统一结构（Q1 物理现象 / Q2 公式 / Q3 前置基础 / Q4 设计选择 / Q5 仿真对照）。
新增论文时照此结构补一份，模板与样例见 `P03_HWP_Ding2015\paper\自测题_5问.md`。

### 命名规则（必守）

1. **包目录**：`P0N_<英文短名>_<课程讲次或年份>`
   - ✅ `P03_HWP_Ding2015` / `P01_Absorber_042`
   - ❌ `P03_等离激元半波片`（中文 → GPU 引擎崩）
2. **`.fsp` 文件名**：纯 ASCII，只用字母/数字/下划线
   - ✅ `hwp_unitcell.fsp`
   - ❌ `半波片单元胞.fsp` → 必须改名，并在包 README 登记新旧对照
3. **论文 PDF**：保留原文件名即可（在 `paper\` 内，不参与仿真路径）
4. **脚本**：`build_*` 建模 / `scan_*` 扫参 / `plot_*` 出图 / `check_*` 校验

---

## 跨包共享（`_shared\`）

只对**两个以上包**有用的东西才放这里。单包专用的留在包内 `scripts\`。

| 文件 | 用途 |
|---|---|
| `_shared\lumapi_common.py` | 会话工厂（含重试）、ASCII 闸门、`assert_ran()` 三判据 |
| `_shared\README.md` | 共享区说明 |

**已交付的通用工具**（留在 `F:\Lumercial_WS\scripts\`，此处只引用不复制）：

| 脚本 | 用途 |
|---|---|
| `z_fix_gpu_res.py cpu\|gpu` | GPU/CPU 资源一键恢复（幂等 + 备份 + 回读） |
| `lumapi_probe.py` | `.fsp` 对象树探查 |
| `fsp_strings.py` | `.fsp` 二进制字符串抽取（材料名唯一来源） |
| `z_ascii_work.py` | 中文路径课件复制到 ASCII 目录 |
| `d2_lib.py` | D2/吸收类共享模块 |
| `gs_cgh.py` / `gs_demo.py` | GS 相位恢复算法（纯 Python） |

---

## 归档状态（2026-09-30 已完成搬迁）

**论文 PDF、`.fsp` 工程、`.lsf` 脚本、引擎日志已从 `Classes\FDTD\` 复制入各包。**
原件在 `Classes\FDTD\` 保留不动。搬迁报告见 `..\_migration_report.md`。

| 类别 | 数量 | 归属 |
|---|---|---|
| 论文 PDF | 9 篇 + P03 原文 | 各包 `paper\`（P03 现有 **2** 份：原文 + 精读版） |
| `.fsp` 工程 | 40 个 | 各包 `fsp\`（**非 ASCII 名已改 ASCII**） |
| `.lsf` 脚本 | 17 个 | 各包 `scripts\` |
| 引擎日志 | 6 个 | 各包 `fsp\`（随 `.fsp` 同名） |
| 课程视频 | 11 个（7.7 GB） | `..\course_media\` |

**改名对照**：凡改过名的包，其 `fsp\_rename_map.json` 记录了「新名 → 原名」。

| 包 | 改名示例 |
|---|---|
| P07 | `我的第一个模型（加密网格）.fsp` → `first_model_mesh_refined.fsp` |
| P01 | `红外完美吸收器.fsp` → `infrared_perfect_absorber.fsp` |
| P08 | `斜入射BFAST.fsp` → `oblique_BFAST.fsp` / `正入射.fsp` → `normal_incidence.fsp` |
| P09 | `石墨烯完美吸收器.fsp` → `graphene_perfect_absorber.fsp` |
| P04 | `fig2c&3.fsp` → `fig2c_and_3.fsp` |

**各包内容一览**：

| 包 | paper | fsp | scripts | 入口工程 |
|---|---|---|---|---|
| P01 | 1 | 2 | 0 | `infrared_perfect_absorber.fsp` |
| P02 | 1 | 4 | 3 | `fig4a.fsp` |
| P04 | 1 | 7 | 7 | `fig1bc.fsp` |
| P05 | 1 | 4 | 2 | `RCP.fsp` |
| P06 | 1 | 11 | 5 | `fig2a.fsp` |
| P07 | 1 | 4 + 1 笔记 | 0 | `first_model_mesh_refined.fsp` |
| P08 | 1 | 4 | 0 | `normal_incidence.fsp` |
| P09 | 1 | 3 | 0 | `graphene_perfect_absorber.fsp` |
| P10 | 1 | 3 | 0 | `fig3a.fsp` |
| P03 | **2**（原文 + 精读版） | 4 | 6 | `fig1_hwp_paper_materials.fsp` |

---

## 尚未搬迁的资产（登记路径）

| 资产 | 当前位置 | 说明 |
|---|---|---|
| D1 的 `.fsp` 与脚本 | `F:\Lumercial_WS\WS\`、`F:\Lumercial_WS\scripts\` | 见 P03 README 的「存量资产位置」 |
| D2 的 `.fsp` | `F:\Lumercial_WS\projects\d2\`、`projects\L042\` | 吸收类，可并入 P01 |
| 通用工具脚本 | `F:\Lumercial_WS\scripts\` | `z_*` 诊断脚本、`lumapi_probe.py` 等 |
| 石墨烯光学常数软件 | `Classes\FDTD\课件\044...\石墨烯光学常数计算软件.zip` | 未搬（可执行程序，非论文/fsp） |

---

## 自检

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" tools\check_packages.py            # 检查全部包
"$PY" tools\check_packages.py --pkg P03  # 只查一个包
```

检查项：论文是否齐 / `.fsp` 文件名是否纯 ASCII / README 是否填完 / 是否有孤儿文件。
