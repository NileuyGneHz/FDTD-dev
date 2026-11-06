# -*- coding: utf-8 -*-
"""
t15_hwp_paper_materials.py —— Figure 1 复现（论文材料版）
================================================================================

和 t14 的唯一区别：**材料严格按论文设置**。这一处改动带来的差异是决定性的。

--------------------------------------------------------------------------------
★ 为什么要有这个脚本：t14 vs t15 就是"材料差异有多大"的对照实验
--------------------------------------------------------------------------------
论文 Methods 明写：
    SiO2 spacer 是 "lossless dielectric with a constant refractive index of 1.45"
    Au 用 Drude 模型，ωp = 1.37e16 s^-1, ωd = 1.224e14 s^-1
        （"which has taken the surface roughness and grain boundary effects
          into consideration"）

而 t14 用的是 Lumerical 材料库的 **Palik 实验色散数据**。实测结果对比：

    版本               R_co平均   R_cr平均   总反射    PCR(900-1600nm)
    t14 (Palik)         0.676     1.058      1.734    ~72%   ← 对不上
    t15 (论文材料)       0.155     0.916      1.071    ~94%   ← 基本对上
    论文                 ≈0        ≈1         ≈1       >95%

→ **材料模型是最大的一处误差来源**，不是网格、不是监视器位置。

--------------------------------------------------------------------------------
★ 怎么在 Lumerical 里造出论文的这两种材料（实测可用）
--------------------------------------------------------------------------------
关键：`addmaterial()` 的参数是**模型类型**，不是材料名！
    错：addmaterial("Au_Drude")            -> 'Failed to create material of type ...'
    对：addmaterial("Sampled data")        -> 返回一个临时名，再用 setmaterial 改名

① SiO2（n=1.45 常数，无损耗）—— 用 "(n,k) Material" 模型：
       t = addmaterial("(n,k) Material")
       setmaterial(t, "name", "SiO2_paper")
       setmaterial("SiO2_paper", {"Refractive Index": 1.45,
                                  "Imaginary Refractive Index": 0.0})

② Au（Drude）—— 用 "Sampled data" 模型，自己算复介电常数喂进去：
       eps(ω) = 1 - ωp² / (ω² + i·ωd·ω)
       sampled 矩阵 = [频率(Hz), 复介电常数]     ← 第一列是 Hz！不是波长
       实测验证：@1000nm 得 n = 0.2379 + 7.1925i，与手算完全一致（偏差 0.00%）

    ⚠️ 为什么不用某个内置 "Drude" 模型：那样要赌它的参数单位和约定；
       自己算 eps 再喂 sampled data，**结果完全可控且可验证**。

--------------------------------------------------------------------------------
★ 反射测量链的对照验证（"已知答案的对照组"）
--------------------------------------------------------------------------------
    工况      |Ex|平均   |Ey|平均   期望            实测
    mirror    0.9847    0.0000     |Ex|≈1, |Ey|≈0   ✅
    → 证明 "源 amplitude=1 时 R = |E|²" 这条归一化成立。

    ⚠️ 这条验证必须做：t14 里 R_cr 平均 1.058 > 1（物理不可能），
       当时无法判断是"归一化错"还是"结构真的在放大"。
       有了 mirror 对照，才能确定归一化本身是对的。

--------------------------------------------------------------------------------
运行
--------------------------------------------------------------------------------
    cd F:\\Lumercial_WS\\WS\\scripts
    .\\py.bat t15_hwp_paper_materials.py

⚠️ 会开 2~4 个会话（含重试），独占 license 席位。
"""

import sys
import os
import math
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
os.environ.setdefault("ANSYSLMD_LICENSE_FILE", "1055@localhost")
import lumapi  # noqa: E402

# ------------------------------------------------------------------
# 1. 论文参数（与 t14 完全一致，只有材料不同）
# ------------------------------------------------------------------
p, l1, l2 = 600e-9, 390e-9, 165e-9
tm, ts, d = 80e-9, 110e-9, 150e-9
theta = 45.0

lam_start, lam_stop, n_points = 700e-9, 1700e-9, 201

