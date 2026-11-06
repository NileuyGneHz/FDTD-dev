#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
t14b_hwp_plot.py —— 从 t14 的结果画 Figure 1b/1c 复现图

读 results/t14_hwp_R.csv，画两张图：
    fig1b_hwp_Rcr_Rco.png   交叉偏振 R_cr 与同偏振 R_co vs 波长
    fig1c_hwp_PCR.png       偏振转换率 PCR vs 波长

对照论文：PCR 在 805-1672 nm 保持 > 95%。
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = r"F:\Lumercial_WS\WS\results\t14_hwp_R.csv"
OUTDIR = r"F:\Lumercial_WS\WS\results"

# 论文的基准线（来自论文正文）
PAPER_BAND = (805, 1672)     # PCR > 95% 的波段
PAPER_PCR = 0.95


def load():
    lam, rco, rcr, pcr = [], [], [], []
    with open(CSV, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            lam.append(float(row["lam_nm"]))
            rco.append(float(row["R_co"]))
            rcr.append(float(row["R_cr"]))
            pcr.append(float(row["PCR"]))
    return (np.array(lam), np.array(rco), np.array(rcr), np.array(pcr))


def main():
    if not os.path.exists(CSV):
        print("找不到 %s，请先跑 t14_hwp_unitcell.py" % CSV)
        return

    lam, rco, rcr, pcr = load()
    os.makedirs(OUTDIR, exist_ok=True)

    # 中文字体
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    # ---------------- Figure 1b ----------------
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.plot(lam, rcr, "-", color="#c0392b", lw=2, label=r"$R_{cr}$ 交叉偏振（想要的）")
    ax.plot(lam, rco, "-", color="#2471a3", lw=2, label=r"$R_{co}$ 同偏振（要消掉的）")
    ax.axhline(1.0, color="gray", ls=":", lw=1)
    ax.axvspan(*PAPER_BAND, color="green", alpha=0.07,
               label="论文 PCR>95%% 波段 (%d-%d nm)" % PAPER_BAND)
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel("反射率")
    ax.set_title("复现 Figure 1b：交叉偏振 vs 同偏振反射\n"
                 "（Au 金砖 390x165nm 转45° / SiO₂ 110nm / Au 膜 150nm，p=600nm）",
                 fontsize=11)
    ax.legend(loc="center right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlim(lam.min(), lam.max())
    ax.set_ylim(0, max(1.6, rcr.max() * 1.1))
    fig.tight_layout()
    p1 = os.path.join(OUTDIR, "fig_t14_1b_Rcr_Rco.png")
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print("已存 ->", p1)

    # ---------------- Figure 1c ----------------
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.plot(lam, pcr * 100, "-", color="#7d3c98", lw=2.2, label="本仿真 PCR")
    ax.axhline(PAPER_PCR * 100, color="#c0392b", ls="--", lw=1.6,
               label="论文基准 PCR = 95%%")
    ax.axvspan(*PAPER_BAND, color="green", alpha=0.07,
               label="论文 PCR>95%% 波段 (%d-%d nm)" % PAPER_BAND)
    imax = int(np.argmax(pcr))
    ax.plot(lam[imax], pcr[imax] * 100, "o", color="#e67e22", ms=8, zorder=5,
            label="本仿真最高 %.1f%% @ %.0f nm" % (pcr[imax] * 100, lam[imax]))
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel("偏振转换率 PCR (%)")
    ax.set_title("复现 Figure 1c：偏振转换率 PCR = R_cr/(R_cr+R_co)", fontsize=11)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlim(lam.min(), lam.max())
    ax.set_ylim(0, 100)
    fig.tight_layout()
    p2 = os.path.join(OUTDIR, "fig_t14_1c_PCR.png")
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print("已存 ->", p2)

    # ---------------- 诊断摘要 ----------------
    print()
    print("=" * 72)
    print("与论文的差距诊断")
    print("=" * 72)
    print("  本仿真 PCR 平均 = %.1f%%   论文 = >95%%" % (pcr.mean() * 100))
    print("  本仿真 PCR 最高 = %.1f%% @ %.0f nm" % (pcr.max() * 100, lam[np.argmax(pcr)]))
    print("  R_cr 平均 = %.3f  (论文≈1)" % rcr.mean())
    print("  R_co 平均 = %.3f  (论文≈0)" % rco.mean())
    print()
    print("  ⚠️ R_cr 出现 >1 的值 → 归一化基准有问题（见 t14 脚本注释）")
    print("     优先排查顺序：材料模型(Drude vs Palik) > 归一化 > 网格")


if __name__ == "__main__":
    main()
