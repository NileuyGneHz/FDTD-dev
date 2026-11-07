#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execution layer for one iteration of the L1 design loop.

Consumes a validated L1 spec (targets / locked / search_space) plus ONE parameter
set, injects it into an EXISTING .fsp through a whitelist, runs it using the
project-verified two-stage sequence, reads the raw monitor results back and
writes a per-iteration ledger. It does not build geometry and it does not decide
which parameters come next (that is fdtd-lumerical-design-loop).

Session lifecycle is NOT reimplemented here: setup_env / open_fdtd / ascii_gate /
verify_and_run are imported from
fdtd-package-workspace/scripts/lumapi_common.py (single implementation).

CLI contract: --config <json> --out <dir> [--dry-run] [--json]
Exit codes:   0 ok / 1 diagnosable failure / 2 argument or config error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Importing the shared module must not leave __pycache__ inside skills/ (K12).
sys.dont_write_bytecode = True

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2

ERROR_CATEGORIES = (
    ("bind socket", "transient", "ansyscl 端口 TIME_WAIT；瞬时态，重试即可"),
    ("diverging", "numerical", "场发散；dt stability factor 0.99 -> 0.95 或改 CPU 双精度"),
    ("1113", "path", "路径含非 ASCII；GPU 引擎会崩，改纯 ASCII 路径"),
    ("layoutmode", "sequence", "必须 save -> 新会话 load -> switchtolayout -> run"),
    ("Failed to checkout", "license", "许可不可用；先跑 z_fix_license_daemon.cmd"),
    ("Auto Shutoff", "convergence", "未收敛；提高 simulation_time"),
    ("analysis mode", "sequence", "改对象前必须 switchtolayout()"),
)


class ConfigError(Exception):
    """Bad but diagnosable configuration."""


class WhitelistError(ConfigError):
    """L1 red line: agent tried to leave the human-defined search space."""


def repo_root() -> Path:
    """Locate the workspace root from __file__; never assume cwd."""
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("找不到仓库根（.git）；脚本必须位于仓库内")


def in_repo(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (root / p)


def classify_error(message: str) -> dict:
    low = (message or "").lower()
    for needle, category, hint in ERROR_CATEGORIES:
        if needle.lower() in low:
            return {"category": category, "hint": hint, "retryable": category == "transient"}
    return {"category": "unknown", "hint": "查 references/session-contract.md 的错误分类表",
            "retryable": False}


def check_whitelist(cfg: dict) -> dict:
    """L1 gate: params <= search_space, never locked, Reproduce never tunes."""
    mode = cfg.get("mode", "Design")
    params = cfg.get("params") or {}
    space = cfg.get("search_space") or {}
    locked = cfg.get("locked") or {}
    pmap = cfg.get("parameter_map") or {}
    if mode not in ("Reproduce", "Design"):
        raise WhitelistError("mode 必须是 Reproduce / Design")
    if mode == "Reproduce" and params:
        raise WhitelistError("Reproduce 模式禁止注入参数（L1 §③：调参凑数=造假）")
    unknown = sorted(set(params) - set(space))
    if unknown:
        raise WhitelistError("参数不在 search_space 内: %s" % unknown)
    frozen = sorted(set(params) & set(locked))
    if frozen:
        raise WhitelistError("参数命中 locked（越界即停，先问人）: %s" % frozen)
    unmapped = sorted(set(params) - set(pmap))
    if unmapped and params:
        raise ConfigError("参数缺 parameter_map 映射: %s" % unmapped)
    for key, value in params.items():
        spec = space[key]
        lo, hi = float(spec["min"]), float(spec["max"])
        if not (lo <= float(value) <= hi):
            raise WhitelistError("%s=%s 超出 [%g, %g]" % (key, value, lo, hi))
    return {"mode": mode, "params": params, "param_key":
            hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]}


