---
name: fdtd-lumerical-headless
description: >
  用 lumapi 无界面构建/验证 Ansys Lumerical FDTD 脚本（.lsf）与工程（.fsp）：
  环境三件套、会话生命周期、改参数读属性、结果提取与三条判据。
  当需要新建或修改 Lumerical 仿真脚本、排查脚本报错、读陌生 .fsp 的对象树或材料、
  做参数扫参自动化时使用。
  触发词：lumapi、FDTD 脚本、headless、.fsp 探查、扫参、会话报错。
  v251 已实测的坑集中在正文，本文件只是入口。
agent_created: true
updated: 2026-11-06
---

# Ansys Lumerical FDTD 无界面脚本开发（入口）

## 概述

用 `lumapi` 在无界面模式下建、改、跑、读 FDTD 模型；本文件只放**进入后必须立刻知道**的规则，
完整正文与八章结构在 `F:\Lumercial_WS\FDTD_WS\SKILL.md`（含 §0 按症状索引，约 1250 行）。

## CRITICAL（违反即停止）

1. **`run()` 必须发生在 `load` 之后的新会话里**：`save` → `close` → 新会话 `load` →
   `switchtolayout` → `run`。直接在建模会话里 `run()` 会**静默失效**——不抛异常、立刻返回、什么都没算。
2. **`close()` 一律落在 `finally`**。每个 `lumapi.FDTD()` = 一个 `fdtd-solutions.exe` = 占 1 个许可席位，
   漏掉一个就少一个席位。
3. **路径必须纯 ASCII**（目录名、文件名都算）。GPU 引擎会报 Windows 1113
   `ERROR_NO_UNICODE_TRANSLATION`，Job Manager 弹窗只显示乱码——**永远以 `_p0.log` 为准**。
4. **`load` 一个已算过的 `.fsp` 后不能直接 `set`**：先 `switchtolayout()`，否则报
   `you cannot modify most simulation objects while in analysis mode`。
5. **`getindex()` 收的是频率（Hz），不是波长**：传 `C0/λ`。误传波长不报错，只会悄悄外推出鬼数字
   （TiO₂ 得到 5.99 而非 2.45）。拿到数先和文献值对照。
6. **判断任何工具有效性或结论是否成立，先设对照组**：同一操作在已知正常的样本上跑一遍，
   再判断是工具坏了还是输入不对。

## 核心工作流

1. **配环境（三件套，顺序不能换）**：
   `os.environ["ANSYSLMD_LICENSE_FILE"]="1055@localhost"` →
   `sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")` →
   `import lumapi` → `f = lumapi.FDTD(hide=True)`。
   是 `import lumapi`，**不是** `import ansys.lumerical`。
2. **用托管 Python**：`C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe`。
   系统 Python 3.14 无 numpy，`import lumapi` 直接崩。
3. **临时脚本写 `F:\Lumercial_WS\FDTD_WS\_scratch\`**，不要写 `%TEMP%`（C 盘），临时脚本不进版本库。
4. **改参数读属性一律 `setnamed(对象, 属性, 值)`**，不要 `select` + 裸 `set`——裸 `set` 依赖
   代码里看不见的「当前对象」全局状态。
5. **跑之前 `save`**，`run` 之后按三条判据确认真的算了（见下）。
6. **读结果前确认 `layoutmode == 0`**；`getv("layoutmode")` 直接读会报 `Failed to get variable`，
   先 `eval("lm = layoutmode;")` 再 `getv("lm")`。

三条「到底算没算」判据，缺一不算：

- `layoutmode == 0`
- 生成了 `<工程名>_p0.log`
- 日志里有 `Completed`

## 示例

```python
f = lumapi.FDTD(hide=True)
f.addfdtd()
t = f.addmaterial("Plasma")            # 不是 "Au"，不是 "Drude"
f.setmaterial(t, "name", "Au_paper")
f.setmaterial("Au_paper", {"Plasma resonance": 1.3665928e16,   # rad/s = 2*pi*2175 THz
                           "Plasma collision": 4.0840704e13})  # rad/s = 2*pi*6.5 THz
f.save(r"F:\Lumercial_WS\FDTD_WS\_scratch\probe.fsp")
f.close()
f = lumapi.FDTD(hide=True)
f.load(r"F:\Lumercial_WS\FDTD_WS\_scratch\probe.fsp")
f.switchtolayout()
f.run()
# 期望：同目录出现 probe_p0.log，日志末行 Auto Shutoff 小于设定阈值
```

## 故障排除

| 症状 | 处置 |
|---|---|
| `Could not bind socket on port …` / `ANSYSLI exited` | ansyscl 端口 TIME_WAIT 的瞬时故障，**重试**。报错里「check licenses」是误导 |
| `wrong number of arguments passed to setname` | `setname`/`getname`（**不带 d**）是另外两个真命令，误用不会抛 `NameError` |
| `Failed to get variable`（读 layoutmode） | 先 `eval("lm = layoutmode;")`，再 `getv("lm")` |
| GPU 引擎报 1113 / 弹窗乱码 | 路径里有非 ASCII；改纯 ASCII 后重跑，以 `_p0.log` 为准 |
| `Auto Shutoff` 末值 ≈1e-2 | 没收敛，`simulation_time` 太短；grep 时正则要带指数 `[0-9.eE+-]+` |
| `getindex` 返回离谱的 n,k | 传成波长了，改传频率 `C0/λ` |
| GitHub 拒收单文件 | >100 MB 直接拒收（不是警告），别把大 `.fsp` / mp4 混进版本库 |

## 按需加载

| 文件 | 何时读 |
|---|---|
| `FDTD_WS\SKILL.md` | **动手前**读一次，八章 + §0 症状索引，唯一正文 |
| `FDTD_WS\agent.md` | 需要协作章程 / 铁律 / 标准循环时 |
| `FDTD_WS\_shared\lumapi_common.py` | 需要已验过的会话/校验函数（setup_env / assert_ran / n_at）时 |
| `FDTD_WS\packages\PACKAGES.md` | 按包 ID 定位论文时 |
| `FDTD_WS\_scratch\archive\SKILL_old_user_level.bak-20260930.md` | 只在回溯旧版结论时 |
