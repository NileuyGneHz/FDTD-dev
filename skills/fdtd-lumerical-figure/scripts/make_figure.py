#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn simulation data into figures. No lumapi, no licence, no engine.

Before this existed, P02/P04/P05/P06 each re-wrote plotting code, so every figure had its own
conventions and none of them could be re-generated from a ledger.  Six kinds cover what the
reproductions actually need:

    stack     layer diagram from a spec's objects[]           (input: spec.json)
    spectra   R/T/A vs wavelength, peak annotated             (input: csv)
    phase     phase (and phase difference) vs wavelength      (input: csv)
    field     |E|^2 or Re(E) map from an .npz dump            (input: npz)
    fom       objective vs iteration                          (input: csv)
    compare   two spectra on one axis                         (input: csv,csv)

Every number printed on a figure is computed from the data being plotted (EXP-45): if the
annotation and the input disagree, the figure is wrong, not the ledger.

    python make_figure.py --kind spectra --input run/point_00.csv --out fig.png [--json] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import matplotlib
matplotlib.use("Agg")                       # headless: never require a display
import matplotlib.pyplot as plt             # noqa: E402
import numpy as np                          # noqa: E402

KINDS = ("stack", "spectra", "phase", "field", "fom", "compare")


class FigureError(Exception):
    """Bad input: say which column/key is missing, do not draw an empty figure."""


def read_csv(path: Path) -> dict:
    if not path.is_file():
        raise FigureError("input not found: %s" % path)
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise FigureError("empty csv: %s" % path)
    cols = {}
    for name in rows[0]:
        try:
            cols[name] = np.array([float(r[name]) for r in rows])
        except (TypeError, ValueError):
            cols[name] = np.array([r[name] for r in rows])
    return cols


def need(cols: dict, *names) -> None:
    missing = [n for n in names if n not in cols]
    if missing:
        raise FigureError("缺少列 %s；实际列 = %s"
                          % ("/".join(missing), ", ".join(sorted(cols)) or "(空)"))


# --------------------------------------------------------------------------- kinds
def fig_stack(ax, payload: dict) -> dict:
    objs = payload.get("objects") or []
    if not objs:
        raise FigureError("spec 里没有 objects[]，无法画层图")
    lo, hi = [], []
    labels = []
    for o in objs:
        span = o.get("span") or [None, None, None]
        centre = o.get("center") or [0, 0, 0]
        try:
            z0 = float(eval(str(centre[2]), {}, payload.get("parameters") or {}))
            dz = abs(float(eval(str(span[2]), {}, payload.get("parameters") or {})))
        except Exception:                       # noqa: BLE001 - 2D objects legitimately lack z
            continue
        ax.add_patch(plt.Rectangle((0, z0 - dz / 2), 1, dz,
                                   facecolor="#9ecae1", edgecolor="k", lw=0.8))
        labels.append((o["id"], z0))
        # 必须记录真实上下界：从 0 起算会把整段负 z 的堆栈画成「没有层」（首版就是这个错）
        lo.append(z0 - dz / 2)
        hi.append(z0 + dz / 2)
    if not labels:
        raise FigureError("objects[] 里没有带 z span 的对象，无法画侧视层图")
    for name, z in labels:
        ax.text(1.02, z, name, va="center", fontsize=7)
    ax.set_xlim(0, 1)
    pad = (max(hi) - min(lo)) * 0.08 or 1e-9
    ax.set_ylim(min(lo) - pad, max(hi) + pad)
    ax.set_yticks([])
    ax.set_ylabel("z (m)")
    ax.set_title("layer stack")
    return {"layers": len(labels), "z_min_m": min(lo), "z_max_m": max(hi),
            "skipped_no_z": len(objs) - len(labels)}


def fig_spectra(ax, cols: dict) -> dict:
    need(cols, "lam_um")
    lam = cols["lam_um"]
    plotted = []
    meta = {}
    for key, style in (("R", dict(color="#c0392b", ls="-")),
                       ("T", dict(color="#27ae60", ls="--")),
                       ("A", dict(color="#2c3e50", ls="-."))):
        if key in cols:
            ax.plot(lam, cols[key], lw=1.2, label=key, **style)
            plotted.append(key)
    if not plotted:
        raise FigureError("csv 里没有 R/T/A 任何一列；实际列 = %s" % ", ".join(sorted(cols)))
    main = "A" if "A" in cols else plotted[0]
    arr = cols[main]
    i = int(np.argmax(arr))
    # 图上的数字必须来自被画的数据本身（EXP-45）
    ax.plot([lam[i]], [arr[i]], "o", ms=4, color="k")
    ax.annotate("peak %s=%.4f @ %.3f um" % (main, arr[i], lam[i]),
                (lam[i], arr[i]), textcoords="offset points", xytext=(6, -12), fontsize=8)
    meta.update({"main": main, "peak_value": float(arr[i]), "peak_lam_um": float(lam[i])})
    ax.set_xlabel("wavelength (um)")
    ax.set_ylabel("R / T / A")
    ax.legend(fontsize=8)
    ax.set_title("spectra (%s)" % ", ".join(plotted))
    return meta


