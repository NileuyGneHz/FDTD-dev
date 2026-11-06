# -*- coding: utf-8 -*-
"""
t15b_hwp_paper_plot.py —— 画 Figure 1b/1c 复现图，并对照"材料模型"的影响
================================================================================

读两个 CSV（都不重新跑仿真）：
    results/t15_hwp_R_paper.csv   论文材料版（Au Drude + SiO2 n=1.45）
    results/t14_hwp_R.csv         旧版（材料库 Palik 数据）

输出：
    results/fig_t15_1c_PCR_paper.png       PCR 对照
    results/fig_t15_1b_Rcr_Rco_paper.png   R_cr / R_co 对照

⚠️ 标签里写 "SiO2" 而不是 "SiO₂"：实测 Microsoft YaHei 缺下标字形 ₂，
   matplotlib 会刷 UserWarning 并把下标渲染成方框。用 ASCII 版本最稳。
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = r"F:\Lumercial_WS\WS\results"
NEW = os.path.join(D, "t15_hwp_R_paper.csv")
OLD = os.path.join(D, "t14_hwp_R.csv")

PAPER_BAND = (805, 1672)
PAPER_PCR = 0.95


def load(path):
    lam, rco, rcr, pcr = [], [], [], []
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            lam.append(float(row["lam_nm"]))
            rco.append(float(row["R_co"]))
            rcr.append(float(row["R_cr"]))
            pcr.append(float(row["PCR"]))
    return tuple(np.array(v) for v in (lam, rco, rcr, pcr))


def main():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    lam, rco, rcr, pcr = load(NEW)
    old = load(OLD) if os.path.exists(OLD) else None

    # ---------------- Figure 1c：PCR ----------------
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    if old is not None:
        ax.plot(old[0], old[3] * 100, "--", color="#95a5a6", lw=1.8,
                label="旧版 PCR（材料库 Palik 数据）")
    ax.plot(lam, pcr * 100, "-", color="#7d3c98", lw=2.4,
            label="本仿真 PCR（论文材料：Au Drude + SiO2 n=1.45）")
    ax.axhline(PAPER_PCR * 100, color="#c0392b", ls="--", lw=1.6,
               label="论文基准 PCR = 95%")
    ax.axvspan(*PAPER_BAND, color="green", alpha=0.07,
               label="论文 PCR>95% 波段 (805-1672 nm)")
    i95 = lam[pcr > PAPER_PCR]
    if len(i95):
        ax.axvspan(i95.min(), i95.max(), color="#f39c12", alpha=0.12,
                   label="本仿真 PCR>95%% 波段 (%.0f-%.0f nm)" % (i95.min(), i95.max()))
    im = int(np.argmax(pcr))
    ax.plot(lam[im], pcr[im] * 100, "o", color="#e67e22", ms=8, zorder=5,
            label="本仿真最高 %.1f%% @ %.0f nm" % (pcr[im] * 100, lam[im]))
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel("偏振转换率 PCR (%)")
    ax.set_title("Figure 1c 复现：偏振转换率 PCR = R_cr/(R_cr+R_co)\n"
                 "材料模型是最大误差来源（金砖 390x165nm 转45 / SiO2 110nm / 金膜 150nm, p=600nm）",
                 fontsize=10.5)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_xlim(lam.min(), lam.max())
    ax.set_ylim(0, 100)
    fig.tight_layout()
    p1 = os.path.join(D, "fig_t15_1c_PCR_paper.png")
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print("图 ->", p1)

    # ---------------- Figure 1b：R_cr / R_co ----------------
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    ax.plot(lam, rcr, "-", color="#c0392b", lw=2.2, label="R_cr 交叉偏振（想要）")
    ax.plot(lam, rco, "-", color="#2471a3", lw=2.2, label="R_co 同偏振（要消掉）")
    if old is not None:
        ax.plot(old[0], old[2], ":", color="#c0392b", lw=1.5, alpha=0.55,
                label="R_cr 旧版（Palik）")
        ax.plot(old[0], old[1], ":", color="#2471a3", lw=1.5, alpha=0.55,
                label="R_co 旧版（Palik）")
    ax.axhline(1.0, color="gray", ls=":", lw=1, label="R = 1 上限")
    ax.axvspan(*PAPER_BAND, color="green", alpha=0.07,
               label="论文 PCR>95% 波段")
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel("反射率")
    ax.set_title("Figure 1b 复现：交叉偏振 vs 同偏振反射\n"
                 "论文：R_cr 几乎 1，R_co 几乎 0", fontsize=10.5)
    ax.legend(loc="center right", fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_xlim(lam.min(), lam.max())
    ax.set_ylim(0, max(1.5, rcr.max() * 1.15))
    fig.tight_layout()
    p2 = os.path.join(D, "fig_t15_1b_Rcr_Rco_paper.png")
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print("图 ->", p2)

    # ---------------- 摘要 ----------------
    m = (lam >= 900) & (lam <= 1600)
    print()
    print("=" * 74)
    print("摘要（论文材料版）")
    print("=" * 74)
    print("  PCR 平均(900-1600nm) = %.4f    论文 >0.95" % pcr[m].mean())
    print("  R_co 平均 = %.4f              论文 ≈0" % rco[m].mean())
    print("  R_cr 平均 = %.4f              论文 ≈1" % rcr[m].mean())
    print("  总反射平均 = %.4f            应 ≤ 1" % (rco[m] + rcr[m]).mean())
    if len(i95):
        print("  PCR>95%% 波段 = %.0f - %.0f nm   论文 805-1672nm"
              % (i95.min(), i95.max()))
    print("  残留问题：个别波长 R_cr > 1（最大 %.3f）→ 见截图说明"
          % rcr.max())
    if old is not None:
        print()
        print("  【材料影响】PCR 平均  旧(Palik)=%.4f  ->  新(论文材料)=%.4f"
              % (old[3][(old[0] >= 900) & (old[0] <= 1600)].mean(), pcr[m].mean()))


if __name__ == "__main__":
    main()
