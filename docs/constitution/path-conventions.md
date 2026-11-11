# 路径约定

> 违反任意一条 → 仿真会在最贵的地方失败，且报错信息误导。

## 1. 纯 ASCII

**目录名、文件名、`.fsp` 路径，全部只能用 ASCII**（空格可以，中文不行）。

- GPU 引擎（`fdtd-engine.exe`）对非 ASCII 路径报 **Windows 1113 `ERROR_NO_UNICODE_TRANSLATION`**，
  Job Manager 弹窗显示为乱码。
- CPU 引擎（`fdtd-engine-msmpi.exe`）没有这个问题——**所以"CPU 能跑"不能证明路径合规**。
- 判断依据永远看 `<工程名>_p0.log`，不看弹窗。

历史遗留的中文目录名要改，**并记录 old → new 映射**在该单元的 `notes/`。

## 2. 工作根

| 概念 | 值 |
|---|---|
| 工作区根 | `F:\Lumercial_WS\FDTD_WS` |
| 会话启动目录 | **必须是工作区根**（见根 `AGENTS.md` 铁律 1） |
| 临时脚本 | `_scratch\`，**不要写 `%TEMP%`** |
| 交付物 | **两轨**：原始产物 → 单元内 `results\`；跨包可比交付物 → 根级 `results\<PkgID>\<YYYY-MM-DD>\`（见 §6） |

## 3. 零外写

- 不写单元目录之外（`_scratch` 除外）。
- 不写 `cases\` 下的任何文件（只读）。
- 不改 `paper\` 里的 PDF。

## 4. 体积

| 项 | 红线 | 依据 |
|---|---|---|
| 单文件 | **> 100 MB 不入库** | GitHub 直接拒收，不是警告 |
| `*.mp4` / `*.rar` / `*.zip` | 全忽略 | 见 `.gitignore` 第 1 条 |
| `.fsp` | 只有超限的那一个被忽略，其余入库 | 见 `.gitignore` 第 2 条 |
| `*_p0.log` | **必须保留** | 三判据之一，删了就无法证明算过 |

提交前跑 `python tools/check_git_limits.py`，`ERROR=0` 才推。

## 5. 许可席位

每个 `lumapi.FDTD()` = 一个 `fdtd-solutions.exe` = 占 1 个许可席位。
`close()` 必须落在 `finally`；批量脚本漏一个就少一个席位。

## 5.1 GPU 加速：什么时候能开、什么时候必须关（2026-11-11 新增）

GPU 由**全局** ini 开关控制（`%APPDATA%\Lumerical\FDTD Solutions.ini` 的
`FDTD\GPU-mode=true|false`），不是单工程属性。所以「这个工程用 GPU」只能靠
**跑前切、跑后还原**实现。

| 工具 | 作用 |
|---|---|
| `tools/gpu_mode.py --status` / `--set gpu\|cpu` | 读/切全局开关（改 ini，**不碰 `setresource`**——它会持久化并污染配置，见 `field-manual.md` §6.3） |
| `tools/gpu_guard.py --fsp <工程> --run "<命令>"` | 按工程资格自动切，跑完（含异常）必还原 |
| `tools/probe_gpu_eligibility.py` | 只判定不切，产出 `gpu_matrix.json` 与批次 |

### 什么工程能上 GPU

| 判据 | 结论 | 依据 |
|---|---|---|
| 路径含非 ASCII | **禁止** | GPU 引擎报 1113 |
| 含 `TFSFSource` | **禁止** | GPU 引擎明确不支持（D-011） |
| `dimension=2D` | **禁止** | 2D 链路未通（D-008） |
| 含 **Drude / Conductive** 金属 | **禁止**（默认） | real32 会发散，见下 |
| 显存估算 > 85% VRAM | **禁止** | 8 GiB 不够 |
| 全介质 / 采样 (n,k) 金属 | **可用** | 实测成功 |

### 为什么「含 Drude」必须拦（实测 2026-11-11，D-019）

同一 spec（P01，Au Drude + Al2O3 + Si），只换引擎：

| 引擎 | wall | 迭代 | peak A | 结果 |
|---|---|---|---|---|
| CPU 双精度 8 proc | 29 s | 跑完 | **0.8069 @ 5.850 µm** | ✅ 正确 |
| GPU real32 | **12 s** | **303（早停）** | **1.0000 @ 4.400 µm** | ❌ 垃圾 |

**GPU 快 2.4 倍，答案全错**。而且引擎**不抛异常**：日志里有
`ERROR: Early termination, fields are diverging`，紧跟着却是
`Simulation completed successfully at: ...`——`run()` 正常返回，产物是 0 或垃圾值。

### 发散的真前兆是日志里这一行，不是材料名

```
WARNING: 0 < permittivity < 1, EM fields may diverge if timestep for GPU simulation is too large!
```

对照实测：P04 用 **Au 采样 (n,k)** 上 GPU → 无此警告 → 成功跑完 12165 iter / 340 s；
P03 与 P01 用 **Drude** → 有此警告 → 发散。所以 `gpu_guard.py --probe-log`
检查的是这行警告，不是材料名。

### 硬规矩

1. **结论一律以 CPU 双精度为准**。GPU 只用于「快速探索 / 粗筛」。
2. 任何 GPU 跑完，**必须**查 `_p0.log` 有无 `diverging` 或 `0 < permittivity < 1`；
   有则整批产物作废，不得进入验收表。
3. 切了必须还原。`gpu_guard.py` 在 `finally` 里还原；手切请用 `gpu_mode.py --set cpu`。
4. **不要用 `setresource` 切引擎**。它改全局配置且不还原会让 GUI 报
   "There are no active GPU resources"（`field-manual.md` §6.3 的实测事故）。

## 6. `results/` 落位：**双轨**（单元轨 + 交付轨）

> 机器判据：`tools/check_results_layout.py`（自带 `--self-test`；`--also-cases` 连单元轨一起查）。
> 本节写它判什么、以及哪些部分判不了只能靠自觉。

### 6.0 两轨分工（2026-11-11 裁定，消除旧版 §2 与 §6 的冲突）

`results/` 有两个合法落点，**不是「两种都行」，是两种不同的东西**：

| 轨 | 路径 | 放什么 | `index.json` | 机器判 |
|---|---|---|---|---|
| **单元轨** | `cases\<P0N>\results\` | 原始产物：`.fsp` / `_p0.log` / `point_*.csv` / `summary.csv` / 单次运行子目录 | **不要求** | `check_results_layout.py --also-cases`（只查平铺与体积） |
| **交付轨** | `results\<PkgID>_<ShortTitle>\<YYYY-MM-DD>\` | 跨包可比交付物：`.png` / 汇总 `.csv` / `repro_report.md` | **必须**（四键，见 §6.2） | `check_results_layout.py`（默认） |

**判定口诀**：跟某一次运行一一对应、换求解器就要重出的 → 单元轨；
要拿来跟别的包横向比、进报告与图的 → 交付轨。

两轨互不复制：交付轨的 `.png` 由单元轨的 `.csv` 画出来，**不要把同一份 csv 两处都放**。

历史依据：2026-11-10 定 §6 时只写了交付轨，`§2` 与根 `AGENTS.md` 的「产出只落单元内」
没同步改，导致两套口径并存到 2026-11-11（根级 3 包 63 文件、单元级 3 包同时在跑）。
本轮把三处一次性改齐：本节 + `§2` 表格 + 根 `AGENTS.md` 铁律段。

### 6.1 目录形状（交付轨）

```
results/
└─ <PkgID>_<ShortTitle>/          # 与 cases/ 同名，正则 ^P\d{2}_[A-Za-z0-9_]+$
   └─ <YYYY-MM-DD>/               # 复现日期，同一个包可以有多天
      ├─ index.json               # 指向本次产物的索引
      └─ ...                      # csv / png / npz 平铺在这一层
