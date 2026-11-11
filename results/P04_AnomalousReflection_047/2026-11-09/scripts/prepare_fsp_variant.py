"""Prepare .fsp variants for direct fdtd-engine.exe invocation (bypasses global ini).

The 'field' and 'field_big' 2D DFT monitors are only consumed by the Fig.1b/3/4
field-plot scripts. Fig.2c needs only the 'R' (Linear X) monitor, so disabling
those two is a pure output optimisation: it does NOT change geometry, materials,
boundaries, mesh, source or the FDTD field evolution.
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


def make(name, sim_time, disable_big_monitors, angle, dt, flat=False):
    target = os.path.join(ROOT, name)
    shutil.copyfile(MASTER, target)
    s = None
    try:
        s = lumapi.FDTD(hide=True)
        s.load(target)
        s.switchtolayout()
        if sim_time is not None:
            s.setnamed("FDTD", "simulation time", float(sim_time))
        if dt is not None:
            s.setnamed("FDTD", "dt stability factor", float(dt))
        if disable_big_monitors:
            for mon in ("field", "field_big"):
                s.setnamed(mon, "enabled", 0)
        if flat:
            # reference run: same stack (Au ground + MgF2) without the nanorod
            # antenna array -> flat mirror, used to calibrate incident power.
            s.setnamed("structure group", "enabled", 0)
            print("FLAT_REFERENCE enabled=",
                  s.getnamed("structure group", "enabled"))
        if angle is not None:
            last = "n/a"
            for prop in ("angle theta", "theta"):
                try:
                    s.setnamed("source", prop, float(angle))
                    print("ANGLE_PROP", prop, "readback",
                          s.getnamed("source", prop))
                    break
                except Exception as exc:
                    last = "%s: %s" % (prop, str(exc)[:150])
            else:
                print("ANGLE_ERROR", last)
        s.save(target)
        print("PREPARED", target, "sim_time", sim_time,
              "big_off", disable_big_monitors, "angle", angle, "dt", dt)
    finally:
        if s is not None:
            s.close()
    return target


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--sim-time", type=float, default=None)
    ap.add_argument("--disable-big", action="store_true")
    ap.add_argument("--angle", type=float, default=None)
    ap.add_argument("--dt", type=float, default=None)
    ap.add_argument("--flat", action="store_true")
    a = ap.parse_args()
    make(a.name, a.sim_time, a.disable_big, a.angle, a.dt, a.flat)