def jsonable(value, cap: int = 2000):
    """Convert lumapi datasets / numpy arrays into JSON-safe, bounded data."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v, cap) for k, v in value.items()}
    if hasattr(value, "tolist"):
        return jsonable(value.tolist(), cap)
    if isinstance(value, (list, tuple)):
        return [jsonable(v, cap) for v in list(value)[:cap]]
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    return str(value)


def read_monitors(fdtd, extract: dict, cap: int) -> dict:
    """Raw getresult -> JSON. Physical interpretation belongs to design-loop."""
    out = {}
    for name, spec in extract.items():
        monitor, result = spec.get("monitor", name), spec.get("result", "T")
        try:
            raw = fdtd.getresult(monitor, result)
            out[name] = jsonable(raw, cap)
        except Exception as e:
            out[name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    return out


def run_one(cfg: dict, root: Path, out: Path) -> dict:
    """One iteration. Imports lumapi ONLY here (never during --dry-run)."""
    shared = root / "skills" / "fdtd-package-workspace" / "scripts"
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))
    from lumapi_common import setup_env, open_fdtd, ascii_gate, verify_and_run

    setup_env(verbose=False)
    base = in_repo(root, cfg["base_fsp"])
    if not base.is_file():
        raise ConfigError("base_fsp 不存在: %s" % base)
    if not ascii_gate(base, verbose=False):
        raise ConfigError("base_fsp 路径含非 ASCII: %s" % base)
    out.mkdir(parents=True, exist_ok=True)

    idx = int(cfg.get("iteration", 1))
    iter_fsp = out / ("iteration_%03d.fsp" % idx)
    t0 = time.time()
    checks = {"params": cfg.get("params") or {}, "parameter_map": cfg.get("parameter_map") or {}}

    # Stage 1: load the EXISTING project, switch to layout, inject whitelisted
    # parameters only (no geometry rebuild), save, close.
    f = open_fdtd()
    try:
        f.load(str(base))
        f.switchtolayout()
        applied = []
        for param, value in checks["params"].items():
            for mapping in checks["parameter_map"].get(param, []):
                f.setnamed(mapping["object"], mapping["property"], float(value)
                            if isinstance(value, (int, float)) else value)
                applied.append({"object": mapping["object"],
                                "property": mapping["property"], "value": value})
        f.save(str(iter_fsp))
        checks["applied"] = applied
    finally:
        f.close()

    # Stage 2: project-verified sequence -- a NEW session loads the saved .fsp
    # before run(); running in the modelling session fails silently.
    f2 = verify_and_run(str(iter_fsp), verbose=False)
    try:
        results = read_monitors(f2, cfg.get("extract") or {},
                               int(cfg.get("max_array_items", 2000)))
    finally:
        f2.close()

    log = iter_fsp.with_name(iter_fsp.stem + "_p0.log")
    ledger = {
        "ok": True, "iteration": idx, "mode": cfg.get("mode", "Design"),
        "params": checks["params"], "applied": checks["applied"],
        "param_key": check_whitelist(cfg)["param_key"],
        "base_fsp": str(base.relative_to(root)) if base.is_relative_to(root) else str(base),
        "base_fsp_size": base.stat().st_size,
        "iter_fsp": str(iter_fsp), "p0_log": str(log) if log.exists() else None,
        "assert_ran": "passed (layoutmode / _p0.log / Completed / no diverging)",
        "results": results,
        "elapsed_s": round(time.time() - t0, 3),
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / ("iteration_%03d.json" % idx)).write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
    return ledger


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One L1 design-loop FDTD iteration")
    ap.add_argument("--config", required=True, help="iteration config JSON")
    ap.add_argument("--out", required=True, help="output directory (all artefacts land here)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan, write nothing, import no lumapi, open no session")
    ap.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        msg = "config not found: %s" % cfg_path
        print(json.dumps({"ok": False, "error": msg}) if args.json else "ERROR " + msg)
        return EXIT_USAGE
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        msg = "bad JSON: %s" % e
        print(json.dumps({"ok": False, "error": msg}) if args.json else "ERROR " + msg)
        return EXIT_USAGE
    try:
        gate = check_whitelist(cfg)
        if not cfg.get("base_fsp"):
            raise ConfigError("缺 base_fsp（本技能不建模，只改既有工程）")
    except ConfigError as e:
        print(json.dumps({"ok": False, "error": str(e)}) if args.json else "ERROR " + str(e))
        return EXIT_FAIL if isinstance(e, WhitelistError) else EXIT_FAIL

    if args.dry_run:
        root = repo_root()
        plan = {"ok": True, "dry_run": True, "mode": gate["mode"],
                "params": gate["params"], "param_key": gate["param_key"],
                "base_fsp": cfg["base_fsp"],
                "base_fsp_resolved": str(in_repo(root, cfg["base_fsp"])),
                "injected_properties": sum(len(v) for v in (cfg.get("parameter_map") or {}).values()),
                "sequence": ["open_fdtd -> load -> switchtolayout",
                             "whitelisted setnamed",
                             "save -> close",
                             "verify_and_run (new session load -> run -> assert_ran)",
                             "getresult -> ledger -> close"],
                "extract": list((cfg.get("extract") or {}).keys()),
                "out": str(Path(args.out)), "session_opened": False}
        print(json.dumps(plan, ensure_ascii=False) if args.json
              else "\n".join("%-20s %s" % (k, v) for k, v in plan.items()))
        return EXIT_OK

    root = repo_root()
    out = Path(args.out)
    retries = int(cfg.get("max_retries", 3))
    last = None
    for attempt in range(retries + 1):
        try:
            ledger = run_one(cfg, root, out)
            ledger["retry_count"] = attempt
            summary = {"ok": True, "iteration": ledger["iteration"],
                       "param_key": ledger["param_key"], "p0_log": ledger["p0_log"],
                       "elapsed_s": ledger["elapsed_s"], "retry_count": attempt,
                       "out": str(out)}
            print(json.dumps(summary, ensure_ascii=False) if args.json
                  else "\n".join("%-20s %s" % (k, v) for k, v in summary.items()))
            return EXIT_OK
        except Exception as e:
            info = classify_error(str(e))
            last = {"ok": False, "error": "%s: %s" % (type(e).__name__, e),
                    "classification": info, "attempt": attempt,
                    "traceback": traceback.format_exc(limit=6)}
            if not info["retryable"] or attempt >= retries:
                break
            time.sleep(2.0 * (attempt + 1))
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "iteration_error.json").write_text(
            json.dumps(last, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    print(json.dumps(last, ensure_ascii=False) if args.json
          else "ERROR " + json.dumps(last, ensure_ascii=False))
    return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