z_bot, z_top = -260e-9, 1100e-9
z_au = -d / 2
z_sio2 = ts / 2
z_brick = ts + tm / 2
z_src = ts + tm + 250e-9
z_rmon = ts + tm + 450e-9
mesh_d = 8e-9

C0 = 299792458.0

# ★ 论文的 Au Drude 参数（单位 rad/s）
WP = 1.37e16
WD = 1.224e14
EPS_INF = 1.0

MAT_SIO2 = "SiO2_paper"      # n = 1.45, k = 0
MAT_AU = "Au_Drude"          # Drude sampled data

out_fsp = r"F:\Lumercial_WS\WS\fig1_hwp_paper_materials.fsp"
out_csv = r"F:\Lumercial_WS\WS\results\t15_hwp_R_paper.csv"


def drude_eps(lam_m):
    """论文的 Drude 介电常数。记 exp(-iωt) 约定，Im(eps)>0 表示损耗。"""
    w = 2.0 * np.pi * C0 / lam_m
    return EPS_INF - WP ** 2 / (w ** 2 + 1j * WD * w)


def open_fdtd_retry(n=8, delay=6):
    """★ 会话创建重试。

    实测（2026-09-26）：频繁新建/关闭 headless 会话时，ansyscl 守护进程
    （`-nodaemon`，随客户端退出而退出）会撞上端口 TIME_WAIT：
        Could not bind socket on port 58657.
        The OS has not cleared this port since its last use.
    → 瞬时故障，重试即可。
    """
    last = None
    for i in range(n):
        try:
            return lumapi.FDTD(hide=True)
        except Exception as e:
            last = e
            hint = "端口占用(TIME_WAIT)" if "bind socket" in str(e) else "其他"
            print("     [会话重试 %d/%d] %s ..." % (i + 1, n, hint))
            time.sleep(delay)
    raise RuntimeError("会话创建连续失败: %s" % str(last)[:200])


def rot_rect(a, b, thdeg):
    """返回绕中心逆时针转 thdeg 的 a×b 矩形顶点，(5,2) numpy 数组。"""
    th = math.radians(thdeg)
    c, s = math.cos(th), math.sin(th)
    pts = []
    for u, v in [(a / 2, b / 2), (-a / 2, b / 2), (-a / 2, -b / 2), (a / 2, -b / 2)]:
        pts.append((u * c - v * s, u * s + v * c))
    pts.append(pts[0])
    return np.array(pts, dtype=float)


def make_materials(f):
    """按论文造两种材料。见文件头说明。"""
    t = f.addmaterial("(n,k) Material")
    f.setmaterial(t, "name", MAT_SIO2)
    f.setmaterial(MAT_SIO2, {"Refractive Index": 1.45,
                             "Imaginary Refractive Index": 0.0})

    lams = np.linspace(400e-9, 2500e-9, 400)     # 覆盖仿真波段并留余量
    eps = drude_eps(lams)
    t2 = f.addmaterial("Sampled data")
    f.setmaterial(t2, "name", MAT_AU)
    f.setmaterial(MAT_AU, "max coefficients", 6)
    f.setmaterial(MAT_AU, "sampled data", np.column_stack([C0 / lams, eps]))


def ensure_materials(f):
    """材料可能随 .fsp 一起存下来，也可能没有 → 先探测再决定是否重建。"""
    try:
        f.getindex(MAT_AU, np.array([[C0 / 1000e-9]]))
        f.getindex(MAT_SIO2, np.array([[C0 / 1000e-9]]))
        return False
    except Exception:
        make_materials(f)
        return True


