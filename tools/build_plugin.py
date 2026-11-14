#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build_plugin.py — 把 FDTD 技能与 P01 完整工程打成 DSH 插件。

产物是一个可直接 `dsh plugin add` 的 npm 包：

    dsh-plugin-fdtd/
    ├─ package.json          name / version / main / dsh.bundle.patch
    ├─ cordis.patch.yml      插入一行到 profile 的插件 roster
    ├─ lib/index.js          host 端：同步技能 + 4 个工具
    ├─ skills/               15 个 fdtd-*（排除 __pycache__）
    ├─ library/py/           fsp_build / lumapi_common / angular_spectrum
    ├─ docs/field-manual.md  技能正文引用的技术手册
    ├─ demo/P01_Absorber/    ★ 已求解工程 + CSV + spec + log + README
    ├─ README.md / README-zh.md
    └─ MANIFEST.json         每个文件的 sha256

用法：
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/build_plugin.py --out F:/dsh_plugins/dsh-plugin-fdtd
    "$PY" tools/build_plugin.py --out ... --dry-run

退出码：0 成功 / 1 自检失败 / 2 参数错误
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
SKILLS_SRC = ROOT / "skills"
LIB_SRC = ROOT / "library" / "py"
DOCS_SRC = ROOT / "docs" / "constitution" / "field-manual.md"
P01 = ROOT / "cases" / "metasurface" / "P01_Absorber_042"
P01_RESULTS = P01 / "results" / "repro_2026-11-09_fsp"

