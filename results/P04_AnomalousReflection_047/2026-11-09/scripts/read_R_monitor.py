"""Read back a solved .fsp (from direct fdtd-engine.exe -gpu run) and export the
Fig.2c angular spectrum. Enforces the three 'did it really run' criteria.
"""
import argparse
import json
import os
import re

import numpy as np

os.environ["ANSYSLMD_LICENSE_FILE"] = "1055@localhost"
import sys
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
import lumapi

ROOT = r"F:\Lumercial_WS\FDTD_WS\_scratch\tmp_p04repro_run"
LAMBDA = 850e-9


def log_evidence(path):
    if not os.path.exists(path):
        return {"exists": False}
    txt = open(path, "r", encoding="utf-8", errors="replace").read()
    run_line = next((l for l in txt.splitlines() if "Running fsp file:" in l), "")
    completed = re.findall(r"Completed\s+(\d+)\s+iterations", txt)
    shutoff = re.findall(r"Auto Shutoff:\s*([0-9.eE+\-]+)", txt)
    grid = re.findall(r"Simulation size in gridpoints:\s*([0-9 x]+)", txt)
    total = re.findall(r"Starting\s+(\d+)\s+total iterations", txt)
    return {
        "exists": True,
        "bytes": os.path.getsize(path),
        "engine_actual": "GPU" if "-gpu" in run_line else ("CPU" if run_line else "unknown"),
        "engine_flags": run_line.split("fdtd-engine")[-1].split(".fsp")[0][:120],
        "real32": "real32" in txt.lower(),
        "detected_gpu": [l.strip() for l in txt.splitlines() if "Detected GPU" in l][:2],
        # 'Early termination ... autoshutoff criteria are satisfied' is NORMAL.
        # A real divergence reads 'ERROR: Early termination ... fields are diverging'.
        "diverged": ("fields are diverging" in txt.lower()
                     or "electromagnetic fields are diverging" in txt.lower()),
        "autoshutoff_termination": "autoshutoff criteria are satisfied" in txt.lower(),
        "permittivity_warning": "0 < permittivity < 1" in txt,
        "grid": grid[0].strip() if grid else None,
        "total_iterations": int(total[0]) if total else None,
        "completed_iterations": int(completed[-1]) if completed else None,
        "auto_shutoff_last": shutoff[-1] if shutoff else None,
        "tail": [l.rstrip() for l in txt.splitlines()[-8:]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fsp", required=True)
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    fsp = a.fsp if os.path.isabs(a.fsp) else os.path.join(ROOT, a.fsp)
    log = os.path.splitext(fsp)[0] + "_p0.log"
    out = {"label": a.label, "fsp": fsp, "p0": log_evidence(log)}

    s = None
    try:
        s = lumapi.FDTD(hide=True)
        s.load(fsp)
        s.eval("lm = layoutmode;")
        out["layoutmode"] = float(s.getv("lm"))
        r = s.getresult("R", "E")
        x = np.array(r["x"]).ravel()
        ecomplex = np.array(r["E"])[:, 0, 0, 0, 1]      # complex Ey, single freq
        out["n_x"] = int(x.size)
        out["x_range_m"] = [float(x.min()), float(x.max())]

        # Exact course-script angular spectrum, evaluated in-engine.
        s.eval("d = getresult('R','E');")
        s.eval("xx = d.x; EE = d.E;")
        s.eval("Ey = matrix(length(xx)); Ey(:) = real(EE(:,1,1,1,2));")
        s.eval("k0 = 2*pi/%.12g;" % LAMBDA)
        s.eval("th = linspace(35,89,300);")
        s.eval("kx = k0*sin(th*pi/180);")
        s.eval("Ek = czt(Ey, xx, kx)/length(xx)*sqrt(2);")
        s.eval("Pk = abs(Ek)^2;")
        theta = np.array(s.getv("th")).ravel()
        pk = np.array(s.getv("Pk")).ravel()
        ey_real = np.array(s.getv("Ey")).ravel()
        i = int(np.argmax(pk))
        out["peak_theta_deg"] = round(float(theta[i]), 3)
        out["peak_P_arb"] = float(pk[i])
        out["fsp_bytes_solved"] = os.path.getsize(fsp)

        npz = os.path.join(ROOT, "spectrum_%s.npz" % a.label)
        np.savez_compressed(npz, theta_deg=theta, P=pk, x=x,
                            Ey=ey_real, E_complex_y=ecomplex)
        out["npz"] = npz
    except Exception as exc:
        out["read_error"] = repr(exc)[:900]
    finally:
        if s is not None:
            s.close()

    dest = os.path.join(ROOT, "result_%s.json" % a.label)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
