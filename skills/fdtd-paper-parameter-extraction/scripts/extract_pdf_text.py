#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""extract_pdf_text.py — dump a paper PDF to text with page markers, and tell you whether it is a scan.

Why: you cannot extract simulation parameters from a paper you have not read, and you cannot trust
your own reading unless you can jump back to the exact page a number came from.

Usage
-----
    python extract_pdf_text.py paper.pdf
    python extract_pdf_text.py paper.pdf --out paper.txt
    python extract_pdf_text.py paper.pdf --images renders/

Output
------
- `<pdf>.txt` next to the PDF (or --out): one `===== PAGE n ===== (chars=N)` block per page.
- A summary table printed to stdout: page, character count, verdict (`text` / `SCAN?`).
  A page with fewer than ~200 characters of text has no text layer — render it and read it visually.

Requires PyMuPDF. On this machine the managed venv already has it:
    C:\\Users\\saber\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe
"""

from __future__ import annotations

import argparse
import os
import sys

SCAN_THRESHOLD = 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=None)
    ap.add_argument("--images", default=None, help="directory to render pages into (150 dpi)")
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()

    try:
        import pymupdf
    except ImportError:
        sys.stderr.write(
            "PyMuPDF is missing. Use the managed venv:\n"
            r"  C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe" + "\n"
        )
        return 2

    doc = pymupdf.open(args.pdf)
    parts = ["# %s | pages=%d" % (os.path.basename(args.pdf), doc.page_count)]
    rows = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        n = len(text.strip())
        parts.append("\n===== PAGE %d ===== (chars=%d)" % (i + 1, n))
        parts.append(text)
        rows.append((i + 1, n))
        if args.images:
            os.makedirs(args.images, exist_ok=True)
            page.get_pixmap(dpi=args.dpi).save(
                os.path.join(args.images, "p%02d.png" % (i + 1)))

    out = args.out or os.path.splitext(args.pdf)[0] + ".txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))

    print("%-6s %-8s %s" % ("page", "chars", "verdict"))
    for pg, n in rows:
        verdict = "SCAN? -> render and read visually" if n < SCAN_THRESHOLD else "text"
        print("%-6d %-8d %s" % (pg, n, verdict))
    print("\nwrote: %s" % out)
    if args.images:
        print("images: %s" % args.images)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