PLUGIN_NAME = "dsh-plugin-fdtd"
VERSION = "0.1.0"

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_FILES = {".pyc", ".pyo"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_tree(src: Path, dst: Path) -> int:
    """复制目录，跳过缓存。返回复制的文件数。"""
    n = 0
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix in SKIP_FILES:
            continue
        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        n += 1
    return n


# --------------------------------------------------------------------- package.json


def make_package_json() -> dict:
    return {
        "name": PLUGIN_NAME,
        "version": VERSION,
        "private": True,
        "type": "module",
        "main": "lib/index.js",
        "exports": {
            ".": "./lib/index.js",
            "./package.json": "./package.json",
        },
        "files": ["lib", "skills", "library", "docs", "demo",
                  "cordis.patch.yml", "README.md", "README-zh.md", "MANIFEST.json"],
        "license": "MIT",
        "description": (
            "FDTD 技能包与 P01 完整工程：论文参数 → .fsp 建模 → R/T/A 谱 → 出图。"
            "含 15 个技能与一份已求解的超材料吸收器工程（layoutmode=0，91 点谱），"
            "打开即可看结果，也可改参数重跑。"
            " FDTD skill pack with a fully solved P01 metasurface absorber project."
        ),
        "keywords": ["dsh-plugin", "deepseek-harness", "fdtd", "lumerical",
                     "metasurface", "photonics", "figure"],
        "dsh": {"bundle": {"patch": "./cordis.patch.yml"}},
        "peerDependencies": {
            "@deepseek-ai/cordis": "^4.0.2",
            "@deepseek-ai/dsh": ">=0.1.7-rc.1",
            "@deepseek-ai/dsh-tools": "^0.1.7-rc.1 || ^0.2.0-rc.1",
        },
        "engines": {"node": "^22.19.0 || >=24.0.0"},
    }


CORDIS_PATCH = """\
# dsh-plugin-fdtd bundle patch: 把 host 端插件插入 profile 的 roster。
# 安装：dsh plugin --profile web add <path-or-git-url>
# 这个 patch 会自动应用，不要再手工往 profile 的 patch 里插一行（重复 id 会让加载器崩）。
- insert:
    - id: dsh-plugin-fdtd
      name: 'dsh-plugin-fdtd'
"""


# ---------------------------------------------------------------------- lib/index.js

INDEX_JS = r"""// dsh-plugin-fdtd — FDTD 技能包 + P01 完整工程
//
// 这个插件做两件事：
//   1) 首次启动时把包内 skills/ 同步到 ~/.agents/skills（幂等，不覆盖已有同名技能）
//   2) 注册 4 个工具，让 agent 能"列出演示 / 直接出图 / 体检环境"
//
// 出图零引擎：make_figure.py 只读 csv/npz，不需要 Lumerical 许可。

import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, cpSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import { defineTool } from '@deepseek-ai/dsh-tools'

const PKG_VERSION = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8')
).version

const PKG_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SKILLS_SRC = join(PKG_ROOT, 'skills')
const DEMO_DIR = join(PKG_ROOT, 'demo')
const SKILL_DIR = join(homedir(), '.agents', 'skills')

export const name = 'dsh-plugin-fdtd'
export const inject = ['tools']

/** 找可用的 python：优先 $DSH_FDTD_PYTHON，其次 python3 / python。 */
function findPython() {
  const explicit = process.env.DSH_FDTD_PYTHON
  if (explicit && existsSync(explicit)) return explicit
  for (const cand of ['python3', 'python']) {
    const r = spawnSync(cand, ['--version'], { encoding: 'utf8' })
    if (r.status === 0) return cand
  }
  return null
}

/** 把包内技能同步到技能库。已存在的同名目录**跳过**，不覆盖用户改动。 */
function syncSkills(log) {
  if (!existsSync(SKILLS_SRC)) return { copied: [], skipped: [] }
  mkdirSync(SKILL_DIR, { recursive: true })
  const copied = []
  const skipped = []
  for (const entry of readdirSync(SKILLS_SRC, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith('_')) continue
    const src = join(SKILLS_SRC, entry.name)
    const dst = join(SKILL_DIR, entry.name)
    if (existsSync(dst)) {
      skipped.push(entry.name)
      continue
    }
    cpSync(src, dst, { recursive: true })
    copied.push(entry.name)
  }
  log?.(`[fdtd] skills: copied ${copied.length}, skipped ${skipped.length} (existing)`)
  return { copied, skipped }
}

/** 读 demo/<id>/README.md 的首个标题作为名字。 */
function demoTitle(dir) {
  const readme = join(dir, 'README.md')
  if (!existsSync(readme)) return null
  const first = readFileSync(readme, 'utf8').split('\n').find((l) => l.startsWith('#'))
  return first ? first.replace(/^#+\s*/, '').trim() : null
}

/** 列出一个 demo 案例的产物。 */
function demoInfo(id) {
  const dir = join(DEMO_DIR, id)
  if (!existsSync(dir)) return null
  const files = readdirSync(dir)
  const fsp = files.find((f) => f.endsWith('.fsp'))
  const csv = files.find((f) => f.endsWith('.csv'))
  return {
    id,
    name: demoTitle(dir) || id,
    dir,
    fsp: fsp ? join(dir, fsp) : null,
    fsp_mb: fsp ? +(statSync(join(dir, fsp)).size / 1024 / 1024).toFixed(2) : null,
    csv: csv ? join(dir, csv) : null,
    spec: files.find((f) => f.endsWith('.json')) ? join(dir, files.find((f) => f.endsWith('.json'))) : null,
    p0_log: files.find((f) => f.endsWith('_p0.log')) ? join(dir, files.find((f) => f.endsWith('_p0.log'))) : null,
    files,
  }
}

export function apply(ctx) {
  const sync = syncSkills()

  // ---- 1) 列出演示案例 -------------------------------------------------
  ctx.tools.register(defineTool({
    name: 'fdtd_demo_list',
    description:
      '列出本插件自带的 FDTD 演示案例（每个案例含一份可打开的 .fsp 工程与一份可出图的 CSV）。'
      + ' 用于回答"你有什么可以看/可以跑"。',
    parameters: {},
    async execute() {
      if (!existsSync(DEMO_DIR)) return { ok: false, error: 'demo 目录不存在', demos: [] }
      const demos = readdirSync(DEMO_DIR, { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .map((e) => demoInfo(e.name))
        .filter(Boolean)
      return { ok: true, plugin_version: PKG_VERSION, skill_dir: SKILL_DIR,
               skills_synced: sync, demos }
    },
  }))

  // ---- 2) 直接出图 -----------------------------------------------------
  ctx.tools.register(defineTool({
    name: 'fdtd_demo_figure',
    description:
      '用演示案例自带的 CSV 出一张图（零引擎、零许可，约 1 秒）。'
      + ' kind ∈ stack/spectra/phase/field/fom/compare。',
    parameters: {
      type: 'object',
      properties: {
        id: { type: 'string', description: '演示案例 ID，例如 P01_Absorber' },
        kind: { type: 'string', enum: ['stack', 'spectra', 'phase', 'field', 'fom', 'compare'],
                description: '图类型，默认 spectra' },
        out: { type: 'string', description: '输出 png 路径；缺省写到 <demo>/out/<kind>.png' },
      },
      required: ['id'],
    },
    async execute(args) {
      const info = demoInfo(args.id)
      if (!info) return { ok: false, error: `没有这个演示案例：${args.id}` }
      const py = findPython()
      if (!py) return { ok: false, error: '找不到 python（设置 DSH_FDTD_PYTHON 环境变量）' }
      const kind = args.kind || 'spectra'
      const script = join(PKG_ROOT, 'skills', 'fdtd-lumerical-figure', 'scripts', 'make_figure.py')
      const input = kind === 'stack' ? info.spec : info.csv
      if (!input) return { ok: false, error: `${args.id} 缺少 ${kind === 'stack' ? 'spec' : 'csv'}` }
      const out = args.out || join(info.dir, 'out', `${kind}.png`)
      const r = spawnSync(py, [script, '--kind', kind, '--input', input, '--out', out, '--json'],
                          { encoding: 'utf8' })
      if (r.status !== 0) {
        return { ok: false, error: (r.stderr || r.stdout || '').slice(0, 800), out }
      }
      let meta = null
      try { meta = JSON.parse(r.stdout.trim().split('\n').pop()) } catch {}
      return { ok: true, out, kind, meta }
    },
  }))

  // ---- 3) 环境体检 -----------------------------------------------------
  ctx.tools.register(defineTool({
    name: 'fdtd_check_env',
    description:
      '检查出图/建模所需的环境：python、numpy、matplotlib、Lumerical API 路径。'
      + ' 出图不需要 Lumerical；建模才需要。',
    parameters: {},
    async execute() {
      const py = findPython()
      const probe = (mod) => {
        if (!py) return false
        const r = spawnSync(py, ['-c', `import ${mod}; print(${mod}.__version__)`], { encoding: 'utf8' })
        return r.status === 0 ? (r.stdout || '').trim() : false
      }
      const api = process.env.LUMERICAL_API_PATH || null
      return {
        ok: true,
        python: py,
        numpy: probe('numpy'),
        matplotlib: probe('matplotlib'),
        lumerical_api_path: api,
        lumerical_available: api ? existsSync(api) : false,
        note: '出图只需 python + numpy + matplotlib；Lumerical 仅建 .fsp / 跑仿真时需要。',
      }
    },
  }))

  // ---- 4) 案例详情 -----------------------------------------------------
  ctx.tools.register(defineTool({
    name: 'fdtd_demo_info',
    description: '返回某个演示案例的完整信息（工程路径、CSV、spec、日志、README 路径）。',
    parameters: {
      type: 'object',
      properties: { id: { type: 'string', description: '演示案例 ID' } },
      required: ['id'],
    },
    async execute(args) {
      const info = demoInfo(args.id)
      if (!info) return { ok: false, error: `没有这个演示案例：${args.id}` }
      return { ok: true, ...info, readme: join(info.dir, 'README.md') }
    },
  }))
}
"""


# ------------------------------------------------------------------------- demo README

DEMO_README = """# P01_Absorber — 超材料完美吸收器（Liu et al. 2010）

## 这是什么

一个**已求解**的 Lumerical FDTD 工程，复现论文 *"Infrared Perfect Absorber"* 的
Figure 2(a)：金属-介质-金属（MIM）十字谐振器的吸收谱。

| 项 | 值 |
|---|---|
| 工程文件 | `P01_complete.fsp`（**已求解**，`layoutmode=0`） |
| 谱数据 | `P01_RTA.csv`（91 点，4.0–8.5 µm） |
| 参数 | `P01_spec.json`（可改参数重建） |
| 收敛证据 | `P01_p0.log`（含 `Completed` 与末值 Auto Shutoff） |
| 吸收峰 | **A = {peak_a} @ {peak_lam} µm** |
| 论文值 | A = 0.97 @ 6.0 µm（CST 仿真 + 实验） |

> **为什么和论文差 0.16**：论文用 CST Microwave Studio 2009，本工程用 Lumerical FDTD v251。
> 这是求解器口径差异，不是建模错误。详见仓库 `defects/D-001`。
> **我们没有为了让数字好看而调参**——这是本项目的红线。

## 三种看法

### 1. 有 Lumerical：直接打开工程

```
Lumerical FDTD → File → Open → P01_complete.fsp
```

打开后**不用跑**，`R` / `T` 监视器里已经有结果：右键 → Visualize，或在
Analysis 里 `getresult("R","T")`。

想重跑就按 Run（单次约 30 秒）。

### 2. 没 Lumerical：用 CSV 出图

```bash
python skills/fdtd-lumerical-figure/scripts/make_figure.py \\
    --kind spectra --input demo/P01_Absorber/P01_RTA.csv \\
    --out out/P01_spectra.png
```

**0.78 秒**出图，不需要任何许可。

### 3. 只想看数字

打开 `P01_RTA.csv`，或读本文件上面的表。

## 这个工程算了什么

| 项 | 设置 |
|---|---|
| 结构 | Si 基底 / Au 地平面 / Al₂O₃ 间隔层 / 十字谐振器 |
| 边界 | x/y Periodic，z PML |
| 网格 | mesh accuracy 4 + 金属区局部加密 |
| 源 | 平面波，正入射，4.0–8.5 µm |
| 监视器 | `R`（反射）、`T`（透射）、`E_spacer`（场）、`nidx_spacer`（折射率） |
| 收敛 | Auto Shutoff 末值见 `P01_p0.log` |

## 想改参数

编辑 `P01_spec.json`，然后：

```bash
# 只看建模计划，不开会话（0 秒）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \\
    --spec demo/P01_Absorber/P01_spec.json --out out/ --dry-run

# 真建工程（需要 Lumerical）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \\
    --spec demo/P01_Absorber/P01_spec.json --out out/
```

## 出处

- 论文：Liu, X. et al. *Infrared Perfect Absorber*. (2010)
- 本工程：`cases/metasurface/P01_Absorber_042/`
- 复现报告：同目录 `results/repro_2026-11-09_fsp/repro_report_2026-11-09.md`
"""


# ------------------------------------------------------------------------ README.md

README_EN = """# dsh-plugin-fdtd

FDTD skill pack + a fully solved P01 metasurface absorber project, for
[DeepSeek Harness](https://github.com/deepseek-ai).

## What you get

| Item | Content |
|---|---|
| **15 skills** | paper→spec→`.fsp`→spectra→figure pipeline, plus field map, phase retrieval, oblique incidence, GS hologram, array assembly |
| **P01 project** | A **solved** Lumerical FDTD project (`layoutmode=0`, 91-point spectrum 4.0–8.5 µm), open it and the spectrum is already there |
| **Figure engine** | `make_figure.py` turns CSV/NPZ into 6 kinds of figures in **0.78 s**, no engine, no license |

## Install

```bash
dsh plugin --profile web add github:NileuyGneHz/dsh-plugin-fdtd
# restart DSH web
```

## Try it

Ask the agent:

```
"List the FDTD demos"
"Make the P01 spectrum figure"
```

Or run directly:

```bash
python skills/fdtd-lumerical-figure/scripts/make_figure.py \\
    --kind spectra --input demo/P01_Absorber/P01_RTA.csv --out out/p01.png
```

## What needs Lumerical

| Task | Needs Lumerical? |
|---|---|
| Figure from CSV/NPZ | ❌ No |
| Read a solved `.fsp` | ✅ Yes (or just use the CSV) |
| Build a new `.fsp` | ✅ Yes |
| Run a simulation | ✅ Yes + license |

Set `LUMERICAL_API_PATH` if your install is not at the default location.

## License

MIT
"""

README_ZH = """# dsh-plugin-fdtd

FDTD 技能包 + 一份**已求解**的 P01 超材料吸收器工程，供
[DeepSeek Harness](https://github.com/deepseek-ai) 使用。

## 装完你有什么

| 项 | 内容 |
|---|---|
| **15 个技能** | 论文→spec→`.fsp`→谱→出图 全链路，另有场图、相位提取、斜入射、全息相位、阵列装配 |
| **P01 完整工程** | 一份**已求解**的 Lumerical 工程（`layoutmode=0`，91 点谱，4.0–8.5 µm），打开就有结果 |
| **出图引擎** | `make_figure.py` 把 CSV/NPZ 变成 6 类图，**0.78 秒**，零引擎、零许可 |

## 安装

```bash
dsh plugin --profile web add github:NileuyGneHz/dsh-plugin-fdtd
# 然后重启 DSH web
```

## 三步体验

### 1. 问 agent

```
"列出 FDTD 演示案例"
"用 P01 出 R/T/A 谱图"
```

### 2. 或者直接跑

```bash
# 出谱图（0.78 秒，不需要 Lumerical）
python skills/fdtd-lumerical-figure/scripts/make_figure.py \\
    --kind spectra --input demo/P01_Absorber/P01_RTA.csv --out out/p01.png
```

### 3. 有 Lumerical 的话

打开 `demo/P01_Absorber/P01_complete.fsp`——**不用跑**，`R`/`T` 监视器里已经有结果。
想重跑就按 Run（约 30 秒）。

## 什么需要 Lumerical

| 任务 | 需要 Lumerical 吗 |
|---|---|
| CSV/NPZ → 图 | ❌ 不需要 |
| 读已求解的 `.fsp` | ✅ 需要（或者直接用 CSV） |
| 新建 `.fsp` | ✅ 需要 |
| 跑仿真 | ✅ 需要 + 许可 |

如果你的 Lumerical 不在默认路径，设置环境变量：

```bash
set LUMERICAL_API_PATH=D:\\Your\\Path\\Lumerical\\api\\python
```

## 技能清单

| 技能 | 用途 |
|---|---|
| `fdtd-paper-parameter-extraction` | 论文 PDF → spec |
| `fdtd-lumerical-fsp-build` | spec → `.fsp`（只建不跑） |
| `fdtd-lumerical-unitcell-simulation` | 跑 R/T/A 谱 |
| `fdtd-lumerical-figure` | 数据 → 6 类图 |
| `fdtd-lumerical-field-map` | 场 → 焦距/焦斑/相位面/OAM |
| `fdtd-lumerical-field-propagate` | 角谱传播（4f 层间） |
| `fdtd-lumerical-fsp-introspection` | 反解析已有 `.fsp` |
| `fdtd-lumerical-phase-retrieval` | 双偏振 Δφ |
| `fdtd-lumerical-oblique-incidence` | 斜入射扫描 |
| `fdtd-holo-phase-retrieval` | 目标图 → 相位版图 |
| `fdtd-metasurface-assembly` | 相位 CSV → 阵列 spec |
| `fdtd-lumerical-session-control` | 白名单调参 |
| `fdtd-lumerical-design-loop` | 设计闭环决策 |
| `fdtd-lumerical-headless` | `.lsf` 执行底座 |
| `fdtd-package-workspace` | 一题一包归档 |

## 已知边界

- 出图零引擎；建模/跑仿真需要 Lumerical v251 或更高
- `.fsp` 是 v251 格式，旧版本可能打不开
- 不支持波导/MZI 的 S 参数提取（技能库里没有）
- GPU 对含 Drude 金属的工程会发散，结论以 CPU 为准

## 许可

MIT
"""


# --------------------------------------------------------------------------- 主流程


def build(out: Path, dry_run: bool) -> int:
    if out.exists():
        print(f"[清理] 已存在，先删除：{out}")
        if not dry_run:
            shutil.rmtree(out)

    print(f"[打包] -> {out}")
    plan = []

    # 1) 技能：只打 fdtd-*（lit-* / core-* 是文献轨，与插件主题无关）
    skills = [d for d in SKILLS_SRC.iterdir()
              if d.is_dir() and d.name.startswith("fdtd-")]
    print(f"  技能 {len(skills)} 个（fdtd-*）")
    plan.append(("skills", len(skills)))

    # 2) demo 素材
    fsp = P01_RESULTS / "P01_Absorber_042_repro.fsp"
    csv = P01_RESULTS / "RTA_spectrum.csv"
    spec = P01 / "config" / "spec_p01.json"
    log = P01_RESULTS / "P01_Absorber_042_repro_p0.log"
    for p, label in ((fsp, "fsp"), (csv, "csv"), (spec, "spec"), (log, "log")):
        if not p.is_file():
            print(f"[ERROR] 缺 {label}: {p}", file=sys.stderr)
            return 1
    print(f"  P01: fsp {fsp.stat().st_size/1024/1024:.2f} MB, "
          f"csv {csv.stat().st_size/1024:.0f} KB, "
          f"spec {spec.stat().st_size/1024:.0f} KB")

    if dry_run:
        print("\n[dry-run] 不写任何文件。计划：")
        for k, v in plan:
            print(f"  {k}: {v}")
        return 0

    # --- 复制 ---
    out.mkdir(parents=True, exist_ok=True)
    n_sk = 0
    for sk in skills:
        n_sk += copy_tree(sk, out / "skills" / sk.name)
    print(f"  复制技能文件 {n_sk} 个")

    lib_dst = out / "library" / "py"
    lib_dst.mkdir(parents=True, exist_ok=True)
    n_lib = 0
    for m in LIB_SRC.glob("*.py"):
        shutil.copy2(m, lib_dst / m.name)
        n_lib += 1
    print(f"  复制 library/py {n_lib} 个模块")

    if DOCS_SRC.is_file():
        (out / "docs").mkdir(exist_ok=True)
        shutil.copy2(DOCS_SRC, out / "docs" / DOCS_SRC.name)
        print("  复制 field-manual.md")

    # demo
    demo = out / "demo" / "P01_Absorber"
    demo.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fsp, demo / "P01_complete.fsp")
    shutil.copy2(csv, demo / "P01_RTA.csv")
    shutil.copy2(spec, demo / "P01_spec.json")
    shutil.copy2(log, demo / "P01_p0.log")

    # 从 CSV 读峰值，写进 demo README（数字来自数据，不写死）
    peak_a, peak_lam = None, None
    try:
        import csv as _csv
        with csv.open(encoding="utf-8") as fh:
            rows = list(_csv.DictReader(fh))
        if rows:
            key_a = next((k for k in rows[0] if k.strip().upper() == "A"), None)
            key_lam = next((k for k in rows[0] if "lam" in k.lower() or "wavelength" in k.lower()), None)
            if key_a and key_lam:
                best = max(rows, key=lambda r: float(r[key_a]))
                peak_a = float(best[key_a])
                peak_lam = float(best[key_lam])
                if peak_lam > 100:      # nm -> um
                    peak_lam /= 1000.0
    except Exception as e:
        print(f"  [WARN] 读 CSV 峰值失败：{e}")

    (demo / "README.md").write_text(
        DEMO_README.format(peak_a=f"{peak_a:.4f}" if peak_a else "见 CSV",
                           peak_lam=f"{peak_lam:.3f}" if peak_lam else "见 CSV"),
        encoding="utf-8")
    print(f"  P01 README（峰值 A={peak_a} @ {peak_lam} um）")

    # --- 生成文件 ---
    (out / "package.json").write_text(
        json.dumps(make_package_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "cordis.patch.yml").write_text(CORDIS_PATCH, encoding="utf-8")
    (out / "lib").mkdir(exist_ok=True)
    (out / "lib" / "index.js").write_text(INDEX_JS, encoding="utf-8")
    (out / "README.md").write_text(README_EN, encoding="utf-8")
    (out / "README-zh.md").write_text(README_ZH, encoding="utf-8")

    # --- MANIFEST ---
    files = {}
    for p in sorted(out.rglob("*")):
        if p.is_file():
            files[str(p.relative_to(out)).replace("\\", "/")] = {
                "bytes": p.stat().st_size, "sha256": sha256(p)}
    (out / "MANIFEST.json").write_text(
        json.dumps({"plugin": PLUGIN_NAME, "version": VERSION,
                    "built_from": str(ROOT), "files": files},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = sum(f["bytes"] for f in files.values())
    print(f"\n[完成] {len(files)} 个文件，{total/1024/1024:.2f} MB")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="把 FDTD 技能与 P01 工程打成 DSH 插件")
    ap.add_argument("--out", required=True, help="插件输出目录")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    if "dsh-plugin" not in out.name:
        print(f"[ERROR] 输出目录名应含 'dsh-plugin'：{out.name}", file=sys.stderr)
        return 2
    return build(out, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
