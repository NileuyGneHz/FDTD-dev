#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
t14_hwp_unitcell.py —— 复现论文 Figure 1 的反射式半波片单元胞
================================================================================

论文：Ding et al., "Broadband High-Efficiency Half-Wave Plate: A Supercell-Based
      Plasmonic Metasurface Approach", ACS Nano 2015, 9(4), 4111-4119.
      DOI: 10.1021/acsnano.5b00218        （导师给的那篇）

本脚本做复现的 L1 + L2 两级：
    L1  建出 Figure 1a 的三层结构，跑通一次仿真
    L2  拿到 R_cr / R_co / PCR 曲线（= Figure 1b + 1c）

--------------------------------------------------------------------------------
结构（论文 Figure 1a，反射式）
--------------------------------------------------------------------------------
        z ↑
          │   反射监视器 R                ← 记录 R_cr / R_co
          │  ─────────────
          │     空气
          │   平面波源（沿 -z 向下入射，x 偏振）
          │  ─────────────
    z=150 │   ┌────────┐                 ← 金纳米砖  l1×l2 = 390×165 nm
    z=110 │   └────────┘  厚 tm = 80 nm     绕 z 轴转 45°
    z=110 │   ▓▓▓▓▓▓▓▓  SiO2 间隔层  ts = 110 nm
    z=0   │   ████████  金膜底板     d  = 150 nm
          │   ▓▓▓▓▓▓▓▓  玻璃基底（往下延伸）
          ▼
          x、y 方向周期边界（p = 600 nm）

--------------------------------------------------------------------------------
运行
--------------------------------------------------------------------------------
    cd F:\\Lumercial_WS\\WS\\scripts
    .\\py.bat t14_hwp_unitcell.py

