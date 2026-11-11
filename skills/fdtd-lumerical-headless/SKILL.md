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
完整正文与八章结构在 `docs/constitution/field-manual.md`（含 §0 按症状索引，约 1250 行）。
**路径一律相对仓库根 `FDTD_WS/`**，不要写 `F:\...` 绝对路径（换机即失效）。

## CRITICAL（违反即停止）

1. **`run()` 之前必须 `save()` 过**：工程没有磁盘路径时，`run()` 不抛异常、`layoutmode` 仍为 1、
   `getresult` 报 `Can not find result`、**不生成 `_p0.log`** —— 引擎什么都没算。
   2026-11-08 本机 v251 三组对照（`_scratch/regress/_gate/session_rule/`）：

   | 序列 | 实测结果 |
   |---|---|
   | 建模 → `run()`（**未 save**） | 4.9 s 后返回、异常为 None、`layoutmode=1`、无 `_p0.log`、`getresult` 失败 |
   | 建模 → `save` → `run()`（**同会话**） | `layoutmode=0`、`_p0.log` 4181 B、`Completed 43 iterations` |
   | `save` → `close` → 新会话 `load` → `run` | 与上一行**逐位一致**（T_max 相同、43 iterations） |

   → 「必须开新会话才能 run」是**误归因**；真正的前提是 `save`。两段式（save→close→新会话 load→run）
   仍可作安全默认（可复算、可重放），但**同会话迭代是允许的**：改参 → `save` → `run` → 读回，
   实测第二轮把 source 波长 1500→1000 nm，`T` 改变、迭代数 43→68（`session_rule/c4b.json`）。
   代价是同一 session 内跑多轮时，**每轮都要 `switchtolayout()` 再改参**。
2. **`close()` 一律落在 `finally`**。每个 `lumapi.FDTD()` = 一个 `fdtd-solutions.exe` = 占 1 个许可席位，
   漏掉一个就少一个席位。
3. **路径必须纯 ASCII**（目录名、文件名都算）。GPU 引擎会报 Windows 1113
   `ERROR_NO_UNICODE_TRANSLATION`，Job Manager 弹窗只显示乱码——**永远以 `_p0.log` 为准**。
4. **`load` 一个已算过的 `.fsp` 后不能直接 `set`**：先 `switchtolayout()`，否则报
   `you cannot modify most simulation objects while in analysis mode`。
5. **`getindex()` 收的是频率（Hz），不是波长**：传 `C0/λ`。误传波长不报错，只会悄悄外推出鬼数字
   （TiO₂ 得到 5.99 而非 2.45）。拿到数先和文献值对照。
6. **headless 下 `?` / `print` 的输出会被静默丢弃**：不在 fd 1、不在 fd 2，`eval()` 也返回 None（实测）。
   `.lsf` **无法用打印汇报结果**——必须赋值给具名变量，再由 Python 侧 `getv("名")` 读回。
7. **判断任何工具有效性或结论是否成立，先设对照组**：同一操作在已知正常的样本上跑一遍，
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

## 跑 `.lsf` 与读回结果（唯一入口）

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-headless/scripts/run_lsf.py \
      --lsf <file.lsf> --config <cfg.json> --out <dir> --read varA,varB [--dry-run] [--json]
```

`run_lsf.py` 是 `.lsf` 的唯一执行入口（`docs/constitution/script-contract.md` §3）。三条安全闸：

| 闸 | 触发 | 退出码 |
|---|---|---|
| 含 `run;` / `run()` / `add*` / `save` 而未写 `allow_run=true` | 会占许可机时 | 2 |
| `allow_run=true` 却无正 `timeout_seconds` | 悬挂占席位 | 2 |
| `config.fsp` 在 `cases/` 内 | 引擎把 `<fsp>_p0.log` 写回只读资产 | 2 |

`--dry-run` 不开会话、不 import `lumapi`，只打印解析出的 plan 与 refusal。

**读回结果的两条硬事实**（2026-11-08 实测）：

- `.lsf` 里 `? x;` / `print(...)` 在 headless 下**不产生任何输出**（见 CRITICAL #6）；
  于是约定：`.lsf` 只负责算，结果赋值给具名变量，Python 侧 `getv("x")` 取回，`--read` 就是这份名单。
- Python API 的 `getresult("mon","T")` 返回的是 **dict**：`{'lambda','f','T','Lumerical_dataset'}`。
  数组在键里，不在返回值本身——`np.array(f.getresult(...))` 会得到 object 数组并炸在 `float()`。

```python
r = f.getresult("T", "T")          # dict
lam = np.array(r["lambda"]).ravel()
T = np.array(r["T"]).ravel()
```

> 每轮 `run_lsf.py` 都会在 `--out` 落一份 `_p0.log`（`acceptance.md` §1 要求），
> 即使没有 `.fsp` 也有可审计记录。

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
| `docs/constitution/field-manual.md` | **动手前**读一次，八章 + §0 症状索引，唯一正文 |
| `docs/constitution/collaboration-charter.md` | 需要协作章程 / 铁律 / 标准循环时 |
| `library/py/lumapi_common.py` | 需要已验过的会话/校验函数（`setup_env` / `verify_and_run` / `assert_ran` / `n_at`）时 |
| `cases/INDEX.md` | 按包 ID 定位论文与工程时（原 `packages/PACKAGES.md` 已迁到这里） |
| `_scratch/archive/SKILL_old_user_level.bak-20260930.md` | 只在回溯旧版结论时 |
