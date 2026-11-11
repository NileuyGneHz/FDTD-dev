#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gpu_mode.py — 安全切换 Lumerical FDTD 的 GPU / CPU 引擎（改 ini，不碰 setresource）。

为什么不用 setresource
----------------------
`setresource('FDTD', n, ...)` 改的是**全局**资源配置文件，不是本会话；改了不还原会让 GUI
报 "There are no active GPU resources"（见 `docs/constitution/field-manual.md` §6.3）。
本脚本直接读写 ini 的 `FDTD\\GPU-mode` 一行，改完读回确认，并保留备份。

改的是什么
----------
```
%APPDATA%\\Lumerical\\FDTD Solutions.ini
  [jobmanager]
  FDTD\\GPU-mode=true|false        # true = 作业走 GPU 引擎；false = 走 SelectedCPUEngine
  FDTD\\SelectedCPUEngine=0        # GPU-mode=false 时用哪个 CPU 引擎（0 = 第一个）
```

前置条件（脚本会检查，不满足就拒绝）
------------------------------------
1. ini 里存在一个 `DeviceType=GPU` 且 `active=true` 的引擎条目；
2. 该条目 `exePath` 指向真实存在的 `fdtd-engine.exe`；
3. 没有正在运行的 `fdtd-solutions.exe`（改 ini 前必须先退出 GUI，否则会被覆盖）。

用法
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/gpu_mode.py --status           # 只看现状，不改
    "$PY" tools/gpu_mode.py --set gpu          # 切到 GPU
    "$PY" tools/gpu_mode.py --set cpu          # 切回 CPU
    "$PY" tools/gpu_mode.py --self-test        # 用临时 ini 验证解析与改写

退出码：0 成功 / 1 前置条件不满足 / 2 参数错误。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

INI = Path(os.environ["APPDATA"]) / "Lumerical" / "FDTD Solutions.ini"
GPU_LINE_RE = re.compile(r"^(FDTD\\GPU-mode=)(true|false)\s*$", re.M | re.I)
CPU_LINE_RE = re.compile(r"^(FDTD\\SelectedCPUEngine=)(\d+)\s*$", re.M)
ENGINE_RE = re.compile(r"<engine>(.*?)</engine>", re.S)