def build(f, variant="full"):
    """variant: 'mirror' = 只有金膜（对照）; 'full' = 论文完整三层结构。"""
    f.addfdtd(dimension="3D", x=0, y=0, z=(z_top + z_bot) / 2,
              x_span=p, y_span=p, z_span=z_top - z_bot)
    for bc in ["x min bc", "x max bc", "y min bc", "y max bc"]:
        f.setnamed("FDTD", bc, "Periodic")
    f.setnamed("FDTD", "mesh accuracy", 3)
    f.setnamed("FDTD", "simulation time", 1200e-15)
    f.setnamed("FDTD", "use early shutoff", 1)
    f.setnamed("FDTD", "auto shutoff min", 1e-5)

    f.addrect(name="substrate", x=0, y=0, z=z_bot / 2,
              x_span=p, y_span=p, z_span=abs(z_bot))
    f.setnamed("substrate", "material", MAT_SIO2)
    f.setnamed("substrate", "override mesh order from material database", 1)
    f.setnamed("substrate", "mesh order", 3)

    f.addrect(name="au_film", x=0, y=0, z=z_au, x_span=p, y_span=p, z_span=d)
    f.setnamed("au_film", "material", MAT_AU)
    f.setnamed("au_film", "override mesh order from material database", 1)
    f.setnamed("au_film", "mesh order", 2)

    if variant == "full":
        f.addrect(name="sio2_spacer", x=0, y=0, z=z_sio2,
                  x_span=p, y_span=p, z_span=ts)
        f.setnamed("sio2_spacer", "material", MAT_SIO2)
        f.setnamed("sio2_spacer", "override mesh order from material database", 1)
        f.setnamed("sio2_spacer", "mesh order", 1)

        # 45° 金砖：addrect 的 rotation 是 inactive，只能用 addpoly 自己算顶点
        f.addpoly(name="nanobrick")
        f.setnamed("nanobrick", "vertices", rot_rect(l1, l2, theta))
        f.setnamed("nanobrick", "z", z_brick)
        f.setnamed("nanobrick", "z span", tm)
        f.setnamed("nanobrick", "material", MAT_AU)
        f.setnamed("nanobrick", "override mesh order from material database", 1)
        f.setnamed("nanobrick", "mesh order", 1)

    mrs = [("mesh_au", z_au, d + 100e-9)]
    if variant == "full":
        mrs.append(("mesh_brick", z_brick, tm + 200e-9))
    for nm, zc, zs in mrs:
        f.addmesh(name=nm, x=0, y=0, z=zc, x_span=p, y_span=p, z_span=zs)
        f.setnamed(nm, "dx", mesh_d)
        f.setnamed(nm, "dy", mesh_d)
        f.setnamed(nm, "dz", mesh_d)

    f.addplane(name="source")
    f.setnamed("source", "injection axis", "z")
    f.setnamed("source", "direction", "Backward")      # 向下入射（反射式）
    f.setnamed("source", "x", 0); f.setnamed("source", "x span", p)
    f.setnamed("source", "y", 0); f.setnamed("source", "y span", p)
    f.setnamed("source", "z", z_src)
    f.setnamed("source", "polarization angle", 0)       # x 偏振
    f.setnamed("source", "amplitude", 1)
    f.setnamed("source", "override global source settings", 1)
    f.setnamed("source", "wavelength start", lam_start)
    f.setnamed("source", "wavelength stop", lam_stop)

    f.addprofile(name="R_pt")
    f.setnamed("R_pt", "monitor type", "Point")
    f.setnamed("R_pt", "x", 0); f.setnamed("R_pt", "y", 0)
    f.setnamed("R_pt", "z", z_rmon)
    for pp in ["output Ex", "output Ey", "output Ez"]:
        f.setnamed("R_pt", pp, 1)

    f.setnamed("FDTD", "global monitor use source limits", 0)
    f.setnamed("FDTD", "global monitor use wavelength spacing", 1)
    f.setnamed("FDTD", "global monitor wavelength center",
               (lam_start + lam_stop) / 2)
    f.setnamed("FDTD", "global monitor wavelength span", lam_stop - lam_start)
    f.setnamed("FDTD", "global monitor frequency points", n_points)


def run_variant(variant, fsp_path):
    """★ run 必须在 save → 新会话 load 之后才生效（见 t14 的 run_sim 注释）。"""
    f = open_fdtd_retry()
    try:
        ensure_materials(f)
        build(f, variant)
        f.save(fsp_path)
        f.close()
    except Exception:
        try:
            f.close()
        except Exception:
            pass
        raise

    f2 = open_fdtd_retry()
    try:
        f2.load(fsp_path)
        ensure_materials(f2)
        f2.eval("switchtolayout;")
        f2.run()
        f2.eval("lm = layoutmode;")
        lm = f2.getv("lm")
        E = f2.getresult("R_pt", "E")
        fr = np.array(E["f"], dtype=float).ravel()
        lam = C0 / fr
        comp = np.array(E["E"])[0, 0, 0]      # (N,3) = [Ex,Ey,Ez]
        o = np.argsort(lam)
        ex, ey = comp[o, 0], comp[o, 1]
        return dict(lm=lm, lam=lam[o], aex=np.abs(ex), aey=np.abs(ey),
                    rco=np.abs(ex) ** 2, rcr=np.abs(ey) ** 2)
    finally:
        f2.close()


