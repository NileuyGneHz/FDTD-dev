#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gpu_guard.py — 按工程资格自动切 GPU / CPU，跑完必还原。

为什么要这个工具
----------------
`FDTD\\GPU-mode` 是**全局**开关（ini 里一行），不是单工程属性。所以「这个工程用 GPU、
那个用 CPU」只能靠「跑前切、跑后还原」实现。手工切两次很容易忘第二次，
而忘了还原的后果是：下一次 CPU 双精度对照悄悄走了 GPU real32，结论不可比。

判据来源
--------
完全复用 `tools/probe_gpu_eligibility.py::classify`，**不另写一套**（避免第二份真相）：

| 判据 | 结论 |
|---|---|
| 路径含非 ASCII | `cpu_only`（GPU 引擎 1113） |
| 含 TFSFSource | `cpu_only`（D-011：GPU 明确不支持） |
| dimension=2D | `cpu_only`（D-008：2D 链路未通） |
| 含 Drude / Conductive / 强损耗金属 | `gpu_risky`（real32 易发散，需 dt<=0.95 + CPU A/B） |
| 显存估算 > 85% VRAM | `cpu_only` |
| 其余 | `gpu` |

`gpu_risky` 默认**不自动上 GPU**（除非显式 `--allow-risky`）——P03 的实测代价是
51523 次迭代后 `ERROR: Early termination, fields are diverging`，产物全废。

### 实测校准：`gpu_risky` 不等于「一定发散」

2026-11-11 对照两个都含金属、都上过 GPU 的工程：

| 工程 | 金属模型 | GPU 日志 | 结果 |
|---|---|---|---|
| P04 `fig4` | Au **(n,k) 采样** | 无 `0 < permittivity < 1` | ✅ 跑完 12165 iter / 340 s / Shutoff 8.4e-6 |
| P03 `fig1_hwp_paper_materials` | **Drude 解析** | **有** `0 < permittivity < 1` | ❌ 51523 iter 后 diverging |

**真正的发散前兆不是「含金属」，而是日志里出现 `0 < permittivity < 1`**
（Drude 的实部 ε 落在 (0,1) 时 real32 会放大误差）。采样 (n,k) 金属不会触发。

所以本工具在 `--allow-risky` 之外再给一条 `--probe-log`：若该工程已有 `_p0.log` 且
**没有** `0 < permittivity < 1`，则视为「历史实测安全」，允许上 GPU。没有日志时仍保守。

