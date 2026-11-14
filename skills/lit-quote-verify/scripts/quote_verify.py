#!/usr/bin/env python3
"""quote_verify.py — 验证论文包 README §2 的每条引用块能否在 PDF 内找到。

    python skills/lit-quote-verify/scripts/quote_verify.py --config <spec.json> --out <dir>
    python skills/lit-quote-verify/scripts/quote_verify.py --config <spec.json> --dry-run

spec.json:
    {"packages": ["cases/P03_...", "cases/P04_..."], "head_chars": 70}

对每个包：
    1. 取 paper/*.pdf 的全文（空白归一 + 跨行连字符归一）
    2. 从 README 的 §2 段提取所有 `> ...` 引用块
    3. 跳过元评论（以 ** 开头、或含「硬要求」「全部为」「注：」）
    4. 逐条检查：先整句，再逐步截短到 30 字符
    5. 无 PDF 的包标记 skipped（不算失败，但要报告）

退出码：0 全部命中（或全部 skipped）/ 1 有 missed / 2 参数错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

META_PREFIXES = ("**", "全部为", "硬要求", "注：", "⚠️", "下面")


def norm(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"-\s+", "-", s)
    return " ".join(s.split())


def norm_loose(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def pdf_text(pkg: Path) -> str | None:
    papers = sorted((pkg / "paper").glob("*.pdf"))
    if not papers:
        return None
    try:
        from pypdf import PdfReader
    except ImportError:
        print("FAIL pypdf 不可用；请把 pypdf 装到 PYTHONPATH 或改用 --head_chars 0",
              file=sys.stderr)
        raise
    reader = PdfReader(str(papers[0]))
    return norm(" ".join((p.extract_text() or "") for p in reader.pages))


def quotes_of(readme: Path) -> list[str]:
    text = readme.read_text(encoding="utf-8-sig")
    sec = re.search(r"##\s*§2.*?(?=\n##\s*§3|\Z)", text, re.S)
    if not sec:
        return []
    out = []
    for line in sec.group(0).splitlines():
        m = re.match(r"^\s*>\s*(.+)$", line)
        if not m:
            continue
        q = m.group(1).strip()
        if len(q) < 40 or q.startswith(META_PREFIXES):
            continue
        out.append(q)
    return out


def verify(pkg: Path, head_chars: int) -> dict:
    readme = pkg / "README.md"
    if not readme.is_file():
        return {"package": pkg.name, "status": "no-readme", "results": []}
    qs = quotes_of(readme)
    text = pdf_text(pkg)
    if text is None:
        return {"package": pkg.name, "status": "no-pdf", "quotes": len(qs), "results": []}

    loose = norm_loose(text)
    results = []
    for q in qs:
        found_at = None
        for n in (len(q), head_chars, 60, 50, 40, 30):
            if n <= 0 or n > len(q):
                continue
            probe = q[:n]
            if norm(probe) in text or norm_loose(probe) in loose:
                found_at = n
                break
        results.append({"quote": q[:100], "found": found_at is not None,
                        "matched_chars": found_at})
    missed = sum(1 for r in results if not r["found"])
    return {"package": pkg.name, "status": "ok" if not missed else "missed",
            "quotes": len(qs), "missed": missed, "results": results}


def main() -> int:
    ap = argparse.ArgumentParser(description="verify README quotes against PDFs")
    ap.add_argument("--config", required=True, help="spec JSON")
    ap.add_argument("--out", required=True, help="report output dir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"FAIL config 不存在: {cfg_path}", file=sys.stderr)
        return 2
    spec = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    pkgs = [Path(p) if Path(p).is_absolute() else ROOT / p for p in spec.get("packages", [])]
    head_chars = int(spec.get("head_chars", 70))
    if not pkgs:
        print("FAIL spec.packages 为空", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"packages": [str(p) for p in pkgs],
                          "head_chars": head_chars, "dry_run": True},
                         ensure_ascii=False, indent=2))
        return 0

    report = []
    for pkg in pkgs:
        if not pkg.is_dir():
            report.append({"package": str(pkg), "status": "missing-dir", "results": []})
            continue
        report.append(verify(pkg, head_chars))

    total_missed = sum(r.get("missed", 0) for r in report)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "quote_verify.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps({"report": report, "missed": total_missed},
                         ensure_ascii=False, indent=2))
    else:
        for r in report:
            st = r["status"]
            n = r.get("quotes", 0)
            m = r.get("missed", 0)
            print(f"{r['package']}: {st} ({n} quotes, {m} missed)")
            for item in r.get("results", []):
                if not item["found"]:
                    print(f"   MISS {item['quote'][:80]}")
        print(f"\nmissed total: {total_missed}")
    return 1 if total_missed else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