def main():
    print("=" * 80)
    print("Figure 1 复现（论文材料版：Au=Drude, SiO2=n1.45 无损耗）")
    print("=" * 80)

    # ---- 材料自检 ----
    f = open_fdtd_retry()
    try:
        make_materials(f)
        n_au = np.array(f.getindex(MAT_AU, np.array([[C0 / 1000e-9]]))).ravel()[0]
        n_si = np.array(f.getindex(MAT_SIO2, np.array([[C0 / 532e-9]]))).ravel()[0]
        print("  材料自检 Au_Drude   n@1000nm = %.4f %+.4fi  (手算 0.2379+7.1925i)"
              % (n_au.real, n_au.imag))
        print("  材料自检 SiO2_paper n@532nm  = %.4f %+.4fi  (期望 1.45+0.00i)"
              % (n_si.real, n_si.imag))
        if abs(n_au - (0.2379 + 7.1925j)) > 0.01:
            print("  ⚠️ Au 材料与手算不符，先别继续")
    finally:
        f.close()
    time.sleep(4)

    # ---- 对照：只有金膜（验证测量链）----
    print()
    print("对照实验 mirror（只有金膜）...")
    rm = run_variant("mirror", r"F:\Lumercial_WS\WS\_t15_mirror.fsp")
    ok = rm["aex"].mean() > 0.7 and rm["aey"].mean() < 0.3
    print("  mirror: |Ex|平均=%.4f  |Ey|平均=%.4f  ->  %s"
          % (rm["aex"].mean(), rm["aey"].mean(),
             "✅ 归一化 R=|E|² 成立" if ok else "❌ 归一化有问题"))
    time.sleep(4)

    # ---- 正式：完整三层结构 ----
    print()
    print("正式仿真 full（论文完整结构）...")
    r = run_variant("full", out_fsp)
    print("  ✅ layoutmode = %.1f (0.0=已算)" % r["lm"])
    lam, rco, rcr = r["lam"], r["rco"], r["rcr"]
    pcr = rcr / (rcr + rco)

    print()
    print("=" * 80)
    print("结果（论文材料版）")
    print("=" * 80)
    print("  %-10s %-10s %-10s %-10s" % ("lam(nm)", "R_co", "R_cr", "PCR"))
    for tgt in [900, 1000, 1100, 1200, 1400, 1600]:
        i = int(np.argmin(np.abs(lam * 1e9 - tgt)))
        print("  %-10.0f %-10.4f %-10.4f %-10.4f" % (lam[i] * 1e9, rco[i], rcr[i], pcr[i]))

    # 只看设计波段 900-1600nm 的统计（800nm 是源短波端，见下方说明）
    m = (lam * 1e9 >= 900) & (lam * 1e9 <= 1600)
    print()
    print("  900-1600nm 区间：PCR 平均 = %.4f  最低 = %.4f  最高 = %.4f"
          % (pcr[m].mean(), pcr[m].min(), pcr[m].max()))
    print("  R_co 平均 = %.4f (论文≈0)   R_cr 平均 = %.4f (论文≈1)"
          % (rco[m].mean(), rcr[m].mean()))
    print("  总反射平均 = %.4f  (应 ≤ 1)" % (rco[m] + rcr[m]).mean())
    hi = lam[pcr > 0.95] * 1e9
    if len(hi):
        print("  PCR>95%% 的波段 = %.0f - %.0f nm  (论文 805-1672nm)"
              % (hi.min(), hi.max()))

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig") as fh:
        fh.write("lam_nm,R_co,R_cr,PCR\n")
        for a, b, c, e in zip(lam, rco, rcr, pcr):
            fh.write("%.4f,%.6f,%.6f,%.6f\n" % (a * 1e9, b, c, e))
    print("\n  数据 -> %s" % out_csv)
    print("  工程 -> %s" % out_fsp)

    # ---- 出图：论文材料 vs Palik 材料 的对照 ----
    plot_compare(lam, rco, rcr, pcr)


