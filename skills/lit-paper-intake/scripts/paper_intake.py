#!/usr/bin/env python3
"""lit-paper-intake.py — 为一个新论文包建骨架并写 config/paper.json。

    python skills/lit-paper-intake/scripts/paper_intake.py --config <spec.json> --out <dir>
    python skills/lit-paper-intake/scripts/paper_intake.py --config <spec.json> --dry-run

spec.json 字段见 references/spec.md。核心字段：
    id / slug / track / title / doi / pdf{...}

行为：
    1. 校验 id / slug / track
    2. 在 cases/ 下建 P0N_*/{paper,config,notes,results,model}
    3. 写 config/paper.json（含 pdf 段）
    4. 若 spec 给了 pdf.source_path 且文件存在，复制进 paper/（改名为 pdf.file）
    5. 若 spec 给了 pdf.missing_reason，则不复制，保留 .gitkeep

退出码：0 成功 / 1 可诊断失败 / 2 参数错误
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "cases"
SLUG_RE = re.compile(r"^P\d{2}_[A-Za-z0-9]+_[A-Za-z]+\d{4}$")
TRACKS = {"A_review", "B_training", "C_hybrid"}
SUBDIRS = ["paper", "config", "notes", "results", "model"]


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="create a paper package skeleton")
    ap.add_argument("--config", required=True, help="intake spec JSON")
    ap.add_argument("--out", required=True, help="报告输出目录")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"FAIL config 不存在: {cfg_path}", file=sys.stderr)
        return 2
    spec = json.loads(cfg_path.read_text(encoding="utf-8-sig"))

    pid = (spec.get("id") or "").strip()
    slug = (spec.get("slug") or "").strip()
    track = (spec.get("track") or "").strip()
    if not pid or not slug:
        return fail("spec 必须有 id 与 slug")
    if not SLUG_RE.match(slug):
        return fail(f"slug={slug!r} 不合法（应为 P01_ShortName_Author2024）")
    if not slug.startswith(pid + "_"):
        return fail(f"slug 必须以 {pid}_ 开头")
    if track not in TRACKS:
        return fail(f"track={track!r} 非法（应为 {'/'.join(sorted(TRACKS))}）")
    for key in ("title", "doi"):
        if not spec.get(key):
            return fail(f"spec 缺必填字段: {key}")
    pdf = spec.get("pdf") or {}
    if "present" not in pdf:
        return fail("spec.pdf 必须有 present")
    if not pdf["present"] and not pdf.get("missing_reason"):
        return fail("pdf.present=false 时必须给 pdf.missing_reason")

    pkg = CASES / slug
    if pkg.exists():
        return fail(f"目标已存在: {pkg}（不覆盖）")

    src = pdf.get("source_path")
    src_path = Path(src) if src else None
    copy_ok = bool(src_path and src_path.is_file())
    if pdf["present"] and not copy_ok:
        return fail(f"pdf.present=true 但 source_path 不存在: {src}")

    plan = {
        "package": str(pkg),
        "subdirs": SUBDIRS,
        "paper_json": str(pkg / "config" / "paper.json"),
        "copy_pdf": (str(src_path) + " -> " + str(pkg / "paper" / (pdf.get("file") or "")))
                    if copy_ok else None,
    }
    if args.dry_run:
        print(json.dumps({**plan, "dry_run": True}, ensure_ascii=False, indent=2))
        return 0

    for sub in SUBDIRS:
        d = pkg / sub
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    if copy_ok:
        dest = pkg / "paper" / (pdf.get("file") or src_path.name)
        shutil.copy2(src_path, dest)
        (pkg / "paper" / ".gitkeep").unlink(missing_ok=True)
        plan["copied_bytes"] = dest.stat().st_size

    record = dict(spec)
    record.pop("pdf", None)
    record["pdf"] = {k: v for k, v in pdf.items() if k != "source_path"}
    (pkg / "config" / "paper.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "intake.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps({**plan, "created": True}, ensure_ascii=False, indent=2))
    else:
        print(f"created {pkg}")
        print("next: fill README.md §0-§2, then run lit-quote-verify")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
