#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_lsf.py — the single entry point for executing Lumerical .lsf scripts.

Declared by docs/constitution/script-contract.md §3, workspace-layout.md,
skills/INDEX.md and iterations/iter-1-foundation/acceptance.md. P04 (2026-11-07)
found this file referenced in four places but not existing -- the "ghost entry".
This implementation closes that gap.

Consumes : --lsf <file.lsf>  and  --config <json>
             config keys: fsp (optional .fsp to load first), env{license,api_path},
             allow_run (bool), timeout_seconds (int), args (optional script vars),
             read (list of workspace variable names to read back),
             allow_cases_write (bool, see below)
Produces : <out>/run_lsf_result.json  (status / error / elapsed / readback values
           / p0_log path and tail)
           <out>/_p0.log  (acceptance.md §1: one audit log per run)

MEASURED 2026-11-08 (probe in _scratch/regress/_gate/probe_api.txt):
  In headless mode (hide=True) Lumerical's `?`/`print` output goes nowhere --
  not stdout (fd 1), not stderr (fd 2), and `f.eval()` returns None. So an .lsf
  CANNOT report results by printing. The only readback path is:
      f.getv("name")            -> scalar (float) or ndarray for vectors/matrices
  So the contract for an .lsf under this entry point is: assign to a named
  variable, then list that name in config.read / --read.

