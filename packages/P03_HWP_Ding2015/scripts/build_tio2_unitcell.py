#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiO2 纳米砖单元胞 —— 骨架工程 + 偏振/尺寸扫参，自动生成"元原子库"

对应论文《超表面全息术：从概念到实现》§2 步骤 1 与 §6 第 3 条②
（"基于 Ansys Lumerical FDTD 建立单元结构库"）

软件：Ansys Lumerical FDTD 2025 R1 (v251)
用法：
    1) 设置环境变量（见 README.md）
    2) python build_tio2_unitcell.py
输出：
    TiO2_nanobrick_unitcell.fsp   —— 骨架工程
    unitcell_library.csv          —— 元原子库（每个 Lx×Ly×偏振 一行）

⚠️ 本脚本会新建一个 FDTD 会话并独占 license，运行前请关闭已打开的 FDTD 实例。
"""

import os
import sys
import csv

# ------------------------------------------------------------------
# 0. 定位并导入 lumapi
# ------------------------------------------------------------------
LUMERICAL_ROOT = r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical"
API_PY = os.path.join(LUMERICAL_ROOT, "api", "python")

if not os.path.isdir(API_PY):
    sys.exit("找不到 Lumerical Python API 目录：%s" % API_PY)
if API_PY not in sys.path:
    sys.path.insert(0, API_PY)

try:
    import lumapi
except Exception as e:
    sys.exit(
        "导入 lumapi 失败：%s\n"
        "请确认 PYTHONPATH 已包含：%s\n"
        "并建议使用 Lumerical 自带 Python：%s"
        % (e, API_PY, os.path.join(LUMERICAL_ROOT, "python-3.9.9-embed-amd64", "python.exe"))
    )

# ------------------------------------------------------------------
# 1. 设计参数
# ------------------------------------------------------------------
P          = 250e-9      # 单元胞周期
H          = 600e-9      # 纳米砖高度
LAMBDA0    = 532e-9      # 设计波长
C0         = 299792458.0

MAT_SUB    = "SiO2 (Glass) - Palik"
MAT_BRICK  = "TiO2 (Titanium Dioxide) - Siefke"

Z_SIM_MIN, Z_SIM_MAX = -700e-9, 900e-9
Z_SUB_TOP, Z_SUB_BOT = 0.0, Z_SIM_MIN - 400e-9
Z_SOURCE, Z_R, Z_T   = -350e-9, -180e-9, Z_SIM_MAX - 150e-9

MESH_D = 8e-9

# 光源带宽与监视器采样（rev4 新增）
# 默认只有 5 个频点、最近点落在 547.8 nm，根本打不到 532 nm，必须显式指定。
BAND_SPAN = 200e-9                    # 带宽 200 nm
LAM_START = LAMBDA0 - BAND_SPAN / 2   # 432 nm
LAM_STOP  = LAMBDA0 + BAND_SPAN / 2   # 632 nm
N_POINTS  = 101                       # 采样点数（实测落到 100 点，步长 2.02 nm）

# 扫参范围（先用粗网格找趋势，再对候选精算）
LX_LIST = [100e-9, 120e-9, 140e-9, 160e-9, 180e-9]
LY_LIST = [ 50e-9,  60e-9,  70e-9,  80e-9]
POL_LIST = [0.0, 90.0]           # 0° = 沿 x 线偏振；90° = 沿 y

OUT_FSP = r"F:\Lumercial_WS\WS\TiO2_nanobrick_unitcell.fsp"
OUT_CSV = r"F:\Lumercial_WS\WS\unitcell_library.csv"

# ------------------------------------------------------------------
# 2. 建工程（用 LSF 构建，与本目录下的 .lsf 脚本逻辑一致）
# ------------------------------------------------------------------
# 注意（rev2 修正）：
#   1) 不要 set("name","FDTD") —— v251 中 FDTD 求解区的 name 属性是
#      inactive，调用会抛 "the requested property 'name' is inactive"。
#      求解区默认名就是 "FDTD"，无需重命名。
#   2) 平面波源必须先 set("override global source settings",1)，
#      否则 "wavelength start/stop" 同样是 inactive 属性。
BUILD_LSF = """
switchtolayout;
deleteall;

addrect;
set("name","substrate");
set("x",0); set("x span",{P});
set("y",0); set("y span",{P});
set("z",{zsubc}); set("z span",{zsubl});
set("material","{matsub}");
set("override mesh order from material database",1);
set("mesh order",2);

addrect;
set("name","nanobrick");
set("x",0); set("x span",{Lx});
set("y",0); set("y span",{Ly});
set("z",{zbrickc}); set("z span",{Hb});
set("material","{matbrick}");
set("override mesh order from material database",1);
set("mesh order",1);

