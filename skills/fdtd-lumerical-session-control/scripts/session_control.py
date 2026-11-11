#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execution layer for one iteration of the L1 design loop.

Consumes a validated L1 spec (targets / locked / search_space) plus ONE parameter
set, injects it into an EXISTING .fsp through a whitelist, runs it using the
project-verified two-stage sequence, reads the raw monitor results back and
writes a per-iteration ledger. It does not build geometry and it does not decide
which parameters come next (that is fdtd-lumerical-design-loop).

Session lifecycle is NOT reimplemented here: setup_env / open_fdtd / ascii_gate /
verify_and_run are imported from `library/py/lumapi_common.py` (the single implementation;
`skills/fdtd-package-workspace/scripts/lumapi_common.py` is now only a forwarder).
2026-11-11: moved from `_shared/` per workspace-layout.md §10.

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
    ("layoutmode", "sequence", "必须先 save 再 run（同会话亦可）；未 save 时 run 静默失效"),
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


def assert_writable_out(root: Path, out: Path) -> Path:
    """Two gates in one place, both learned the hard way.

    ① `--out` must be turned ABSOLUTE before ``f.save()``.  The engine's cwd is not the
       repo root, so a relative path makes ``save()`` fail with a *permission* message —
       which sends people hunting for non-ASCII paths (P05 event).  The real cause is cwd.
    ② `cases/` is the reference corpus and must never be written by a run
       (same gate as ``run_lsf.py``'s ``config.fsp inside cases/ -> exit 2``).
    """
    resolved = out if out.is_absolute() else (root / out)
    resolved = resolved.resolve()
    cases = (root / "cases").resolve()
    if resolved == cases or cases in resolved.parents:
        raise ConfigError(
            "--out 落在只读参考语料 cases/ 内：%s。产物请写到 _scratch/ 或其它工作目录" % resolved)
    return resolved


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


