#!/usr/bin/env python3
"""check_reproduction.py — 复现约束体检（机器可读语料门禁）。

    python tools/check_reproduction.py --case P01
    python tools/check_reproduction.py --card <path>    # 草稿卡自检
    python tools/check_reproduction.py --self-test      # 负对照：门禁没退化
    python tools/check_reproduction.py --json
    python tools/check_reproduction.py --emit-template

规则出处：docs/constitution/reproduction-contract.md（逐条对应 [R1]–[R12]）。
与 tools/check_skill_contract.py 的分工：
    check_skill_contract = 技能内容合不合契约
    check_reproduction   = 一次复现的证据齐不齐、能不能拿来训练技能

检查项：
    [R1]  notes/repro-card.md 存在，```repro-card JSON 块合法，必填字段齐全
    [R2]  mode=reproduce 时 locked 齐全，verdict.status 不得为 fitted（禁止调参凑数）
    [R3]  口径声明齐全；求解器不同时 verdict 只能判 solver_mismatch / inconclusive
    [R4]  每个参考 .fsp 存在；converged / shutoff 声明与 _p0.log 实测一致
    [R5]  每个 run 的 shutoff_final < threshold；日志在场时与末值一致
    [R6]  same_input_regression.delta <= tolerance，且 runs >= 2
    [R7]  excluded[] 每条有 suspect / verdict / 非空 evidence
    [R8]  verdict.stop_reason 非空、gap 有数值、explainable_by 与 status 自洽
    [R9]  所有 runs[].out 不落在只读 cases/
    [R10] defects[] 每个 D 号文件存在且三段（根因/修复/验证）齐全
    [R11] training_items[] 非空，destination 合法，landed=true 时 target_path 存在
    [R12] rerun_commands[] 非空、全卡无绝对路径；命令缺 --out 记 WARN

退出码：0 = 通过（允许 WARN；--self-test 通过亦为 0）；1 = 有 FAIL 或负对照未拦全；
        2 = 参数或卡片枚举错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_PATTERNS = ("cases/*/notes/repro-card.md", "projects/*/notes/repro-card.md")
CARD_BLOCK_RE = re.compile(r"```repro-card\s*\r?\n(.*?)\r?\n```", re.S)
SHUTOFF_RE = re.compile(r"Auto Shutoff:\s*([0-9.eE+-]+)", re.I)
EARLY_RE = re.compile(r"Early termination of simulation", re.I)
P100_RE = re.compile(r"100%\s*complete", re.I)
COMPLETED_RE = re.compile(r"Completed\s+\d+\s+iterations", re.I)
ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
DESTINATIONS = {"defects", "notes", "references", "scripts", "SKILL.md"}
STATUSES = {"reproduced", "solver_mismatch", "inconclusive", "unresolved", "fitted"}
REQUIRED_FIELDS = (
    "case", "mode", "date", "target", "actual_solver", "locked",
    "truth_sources", "runs", "same_input_regression", "excluded",
    "verdict", "defects", "training_items", "rerun_commands",
)
REQUIRED_LOCKED = {"materials", "layer_stack", "topology", "geometry"}

fails: list[str] = []
warns: list[str] = []
ok_count = 0
QUIET = False


def ok(n: str, msg: str) -> None:
    global ok_count
    ok_count += 1
    if not QUIET:
        print(f"  [{n}] OK    {msg}")


def bad(n: str, msg: str, hint: str = "") -> None:
    fails.append(f"[{n}] {msg}")
    if not QUIET:
        print(f"  [{n}] FAIL  {msg}")
        if hint:
            print(f"        -> {hint}")


def warn(n: str, msg: str) -> None:
    warns.append(f"[{n}] {msg}")
    if not QUIET:
        print(f"  [{n}] WARN  {msg}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def close(a: float, b: float, rel: float = 1e-3) -> bool:
    return abs(a - b) <= max(1e-18, abs(b) * rel)


def resolve(raw: str, pkg_root: Path) -> Path:
    """卡内路径：顶层目录在仓库根存在则按仓库根解析，否则按包根解析。

    cases/ skills/ defects/ _scratch/ -> ROOT；model/ notes/ config/ -> 单元包内。
    """
    p = Path(raw.replace("\\", "/"))
    if p.parts and (ROOT / p.parts[0]).exists():
        return ROOT / p
    return pkg_root / p


def parse_log(path: Path, threshold: float | None) -> dict:
    txt = read(path)
    vals = SHUTOFF_RE.findall(txt)
    final = None
    for raw in reversed(vals):
        final = num(raw)
        if final is not None:
            break
    early = bool(EARLY_RE.search(txt))
    p100 = bool(P100_RE.search(txt))
    converged = bool(
        final is not None and threshold is not None
        and final < threshold and (early or p100)
    )
    return {
        "final": final, "early": early, "p100": p100,
        "completed": bool(COMPLETED_RE.search(txt)), "converged": converged,
    }


def check_convergence(n: str, label: str, entry: dict, pkg_root: Path) -> None:
    """[R4]/[R5] 共用：数值自洽 + 日志在场时与实测比对。"""
    final = num(entry.get("shutoff_final", entry.get("shutoff")))
    thr = num(entry.get("threshold"))
    declared = entry.get("converged")
    if final is None or thr is None:
        bad(n, f"{label} 缺 shutoff/threshold 数值")
        return
    if declared is False:
        # 未收敛的参考工程是合法真相源，只要求与日志一致，不要求末值低于阈值
        if final < thr:
            warn(n, f"{label} 声明未收敛但末值 {final:g} 已低于阈值 {thr:g}，请核对")
    elif not final < thr:
        bad(n, f"{label} shutoff_final={final:g} 不小于阈值 {thr:g}")
        return
    log_raw = entry.get("p0_log")
    if not log_raw:
        warn(n, f"{label} 未登记 p0_log，收敛数值不可复核")
        return
    logp = resolve(str(log_raw), pkg_root)
    if not logp.exists():
        warn(n, f"{label} 日志未归档（{log_raw}），换机器不可核验")
        return
    info = parse_log(logp, thr)
    if info["final"] is None:
        bad(n, f"{label} 日志里没有 Auto Shutoff 行：{logp}")
        return
    if not close(info["final"], final):
        bad(n, f"{label} 卡片 shutoff={final} 与日志末值 {info['final']} 不符",
            f"改 {logp} 对应的卡片数值")
        return
    if declared is None and not info["converged"]:
        bad(n, f"{label} run 未收敛（末值 {info['final']:g}），结果不可信")
        return
    if declared is not None and bool(declared) != info["converged"]:
        bad(n, f"{label} converged={declared} 与日志判定 {info['converged']} 不符",
            "检查是否有 Early termination / 100% complete 行")
        return
    ok(n, f"{label} 收敛数值与日志一致（{info['final']:g}，converged={info['converged']}）")


def check_card(card: Path) -> None:
    pkg_root = card.parent.parent
    tag = f"{pkg_root.name}/{card.name}"
    if not QUIET:
        print(f"\n=== {tag} ===")
    text = read(card)
    m = CARD_BLOCK_RE.search(text)
    if not m:
        bad("R1", f"{tag} 没有 ```repro-card JSON 代码块")
        return
    try:
        c = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        bad("R1", f"{tag} 卡片 JSON 解析失败：{e}")
        return
    missing = [k for k in REQUIRED_FIELDS if k not in c]
    if missing:
        bad("R1", f"{tag} 缺必填字段：{', '.join(missing)}")
        return
    ok("R1", f"{tag} 卡片可解析，14 个必填字段齐全")

    # [R2] 锁定项与禁止调参凑数
    locked = set(c.get("locked") or [])
    verdict = c.get("verdict") or {}
    status = str(verdict.get("status", ""))
    if c.get("mode") == "reproduce":
        lack = REQUIRED_LOCKED - locked
        if lack:
            bad("R2", f"{tag} locked 缺 {', '.join(sorted(lack))}")
        elif status == "fitted":
            bad("R2", f"{tag} verdict.status=fitted：把拟合当复现，违反 L1 §3",
                "恢复论文几何参数，重新判定")
        else:
            ok("R2", f"{tag} 锁定项齐全，status={status}（非 fitted）")
    else:
        warn("R2", f"{tag} mode={c.get('mode')}，非 reproduce，跳过锁定项检查")

    # [R3] 口径声明
    t = c.get("target") or {}
    paper_solver = str(t.get("solver") or "")
    actual = str(c.get("actual_solver") or "")
    if (num(t.get("value")) is None or not t.get("quantity")
            or not t.get("source") or not paper_solver or not actual):
        bad("R3", f"{tag} 口径声明不全（quantity/value/source/solver/actual_solver）")
    elif paper_solver != actual and status not in {"solver_mismatch", "inconclusive"}:
        bad("R3", f"{tag} 求解器不同（{paper_solver} vs {actual}）却判 status={status}",
            "改为 solver_mismatch / inconclusive，差异本身是产出")
    else:
        ok("R3", f"{tag} 口径声明齐全；solver={'不同' if paper_solver != actual else '相同'} → {status}")

    # [R4] 真相源
    sources = c.get("truth_sources") or []
    if not sources:
        warn("R4", f"{tag} 没有登记参考 .fsp（若本包确实没有，可忽略）")
    for s in sources:
        label = str(s.get("path") or "<unnamed>")
        fsp = resolve(label, pkg_root)
        if not fsp.exists():
            bad("R4", f"{tag} 参考工程不存在：{label}")
            continue
        ok("R4", f"{tag} 参考工程存在：{label}")
        check_convergence("R4", f"{tag} {fsp.name}", s, pkg_root)

    # [R5] 运行收敛；[R6] 还要求至少两条可对照的 run
    runs = c.get("runs") or []
    if len(runs) < 2:
        bad("R6", f"{tag} runs 只有 {len(runs)} 条，至少需要基线 + 对照两条")
    for r in runs:
        check_convergence("R5", f"{tag} run:{r.get('name', '?')}", r, pkg_root)

    # [R6] 同输入回归
    reg = c.get("same_input_regression") or {}
    delta = num(reg.get("delta"))
    tol = num(reg.get("tolerance"))
    b = num(reg.get("baseline_A"))
    r = num(reg.get("repeat_A"))
    if delta is None or tol is None or b is None or r is None:
        bad("R6", f"{tag} same_input_regression 缺数值字段")
    elif delta > tol:
        bad("R6", f"{tag} 同输入回归 delta={delta} 超过容差 {tol}，先查脚本")
    elif not close(delta, abs(b - r), 1e-6):
        bad("R6", f"{tag} delta={delta} 与 |{b}-{r}|={abs(b-r):g} 不自洽")
    else:
        ok("R6", f"{tag} 同输入回归通过（delta={delta:g} <= {tol:g}）")

    # [R7] 排除清单
    excluded = c.get("excluded") or []
    if not excluded:
        bad("R7", f"{tag} excluded[] 为空，差异诊断没有排除法证据")
    for i, e in enumerate(excluded):
        ev = str(e.get("evidence") or "").strip()
        if not e.get("suspect") or not e.get("verdict") or not ev or ev in {"已确认", "confirmed"}:
            bad("R7", f"{tag} excluded[{i}] 缺 suspect/verdict/可复跑证据")
        else:
            ok("R7", f"{tag} 排除项 {e.get('suspect')} 有证据")

    # [R8] 结论与停下理由
    gap = num(verdict.get("gap"))
    stop = str(verdict.get("stop_reason") or "").strip()
    explain = verdict.get("explainable_by")
    if status not in STATUSES:
        bad("R8", f"{tag} 非法 verdict.status={status}")
    elif not stop or gap is None:
        bad("R8", f"{tag} verdict 缺 stop_reason 或 gap 数值")
    elif status == "solver_mismatch" and explain and re.search(
            r"tune|fit|调参|凑", str(explain), re.I):
        bad("R8", f"{tag} solver_mismatch 却把差异归因于可调参数：{explain}")
    else:
        ok("R8", f"{tag} verdict={status}，gap={gap:g}，停下的理由已记录")

    # [R9] 输出隔离
    for run in runs:
        out = str(run.get("out") or "")
        if not out:
            bad("R9", f"{tag} run:{run.get('name')} 缺 out")
        elif out.startswith("cases/") or "\\cases\\" in out or "/cases/" in out:
            bad("R9", f"{tag} run:{run.get('name')} 输出写进只读 cases/：{out}",
                "改用 _scratch/regress/<date>/...")
        else:
            ok("R9", f"{tag} run:{run.get('name')} 输出隔离 OK（{out}）")

    # [R10] 缺陷三段
    for d in c.get("defects") or []:
        hits = sorted((ROOT / "defects").glob(f"{d}-*.md"))
        if not hits:
            bad("R10", f"{tag} 找不到 {d} 对应的 defect 文件")
            continue
        body = read(hits[0])
        groups = [
            ("根因", r"^##\s*.*(根因|Root\s+Cause)", re.M | re.I),
            ("修复", r"^##\s*.*(修复|Fix|Resolution)", re.M | re.I),
            ("验证", r"^##\s*.*(验证|Verification|Validation)", re.M | re.I),
        ]
        lack = [name for name, pat, flags in groups if not re.search(pat, body, flags)]
        if lack:
            bad("R10", f"{tag} {hits[0].name} 缺三段：{', '.join(lack)}")
        else:
            ok("R10", f"{tag} {hits[0].name} 三段齐全")

    # [R11] 训练条目
    items = c.get("training_items") or []
    if not items:
        bad("R11", f"{tag} training_items 为空，本次复现没有产出可训练语料")
    for i, it in enumerate(items):
        dest = str(it.get("destination") or "")
        if not it.get("id") or not it.get("observation") or not it.get("evidence"):
            bad("R11", f"{tag} training_items[{i}] 缺 id/observation/evidence")
        elif dest not in DESTINATIONS:
            bad("R11", f"{tag} training_items[{i}] 非法 destination={dest}")
        elif it.get("landed"):
            tp = it.get("target_path")
            if not tp or not resolve(str(tp), pkg_root).exists():
                bad("R11", f"{tag} {it.get('id')} 标 landed=true 但 target_path 不存在：{tp}")
            else:
                ok("R11", f"{tag} {it.get('id')} 已落地 {dest}")
        else:
            ok("R11", f"{tag} {it.get('id')} 归属 {dest}（待落地）")

    # [R12] 可重跑命令与相对路径
    cmds = c.get("rerun_commands") or []
    if not cmds:
        bad("R12", f"{tag} rerun_commands 为空")
    for cmd in cmds:
        if "--out" not in str(cmd):
            warn("R12", f"{tag} 命令未显式 --out：{str(cmd)[:70]}")
    if ABS_PATH_RE.search(text):
        bad("R12", f"{tag} 卡片里出现绝对路径，换机器即死",
            "改为仓库相对路径")
    else:
        ok("R12", f"{tag} {len(cmds)} 条可重跑命令，全卡无绝对路径")


TEMPLATE = """# <CASE> 复现卡（<DATE>）

