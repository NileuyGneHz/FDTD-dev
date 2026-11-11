"""Enable field_big and export |Ey(x,z)| for the bound-surface-wave case.

Paper Fig.3d: theta_i = +20 deg (paper) = -20 deg in Lumerical 'angle theta'.
The 'field_big' monitor is a 2D Y-normal DFT monitor spanning x and z; it is
the only monitor that can show the trapped surface wave.

Usage: python tmp_p04repro_field_prepare.py --name run_sw_p20.fsp --angle -20
"""
import argparse
import os
import shutil
import sys

os.environ["ANSYSLMD_LICENSE_FILE"] = "1055@localhost"
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
import lumapi

ROOT = r"F:\Lumercial_WS\FDTD_WS\_scratch\tmp_p04repro_run"
MASTER = os.path.join(ROOT, "fig2c_and_3_run.fsp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--angle", type=float, required=True)
    ap.add_argument("--dt", type=float, default=0.95)
    a = ap.parse_args()

    target = os.path.join(ROOT, a.name)
    shutil.copyfile(MASTER, target)
    s = None
    try:
        s = lumapi.FDTD(hide=True)
        s.load(target)
        s.switchtolayout()
        s.setnamed("FDTD", "dt stability factor", a.dt)
        # keep field_big (the x-z map), drop the small 'field' monitor
        s.setnamed("field", "enabled", 0)
        s.setnamed("field_big", "enabled", 1)
        s.setnamed("source", "angle theta", a.angle)
        print("PREPARED", target)
        print("  dt", s.getnamed("FDTD", "dt stability factor"))
        print("  field_big enabled", s.getnamed("field_big", "enabled"))
        print("  angle theta", s.getnamed("source", "angle theta"))
        print("  field_big x", s.getnamed("field_big", "x span"),
              "z", s.getnamed("field_big", "z span"))
        for p in ("x min", "x max", "z min", "z max"):
            try:
                print("  field_big", p, s.getnamed("field_big", p))
            except Exception:
                pass
        s.save(target)
    finally:
        if s is not None:
            s.close()


if __name__ == "__main__":
    main()