用法
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

    # 只看会怎么判，不改 ini、不开会话
    "$PY" tools/gpu_guard.py --fsp cases/P04_.../model/fig4.fsp --dry-run

    # 包住一次运行：跑前按判据切换，跑完（含异常）自动还原
    "$PY" tools/gpu_guard.py --fsp <工程> --run "python skills/.../run_fdtd_sweep.py --config ..."

    # 允许 gpu_risky 上 GPU（需自己保证 dt<=0.95 且有 CPU 对照）
    "$PY" tools/gpu_guard.py --fsp <工程> --run "..." --allow-risky

    # 用已有 _p0.log 证明「历史实测不发散」后放行
    "$PY" tools/gpu_guard.py --fsp <工程> --run "..." --probe-log

    # 批量判定（不开会话，用已有 _p0.log 估网格）
    "$PY" tools/gpu_guard.py --fsp cases/P0*/*.fsp --dry-run

退出码：0 正常 / 1 判定失败或运行失败 / 2 参数错误。
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TOOLS_DIR = Path(__file__).resolve().parent
WS_ROOT = TOOLS_DIR.parent
PROBE = TOOLS_DIR / "probe_gpu_eligibility.py"
GPU_MODE = TOOLS_DIR / "gpu_mode.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_fsp(fsp: Path) -> dict:
    """用 probe 的 classify 判一个 .fsp。

    读对象树必须开会话（`inspect_structure` 要的是已 load 的 FDTD 句柄），
    这里按 probe 主流程同样的方式：load → inspect_structure → classify → close。
    """
    import os

    probe = load_module(PROBE, "probe_gpu_eligibility")
    inspector = probe.load_inspector()

    api_path = os.environ.get("LUMERICAL_API_PATH", inspector.DEFAULT_API_PATH)
    os.environ.setdefault("ANSYSLMD_LICENSE_FILE",
                          os.environ.get("ANSYSLMD_LICENSE_FILE",
                                         inspector.DEFAULT_LICENSE))
    if api_path not in sys.path:
        sys.path.insert(0, api_path)
    import lumapi  # noqa: E402

    f = None
    try:
        with inspector.quiet_native_stdout(True):
            f = lumapi.FDTD(hide=True)
            f.load(str(fsp))
            info = inspector.inspect_structure(f, full=False, max_depth=3,
                                               max_objects=400)
        return probe.classify(fsp, info)
    finally:
        if f is not None:
            try:
                f.close()
            except Exception:
                pass


def log_says_safe(fsp: Path) -> tuple[bool, str]:
    """查同目录 <stem>_p0.log：有没有 `0 < permittivity < 1` 这个发散前兆。

    实测依据（2026-11-11）：P04 用 Au 采样 (n,k) 上 GPU 成功且日志无此警告；
    P03 用 Drude 上 GPU 发散且日志有。所以「含金属」不是判据，这条警告才是。
    """
    log = fsp.with_name(fsp.stem + "_p0.log")
    if not log.is_file():
        return False, "无 _p0.log，无法证明历史安全"
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"日志读不了（{e}）"
    if "0 < permittivity < 1" in text:
        return False, "日志有 `0 < permittivity < 1` → 实测会发散"
    if "diverging" in text:
        return False, "日志有 diverging → 实测发散过"
    if "Completed" not in text and "Auto Shutoff" not in text:
        return False, "日志不像跑完过（无 Completed / Auto Shutoff）"
    return True, "日志无发散前兆（无 `0 < permittivity < 1`）"


def decide(fsp: Path, allow_risky: bool, probe_log: bool = False) -> tuple[str, list[str]]:
    """返回 (want, reasons)；want ∈ {gpu, cpu}。"""
    try:
        res = classify_fsp(fsp)
    except Exception as e:  # 读不出来就保守走 CPU，绝不猜
        return "cpu", [f"无法反解析（{str(e)[:70]}）→ 保守走 CPU"]
    verdict = res.get("verdict", "cpu_only")
    reasons = list(res.get("reasons") or [])
    if verdict == "gpu":
        return "gpu", reasons or ["全部判据通过"]
    if verdict == "gpu_risky":
        if allow_risky:
            return "gpu", reasons + ["--allow-risky：已显式接受发散风险"]
        if probe_log:
            ok, why = log_says_safe(fsp)
            if ok:
                return "gpu", reasons + [f"--probe-log：{why}"]
            return "cpu", reasons + [f"--probe-log 未放行：{why}"]
        return "cpu", reasons + ["gpu_risky 未加 --allow-risky/--probe-log → 走 CPU"]
    return "cpu", reasons


def switch(want: str) -> int:
    gm = load_module(GPU_MODE, "gpu_mode")
    return gm.set_mode(gm.INI, want)


def run_guarded(fsp: Path, cmd: str, allow_risky: bool, probe_log: bool) -> int:
    want, reasons = decide(fsp, allow_risky, probe_log)
    print(f"[判定] {fsp}")
    print(f"       引擎 = {want.upper()}")
    for r in reasons:
        print(f"       - {r}")

    gm = load_module(GPU_MODE, "gpu_mode")
    original = gm.gpu_mode(gm.read_ini(gm.INI))  # "true" / "false"
    target = "gpu" if want == "gpu" else "cpu"

    if switch(target) != 0:
        print(f"[FAIL] 无法切到 {target}，不执行命令")
        return 1

    code = 1
    try:
        print(f"[运行] {cmd}")
        code = subprocess.run(cmd, shell=True, cwd=str(WS_ROOT)).returncode
        print(f"[运行] 退出码 {code}")
    finally:
        # 无论成功、失败还是 Ctrl-C，都还原到跑之前的状态
        back = "gpu" if original == "true" else "cpu"
        if switch(back) == 0:
            print(f"[还原] GPU-mode 已恢复到 {original}")
        else:
            print(f"[FAIL] 还原失败！请手工执行: tools/gpu_mode.py --set {back}",
                  file=sys.stderr)
    return code


def dry_run(fsps: list[Path], allow_risky: bool, probe_log: bool) -> int:
    bad = 0
    for fsp in fsps:
        want, reasons = decide(fsp, allow_risky, probe_log)
        rel = fsp.relative_to(WS_ROOT) if fsp.is_relative_to(WS_ROOT) else fsp
        print(f"{want.upper():<4} {rel}")
        for r in reasons:
            print(f"       - {r}")
        if want == "cpu" and reasons:
            bad += 1
    print(f"\n汇总：{len(fsps)} 个工程，{bad} 个不走 GPU")
    return 0


def expand(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in patterns:
        p = Path(raw)
        if not p.is_absolute():
            p = WS_ROOT / p
        if any(ch in raw for ch in "*?["):
            out.extend(sorted(p.parent.glob(p.name)))
        elif p.is_file():
            out.append(p)
        else:
            out.extend(sorted(p.rglob("*.fsp")) if p.is_dir() else [])
    return out


def self_test() -> int:
    """只验判定分发逻辑（不碰 ini、不开会话）。"""
    tmp = Path(tempfile.mkdtemp(prefix="gpuguard_"))
    try:
        fake = tmp / "fake.fsp"
        fake.write_text("", encoding="utf-8")

        # 打桩：绕过真反解析
        global classify_fsp
        orig = classify_fsp

        cases = [
            ({"verdict": "gpu", "reasons": []}, False, "gpu"),
            ({"verdict": "gpu_risky", "reasons": ["drude"]}, False, "cpu"),
            ({"verdict": "gpu_risky", "reasons": ["drude"]}, True, "gpu"),
            ({"verdict": "cpu_only", "reasons": ["2D"]}, True, "cpu"),
        ]
        for res, allow, want_expected in cases:
            classify_fsp = lambda f, _r=res: _r  # noqa: E731
            got, _ = decide(fake, allow)
            if got != want_expected:
                print(f"self-test: {res['verdict']} allow_risky={allow} "
                      f"应判 {want_expected}，实判 {got}", file=sys.stderr)
                return 1

        # 负例：反解析抛异常 → 必须降级到 cpu，不能猜 gpu
        def boom(_f):
            raise RuntimeError("cannot inspect")
        classify_fsp = boom
        got, reasons = decide(fake, True)
        if got != "cpu":
            print("self-test: 反解析失败时应降级 cpu", file=sys.stderr)
            return 1
        if not any("无法反解析" in r for r in reasons):
            print("self-test: 降级原因未记录", file=sys.stderr)
            return 1

        classify_fsp = orig
        print("self-test: 5 例（gpu / risky×2 / cpu_only / 异常降级）全部符合预期")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="按工程资格自动切 GPU/CPU，跑完还原")
    ap.add_argument("--fsp", nargs="+", help="一个或多个 .fsp（支持通配与目录）")
    ap.add_argument("--run", help="要包住的命令（跑前切、跑后还原）")
    ap.add_argument("--probe-log", action="store_true",
                    help="gpu_risky 时用已有 _p0.log 证明历史不发散，则放行 GPU")
    ap.add_argument("--allow-risky", action="store_true",
                    help="允许 gpu_risky 上 GPU（需自行保证 dt<=0.95 且配 CPU 对照）")
    ap.add_argument("--dry-run", action="store_true", help="只判定不改 ini")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.fsp:
        ap.error("需要 --fsp")
    fsps = expand(args.fsp)
    if not fsps:
        print("[FAIL] 没匹配到任何 .fsp")
        return 1

    if args.dry_run or not args.run:
        return dry_run(fsps, args.allow_risky, args.probe_log)
    if len(fsps) > 1:
        ap.error("--run 只接受单个 --fsp（多工程请逐个包）")
    return run_guarded(fsps[0], args.run, args.allow_risky, args.probe_log)


if __name__ == "__main__":
    sys.exit(main())