```

**两级都必须存在，中间不能省。** 直接把 `sw_field_ey_xz.png` 放进
`results/P04_AnomalousReflection_047/` 是违规（2026-11-10 实测 49 处这类历史残留）。

理由不是洁癖：一个包会被复现多次（换求解器、换网格、修 bug 后重跑）。只有一层目录时，
`R.csv` 到底是 11-03 的还是 11-09 的，只能靠文件时间戳猜——而 `_p0.log` 的时间戳
恰恰是「是否真跑过」的判据之一，用时间戳区分结果会把两件事混成一件。

### 6.2 `index.json`

```json
{
  "case": "P02",
  "date": "2026-11-10",
  "verdict": "solver_mismatch",
  "artifacts": ["curve_pcr.csv", "spectra.png"]
}
```

| 项 | 机器判 | 说明 |
|---|---|---|
| `case` / `date` / `verdict` / `artifacts` 四个键 | ✅ 缺键即 FAIL | |
| `date` 与所在目录名逐字相等 | ✅ 不等即 FAIL | 防「复制昨天的目录改天」 |
| `verdict` 的取值 | ❌ 靠自觉 | 沿用复现卡 `verdict.status` 五值：`reproduced` / `solver_mismatch` / `inconclusive` / `unresolved` / `fitted`。**不要自造词** |
| `artifacts[]` 是否列全了本目录的文件 | ❌ 靠自觉 | 脚本不比对目录内容；漏列等于下次没人知道哪个文件是结论 |
| `index.json` 只放指针、不抄长表 | ❌ 靠自觉 | 与 `docs/AGENTS.md`「不复制内容」同一条原则 |

### 6.3 豁免与迁移

- 占位文件（`.gitkeep` / `.keep` / `.gitignore`）与以 `.` 开头的目录**不算违规**。
- **已知的两种历史形态**（2026-11-10 实测 49 处，都由旧约定或旧习惯产生，不是缺陷）：
  1. **平铺在论文目录下**（45 处，P02 20 / P03 8 / P04 17）：
     `results/P02_.../curve_pcr.csv` 直接躺在论文目录里，没有日期层。
  2. **按用途分类的子目录**（4 处，全在 P04）：
     `logs/`、`scripts/`、`run_thi00_gpu/`、`P04_AnomalousReflection_047_repro/`。
     目录名不是日期 → 违规。这类最容易被误认为「已经分好类了」，
     但 `logs/` 里混着不同日期的 `_p0.log`，正是本次要拆开的对象。
- **归位规则**：按**内容日期**（不是 `mv` 时的今天）拆进 `<YYYY-MM-DD>/`；
  `_p0.log` 跟它对应的那次结果同一天。归位只动位置、不改文件名与内容；
  同一天的多个产物进同一个日期目录，并补一个 `index.json`（§6.2）。
- 归位本身不产生新的科学结论，**不需要** `[R6]` 同输入回归。
- 旧文档 `naming.md` §5 曾写 `results/<run_id>/`（例 `20261106_a`），**该条已废止**，
  与本节的差异不是「两种都行」，是旧规则错了：单层目录无法区分同一个包的多次复现。
- **单元轨的豁免**（2026-11-11 新增）：`cases\<P0N>\results\` 只查两件事——
  ① 根下不得有平铺文件（必须进子目录）；② 单文件不得超过 100 MB（§4 体积红线）。
  子目录名**不做格式约束**（`repro_2026-11-09_fsp/`、`repro_p01/` 都合法），
  也不要求 `index.json`——单元轨的追溯靠 `_p0.log` 与目录名，不靠索引文件。