def fig_phase(ax, cols: dict) -> dict:
    need(cols, "lam_um")
    lam = cols["lam_um"]
    meta = {}
    if "dphi_deg" in cols:
        ax.plot(lam, cols["dphi_deg"], lw=1.2, color="#8e44ad")
        i = int(np.argmax(np.abs(cols["dphi_deg"])))
        meta["max_abs_dphi_deg"] = float(cols["dphi_deg"][i])
        ax.set_ylabel("phi_x - phi_y (deg)")
    elif "phi_x_deg" in cols and "phi_y_deg" in cols:
        ax.plot(lam, cols["phi_x_deg"], lw=1.2, label="phi_x")
        ax.plot(lam, cols["phi_y_deg"], lw=1.2, label="phi_y")
        d = cols["phi_x_deg"] - cols["phi_y_deg"]
        meta["max_abs_dphi_deg"] = float(np.max(np.abs(d)))
        ax.set_ylabel("phase (deg)")
        ax.legend(fontsize=8)
    else:
        raise FigureError("phase 需要 dphi_deg，或 phi_x_deg + phi_y_deg；实际列 = %s"
                          % ", ".join(sorted(cols)))
    ax.set_xlabel("wavelength (um)")
    ax.set_title("phase")
    return meta


def fig_field(ax, npz: dict) -> dict:
    keys = [k for k in npz if npz[k].ndim == 2]
    if not keys:
        raise FigureError("npz 里没有二维数组；实际键 = %s" % ", ".join(npz))
    key = "E" if "E" in keys else keys[0]
    arr = np.asarray(npz[key])
    if arr.ndim == 3:                           # (nx,ny,3) -> |E|^2
        arr = np.sum(np.abs(arr) ** 2, axis=-1)
    im = ax.imshow(np.abs(arr).T, origin="lower", cmap="inferno", aspect="auto")
    plt.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("|%s| (%s)" % (key, "x".join(str(n) for n in arr.shape)))
    return {"key": key, "shape": list(arr.shape), "max": float(np.abs(arr).max())}


def fig_fom(ax, cols: dict) -> dict:
    need(cols, "iteration", "fom")
    ax.plot(cols["iteration"], cols["fom"], "o-", lw=1.2, color="#16a085")
    best = int(np.argmax(cols["fom"]))
    ax.plot([cols["iteration"][best]], [cols["fom"][best]], "r*", ms=10)
    ax.set_xlabel("iteration")
    ax.set_ylabel("FOM")
    ax.set_title("convergence")
    return {"best_iteration": float(cols["iteration"][best]),
            "best_fom": float(cols["fom"][best])}


def fig_compare(ax, cols_a: dict, cols_b: dict, labels) -> dict:
    need(cols_a, "lam_um")
    need(cols_b, "lam_um")
    key = "A" if "A" in cols_a else ("R" if "R" in cols_a else "T")
    if key not in cols_b:
        raise FigureError("第二个文件缺 %s 列；实际列 = %s" % (key, ", ".join(sorted(cols_b))))
    ax.plot(cols_a["lam_um"], cols_a[key], lw=1.2, label=labels[0])
    ax.plot(cols_b["lam_um"], cols_b[key], lw=1.2, ls="--", label=labels[1])
    d = float(abs(np.max(cols_a[key]) - np.max(cols_b[key])))
    ax.set_xlabel("wavelength (um)")
    ax.set_ylabel(key)
    ax.legend(fontsize=8)
    ax.set_title("compare %s (peak delta=%.4f)" % (key, d))
    return {"quantity": key, "peak_delta": d}


# --------------------------------------------------------------------------- driver
def build(kind: str, inputs, out: Path, labels, dpi: int = 160) -> dict:
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    meta = {}
    try:
        if kind == "stack":
            payload = json.loads(Path(inputs[0]).read_text(encoding="utf-8"))
            meta = fig_stack(ax, payload)
        elif kind == "spectra":
            meta = fig_spectra(ax, read_csv(Path(inputs[0])))
        elif kind == "phase":
            meta = fig_phase(ax, read_csv(Path(inputs[0])))
        elif kind == "field":
            meta = fig_field(ax, dict(np.load(Path(inputs[0]), allow_pickle=False)))
        elif kind == "fom":
            meta = fig_fom(ax, read_csv(Path(inputs[0])))
        elif kind == "compare":
            if len(inputs) < 2:
                raise FigureError("compare 需要两个输入文件")
            meta = fig_compare(ax, read_csv(Path(inputs[0])), read_csv(Path(inputs[1])), labels)
        else:
            raise FigureError("unknown kind %r（可选 %s）" % (kind, ", ".join(KINDS)))
        fig.tight_layout()
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi)
    finally:
        plt.close(fig)
    meta.update({"kind": kind, "out": str(out),
                 "bytes": out.stat().st_size if out.is_file() else 0})
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Data -> figure, no engine")
    ap.add_argument("--kind", required=True, choices=KINDS)
    ap.add_argument("--input", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", nargs="*", default=["A", "B"])
    ap.add_argument("--dpi", type=int, default=160)
    ap.add_argument("--dry-run", action="store_true", help="validate inputs and columns only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.dry_run:
        info = {"kind": args.kind, "inputs": args.input, "out": args.out, "dry_run": True}
        # still validate the schema so `--dry-run` is a real pre-flight, not a no-op
        try:
            if args.kind in ("spectra", "phase", "fom", "compare"):
                need(read_csv(Path(args.input[0])), "lam_um" if args.kind != "fom" else "iteration")
        except FigureError as e:
            print("ERROR %s" % e)
            return 2
        print(json.dumps(info, ensure_ascii=False) if args.json
              else "\n".join("%-10s %s" % (k, v) for k, v in info.items()))
        return 0

    try:
        meta = build(args.kind, args.input, Path(args.out), args.label, args.dpi)
    except FigureError as e:
        print("ERROR %s" % e)
        return 2
    if meta["bytes"] <= 0:
        print("ERROR figure was not written: %s" % args.out)
        return 1
    print(json.dumps(meta, ensure_ascii=False) if args.json
          else "\n".join("%-16s %s" % (k, v) for k, v in meta.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
