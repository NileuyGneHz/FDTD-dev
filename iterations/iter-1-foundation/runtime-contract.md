# iter-1 · 运行契约

> 本文件是**唯一真相源**：`agents/*/agent.yaml`、`tools.yaml` 的取值以它为准。
> 两者冲突时，先改这里，再改配置。

## 1. 平台

- **仅 Windows**：Lumerical 只在该平台发布，工作区不做跨平台兼容。
- 工作根：`F:\Lumercial_WS\FDTD_WS`；**会话必须在此目录启动**。
- 路径：纯 ASCII；不接受中文目录名与文件名（GPU 引擎 1113）。

## 2. 运行时

| 项 | 值 | 说明 |
|---|---|---|
| Python | `C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe` | 系统 Python 3.14 无 numpy，`import lumapi` 直接崩 |
| lumapi | `F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python` | 通过 `sys.path.insert` 挂入，不走 `pip install` |
| License | `ANSYSLMD_LICENSE_FILE=1055@localhost` | 每次会话前设置 |
| 临时区 | `_scratch\` | 不写 `%TEMP%` |

## 3. Agent 参数

| 项 | 值 | 理由 |
|---|---|---|
| temperature | 0.2 | 路径、数值、属性名都不能"发挥" |
| max_steps | 120 | 一条完整复现约 40–80 步（含重跑） |
| timeout | 3600 s | 单次 FDTD 扫描可能几十分钟 |
| 自愈上限 | 5 次 | 超过即停手，写 `journal/` 交人 |

## 4. 工具白名单

**允许**：`read` / `write` / `edit` / `glob` / `grep` / `pwsh`（限本工作区）/ 技能脚本。

**禁止**：
- 写 `cases/` 下任何文件（只读资产）
- 删除 `_p0.log`、`.fsp`、`paper/` 内文件
- 任何联网操作（本工作区默认离线）
- 在 `projects/` 之外创建课题目录

## 5. 许可席位

- 每个 `lumapi.FDTD()` = 一个 `fdtd-solutions.exe` = 1 个席位。
- `close()` 必须落在 `finally`。
- 批量脚本先跑 `--dry-run` 数一下会开几个会话。

## 6. 双宿主

| 宿主 | 入口 | 约束 |
|---|---|---|
| DSH | `.agents/skills`（真目录 + junction） | 项目根靠 `.git` 定 |
| WorkBuddy | `.workbuddy/skills`（同上） | 只认 `cwd`，不向上搜 |

两处入口由 `tools/skills-wire.py` 生成；增删技能后必须重跑。

## 7. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-06 | 初版：确立 Windows-only、托管 Python、温度 0.2、自愈上限 5 |