Safety gates (each derived from a measured incident):
  * --dry-run opens NO Lumerical session and imports NO lumapi.
  * Scripts containing run(/addfdtd(/save( require config.allow_run=true AND
    timeout_seconds, otherwise exit 2. P04's fig2c rerun took ~1h11m while its
    README claimed 35-60 s -- unchecked runs hold a license seat for hours.
  * config.fsp inside cases/ is refused unless allow_cases_write=true: the engine
    writes <fsp>_p0.log NEXT TO the .fsp, so loading a read-only asset mutates it.
    Copy the .fsp into the unit's results/ first.
  * Non-ASCII paths are rejected (GPU error 1113).
  * --out must be outside cases/.
  * close() always in finally.

Paths are resolved RELATIVE TO THE REPOSITORY ROOT, never relative to cwd.
CLI     : --lsf <path> --config <json> --out <dir> [--read a,b] [--dry-run] [--json]
Exit    : 0 = script evaluated (or dry-run plan printed);
          1 = evaluation/load failed; 2 = usage / config / safety gate violation
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# 2026-11-11（D-017 同类）：--json 输出含中文（如「含」「发散」），进程 stdout 不是 UTF-8
# 时 print(json.dumps(..., ensure_ascii=False)) 会抛 UnicodeEncodeError，exit 1。
# 而门禁崩掉与「检出违规」同为 exit 1，调用方无法区分。统一钉死 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:                       # noqa: BLE001 - 已被重定向的流无法 reconfigure
    pass

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_API_PATH = os.environ.get(
    "LUMERICAL_API_PATH", r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
DEFAULT_LICENSE = os.environ.get("ANSYSLMD_LICENSE_FILE", "1055@localhost")

# Lumerical script commands that start a solve, add solver objects, or mutate disk.
# MEASURED 2026-11-08: .lsf allows the no-arg statement form (`run;`) as well as
# the call form (`run(...)`). An earlier regex matched only `run(` and therefore
# let cases/P03_HWP_Ding2015/model/build_tio2_unitcell.lsf:311 `run;` through the
# safety gate with allow_run=false -- a real solve, silently unchecked.
MUTATING_CALL_RE = re.compile(
    r"(?<![\w.])(run|runanalysis|restart|save|saveas|deleteall|addfdtd|addmesh"
    r"|addplane|addpower|addprofile|addmode|addobject|addrect|addcircle)\s*\(",
    re.I)
MUTATING_BARE_RE = re.compile(
    r"(?<![\w.])(run|runanalysis|restart|save|deleteall)\s*;", re.I)
VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def scan_mutations(script: str):
    """Return sorted mutating commands, ignoring `#` comments.

    Lumerical treats `#` as a line comment; a commented-out `#run;` must not
    trip the gate, and a live `run;` must not be hidden by one.
    """
    live = "\n".join(ln.split("#", 1)[0] for ln in script.splitlines())
    found = MUTATING_CALL_RE.findall(live) + MUTATING_BARE_RE.findall(live)
    return sorted(set(m.lower() for m in found))


class UsageError(Exception):
    """Config / CLI / safety problem -> exit code 2."""


def resolve_repo(p):
    q = Path(str(p).replace("\\", "/"))
    return q.resolve() if q.is_absolute() else (REPO_ROOT / q).resolve()


def ascii_gate(p):
    try:
        str(p).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def in_cases(p: Path) -> bool:
    rel = os.path.relpath(p, REPO_ROOT).replace("\\", "/")
    return rel == "cases" or rel.startswith("cases/") or "/cases/" in rel


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def to_jsonable(v):
    """numpy scalars/arrays -> plain JSON; anything else -> repr fallback.

    getv() returns Lumerical vectors as shape (1, N); squeeze those to a flat
    list so consumers do not have to unwrap a phantom outer axis.
    """
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if hasattr(v, "squeeze"):
        try:
            v = v.squeeze()
        except Exception:
            pass
    if hasattr(v, "tolist"):
        try:
            return v.tolist()
        except Exception:
            pass
    return repr(v)


def parse_read(raw):
    if not raw:
        return []
    if isinstance(raw, str):
        raw = [s for s in re.split(r"[,\s]+", raw) if s]
    out = []
    for name in raw:
        name = str(name).strip()
        if not name:
            continue
        if not VAR_RE.match(name):
            raise UsageError("illegal read variable name: %r" % name)
        if name not in out:
            out.append(name)
    return out


def load_inputs(lsf_raw, config_raw, out_raw, read_raw):
    lsf = resolve_repo(lsf_raw)
    if not lsf.is_file():
        raise UsageError("lsf not found: %s" % lsf)
    if lsf.suffix.lower() != ".lsf":
        raise UsageError("--lsf must point to a .lsf file: %s" % lsf)
    if not ascii_gate(lsf):
        raise UsageError("non-ASCII lsf path (GPU error 1113): %s" % lsf)
    cfg_path = resolve_repo(config_raw) if config_raw else None
    cfg = {}
    if cfg_path is not None:
        if not cfg_path.is_file():
            raise UsageError("config not found: %s" % cfg_path)
        try:
            cfg = json.loads(read(cfg_path))
        except Exception as e:
            raise UsageError("config is not valid JSON: %r" % (e,))
        if not isinstance(cfg, dict):
            raise UsageError("config must be a JSON object")
    out = resolve_repo(out_raw)
    if in_cases(out):
        raise UsageError("--out must not be inside read-only cases/: %s"
                         % os.path.relpath(out, REPO_ROOT))
    if not ascii_gate(out):
        raise UsageError("non-ASCII out path (GPU error 1113): %s" % out)
    fsp = resolve_repo(cfg["fsp"]) if cfg.get("fsp") else None
    if fsp is not None:
        if not fsp.is_file():
            raise UsageError("config.fsp not found: %s" % fsp)
        if fsp.suffix.lower() != ".fsp":
            raise UsageError("config.fsp must be a .fsp file: %s" % fsp)
        if not ascii_gate(fsp):
            raise UsageError("non-ASCII fsp path (GPU error 1113): %s" % fsp)
    read_vars = parse_read(read_raw) or parse_read(cfg.get("read") or [])
    return lsf, cfg, out, fsp, read_vars


def build_plan(lsf, cfg, out, fsp, read_vars):
    script = read(lsf)
    mutations = scan_mutations(script)
    p0 = fsp.with_name(fsp.stem + "_p0.log") if fsp else None
    return {
        "lsf": str(lsf),
        "fsp_to_load": str(fsp) if fsp else None,
        "p0_log_expected": str(p0) if p0 else None,
        "out": str(out),
        "script_lines": len(script.splitlines()),
        "script_bytes": lsf.stat().st_size,
        "mutating_commands": mutations,
        "allow_run": bool(cfg.get("allow_run", False)),
        "allow_cases_write": bool(cfg.get("allow_cases_write", False)),
        "timeout_seconds": cfg.get("timeout_seconds"),
        "script_args": cfg.get("args") or {},
        "read_vars": read_vars,
        "safety_gate_required": bool(mutations),
        "env": {"license": cfg.get("env", {}).get("license", DEFAULT_LICENSE),
                "api_path": cfg.get("env", {}).get("api_path", DEFAULT_API_PATH)},
    }


def enforce_safety(plan):
    """Reject work that would burn machine time or mutate read-only assets."""
    if plan["fsp_to_load"] and plan["mutating_commands"]:
        fsp = Path(plan["fsp_to_load"])
        if in_cases(fsp) and not plan["allow_cases_write"]:
            return ("config.fsp 在只读 cases/ 内：引擎会把 %s_p0.log 写在 .fsp 旁边，"
                    "等于改写案例资产。先把 .fsp 复制到单元的 results/ 再跑；"
                    "确需原地跑就显式写 allow_cases_write=true" % fsp.stem)
    if not plan["safety_gate_required"]:
        return None
    if not plan["allow_run"]:
        return ("lsf 含 %s：会启动求解或修改工程，但 config 未写 allow_run=true。"
                "P04 实测单次仿真约 1h11m，README 却写 35-60 s；"
                "必须人工确认机时预算后再放行" % plan["mutating_commands"])
    ts = plan["timeout_seconds"]
    if not isinstance(ts, (int, float)) or ts <= 0:
        return "allow_run=true 时必须给正的 timeout_seconds（秒），防止无限占许可席位"
    return None


def execute(plan, lsf):
    os.environ.setdefault("ANSYSLMD_LICENSE_FILE", plan["env"]["license"])
    api_path = plan["env"]["api_path"]
    if api_path not in sys.path:
        sys.path.insert(0, api_path)
    try:
        import lumapi
    except Exception as e:
        return {"status": "import_failed", "error": repr(e),
                "hint": "检查 env.api_path（默认 %s）与 Python 位数" % DEFAULT_API_PATH}, 1

    script = read(lsf)
    f = None
    t0 = time.time()
    result = {
        "status": "ok", "lsf": plan["lsf"], "fsp_to_load": plan["fsp_to_load"],
        "mutating_commands": plan["mutating_commands"],
        "allow_run": plan["allow_run"], "timeout_seconds": plan["timeout_seconds"],
        "error": None, "readback": {}, "readback_missing": [],
        "p0_log": plan["p0_log_expected"], "p0_log_written": False, "p0_tail": None,
        "note": "headless: ?/print output is discarded by the engine; results must "
                "be assigned to named variables and listed in config.read",
    }
    try:
        f = lumapi.FDTD(hide=True)
        if plan["fsp_to_load"]:
            f.load(plan["fsp_to_load"])
        for k, v in (plan["script_args"] or {}).items():
            if not VAR_RE.match(str(k)):
                raise UsageError("illegal script var name: %r" % k)
            f.eval("%s = %s;" % (k, json.dumps(v)))
        try:
            f.eval(script)
        except Exception as e:
            result["status"] = "eval_failed"
            result["error"] = repr(e)
        for name in plan["read_vars"]:
            try:
                result["readback"][name] = to_jsonable(f.getv(name))
            except Exception as e:
                result["readback_missing"].append({"name": name, "error": repr(e)})
        if result["readback_missing"]:
            result["status"] = "readback_failed" if result["status"] == "ok" \
                else result["status"]
        result["elapsed_seconds"] = round(time.time() - t0, 2)
    except UsageError as e:
        result["status"] = "config_error"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "session_failed"
        result["error"] = repr(e)
    finally:
        if f is not None:
            try:
                f.close()
            except Exception:
                pass

    p0 = result.get("p0_log")
    if p0 and Path(p0).is_file():
        result["p0_log_written"] = True
        try:
            lines = [ln for ln in Path(p0).read_text(
                encoding="utf-8", errors="replace").splitlines() if ln.strip()]
            result["p0_tail"] = lines[-3:]
        except Exception:
            pass
    return result, (0 if result["status"] == "ok" else 1)


def write_p0_log(out: Path, result: dict) -> None:
    """Mirror the run into <out>/_p0.log (acceptance.md §1).

    The engine only writes <fsp>_p0.log next to the .fsp, so a pure .lsf run
    (no .fsp loaded) would leave no log at all. One auditable file per run keeps
    "算没算" reviewable in both cases.
    """
    lines = [
        "# run_lsf.py audit log",
        "# lsf=%s" % result.get("lsf"),
        "# fsp=%s" % result.get("fsp_to_load"),
        "# status=%s" % result.get("status"),
        "# elapsed=%ss" % result.get("elapsed_seconds"),
        "# error=%s" % result.get("error"),
        "# note=%s" % result.get("note"),
        "# readback=%s" % json.dumps(result.get("readback") or {}, ensure_ascii=False),
    ]
    if result.get("p0_tail"):
        lines.append("# engine_p0_tail=%s" % json.dumps(result["p0_tail"],
                                                        ensure_ascii=False))
    (out / "_p0.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        description="Execute a Lumerical .lsf through the single headless entry point")
    ap.add_argument("--lsf", required=True)
    ap.add_argument("--config", required=False,
                    help="optional JSON: fsp / env / allow_run / timeout_seconds / "
                         "args / read / allow_cases_write")
    ap.add_argument("--out", required=True)
    ap.add_argument("--read", default=None,
                    help="comma-separated workspace variables to read back via getv()")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        lsf, cfg, out, fsp, read_vars = load_inputs(
            args.lsf, args.config, args.out, args.read)
        plan = build_plan(lsf, cfg, out, fsp, read_vars)
        refused = enforce_safety(plan)
    except UsageError as e:
        print("config error: %s" % e, file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan, "refusal": refused,
                          "note": "no Lumerical session was opened; "
                                  "lumapi was not imported"},
                         ensure_ascii=False, indent=2))
        return 0

    if refused:
        payload = {"status": "refused_by_safety_gate", "reason": refused, "plan": plan}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("refused: %s" % refused, file=sys.stderr)
        return 2

    out.mkdir(parents=True, exist_ok=True)
    result, code = execute(plan, lsf)
    (out / "run_lsf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_p0_log(out, result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("%s -> %s (%.2fs) status=%s readback=%d p0=%s"
              % (lsf.name, out, result.get("elapsed_seconds") or 0, result["status"],
                 len(result.get("readback") or {}),
                 "yes" if result.get("p0_log_written") else "-"))
        if result["error"]:
            print("error: %s" % result["error"], file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