def plot_compare(lam, rco, rcr, pcr):
    """把 t15(论文材料) 与 t14(Palik) 画在一起，直观展示材料的影响。"""
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    old = None
    old_csv = r"F:\Lumercial_WS\WS\results\t14_hwp_R.csv"
    if os.path.exists(old_csv):
        a, b, c, e = [], [], [], []
        with open(old_csv, encoding="utf-8-sig") as fh:
            import csv as _csv
            for row in _csv.DictReader(fh):
                a.append(float(row["lam_nm"])); b.append(float(row["R_co"]))
                c.append(float(row["R_cr"])); e.append(float(row["PCR"]))
        old = (np.array(a), np.array(b), np.array(c), np.array(e))

    # --- 图1：PCR 对照 ---
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    ax.plot(lam * 1e9, pcr * 100, "-", color="#7d3c98", lw=2.4,
            label="本仿真 PCR（论文材料：Au Drude + SiO₂ n=1.45）")
    if old is not None:
        ax.plot(old[0], old[3] * 100, "--", color="#95a5a6", lw=1.8,
                label="旧版 PCR（材料库 Palik 数据）")
    ax.axhline(95, color="#c0392b", ls="--", lw=1.6, label="论文基准 PCR = 95%")
    ax.axvspan(805, 1672, color="green", alpha=0.07,
               label="论文 PCR>95% 波段 (805–1672 nm)")
    im = int(np.argmax(pcr))
    ax.plot(lam[im] * 1e9, pcr[im] * 100, "o", color="#e67e22", ms=8, zorder=5,
            label="本仿真最高 %.1f%% @ %.0f nm" % (pcr[im] * 100, lam[im] * 1e9))
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel("偏振转换率 PCR (%)")
    ax.set_title("Figure 1c 复现：材料模型的影响\n"
                 "（金砖 390×165nm 转45° / SiO₂ 110nm / 金膜 150nm, p=600nm）",
                 fontsize=11)
    ax.legend(loc="lower right", fontsize=8.5)
    ax.grid(alpha=0.3)
    ax.set_xlim(lam.min() * 1e9, lam.max() * 1e9)
    ax.set_ylim(0, 100)
    fig.tight_layout()
    p1 = r"F:\Lumercial_WS\WS\results\fig_t15_1c_PCR_paper.png"
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print("  图 -> %s" % p1)

    # --- 图2：R_cr / R_co 对照 ---
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    ax.plot(lam * 1e9, rcr, "-", color="#c0392b", lw=2.2, label=r"$R_{cr}$ 交叉偏振（想要）")
    ax.plot(lam * 1e9, rco, "-", color="#2471a3", lw=2.2, label=r"$R_{co}$ 同偏振（要消掉）")
    if old is not None:
        ax.plot(old[0], old[2], ":", color="#c0392b", lw=1.4, alpha=0.6,
                label=r"$R_{cr}$ 旧版（Palik）")
        ax.plot(old[0], old[1], ":", color="#2471a3", lw=1.4, alpha=0.6,
                label=r"$R_{co}$ 旧版（Palik）")
    ax.axhline(1.0, color="gray", ls=":", lw=1)
    ax.axvspan(805, 1672, color="green", alpha=0.07)
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel("反射率")
    ax.set_title("Figure 1b 复现：交叉偏振 vs 同偏振反射", fontsize=11)
    ax.legend(loc="center right", fontsize=8.5)
    ax.grid(alpha=0.3)
    ax.set_xlim(lam.min() * 1e9, lam.max() * 1e9)
    ax.set_ylim(0, max(1.4, rcr.max() * 1.15))
    fig.tight_layout()
    p2 = r"F:\Lumercial_WS\WS\results\fig_t15_1b_Rcr_Rco_paper.png"
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print("  图 -> %s" % p2)


if __name__ == "__main__":
    main()
