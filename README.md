# FDTD_WS — 超表面 Lumerical 研究工作空间

> 面向超表面科研人员的本地工作区：把「读论文 → 提参数 → 建模 → 跑谱 → 判偏差 → 出图」
> 固化成可复现、可审计的流水线，并让 **DSH** 与 **WorkBuddy** 两个 AI 宿主按同一套技能接管。
> **仅支持 Windows**（Lumerical 只在该平台发布）。

## 五分钟入项

| 顺序 | 读什么 | 为什么 |
|---|---|---|
| 1 | [`AGENTS.md`](AGENTS.md) | 运行契约：铁律、目录地图、一次会话怎么开 |
| 2 | [`docs/product-context/README.md`](docs/product-context/README.md) | 为谁做、解决什么、**不做什么** |
| 3 | [`docs/constitution/workspace-layout.md`](docs/constitution/workspace-layout.md) | 目录契约全文 |
| 4 | [`docs/tasks/active/`](docs/tasks/active/) | 现在在做什么（AI 优先读这里） |

## 目录

```
FDTD_WS\
├─ AGENTS.md / CLAUDE.md     给 AI 的运行契约
├─ docs\                     流程与决策（L1–L5）
│  ├─ product-context\       L1 为什么存在
│  ├─ constitution\          L2 路径/命名/归档/脚本/宿主接入
│  ├─ features\specs\        L3 能力验收
│  ├─ plans\                 L4 有日期的方案
│  └─ tasks\{active,recent,archive}\   L5 动作拆分
├─ cases\                    十个已复现论文（只读，论文与 .fsp 同包）
├─ projects\                 在研课题（可写，与 cases 同构）
├─ library\                  跨课题复用：材料 / 纯模块 / schema / 图样式
├─ skills\                   唯一的可执行能力库（DSH 与 WorkBuddy 共用）
├─ agents\                   角色包：契约 / 参数 / 编排 / 工具白名单 / 评测 / 记忆
├─ tools\                    自检：包结构、脚本归属、体积、宿主接线
├─ defects\  journal\  iterations\
├─ _scratch\                 一次性脚本与中间产物（不进库）
└─ _archive\                 课程素材与历史日志（不进库）
```

## 归档单元：论文和工程必须在一起

一个单元 = 一篇论文或一个课题，四样东西互相可追溯：

```
P01_Absorber_Liu2010\
├─ README.md   §0 目标与验收 · §1 论文 · §2 参数 · §3 偏差诊断
├─ paper\      论文 PDF + 补充材料（只读）
├─ model\      .fsp（状态） + .lsf（可读源） + spec_<id>.json（参数）
├─ config\     sweep_*.json —— 只有参数，没有逻辑
├─ results\    csv / 图 / report.md / _p0.log
└─ notes\      踩坑、口径差异、待问作者
```

包内**不放 `.py`**：能力脚本属于 `skills/`，`.lsf` 留在 `model/`，一次性脚本进 `_scratch/`。

## 两个宿主怎么接

| 宿主 | 项目入口 | 说明 |
|---|---|---|
| DSH | `.agents/skills/<name>` | 靠**仓库根的 `.git`** 定项目根 |
| WorkBuddy | `.workbuddy/skills/<name>` | 只认**当前目录**，不向上搜索 |

两处都是**真实目录 + 逐技能 junction**，由脚本生成，不手改：

```powershell
python tools\skills-wire.py            # dry-run
python tools\skills-wire.py --apply    # 执行
python tools\skills-doctor.py          # 六项体检，应输出 ALL GREEN
```

> ⚠️ 会话必须在 `FDTD_WS` 根启动。从 `projects\R01_x` 打开，项目技能会全部消失且不报错。

## 自检

```powershell
python tools\skills-doctor.py      # 宿主接线
python tools\check_scripts.py      # 包内不许有 .py
python tools\check_packages.py     # 单元结构
python tools\check_git_limits.py   # 提交前体积（单文件 > 100 MB 会被 GitHub 拒收）
```

## 铁律（完整版见 `docs/constitution/`）

1. **路径纯 ASCII** —— GPU 引擎对非 ASCII 路径报 1113，弹窗只显示乱码。
2. **`.fsp` 不并行改** —— 二进制，无法 diff、无法合并；谁改谁立刻提交。
3. **单文件 > 100 MB 不入库** —— GitHub 直接拒收。
4. **不看 `_p0.log` 不算跑过** —— `layoutmode == 0` + 存在 `_p0.log` + 日志含 `Completed`。
5. **先设对照组再下结论** —— 本项目最贵的一条。

## 技能与角色

- 技能总表：[`skills/INDEX.md`](skills/INDEX.md)（`stage` 决定编排顺序）
- 角色总表：[`agents/INDEX.md`](agents/INDEX.md)
- 新增技能只改 `skills/INDEX.md` 一行 + 复制 `_TEMPLATE`，**不改已有技能名**

## 当前迭代

[`iterations/iter-1-foundation/`](iterations/iter-1-foundation/)：目录重建、技能接线、检查脚本。
验收条件见 [`acceptance.md`](iterations/iter-1-foundation/acceptance.md)。
