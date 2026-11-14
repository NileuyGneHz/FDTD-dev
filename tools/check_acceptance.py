#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_acceptance.py — 验收表（config/acceptance.json）结构门禁。

为什么要有它
------------
P02/P03/P04 的验收结论只存在于散文报告里：哪一行是 PASS、哪一行是 N/A、
判据来自论文哪一页、用的是什么定义，机器都读不到。结果是三种漂移：
  * 论文没给的量被写成数字（P02 的 poly-Si 材料、P05 的 −0.958）；
  * 报告写 PASS、复现卡里没有对应 target（两套真相）；
  * N/A 不写原因，下一个人以为「测了但不合格」。

本工具把验收行变成数据，并和 `notes/repro-card.md` 的 target 做双向比对。

一条 item 的字段
----------------
    id / claim / quantity / paper_value / unit / source / definition /
    tolerance / measured / status / cause / unmeasured_reason / card_target

    status ∈ {PASS, FAIL, N/A, CALIBER}
    FAIL  必须给 cause（D 号或报告章节）
    N/A   必须给 unmeasured_reason，且 measured 必须为 null
    PASS/FAIL 的 source 必须像出处（含 Fig./Eq./Table/p./§）

用法
----
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/check_acceptance.py --case P02
    "$PY" tools/check_acceptance.py --all --json
    "$PY" tools/check_acceptance.py --self-test