def read_monitors(fdtd, extract: dict, cap: int, npz_dir: Path | None = None) -> dict:
    """Raw getresult -> JSON (bounded) or .npz (full arrays).

    A 301x301 field map is 90601 points per component; ``max_array_items=2000``
    truncates it into a number that looks like data.  ``format: npz`` writes the
    untruncated array next to the ledger and leaves only metadata in JSON.
    """
    out = {}
    for name, spec in extract.items():
        monitor, result = spec.get("monitor", name), spec.get("result", "T")
        fmt = str(spec.get("format", "json")).lower()
        try:
            if fmt == "npz":
                if npz_dir is None:
                    raise ConfigError("format=npz 但未给 npz 目录")
                import numpy as np

                raw = fdtd.getresult(monitor, result)
                arrs = {}
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        try:
                            a = np.asarray(v)
                        except Exception:      # noqa: BLE001 - non-array keys are metadata
                            continue
                        # 只收数值数组：v251 的 dict 里还有 'Lumerical_dataset' 之类的
                        # 对象句柄，存进 npz 会变成 dtype=object（必须 pickle 才能读回）。
                        # "c" 必须留着：场监视器的 E/x 之外，E 本身是复数，
                        # 漏掉它会让 npz 只剩坐标，而 dump 仍然「成功」（D-015）。
                        if a.dtype.kind in "fiubc" and a.size:
                            arrs[k] = a
                else:
                    arrs[result] = np.asarray(raw)
                if not arrs:
                    raise ConfigError(
                        "监视器 %r 的 %r 没有任何数值数组（只有对象句柄），"
                        "写出去会得到一个空 npz 而 dump 看起来是成功的" % (monitor, result))
                path = npz_dir / ("%s_%s.npz" % (name, result))
                np.savez_compressed(path, **arrs)
                out[name] = {
                    "format": "npz", "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
                    "arrays": {k: {"shape": list(v.shape), "dtype": str(v.dtype)}
                               for k, v in arrs.items()},
                }
            else:
                out[name] = jsonable(fdtd.getresult(monitor, result), cap)
        except Exception as e:
            out[name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    return out


def run_one(cfg: dict, root: Path, out: Path) -> dict:
    """One iteration. Imports lumapi ONLY here (never during --dry-run)."""
    shared = root / "library" / "py"                  # 唯一实现（2026-11-11 从 _shared/ 迁入）
    if not (shared / "lumapi_common.py").is_file():   # 兼容只带技能目录的部署
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
    params = cfg.get("params") or {}
    force = bool(cfg.get("force"))
    extract = cfg.get("extract") or {}
    need_npz = any(str(s.get("format", "json")).lower() == "npz" for s in extract.values())
    npz_dir = out / "npz"
    checks = {"params": params, "parameter_map": cfg.get("parameter_map") or {}}

    # Stage 1: load the EXISTING project, switch to layout, inject whitelisted
    # parameters only (no geometry rebuild), save, close.
    f = open_fdtd()
    reused = False
    layoutmode = None
    try:
        f.load(str(base))
        f.eval("lm_probe = layoutmode;")
        layoutmode = float(f.getv("lm_probe"))
        if layoutmode == 0.0 and not params and not force:
            # The reference project already holds results.  Re-running it costs a full
            # solve and changes nothing (P05: 4 projects x 70 min of pure repetition).
            reused = True
            if need_npz:
                npz_dir.mkdir(parents=True, exist_ok=True)
            results = read_monitors(f, extract, int(cfg.get("max_array_items", 2000)),
                                    npz_dir if need_npz else None)
            applied = []
        else:
            f.switchtolayout()
            applied = []
            for param, value in checks["params"].items():
                for mapping in checks["parameter_map"].get(param, []):
                    f.setnamed(mapping["object"], mapping["property"], float(value)
                               if isinstance(value, (int, float)) else value)
                    applied.append({"object": mapping["object"],
                                    "property": mapping["property"], "value": value})
            if need_npz:
                npz_dir.mkdir(parents=True, exist_ok=True)
            f.save(str(iter_fsp))
        checks["applied"] = applied
    finally:
        f.close()

    if not reused:
        # Stage 2: project-verified sequence -- save (done above) then run.  A new session
        # is the default because it is replayable; same-session iteration is also valid
        # (defects/D-004 proved it is `save`, not session age, that matters).
        f2 = verify_and_run(str(iter_fsp), verbose=False)
        try:
            results = read_monitors(f2, extract, int(cfg.get("max_array_items", 2000)),
                                    npz_dir if need_npz else None)
        finally:
            f2.close()

    log = iter_fsp.with_name(iter_fsp.stem + "_p0.log")
    caliber = cfg.get("caliber") or None
    ledger = {
        "ok": True, "iteration": idx, "mode": cfg.get("mode", "Design"),
        "params": checks["params"], "applied": checks["applied"],
        "param_key": check_whitelist(cfg)["param_key"],
        "base_fsp": str(base.relative_to(root)) if base.is_relative_to(root) else str(base),
        "base_fsp_size": base.stat().st_size,
        "iter_fsp": str(iter_fsp) if not reused else str(base),
        "layoutmode_at_load": layoutmode,
        "reused_stored": int(reused),
        "force": int(force),
        "p0_log": str(log) if log.exists() else None,
        "assert_ran": ("not run: reused stored results (layoutmode=0, no params, --force not set)"
                       if reused else
                       "passed (layoutmode / _p0.log / Completed / no diverging)"),
        "results": results,
        "caliber": caliber,
        "elapsed_s": round(time.time() - t0, 3),
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if caliber:
        # repro-card compatible projection, so the same run feeds check_reproduction
        # without retyping the same声明 a second time (P05 §7).
        ledger["repro_card"] = {
            "target": {"quantity": caliber.get("target_quantity"),
                       "value": caliber.get("target_value"),
                       "source": caliber.get("paper_ref")},
            "actual_solver": caliber.get("actual_solver"),
            "numerics_aligned_from": caliber.get("numerics_aligned_from"),
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
        try:
            out_probe = assert_writable_out(root, Path(args.out))
        except ConfigError as e:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
                  if args.json else "ERROR " + str(e))
            return EXIT_USAGE
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
                "reuse_if_stored": not (cfg.get("params") or {}) and not cfg.get("force"),
                "extract": list((cfg.get("extract") or {}).keys()),
                "out": str(out_probe), "session_opened": False}
        print(json.dumps(plan, ensure_ascii=False) if args.json
              else "\n".join("%-20s %s" % (k, v) for k, v in plan.items()))
        return EXIT_OK

    root = repo_root()
    try:
        out = assert_writable_out(root, Path(args.out))
    except ConfigError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
              if args.json else "ERROR " + str(e))
        return EXIT_USAGE
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