> 本卡是结构化索引，长表格与推导放同目录 notes 里，不在此复制。
> 生成骨架：python tools/check_reproduction.py --emit-template

```repro-card
{
  "case": "P02",
  "mode": "reproduce",
  "date": "2026-11-08",
  "target": {
    "quantity": "<from paper>",
    "value": 0.0,
    "wavelength_um": 0.0,
    "source": "<figure / text / experiment>",
    "solver": "<paper solver>"
  },
  "actual_solver": "Lumerical FDTD v251",
  "locked": ["materials", "layer_stack", "topology", "geometry"],
  "numerics_aligned_from": null,
  "truth_sources": [
    {
      "path": "model/<ref>.fsp",
      "role": "reference",
      "converged": false,
      "shutoff": 0.0,
      "threshold": 1e-05,
      "p0_log": "model/<ref>_p0.log"
    }
  ],
  "runs": [
    {
      "name": "baseline",
      "out": "_scratch/regress/<date>/baseline",
      "p0_log": "_scratch/regress/<date>/baseline/point_00_base_p0.log",
      "shutoff_final": 0.0,
      "threshold": 0.0001,
      "peak_A": 0.0,
      "peak_lam_um": 0.0
    },
    {
      "name": "reference_calibrated",
      "out": "_scratch/regress/<date>/fsp_calibrated",
      "p0_log": "_scratch/regress/<date>/fsp_calibrated/point_00_base_p0.log",
      "shutoff_final": 0.0,
      "threshold": 1e-05,
      "peak_A": 0.0,
      "peak_lam_um": 0.0
    }
  ],
  "same_input_regression": {
    "baseline_A": 0.0,
    "repeat_A": 0.0,
    "delta": 0.0,
    "tolerance": 0.005
  },
  "excluded": [
    {
      "suspect": "<suspect>",
      "verdict": "excluded",
      "evidence": "<command + output, or notes path>",
      "rerun": "<command>"
    }
  ],
  "verdict": {
    "status": "inconclusive",
    "gap": 0.0,
    "explainable_by": null,
    "stop_reason": "<why stopped here>"
  },
  "defects": ["D-003"],
  "training_items": [
    {
      "id": "R-001",
      "observation": "<what breaks or how to judge correctly>",
      "evidence": "<command + output, or defects/D-xxx path>",
      "destination": "references",
      "landed": false,
      "target_path": null
    }
  ],
  "rerun_commands": [
    "python skills/<name>/scripts/<script>.py --config <json> --out _scratch/regress/<date>/x"
  ]
}
```
"""


BAD_CARD = {
    "case": "NEGATIVE-CONTROL",
    "mode": "reproduce",
    "date": "2026-11-07",
    "target": {"quantity": "peak_absorption", "value": 0.97, "wavelength_um": 6.0,
               "source": "Fig.2a", "solver": "CST 2009"},
    "actual_solver": "Lumerical FDTD v251",
    "locked": ["materials"],
    "truth_sources": [],
    "runs": [{"name": "only_one", "out": "cases/P01/results",
              "shutoff_final": 0.5, "threshold": 1e-05,
              "peak_A": 0.9, "peak_lam_um": 6.0}],
    "same_input_regression": {"baseline_A": 0.9, "repeat_A": 0.1,
                              "delta": 0.8, "tolerance": 0.005},
    "excluded": [],
    "verdict": {"status": "fitted", "gap": 0.07,
                "explainable_by": None, "stop_reason": ""},
    "defects": ["D-999"],
    "training_items": [],
    "rerun_commands": [],
}


def self_test() -> int:
    """负对照：喂一张故意违规的卡，确认门禁真的会 FAIL 而不是永远 ALL GREEN。"""
    import os
    import tempfile

    global QUIET, ok_count
    QUIET = True
    fails.clear()
    warns.clear()
    ok_count = 0
    fd, name = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text("```repro-card\n" + json.dumps(BAD_CARD, ensure_ascii=False)
                       + "\n```\n", encoding="utf-8")
        check_card(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    caught = {f.split("]")[0].lstrip("[") for f in fails}
    expected = {"R2", "R3", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12"}
    print(f"self-test: {len(fails)} failures caught across {len(caught & expected)} rules")
    missed = sorted(expected - caught)
    if missed:
        print(f"SELF-TEST FAILED, missed: {', '.join(missed)}", file=sys.stderr)
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    global QUIET
    ap = argparse.ArgumentParser(description="复现约束体检（reproduction-contract.md R1-R12）")
    ap.add_argument("--case", help="只查指定包，如 P01")
    ap.add_argument("--card", help="只检查指定卡片文件（草稿自检 / 负对照）")
    ap.add_argument("--json", action="store_true", help="只输出机器可读 JSON")
    ap.add_argument("--emit-template", action="store_true", help="打印复现卡骨架后退出")
    ap.add_argument("--self-test", action="store_true", help="负对照：验证门禁能拦下违规卡")
    args = ap.parse_args()
    if args.emit_template:
        print(TEMPLATE)
        return 0
    if args.self_test:
        return self_test()
    QUIET = args.json

    cards: list[Path] = []
    if args.card:
        p = Path(args.card)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"Card not found: {p}", file=sys.stderr)
            return 2
        cards = [p]
    else:
        for pat in CARD_PATTERNS:
            cards.extend(sorted(ROOT.glob(pat)))
        if args.case:
            key = args.case.lower()
            case_re = re.compile(r'"case"\s*:\s*"%s"' % re.escape(key), re.I)
            cards = [c for c in cards
                     if c.parent.parent.name.lower().startswith(key) or case_re.search(read(c))]
            if not cards:
                print(f"No repro-card found for case={args.case}", file=sys.stderr)
                return 2
        if not cards:
            warn("R1", "仓库里还没有任何 repro-card.md，本契约尚未被使用")

    for card in cards:
        check_card(card)

    result = {
        "cards": len(cards), "ok": ok_count,
        "warn": len(warns), "fail": len(fails),
        "fails": fails, "warns": warns,
        "verdict": "ALL GREEN" if not fails else "FAILED",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'-' * 60}")
        print(f"{len(cards)} card(s) · OK {ok_count} · WARN {len(warns)} · FAIL {len(fails)}"
              f" · {result['verdict']}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