退出码：0 全绿 / 1 有 FAIL / 2 参数或路径错误。
"""

from __future__ import annotations

import argparse
import json
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

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"
STATUSES = {"PASS", "FAIL", "N/A", "CALIBER"}
SOURCE_HINT = re.compile(r"(Fig|Eq\.?|Table|p\.\s*\d|§)", re.I)
REQUIRED = ["id", "claim", "quantity", "paper_value", "unit", "source",
            "definition", "tolerance", "status"]

issues: list[tuple[str, str]] = []      # (level, message)


def bad(msg: str) -> None:
    issues.append(("FAIL", msg))


def ok(msg: str) -> None:
    issues.append(("OK", msg))


def warn(msg: str) -> None:
    issues.append(("WARN", msg))


TRACK_DIRS = {"metasurface", "photonic"}


def iter_pkgs() -> list[tuple[str, Path]]:
    """枚举所有包，兼容扁平（cases/P01_xxx）与双轨（cases/<track>/P01_xxx）。"""
    out: list[tuple[str, Path]] = []
    if not CASES.is_dir():
        return out
    for entry in sorted(CASES.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if entry.name in TRACK_DIRS:
            for sub in sorted(entry.iterdir()):
                if sub.is_dir() and not sub.name.startswith("_"):
                    out.append((entry.name, sub))
        else:
            out.append(("", entry))
    return out


def find_pkg(case: str) -> Path | None:
    """`P03` 或 `metasurface/P03` 都能定位。"""
    want = case.replace("\\", "/").strip("/")
    for track, d in iter_pkgs():
        label = f"{track}/{d.name}" if track else d.name
        if label.startswith(want) or d.name.startswith(want.split("/")[-1]):
            return d
    return None


def parse_card_target(pkg: Path) -> dict | None:
    card = pkg / "notes" / "repro-card.md"
    if not card.is_file():
        return None
    text = card.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"```repro-card\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def validate(pkg: Path) -> None:
    tag = pkg.name
    path = pkg / "config" / "acceptance.json"
    if not path.is_file():
        # 只有「声称做过复现」的包才必须交验收表；其余包跳过，避免把没开工的包判失败
        reports = [ROOT / "docs" / tag / "repro_report.md",
                   pkg / "results" / "repro_report.md"]
        if any(p.is_file() for p in reports):
            bad(f"{tag} 有复现报告但缺 config/acceptance.json")
        else:
            issues.append(("SKIP", f"{tag} 未做复现（无报告），跳过"))
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        bad(f"{tag} acceptance.json 解析失败：{e}")
        return

    for k in ("case", "paper", "items"):
        if k not in data:
            bad(f"{tag} 缺顶层字段 {k}")
    items = data.get("items") or []
    if not items:
        bad(f"{tag} items 为空")
        return
    ok(f"{tag} acceptance.json 可解析，{len(items)} 条")

    seen_ids = set()
    card_targets = []
    for i, it in enumerate(items):
        missing = [k for k in REQUIRED if k not in it]
        if missing:
            bad(f"{tag} items[{i}] 缺字段 {', '.join(missing)}")
            continue
        iid = str(it.get("id"))
        if iid in seen_ids:
            bad(f"{tag} items[{i}] id 重复：{iid}")
        seen_ids.add(iid)

        status = str(it.get("status"))
        if status not in STATUSES:
            bad(f"{tag} items[{i}] 非法 status={status}")
            continue
        if not str(it.get("definition") or "").strip():
            bad(f"{tag} items[{i}] 缺 definition（判据定义）")
        if status in {"PASS", "FAIL"}:
            if not SOURCE_HINT.search(str(it.get("source") or "")):
                bad(f"{tag} items[{i}] source 缺出处定位（Fig./Eq./p./§）：{it.get('source')}")
            if not isinstance(it.get("measured"), (int, float)):
                bad(f"{tag} items[{i}] status={status} 但 measured 不是数值")
        if status == "FAIL" and not str(it.get("cause") or "").strip():
            bad(f"{tag} items[{i}] FAIL 缺 cause")
        if status == "N/A":
            if not str(it.get("unmeasured_reason") or "").strip():
                bad(f"{tag} items[{i}] N/A 缺 unmeasured_reason")
            if it.get("measured") is not None:
                bad(f"{tag} items[{i}] N/A 却给了 measured 数值")
        if it.get("card_target") is True:
            card_targets.append(it)

    ok(f"{tag} 逐条字段检查完成")

    # 与复现卡双向比对：卡里必须有 target，且恰好一条 item 标 card_target
    card = parse_card_target(pkg)
    if card is None:
        warn(f"{tag} 没有可解析的 notes/repro-card.md，跳过卡-表比对")
        return
    if len(card_targets) != 1:
        bad(f"{tag} card_target 标记 {len(card_targets)} 条，必须恰好 1 条")
        return
    ct = card_targets[0]
    t = card.get("target") or {}
    if str(ct.get("quantity")) != str(t.get("quantity")):
        bad(f"{tag} 卡 target.quantity={t.get('quantity')} 与 card_target "
            f"item.quantity={ct.get('quantity')} 不一致")
    else:
        ok(f"{tag} 卡-表 quantity 一致：{t.get('quantity')}")
    reason = str(t.get("unmeasured_reason") or "").strip()
    if reason and ct.get("status") != "N/A":
        bad(f"{tag} 卡声明未测量（{reason}）但表里 card_target status={ct.get('status')}")


def self_test() -> int:
    """正例 + 三个负例：缺 source 定位、N/A 无原因、卡表 quantity 不一致。"""
    global issues
    tmp = Path(tempfile.mkdtemp(prefix="acc_self_"))
    try:
        pkg = tmp / "P99_SelfTest"
        (pkg / "config").mkdir(parents=True)
        (pkg / "notes").mkdir()

        def write(items, quantity="dphi"):
            data = {
                "case": "P99",
                "paper": {"title": "t", "doi": "10.0/x", "file": "paper/x.pdf"},
                "items": items,
            }
            (pkg / "config" / "acceptance.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
            card = {"target": {"quantity": quantity, "value": 180, "source": "Fig.2c",
                               "solver": "FEM", "unmeasured_reason": None}}
            (pkg / "notes" / "repro-card.md").write_text(
                "```repro-card\n" + json.dumps(card) + "\n```\n", encoding="utf-8")

        good = {"id": "A1", "claim": "Δφ", "quantity": "dphi", "paper_value": 180,
                "unit": "deg", "source": "Fig.2c p.5", "definition": "arg<Ex>-arg<Ey>",
                "tolerance": "±18", "measured": 211.1, "status": "FAIL",
                "cause": "C-1", "card_target": True}
        write([good])
        issues = []
        validate(pkg)
        if any(l == "FAIL" for l, _ in issues):
            print("self-test: good fixture should pass", file=sys.stderr)
            return 1

        write([{**good, "source": "paper"}])
        issues = []
        validate(pkg)
        if not any("source 缺出处定位" in m for l, m in issues if l == "FAIL"):
            print("self-test: missing source locator not caught", file=sys.stderr)
            return 1

        write([{**good, "status": "N/A", "measured": None, "unmeasured_reason": ""}])
        issues = []
        validate(pkg)
        if not any("N/A 缺 unmeasured_reason" in m for l, m in issues if l == "FAIL"):
            print("self-test: N/A without reason not caught", file=sys.stderr)
            return 1

        write([good], quantity="PCR")
        issues = []
        validate(pkg)
        if not any("不一致" in m for l, m in issues if l == "FAIL"):
            print("self-test: card/table mismatch not caught", file=sys.stderr)
            return 1

        print("self-test: 1 正例 + 3 负例全部符合预期")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="验收表结构门禁")
    ap.add_argument("--case", help="包 ID，如 P02")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not args.case and not args.all:
        print("需要 --case 或 --all（或 --self-test）", file=sys.stderr)
        return 2

    pkgs = [d for _, d in iter_pkgs() if d.name.startswith("P")]
    if args.case:
        want = args.case.replace("\\", "/").strip("/")
        frag = want.split("/")[-1]
        pkgs = [d for d in pkgs if d.name.startswith(frag)]
        if not pkgs:
            print(f"没有匹配 {args.case} 的包", file=sys.stderr)
            return 2

    for p in pkgs:
        validate(p)

    fails = [m for l, m in issues if l == "FAIL"]
    if args.json:
        print(json.dumps({"packages": [p.name for p in pkgs],
                          "failures": fails,
                          "issues": [{"level": l, "msg": m} for l, m in issues]},
                         ensure_ascii=False, indent=2))
    else:
        for l, m in issues:
            if l != "OK":
                print(f"[{l:4}] {m}")
        print(f"\n汇总：FAIL={len(fails)}  packages={len(pkgs)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
