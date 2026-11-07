#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decision layer for the L1 design loop (AGENT.md 3.2, steps 2/3/4/5).

Consumes the L1 spec fields ``targets`` / ``locked`` / ``search_space`` plus
observations produced by ``fdtd-lumerical-session-control``; produces the next
parameter set, a FOM trail and one of three verdicts
(PASS / INFEASIBLE / NEEDS_HUMAN).

This module NEVER imports lumapi and NEVER opens an FDTD session. It decides
*which parameters to try*; the executor is a different skill. It does not build
geometry -- that remains fdtd-lumerical-unitcell-simulation's job.

CLI contract: --config <json> --out <dir> [--dry-run] [--json]
Exit codes:   0 ok / 1 diagnosable failure / 2 argument or config error
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from itertools import product
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2
KINDS = ("grid", "coordinate_descent", "local_search")
POLICY = ("grid sampling -> coordinate descent -> local search (L1 MVP; no adjoint)")


class ConfigError(Exception):
    """Bad but diagnosable configuration."""


# --------------------------------------------------------------------------
# pure decision functions (no I/O, unit-testable)
# --------------------------------------------------------------------------

def phase_distance_deg(a: float, b: float) -> float:
    """Wrapped phase distance in degrees. A 10 degree miss is 10, never 350."""
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def _as_scalar(value):
    if isinstance(value, (list, tuple)):
        return float(value[-1]) if value else float("nan")
    return float(value)


def target_margin(target: dict, metrics: dict) -> dict:
    """One target -> gap (>0 means violation), pass flag, actual value."""
    name = target.get("metric")
    if not name:
        raise ConfigError("target 缺 metric")
    if name not in metrics:
        return {"metric": name, "pass": False, "gap": float("inf"),
                "actual": None, "expected": None,
                "reason": "metric missing from observation"}
    actual = _as_scalar(metrics[name])
    if math.isnan(actual):
        return {"metric": name, "pass": False, "gap": float("inf"),
                "actual": None, "expected": None, "reason": "empty metric array"}

    kind = target.get("kind", "linear")
    gaps = []
    if "value" in target:
        want = float(target["value"])
        tol = float(target.get("tol", target.get("tol_deg", 0.0)))
        delta = (phase_distance_deg(actual, want) if kind == "phase"
                 else abs(actual - want))
        gaps.append(delta - tol)
        expected = "%.6g +/- %.6g" % (want, tol)
    else:
        expected = {}
        if "min" in target:
            gaps.append(float(target["min"]) - actual)
            expected["min"] = target["min"]
        if "max" in target:
            gaps.append(actual - float(target["max"]))
            expected["max"] = target["max"]
        if not expected:
            raise ConfigError("target %s 需要 value+tol / min / max 之一" % name)
    gap = max(gaps)
    return {"metric": name, "pass": gap <= 0.0, "gap": gap,
            "actual": actual, "expected": expected}


def evaluate(targets: list, metrics: dict) -> dict:
    """FOM = sum of squared positive gaps. Zero means every target is met."""
    rows = [target_margin(t, metrics) for t in targets]
    finite = [r["gap"] for r in rows if math.isfinite(r["gap"])]
    fom = sum(max(0.0, g) ** 2 for g in finite)
    if not all(math.isfinite(r["gap"]) for r in rows):
        fom = float("inf")
    return {"fom": fom, "pass": all(r["pass"] for r in rows), "targets": rows}


def grid_points(space: dict, cap: int = 64) -> list:
    axes = []
    for key in sorted(space):
        spec = space[key]
        lo, hi = float(spec["min"]), float(spec["max"])
        step = float(spec.get("step", (hi - lo) / 4.0))
        if step <= 0:
            raise ConfigError("%s.step 必须 > 0" % key)
        n = int(math.floor((hi - lo) / step + 1e-9)) + 1
        axes.append((key, [round(lo + i * step, 12) for i in range(n)]))
    total = 1
    for _, vals in axes:
        total *= len(vals)
    if total > cap:
        raise ConfigError("网格 %d 点 > max_grid_points=%d；请调大 step 或改用坐标下降" % (total, cap))
    return [dict(zip([k for k, _ in axes], combo))
            for combo in product(*[v for _, v in axes])]