def read_ini(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def engines(text: str) -> list[dict]:
    """解析 FDTD_v2= 里的每个 <engine>。"""
    m = re.search(r"FDTD_v2=(.*?)(?:\r?\n[A-Za-z]|$)", text, re.S)
    blob = m.group(1) if m else text
    out = []
    for e in ENGINE_RE.finditer(blob):
        body = e.group(1)

        def tag(name: str) -> str:
            mm = re.search(rf"<{name}>(.*?)</{name}>", body, re.S)
            return mm.group(1) if mm else ""

        out.append({
            "name": tag("name"),
            "device": tag("DeviceType"),
            "nProc": tag("nProc"),
            "nThread": tag("nThread"),
            "active": tag("active"),
            "exePath": tag("exePath").replace("\\\\", "\\"),
            "solver": tag("solverName"),
        })
    return out


def gpu_mode(text: str) -> str | None:
    m = GPU_LINE_RE.search(text)
    return m.group(2).lower() if m else None


def status(path: Path) -> int:
    if not path.is_file():
        print(f"[FAIL] ini 不存在：{path}")
        return 1
    text = read_ini(path)
    mode = gpu_mode(text)
    engs = engines(text)
    fdtd = [e for e in engs if e["solver"] == "FDTD" or not e["solver"]]

    print(f"ini : {path}")
    print(f"FDTD\\GPU-mode = {mode}")
    print("\n引擎条目：")
    for i, e in enumerate(fdtd, 1):
        exe_ok = "OK" if Path(e["exePath"]).is_file() else "缺失"
        print(f"  [{i}] {e['device']:<4} nProc={e['nProc']} nThread={e['nThread']} "
              f"active={e['active']} exe={exe_ok}")
        print(f"      {e['exePath']}")

    has_gpu = any(e["device"] == "GPU" and e["active"].lower() == "true"
                  and Path(e["exePath"]).is_file() for e in fdtd)
    print(f"\nGPU 可用（有 active 且 exe 存在的 GPU 引擎）: {has_gpu}")
    return 0


def procs_running() -> list[str]:
    """不引入 psutil：用 tasklist 查 GUI 进程。"""
    import subprocess
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq fdtd-solutions.exe"],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    return ["fdtd-solutions.exe"] if "fdtd-solutions" in out.lower() else []


def set_mode(path: Path, want: str) -> int:
    if not path.is_file():
        print(f"[FAIL] ini 不存在：{path}")
        return 1
    text = read_ini(path)
    engs = engines(text)
    fdtd = [e for e in engs if e["solver"] == "FDTD" or not e["solver"]]

    if want == "gpu":
        ok = [e for e in fdtd if e["device"] == "GPU"
              and e["active"].lower() == "true" and Path(e["exePath"]).is_file()]
        if not ok:
            print("[FAIL] 没有可用的 GPU 引擎（需 DeviceType=GPU + active=true + exe 存在）")
            return 1
        running = procs_running()
        if running:
            print(f"[FAIL] {running} 正在运行——改 ini 会被覆盖，先退出 GUI")
            return 1

    cur = gpu_mode(text)
    if cur is None:
        print("[FAIL] ini 里找不到 FDTD\\GPU-mode 行")
        return 1
    target = "true" if want == "gpu" else "false"
    if cur == target:
        print(f"[skip] 已是 GPU-mode={target}，无需改动")
        return 0

    bak = path.with_suffix(path.suffix + ".bak-gpumode")
    shutil.copy2(path, bak)
    new = GPU_LINE_RE.sub(lambda m: m.group(1) + target, text, count=1)
    path.write_text(new, encoding="utf-8")

    # 读回确认
    back = gpu_mode(read_ini(path))
    if back != target:
        print(f"[FAIL] 写回后读到的仍是 {back}，已从备份恢复")
        shutil.copy2(bak, path)
        return 1
    print(f"[OK] FDTD\\GPU-mode: {cur} -> {back}")
    print(f"[备份] {bak}")
    if want == "gpu":
        print("\n注意：GPU 是 real32 单精度。含 Drude/采样金属的工程会发散（D-011 同类），")
        print("      需 dt stability factor <= 0.95 并配 CPU 双精度对照。")
        print("      跑完想切回：tools/gpu_mode.py --set cpu")
    return 0


def self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gpumode_"))
    try:
        ini = tmp / "FDTD Solutions.ini"
        ini.write_text(
            "[jobmanager]\n"
            "FDTD\\GPU-mode=false\n"
            "FDTD\\SelectedCPUEngine=0\n"
            "FDTD_v2=<engines>"
            "<engine><name>Local Host</name><nProc>8</nProc><nThread>1</nThread>"
            "<active>true</active><solverName>FDTD</solverName>"
            "<exePath>" + str(tmp / "cpu.exe").replace("\\", "\\\\") + "</exePath>"
            "<DeviceType>CPU</DeviceType></engine>"
            "<engine><name>Local Host</name><nProc>1</nProc><nThread>8</nThread>"
            "<active>true</active><solverName>FDTD</solverName>"
            "<exePath>" + str(tmp / "gpu.exe").replace("\\", "\\\\") + "</exePath>"
            "<DeviceType>GPU</DeviceType></engine>"
            "</engines>\n",
            encoding="utf-8")
        (tmp / "cpu.exe").write_text("", encoding="utf-8")
        (tmp / "gpu.exe").write_text("", encoding="utf-8")

        t = read_ini(ini)
        if gpu_mode(t) != "false":
            print("self-test: 初始 GPU-mode 解析错误", file=sys.stderr)
            return 1
        engs = engines(t)
        if len(engs) != 2:
            print(f"self-test: 引擎数应为 2，实为 {len(engs)}", file=sys.stderr)
            return 1
        if [e["device"] for e in engs] != ["CPU", "GPU"]:
            print("self-test: DeviceType 解析错误", file=sys.stderr)
            return 1
        if engs[1]["exePath"] != str(tmp / "gpu.exe"):
            print(f"self-test: exePath 反转义错误 {engs[1]['exePath']}", file=sys.stderr)
            return 1

        if set_mode(ini, "gpu") != 0:
            print("self-test: 切 GPU 失败", file=sys.stderr)
            return 1
        if gpu_mode(read_ini(ini)) != "true":
            print("self-test: 切 GPU 后读回不是 true", file=sys.stderr)
            return 1
        if set_mode(ini, "cpu") != 0:
            print("self-test: 切 CPU 失败", file=sys.stderr)
            return 1
        if gpu_mode(read_ini(ini)) != "false":
            print("self-test: 切 CPU 后读回不是 false", file=sys.stderr)
            return 1

        # 负例：删掉 GPU 引擎后应拒绝切 GPU
        ini.write_text(t, encoding="utf-8")
        (tmp / "gpu.exe").unlink()
        if set_mode(ini, "gpu") == 0:
            print("self-test: GPU exe 缺失时不该允许切 GPU", file=sys.stderr)
            return 1

        print("self-test: 2 正例（切 GPU / 切 CPU）+ 3 负例全部符合预期")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="安全切换 Lumerical FDTD 的 GPU / CPU 引擎")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--status", action="store_true", help="只看现状")
    g.add_argument("--set", choices=["gpu", "cpu"], help="切到 gpu 或 cpu")
    g.add_argument("--self-test", action="store_true")
    g.add_argument("--ini", help="显式指定 ini（测试用）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    path = Path(args.ini) if args.ini else INI
    if args.status:
        return status(path)
    return set_mode(path, args.set)


if __name__ == "__main__":
    sys.exit(main())