addfdtd;
set("x",0); set("x span",{P});
set("y",0); set("y span",{P});
set("z",{zsimc}); set("z span",{zsiml});
set("x min bc","Periodic");  set("x max bc","Periodic");
set("y min bc","Periodic");  set("y max bc","Periodic");
set("z min bc","PML");       set("z max bc","PML");
set("mesh accuracy",3);
set("simulation time",3000e-15);
set("use early shutoff",1);
set("auto shutoff min",1e-5);

addmesh;
set("name","mesh_brick");
set("x",0); set("x span",{P});
set("y",0); set("y span",{P});
set("z",{zbrickc}); set("z span",{Hb} + 200e-9);
set("dx",{md}); set("dy",{md}); set("dz",{md});

addplane;
set("name","source");
set("injection axis","z");
set("direction","Forward");
set("x",0); set("x span",{P});
set("y",0); set("y span",{P});
set("z",{zsrc});
set("polarization angle",0);
set("amplitude",1);
set("phase",0);
set("override global source settings",1);
set("wavelength start",{lamstart});
set("wavelength stop",{lamstop});

addpower;
set("name","T");
set("monitor type","2D Z-normal");
set("x",0); set("x span",{P});
set("y",0); set("y span",{P});
set("z",{zT});

addpower;
set("name","R");
set("monitor type","2D Z-normal");
set("x",0); set("x span",{P});
set("y",0); set("y span",{P});
set("z",{zR});

addprofile;
set("name","T_pt");
set("monitor type","Point");
set("x",0); set("y",0);
set("z",{zT});