⚠️ 会独占一个 license 席位。
"""

import os
import sys
import math

import numpy as np

# ------------------------------------------------------------------
# 0. 环境
# ------------------------------------------------------------------
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
os.environ.setdefault("ANSYSLMD_LICENSE_FILE", "1055@localhost")

import lumapi  # noqa: E402

# ------------------------------------------------------------------
# 1. 论文参数（变量名照抄论文符号，方便和研究生对齐；单位：米）
# ------------------------------------------------------------------
p        = 600e-9     # 单胞周期（x、y 同）
l1       = 390e-9     # 金砖长边
l2       = 165e-9     # 金砖短边
tm       =  80e-9     # 金砖厚度
ts       = 110e-9     # SiO2 间隔层厚度（论文说是扫参得到的！）
d        = 150e-9     # 金膜厚度（不透光 → 反射式）
theta    =  45.0      # 金砖旋转角（逆时针，相对 +x 轴）

# 论文关注近红外；宽带窗口是 805-1672 nm。取 700-1700 nm 把它包进来。
lam_start = 700e-9
lam_stop  = 1700e-9
n_points  = 201       # 步长 5 nm

# z 布局
z_bot    = -260e-9                 # 仿真区下沿
z_top    =  1100e-9                # 仿真区上沿
z_au     = -d / 2                  # 金膜中心  = -75 nm
z_sio2   =  ts / 2                 # SiO2 中心  =  55 nm
z_brick  =  ts + tm / 2            # 金砖中心   = 150 nm
z_src    =  ts + tm + 250e-9       # 源（结构上方，向下入射）
z_rmon   =  ts + tm + 450e-9       # 反射监视器（源上方，避开近场）

mesh_d   = 8e-9                    # 金属区局部网格

mat_au   = "Au (Gold) - Palik"     # ⚠️ 论文用 Drude 模型，见文件末说明
mat_sio2 = "SiO2 (Glass) - Palik"  # ⚠️ 论文简化为常数 n = 1.45

out_fsp  = r"F:\Lumercial_WS\WS\fig1_hwp_unitcell.fsp"
out_csv  = r"F:\Lumercial_WS\WS\results\t14_hwp_R.csv"

C0 = 299792458.0


# ------------------------------------------------------------------
# 2. ★ 技巧一：用 addpoly 建 45° 旋转的矩形
# ------------------------------------------------------------------
def rotated_rect_vertices(l1_, l2_, theta_deg):
    """把 l1_×l2_ 的矩形绕中心逆时针转 theta_deg，返回 (5, 2) 顶点矩阵。

    为什么不用 addrect + 旋转？
        实测：`addrect` 属性表里**确实有** `rotation 1/2/3`，
        但读取返回 0.0，一旦 set 就报
            "in setnamed, the requested property 'rotation 1' is inactive"
        在 v251 里**对 Rectangle 和 structure group 都是 inactive**。
        → 「给矩形设旋转角」这条最直觉的路走不通。
        唯一干净的办法：addpoly，自己算旋转后的 4 个顶点。

    ⚠️ vertices 的数据格式有坑（实测）：
        Python list            -> ❌ "wrong type ... Expected type is: Matrix"
        numpy 一维 (10,)       -> ❌ "not acceptable ... incorrect dimensions"
        numpy 二维 (5, 2)      -> ✅ 成功
    """
    th = math.radians(theta_deg)
    c, s = math.cos(th), math.sin(th)
    pts = []
    for u, v in [(+l1_ / 2, +l2_ / 2), (-l1_ / 2, +l2_ / 2),
                 (-l1_ / 2, -l2_ / 2), (+l1_ / 2, -l2_ / 2)]:
        pts.append((u * c - v * s, u * s + v * c))
    pts.append(pts[0])                 # 闭合
    return np.array(pts, dtype=float)


# ------------------------------------------------------------------
# 3. 建模
# ------------------------------------------------------------------
def build(fdtd, l1_=l1, l2_=l2, tm_=tm, ts_=ts, d_=d, theta_=theta):
    """建出论文 Figure 1a 的三层结构 + 源 + 监视器。"""

    # ---- 玻璃基底（往下伸远，模拟半无限；同时充当 SiO2 间隔层的材料）----
    fdtd.addrect(name="substrate", x=0, y=0, z=z_bot / 2,
                 x_span=p, y_span=p, z_span=abs(z_bot))
    fdtd.setnamed("substrate", "material", mat_sio2)
    fdtd.setnamed("substrate", "override mesh order from material database", 1)
    fdtd.setnamed("substrate", "mesh order", 3)

    # ---- 底层金膜（功能层：与顶层金砖构成 FP 腔）----
    fdtd.addrect(name="au_film", x=0, y=0, z=-d_ / 2,
                 x_span=p, y_span=p, z_span=d_)
    fdtd.setnamed("au_film", "material", mat_au)
    fdtd.setnamed("au_film", "override mesh order from material database", 1)
    fdtd.setnamed("au_film", "mesh order", 2)

    # ---- 中间 SiO2 间隔层（= FP 腔腔长，论文靠扫参定下来）----
    fdtd.addrect(name="sio2_spacer", x=0, y=0, z=ts_ / 2,
                 x_span=p, y_span=p, z_span=ts_)
    fdtd.setnamed("sio2_spacer", "material", mat_sio2)
    fdtd.setnamed("sio2_spacer", "override mesh order from material database", 1)
    fdtd.setnamed("sio2_spacer", "mesh order", 1)

    # ---- ★ 顶层金纳米砖，绕 z 转 45°（addpoly）----
    verts = rotated_rect_vertices(l1_, l2_, theta_)
    fdtd.addpoly(name="nanobrick")
    fdtd.setnamed("nanobrick", "vertices", verts)     # 必须 (N,2) numpy 矩阵
    fdtd.setnamed("nanobrick", "z", ts_ + tm_ / 2)
    fdtd.setnamed("nanobrick", "z span", tm_)
    fdtd.setnamed("nanobrick", "material", mat_au)
    fdtd.setnamed("nanobrick", "override mesh order from material database", 1)
    fdtd.setnamed("nanobrick", "mesh order", 1)

    # ---- FDTD 求解区 ----
    # ⚠️ 不能写 addfdtd(name="FDTD", ...) → "In 'addfdtd', 'name' property is inactive"
    fdtd.addfdtd(dimension="3D", x=0, y=0,
                 z=(z_top + z_bot) / 2, x_span=p, y_span=p,
                 z_span=z_top - z_bot)
    for bc, val in [("x min bc", "Periodic"), ("x max bc", "Periodic"),
                    ("y min bc", "Periodic"), ("y max bc", "Periodic"),
                    ("z min bc", "PML"),      ("z max bc", "PML")]:
        fdtd.setnamed("FDTD", bc, val)
    fdtd.setnamed("FDTD", "mesh accuracy", 3)
    fdtd.setnamed("FDTD", "simulation time", 1200e-15)
    fdtd.setnamed("FDTD", "use early shutoff", 1)
    fdtd.setnamed("FDTD", "auto shutoff min", 1e-5)

    # ---- 金属层局部加密 ----
    for nm, zc, zs in [("mesh_au_film", -d_ / 2, d_ + 100e-9),
                       ("mesh_brick", ts_ + tm_ / 2, tm_ + 200e-9)]:
        fdtd.addmesh(name=nm, x=0, y=0, z=zc, x_span=p, y_span=p, z_span=zs)
        fdtd.setnamed(nm, "dx", mesh_d)
        fdtd.setnamed(nm, "dy", mesh_d)
        fdtd.setnamed(nm, "dz", mesh_d)

    # ---- 平面波源：沿 -z 向下入射（反射式）----
    fdtd.addplane(name="source")
    fdtd.setnamed("source", "injection axis", "z")
    fdtd.setnamed("source", "direction", "Backward")     # ★ 向下
    fdtd.setnamed("source", "x", 0); fdtd.setnamed("source", "x span", p)
    fdtd.setnamed("source", "y", 0); fdtd.setnamed("source", "y span", p)
    fdtd.setnamed("source", "z", z_src)
    fdtd.setnamed("source", "polarization angle", 0)      # x 偏振
    fdtd.setnamed("source", "amplitude", 1)
    fdtd.setnamed("source", "phase", 0)
    # 主控开关必须先开，否则 wavelength start/stop 是 inactive
    fdtd.setnamed("source", "override global source settings", 1)
    fdtd.setnamed("source", "wavelength start", lam_start)
    fdtd.setnamed("source", "wavelength stop", lam_stop)

    # ---- 反射监视器（2D Z-normal，取偏振分量）----
    fdtd.addpower(name="Rm")
    fdtd.setnamed("Rm", "monitor type", "2D Z-normal")
    fdtd.setnamed("Rm", "x", 0); fdtd.setnamed("Rm", "x span", p)
    fdtd.setnamed("Rm", "y", 0); fdtd.setnamed("Rm", "y span", p)
    fdtd.setnamed("Rm", "z", z_rmon)

    # ---- 点监视器（取复振幅，用于算相位）----
    fdtd.addprofile(name="R_pt")
    fdtd.setnamed("R_pt", "monitor type", "Point")
    fdtd.setnamed("R_pt", "x", 0)
    fdtd.setnamed("R_pt", "y", 0)
    fdtd.setnamed("R_pt", "z", z_rmon)
    for pp in ["output Ex", "output Ey", "output Ez"]:
        fdtd.setnamed("R_pt", pp, 1)

    # ---- 全局监视器栅格（默认 5 点，远远不够）----
    fdtd.select("FDTD")
    fdtd.setnamed("FDTD", "global monitor use source limits", 0)
    fdtd.setnamed("FDTD", "global monitor use wavelength spacing", 1)
    fdtd.setnamed("FDTD", "global monitor wavelength center",
                  (lam_start + lam_stop) / 2)
    fdtd.setnamed("FDTD", "global monitor wavelength span", lam_stop - lam_start)
    fdtd.setnamed("FDTD", "global monitor frequency points", n_points)


# ------------------------------------------------------------------
# 4. ★★ 技巧二：run 必须在「save → 重新 load」之后才生效
# ------------------------------------------------------------------
def run_sim(fdtd, fsp_path):
    """★ 本脚本最反直觉的一步，实测确认。

    现象（2026-09-24 实测）：
        在**新建的 headless 会话**里建完对象直接 f.run()，
        run 会**静默返回**、什么都不算：
            layoutmode 跑完仍是 1.0（1 = 还在 layout 模式）
            nsim = 0
            所有监视器都取不到结果：
                "Can not find result 'E' in the result provider 'Rm'"
        而且 f.run() 不抛任何异常 —— 典型的**静默失败**。

    对照实验（同一次会话内）：

        | 操作顺序                    | run 后 layoutmode | 能取到结果吗 |
        |-----------------------------|-------------------|--------------|
        | build -> run                | 1.0               | ❌ 不能      |
        | build -> save -> load -> run| 0.0               | ✅ 能        |
        | load 现成 .fsp -> run       | 0.0               | ✅ 能        |

    结论：**先 save 成 .fsp，再 load 回来，run 才真正开始算。**
    所以本函数强制走 save → switchtolayout → load → run 这个序列。

    另注：改任何结构参数都会把会话退回 layout 模式（layoutmode=1）。
    """
    fdtd.save(fsp_path)                      # 1) 落盘
    fdtd.close()                             # 2) 关掉旧会话

    f2 = lumapi.FDTD(hide=True)              # 3) 开新会话
    f2.load(fsp_path)                        # 4) 载入 → 进入可计算状态
    f2.eval("switchtolayout;")               # 显式确认在 layout 模式
    f2.run()                                 # 5) 这次真的算了
    return f2


# ------------------------------------------------------------------
# 5. 取结果
# ------------------------------------------------------------------
def extract_Rcr_Rco(fdtd):
    """从点监视器取复振幅 → 算 R_co / R_cr / PCR。

    入射是 x 偏振，所以：
        Ex -> 同偏振（copolarized）  = R_co  ← 要消掉的
        Ey -> 交叉偏振（cross-pol.） = R_cr  ← 想要的

    ★ 结果的数据结构（实测，很容易踩空）：
        E = fdtd.getresult("R_pt", "E")
        E.keys() = ['lambda','f','x','y','z','E','Lumerical_dataset']
        注意：**没有** 'Ex'/'Ey' 键！分量全在 E["E"] 这个 5 维数组里：
            E["E"].shape = (1, 1, 1, N_freq, 3)
                                  ^  ^     ^
                                  x  y     z 位置（点监视器各 1）
                                           最后一维 = [Ex, Ey, Ez]
        所以要取 Ex / Ey，必须切最后一维，不能用 E["Ex"]。

        （对照：LSF 侧的 getresult("R_pt") 会列出 Ex/Ey/Ez 这些字段名，
          那是 LSF 的 dataset 视图；Python 侧拿到的是一整个数组。）

    ★ 归一化：用源的复振幅做基准。这里源的 amplitude 已设为 1，
      且监视器在空气中（与源同介质），所以 R = |E|² 直接可用。
      严谨做法是同时记录源的 E 并相除，D15 再做精细化。
    """
    E = fdtd.getresult("R_pt", "E")
    f = np.array(E["f"], dtype=float).ravel()
    lam = C0 / f

    comp = np.array(E["E"])                 # (1,1,1,N,3)
    comp = comp[0, 0, 0]                     # (N, 3)
    ex = comp[:, 0]
    ey = comp[:, 1]

    rco = np.abs(ex) ** 2
    rcr = np.abs(ey) ** 2
    pcr = rcr / (rcr + rco)
    order = np.argsort(lam)
    return lam[order], rco[order], rcr[order], pcr[order]


# ------------------------------------------------------------------
# 6. 主流程
# ------------------------------------------------------------------
def main():
    print("=" * 74)
    print("复现论文 Figure 1：反射式等离激元半波片单元胞")
    print("=" * 74)
    print("  周期 p        = %.0f nm" % (p * 1e9))
    print("  金砖 l1 x l2  = %.0f x %.0f nm, 厚 %.0f nm, 转 %.0f deg"
          % (l1 * 1e9, l2 * 1e9, tm * 1e9, theta))
    print("  SiO2 间隔层   = %.0f nm" % (ts * 1e9))
    print("  金膜 d        = %.0f nm" % (d * 1e9))
    print("  波长窗口      = %.0f - %.0f nm, %d 点"
          % (lam_start * 1e9, lam_stop * 1e9, n_points))
    print()

    fdtd = lumapi.FDTD(hide=True)
    print("建模中 ...")
    try:
        build(fdtd)

        # ---- 几何自检 ----
        root = fdtd.getObjectById("::model")
        kids = [k._id.name for k in root.getChildren()]
        print("  ✅ 对象树 (%d 个): %s" % (len(kids), kids))

        v = np.array(fdtd.getnamed("nanobrick", "vertices"), dtype=float)
        d01 = math.hypot(v[1][0] - v[0][0], v[1][1] - v[0][1])
        d12 = math.hypot(v[2][0] - v[1][0], v[2][1] - v[1][1])
        # 长边 P0->P1 的方向角，折到 0-180 度看取向
        ang = math.degrees(math.atan2(v[1][1] - v[0][1], v[1][0] - v[0][0])) % 180.0
        print("  ✅ 金砖自检：长边 %.1f nm / 短边 %.1f nm / 长边取向 %.1f deg"
              % (d01 * 1e9, d12 * 1e9, ang))
        print("     顶点(nm): " + " ".join("(%.0f,%.0f)" % (pt[0] * 1e9, pt[1] * 1e9)
                                           for pt in v[:4]))

        os.makedirs(os.path.dirname(out_fsp), exist_ok=True)
        print("\n运行仿真（save → load → run，见 run_sim 注释）...")
    finally:
        fdtd.close()
        print("  建模会话已关")

    # ★ 关键：save → load → run
    fdtd = lumapi.FDTD(hide=True)
    try:
        build(fdtd)
        fdtd = run_sim(fdtd, out_fsp)

        fdtd.eval("lm = layoutmode;")
        lm = fdtd.getv("lm")
        print("  ✅ run 完成，layoutmode = %.1f  (0.0 = 已算出结果)" % lm)
        if lm != 0.0:
            print("  ⚠️ layoutmode 不是 0 —— 仿真可能没真正执行！")
            return

        lam, rco, rcr, pcr = extract_Rcr_Rco(fdtd)
        print("  ✅ 取到 %d 个频点" % len(lam))

        # ---- 结果摘要 ----
        print()
        print("=" * 74)
        print("结果摘要（对照论文 Figure 1b/1c）")
        print("=" * 74)
        print("  %-10s %-10s %-10s %-10s" % ("lam(nm)", "R_co", "R_cr", "PCR"))
        for target in [850, 1000, 1200, 1400, 1600]:
            i = int(np.argmin(np.abs(lam * 1e9 - target)))
            print("  %-10.0f %-10.4f %-10.4f %-10.4f"
                  % (lam[i] * 1e9, rco[i], rcr[i], pcr[i]))

        print()
        print("  R_cr 平均     = %.4f   (论文：几乎 1)" % rcr.mean())
        print("  R_co 平均     = %.4f   (论文：几乎 0)" % rco.mean())
        print("  PCR 平均      = %.4f" % pcr.mean())
        print("  PCR 最大      = %.4f @ %.0f nm" % (pcr.max(), lam[np.argmax(pcr)] * 1e9))
        hi = lam[pcr > 0.95] * 1e9
        if len(hi):
            print("  PCR > 95%% 带宽 = %.0f - %.0f nm (%.0f nm 宽)"
                  % (hi.min(), hi.max(), hi.max() - hi.min()))
        else:
            print("  PCR > 95%% 带宽 = 【无】—— 与论文对不上，见下方排查提示")

        # ---- 存数据 ----
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        with open(out_csv, "w", encoding="utf-8-sig") as fh:
            fh.write("lam_nm,R_co,R_cr,PCR\n")
            for a, b, c, dd in zip(lam, rco, rcr, pcr):
                fh.write("%.4f,%.6f,%.6f,%.6f\n" % (a * 1e9, b, c, dd))
        print("\n  数据 -> %s" % out_csv)
        print("  工程 -> %s" % out_fsp)
    finally:
        fdtd.close()
        print("\n会话已关闭")

    print()
    print("=" * 74)
    print("下一步（对照论文排查）")
    print("=" * 74)
    print("  1. 论文 PCR > 95% 覆盖 805-1672 nm。若你的明显偏低，按序查：")
    print("     (a) 材料模型 —— 论文用 Drude，本脚本用材料库 Palik 数据（D17 专项）")
    print("     (b) 网格密度 —— 80 nm 金砖+8 nm 网格是否够；试 mesh accuracy 4")
    print("     (c) 监视器位置 —— 太靠近结构会收到近场（evanescent）")
    print("  2. R_co 接近 0 且 R_cr 接近 1，才说明偏振转换干净")
    print("  3. 复现出 Figure 1b/1c 后，再做 D16 的 u/v 分解图（Figure 3）")


if __name__ == "__main__":
    main()