def param_key(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


def clamp(v, spec):
    return max(float(spec["min"]), min(float(spec["max"]), v))


def next_candidate(strategy: dict, space: dict, observations: list, seen: set) -> dict | None:
    """Pick the next parameter set. Returns None when the space is exhausted."""
    kind = strategy.get("kind", "coordinate_descent")
    if kind not in KINDS:
        raise ConfigError("strategy.kind 必须是 %s" % (KINDS,))
    if kind == "grid":
        pool = grid_points(space, int(strategy.get("max_grid_points", 64)))
    else:
        scored = [(o.get("fom", float("inf")), o.get("params", {})) for o in observations]
        scored = [(f, p) for f, p in scored if p and math.isfinite(float(f))]
        if scored:
            _, base = min(scored, key=lambda x: x[0])
        else:
            base = {k: (float(s["min"]) + float(s["max"])) / 2.0 for k, s in space.items()}
        pool = []
        if kind == "coordinate_descent":
            for k in sorted(space):
                step = float(space[k].get("step", (float(space[k]["max"]) - float(space[k]["min"])) / 4.0))
                for sign in (-1, 1):
                    cand = dict(base)
                    cand[k] = clamp(float(base.get(k, 0.0)) + sign * step, space[k])
                    pool.append(cand)
            pool.insert(0, {k: clamp(float(base.get(k, 0.0)), space[k]) for k in space})
        else:  # local_search, deterministic for reproducibility
            rng = random.Random(int(strategy.get("seed", 20261107)) + len(observations))
            for _ in range(int(strategy.get("samples", 8))):
                cand = {}
                for k, s in space.items():
                    step = float(s.get("step", (float(s["max"]) - float(s["min"])) / 4.0))
                    cand[k] = clamp(float(base.get(k, 0.0)) + rng.uniform(-step, step), s)
                pool.append(cand)
    for cand in pool:
        if param_key(cand) not in seen:
            return cand
    return None


def on_boundary(params: dict, space: dict) -> bool:
    for k, v in params.items():
        if k not in space:
            continue
        lo, hi = float(space[k]["min"]), float(space[k]["max"])
        if abs(float(v) - lo) < 1e-12 or abs(float(v) - hi) < 1e-12:
            return True
    return False


def decide(cfg: dict) -> dict:
    """Pure: config in, decision out. No filesystem, no lumapi."""
    mode = cfg.get("mode", "Design")
    if mode not in ("Reproduce", "Design"):
        raise ConfigError("mode 必须是 Reproduce / Design")
    if mode == "Reproduce":
        raise ConfigError("Reproduce 模式禁止调参（L1 §③）；本技能只服务 Design 模式")
    for key in ("targets", "search_space"):
        if not cfg.get(key):
            raise ConfigError("缺 L1 必填字段 %s" % key)
    locked = cfg.get("locked") or {}
    for key in cfg["search_space"]:
        if key in locked:
            raise ConfigError("search_space 与 locked 冲突: %s" % key)

    strategy = cfg.get("strategy") or {"kind": "coordinate_descent"}
    budget = cfg.get("budget") or {}
    max_runs = int(budget.get("max_runs", 20))
    stale = int(budget.get("stale_limit", 5))

    observations = list(cfg.get("observations") or [])
    obs = cfg.get("observation")
    if obs:
        observations.append(obs)
    for o in observations:
        if "params" not in o or "metrics" not in o:
            raise ConfigError("observation 必须含 params 与 metrics")
        ev = evaluate(cfg["targets"], o["metrics"])
        o.setdefault("fom", ev["fom"])
        o.setdefault("verdict_rows", ev["targets"])

    passed = [o for o in observations if o.get("fom", float("inf")) == 0.0]
    seen = {param_key(o["params"]) for o in observations}
    run_count = len(observations)

    if passed:
        verdict, reason = "PASS", "所有 targets 在容差内达标"
        nxt = None
    elif run_count >= max_runs:
        verdict = "INFEASIBLE"
        reason = "预算耗尽（%d/%d 轮），在给定 search_space 内未达标" % (run_count, max_runs)
        nxt = None
    else:
        nxt = next_candidate(strategy, cfg["search_space"], observations, seen)
        if nxt is None:
            verdict, reason = "INFEASIBLE", "search_space 已穷尽，未达标"
        else:
            recent = observations[-stale:] if stale else []
            improving = len({round(float(o.get("fom", float("inf"))), 9) for o in recent}) > 1
            best = min((float(o.get("fom", float("inf"))) for o in observations),
                       default=float("inf"))
            best_params = min(observations, key=lambda o: float(o.get("fom", float("inf"))))["params"] if observations else {}
            if len(observations) >= stale and not improving and on_boundary(best_params, cfg["search_space"]):
                verdict = "NEEDS_HUMAN"
                reason = "连续 %d 轮无改善且最优点落在 search_space 边界；继续需要改 locked（人来）" % stale
                nxt = None
            else:
                verdict, reason = "CONTINUE", "继续下一组参数"

    finite = [o for o in observations if math.isfinite(float(o.get("fom", float("inf"))))]
    best_fom = min((float(o["fom"]) for o in finite), default=None)
    return {
        "mode": mode, "policy": POLICY, "verdict": verdict, "reason": reason,
        "run_count": run_count, "max_runs": max_runs,
        "best_fom": best_fom, "next_params": nxt,
        "observations": observations,
        "boundary_evidence": ({"best_fom": best_fom,
                               "best_params": min(finite, key=lambda o: o["fom"])["params"]}
                              if verdict == "INFEASIBLE" and finite else None),
    }


# --------------------------------------------------------------------------
# I/O layer
# --------------------------------------------------------------------------

def write_outputs(out: Path, cfg: dict, decision: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    obs = decision["observations"]
    with (out / "observations.jsonl").open("w", encoding="utf-8") as fh:
        for o in obs:
            fh.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")
    with (out / "search_log.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "fom", "params", "metrics"])
        for i, o in enumerate(obs, 1):
            w.writerow([i, o.get("fom"), json.dumps(o["params"], sort_keys=True),
                        json.dumps(o["metrics"], sort_keys=True)])
    with (out / "fom_curve.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "fom", "best_so_far"])
        best = float("inf")
        for i, o in enumerate(obs, 1):
            f = float(o.get("fom", float("inf")))
            best = min(best, f)
            w.writerow([i, f, best])
    (out / "verdict.json").write_text(
        json.dumps({k: v for k, v in decision.items() if k != "observations"},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "next_params.json").write_text(
        json.dumps(decision["next_params"] or {}, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"search_log.csv": len(obs), "fom_curve.csv": len(obs),
            "verdict.json": 1, "next_params.json": 1,
            "observations.jsonl": len(obs)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="L1 design-loop decision layer")
    ap.add_argument("--config", required=True, help="L1 spec JSON (targets/locked/search_space)")
    ap.add_argument("--out", required=True, help="output directory (all artefacts land here)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing, open no session")
    ap.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(json.dumps({"ok": False, "error": "config not found: %s" % cfg_path}) if args.json
              else "ERROR config not found: %s" % cfg_path)
        return EXIT_USAGE
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "error": "bad JSON: %s" % e}) if args.json
              else "ERROR bad JSON: %s" % e)
        return EXIT_USAGE
    try:
        decision = decide(cfg)
    except ConfigError as e:
        print(json.dumps({"ok": False, "error": str(e)}) if args.json
              else "ERROR %s" % e)
        return EXIT_FAIL

    if args.dry_run:
        plan = {"ok": True, "dry_run": True, "mode": decision["mode"],
                "policy": decision["policy"], "verdict": decision["verdict"],
                "run_count": decision["run_count"], "max_runs": decision["max_runs"],
                "next_params": decision["next_params"],
                "would_write": ["search_log.csv", "fom_curve.csv", "verdict.json",
                                "next_params.json", "observations.jsonl"],
                "out": str(Path(args.out))}
        print(json.dumps(plan, ensure_ascii=False) if args.json
              else "\n".join("%-18s %s" % (k, v) for k, v in plan.items()))
        return EXIT_OK

    try:
        counts = write_outputs(Path(args.out), cfg, decision)
    except OSError as e:
        print(json.dumps({"ok": False, "error": str(e)}) if args.json
              else "ERROR %s" % e)
        return EXIT_FAIL
    summary = {"ok": True, "verdict": decision["verdict"],
               "reason": decision["reason"], "run_count": decision["run_count"],
               "best_fom": decision["best_fom"], "next_params": decision["next_params"],
               "out": str(Path(args.out)), "files": counts}
    print(json.dumps(summary, ensure_ascii=False) if args.json
          else "\n".join("%-18s %s" % (k, v) for k, v in summary.items()))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