# 全局监视器栅格挂在 FDTD 求解区上，此刻选中的是 T_pt，必须先切回去。
# set 只作用于当前选中对象 —— 这是 Lumerical 脚本最常见的坑。
select("FDTD");
set("global monitor use source limits",0);
set("global monitor use wavelength spacing",1);
set("global monitor wavelength center",{lamstart0});
set("global monitor wavelength span",{bandspan});
set("global monitor frequency points",{npoints});
""".format(
    P=P, Lx=120e-9, Ly=60e-9,
    zsubc=(Z_SUB_TOP + Z_SUB_BOT) / 2, zsubl=Z_SUB_TOP - Z_SUB_BOT,
    zbrickc=H / 2, Hb=H,
    zsimc=(Z_SIM_MAX + Z_SIM_MIN) / 2, zsiml=Z_SIM_MAX - Z_SIM_MIN,
    md=MESH_D, zsrc=Z_SOURCE, zT=Z_T, zR=Z_R,
    matsub=MAT_SUB, matbrick=MAT_BRICK,
    lamstart=LAM_START, lamstop=LAM_STOP,
    lamstart0=LAMBDA0, bandspan=BAND_SPAN, npoints=N_POINTS,
)

# 提取结果：把复振幅线性插值到设计波长（栅格不保证落在 lambda0 上），
# 相位/振幅都在 LSF 侧算好再读回。
EXTRACT_LSF = """
r = getresult("T_pt","E");
fvec = r.f;
n = length(fvec);
f0 = {c0}/{lam0};
idx = 1;
dmin = 1e30;
for (i=1:n) {{
    d = abs(fvec(i) - f0);
    if (d < dmin) {{ dmin = d; idx = i; }}
}}
j = idx;
if (idx < n) {{ j = idx + 1; }} else {{ j = idx - 1; }}
if ( (fvec(idx) - f0) * (fvec(j) - f0) > 0 ) {{
    if (idx > 1) {{ j = idx - 1; }}
}}
wgt = (f0 - fvec(idx)) / (fvec(j) - fvec(idx));
Exv = r.Ex(idx) + wgt*(r.Ex(j) - r.Ex(idx));
Eyv = r.Ey(idx) + wgt*(r.Ey(j) - r.Ey(idx));
lam_near = {c0}/fvec(idx);
amp_x    = abs(Exv);
phase_x  = angle(Exv) * 180/pi;
amp_y    = abs(Eyv);
phase_y  = angle(Eyv) * 180/pi;
dphase   = phase_x - phase_y;
Ts = transmission("T");
if (length(Ts) == n) {{ T_pow = Ts(idx); }} else {{ T_pow = mean(Ts); }}
""".format(c0=C0, lam0=LAMBDA0)


def main():
    print("启动 FDTD 会话 ...")
    fdtd = lumapi.FDTD(hide=True)

    print("构建骨架工程 ...")
    fdtd.eval(BUILD_LSF)

    rows = []
    total = len(LX_LIST) * len(LY_LIST) * len(POL_LIST)
    k = 0

    for Lx in LX_LIST:
        for Ly in LY_LIST:
            for pol in POL_LIST:
                k += 1
                fdtd.switchtolayout()
                fdtd.setnamed("nanobrick", "x span", Lx)
                fdtd.setnamed("nanobrick", "y span", Ly)
                fdtd.setnamed("source", "polarization angle", pol)

                print("[%d/%d] Lx=%.0f nm  Ly=%.0f nm  pol=%.0f deg ..."
                      % (k, total, Lx * 1e9, Ly * 1e9, pol), end="")
                sys.stdout.flush()

                # 运行 + 校验。
                # 实测遇到过 fdtd.run() 不产生结果的偶发情况（脚本不会报错，
                # 但后面取结果会全部失败）。这里显式检查一次结果是否存在，
                # 缺失就补一次显式 LSF run，避免把空数据写进库。
                fdtd.run()
                got = False
                for _try in range(2):
                    try:
                        fdtd.eval('rr = getresult("T_pt","E"); chkf = length(rr.f);')
                        got = True
                        break
                    except Exception:
                        print("\n   [warn] 本次 run 未产生结果，补跑一次 ...")
                        try:
                            fdtd.eval("run;")
                        except Exception as e2:
                            print("   [warn] 补跑也失败: %s" % e2)
                if not got:
                    print("\n   [ERROR] 该点连续两次都拿不到结果，跳过 "
                          "(Lx=%.0f nm, Ly=%.0f nm, pol=%.0f)"
                          % (Lx * 1e9, Ly * 1e9, pol))
                    continue

                fdtd.eval(EXTRACT_LSF)

                # 单次运行只能拿到"该偏振下自己的主轴响应"，交叉分量应接近 0。
                # 真正的双折射相位差 delta 必须由 pol=0 与 pol=90 两次配对算出（见下）。
                own = "x" if pol == 0.0 else "y"
                row = dict(
                    Lx_nm=round(Lx * 1e9, 2),
                    Ly_nm=round(Ly * 1e9, 2),
                    pol_deg=pol,
                    own_axis=own,
                    lam_near_nm=round(float(fdtd.getv("lam_near")) * 1e9, 2),
                    wgt=round(float(fdtd.getv("wgt")), 4),
                    amp_own=float(fdtd.getv("amp_%s" % own)),
                    phase_own_deg=float(fdtd.getv("phase_%s" % own)),
                    amp_cross=float(fdtd.getv("amp_%s" % ("y" if own == "x" else "x"))),
                    T=float(fdtd.getv("T_pow")),
                    delta_xy_deg=None,
                )
                rows.append(row)
                print("  T=%.4f  |E%s|=%.4f  phi_%s=%+.1f deg   交叉偏振 |E|=%.2e"
                      % (row["T"], own, row["amp_own"], own,
                         row["phase_own_deg"], row["amp_cross"]))

    # ------------------------------------------------------------
    # 配对计算双折射相位差 delta = phase_x - phase_y
    # 必须由 pol=0 与 pol=90 两次运行配对，单次运行里算不出来。
    # 判据：|delta| 接近 180 度 且两个振幅都接近 1  ->  等效半波片
    # ------------------------------------------------------------
    print("\n=== 双折射相位差 delta（配对结果）===")
    by_geo = {}
    for r in rows:
        by_geo.setdefault((r["Lx_nm"], r["Ly_nm"]), {})[r["own_axis"]] = r

    for (lx, ly) in sorted(by_geo):
        pair = by_geo[(lx, ly)]
        if "x" in pair and "y" in pair:
            d = pair["x"]["phase_own_deg"] - pair["y"]["phase_own_deg"]
            d = (d + 180.0) % 360.0 - 180.0          # 归一到 [-180, 180]
            pair["x"]["delta_xy_deg"] = round(d, 2)
            pair["y"]["delta_xy_deg"] = round(d, 2)
            amp_ok = min(pair["x"]["amp_own"], pair["y"]["amp_own"])
            tag = ""
            if abs(abs(d) - 180.0) < 20.0 and amp_ok > 0.5:
                tag = "   <== 半波片候选！"
            print("  Lx=%3.0f nm  Ly=%3.0f nm   delta=%+7.2f deg   透射振幅 min=%.3f%s"
                  % (lx, ly, d, amp_ok, tag))
        else:
            print("  Lx=%3.0f nm  Ly=%3.0f nm   缺少 pol=0/90 之一，无法配对" % (lx, ly))

    # 保存工程
    fdtd.save(OUT_FSP)
    print("\n工程已保存 -> %s" % OUT_FSP)

    # 写库文件
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("元原子库已导出 -> %s  (%d 行)" % (OUT_CSV, len(rows)))

    fdtd.close()


if __name__ == "__main__":
    main()
