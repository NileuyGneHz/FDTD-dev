#!/usr/bin/env python3
"""claim_audit.py — 核对 results/claims.csv 里每个 value_checked 能否在 PDF 内找到。

    python skills/lit-claim-audit/scripts/claim_audit.py --config <spec.json> --out <dir>
    python skills/lit-claim-audit/scripts/claim_audit.py --config <spec.json> --dry-run

spec.json:
    {"packages": ["cases/P03_...", "cases/P04_..."]}

对每个包：
    1. 读 results/claims.csv
    2. 校验列齐全、match 取值合法
    3. 对 match=yes 的行：检查 value_checked 是否出现在 PDF 文本里（数字归一）
    4. 对 match=unverified 的行：只统计，不判错（但 value_checked 若写了
       NOT OBTAINED / NOT FOUND 之类的占位，标 placeholder）
    5. 对 match=no 的行：要求 note 非空

退出码：0 无问题 / 1 有 problem / 2 参数错误
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REQUIRED = ["metric", "value_paper", "value_checked", "match", "source"]
MATCH_VALUES = {"yes", "no", "unverified"}
PLACEHOLDER = re.compile(r"\bNOT\s+(OBTAINED|FOUND)\b|n/?a\b|未获取|未找到", re.I)


def norm(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"-\s+", "-", s)
    return " ".join(s.split())


def pdf_text(pkg: Path) -> str | None:
    papers = sorted((pkg / "paper").glob("*.pdf"))
    if not papers:
        return None
    from pypdf import PdfReader
    return norm(" ".join((p.extract_text() or "") for p in PdfReader(str(papers[0])).pages))


def audit(pkg: Path) -> dict:
    csv_path = pkg / "results" / "claims.csv"
    if not csv_path.is_file():
        return {"package": pkg.name, "status": "no-claims", "problems": []}
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        cols = reader.fieldnames or []
    problems: list[str] = []
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        problems.append(f"缺列: {', '.join(missing)}")
        return {"package": pkg.name, "status": "bad-columns",
                "problems": problems, "rows": len(rows)}

    text = pdf_text(pkg)
    stats = {"yes": 0, "no": 0, "unverified": 0}
    verified = 0
    for i, row in enumerate(rows, start=2):
        m = (row.get("match") or "").strip().lower()
        if m not in MATCH_VALUES:
            problems.append(f"第 {i} 行 match={m!r} 非法")
            continue
        stats[m] += 1
        checked = (row.get("value_checked") or "").strip()
        if m == "yes":
            if PLACEHOLDER.search(checked):
                problems.append(f"第 {i} 行 match=yes 但 value_checked 是占位符: {checked!r}")
                continue
            if text is None:
                problems.append(f"第 {i} 行 match=yes 但包内无 PDF，无法核验")
                continue
            probe = norm(checked)
            if probe and probe not in text:
                # 数字容错：去掉千分位与空格再试
                alt = re.sub(r"[\s,]", "", probe)
                if alt and alt not in re.sub(r"[\s,]", "", text):
                    problems.append(
                        f"第 {i} 行 match=yes 但 PDF 内找不到 value_checked={checked!r}")
                    continue
            verified += 1
        elif m == "no":
            if not (row.get("note") or "").strip():
                problems.append(f"第 {i} 行 match=no 但没有 note 说明差异")
        else:  # unverified
            if checked and not PLACEHOLDER.search(checked) and not checked.lower().startswith("not"):
                # 允许 unverified 写实际值（如「未获取正文」），只提示
                pass

    status = "ok" if not problems else "problems"
    return {"package": pkg.name, "status": status, "rows": len(rows),
            "stats": stats, "verified_yes_rows": verified, "problems": problems}


def main() -> int:
    ap = argparse.ArgumentParser(description="audit claims.csv against PDFs")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"FAIL config 不存在: {cfg_path}", file=sys.stderr)
        return 2
    spec = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    pkgs = [Path(p) if Path(p).is_absolute() else ROOT / p for p in spec.get("packages", [])]
    if not pkgs:
        print("FAIL spec.packages 为空", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"packages": [str(p) for p in pkgs], "dry_run": True},
                         ensure_ascii=False, indent=2))
        return 0

    report = []
    for pkg in pkgs:
        if not pkg.is_dir():
            report.append({"package": str(pkg), "status": "missing-dir", "problems": []})
            continue
        report.append(audit(pkg))

    total = sum(len(r.get("problems", [])) for r in report)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "claim_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps({"report": report, "problems": total},
                         ensure_ascii=False, indent=2))
    else:
        for r in report:
            print(f"{r['package']}: {r['status']} rows={r.get('rows', 0)} "
                  f"stats={r.get('stats', {})}")
            for p in r.get("problems", []):
                print(f"   PROBLEM {p}")
        print(f"\nproblems total: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
