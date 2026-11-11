"""P04 final analysis: 5-point incidence scan, Eq.(2) check, conventional-order suppression.

Inputs : spectrum_<label>.npz written by tmp_p04repro_read.py  (x, E_complex_y)
Outputs: results/P04_AnomalousReflection_047/
           farfield_fullangle_all_incidences.{csv,png}
           incidence_scan_summary.json
           farfield_fullangle_850nm.{csv,png}   (normal incidence, standalone)
"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = r"F:\Lumercial_WS\FDTD_WS\_scratch\tmp_p04repro_run"
DEST = r"F:\Lumercial_WS\FDTD_WS\results\P04_AnomalousReflection_047"

LAMBDA = 850e-9      # m
PERIOD = 1200e-9     # supercell period Lx, m
XI = LAMBDA / PERIOD             # xi/k0 = lambda/Lx
K0 = 2 * np.pi / LAMBDA          # rad/m

# (label, Lumerical 'angle theta' in deg).  Paper theta_i = -angle_theta (verified empirically).
RUNS = [
    ("thim20", -20.0),
    ("thi10", 10.0),
    ("thim10", -10.0),
    ("thi20", 20.0),
    ("thi00", 0.0),
]

th_grid = np.linspace(-89.0, 89.0, 7201)
kx = K0 * np.sin(np.radians(th_grid))

rows, curves = [], {}
fig, ax = plt.subplots(figsize=(9.0, 5.0), dpi=160)

for label, lum_deg in RUNS:
    path = os.path.join(ROOT, "spectrum_%s.npz" % label)
    if not os.path.exists(path):
        print("MISSING", path)
        continue
    z = np.load(path)
    x, ey = z["x"], z["E_complex_y"]
    w = np.gradient(x)
    ek = np.array([np.sum(ey * w * np.exp(-1j * k * x)) for k in kx])
    p_raw = np.abs(ek) ** 2
    peak_raw = float(p_raw.max())
    p = p_raw / peak_raw
    curves[label] = p

    paper_thi = -lum_deg
    i = int(np.argmax(p))
    peak_th = float(th_grid[i])

    # Eq.(2): sin(theta_r) = sin(theta_i) + xi/k0
    s = np.sin(np.radians(paper_thi)) + XI
    predicted = float(np.degrees(np.arcsin(s))) if abs(s) <= 1.0 else None

    # conventional (specular) order level at theta_r = theta_i
    #   only meaningful when |theta_i| is not degenerate with the anomalous peak
    j = int(np.argmin(np.abs(th_grid - paper_thi)))
    conv_level = float(p[j])
    # robust version: fraction of reflected power within +-1 deg of the
    # specular direction (single-point sampling is grid-sensitive near a null)
    spec_band = np.abs(th_grid - paper_thi) <= 1.0
    conv_frac = float(p_raw[spec_band].sum() / p_raw.sum())

    # energy fraction within +-4 deg of the anomalous peak (normalised to own total)
    band = np.abs(th_grid - peak_th) <= 4.0
    frac_band = float(p_raw[band].sum() / p_raw.sum())

    rows.append({
        "label": label,
        "lumerical_angle_theta_deg": lum_deg,
        "paper_theta_i_deg": paper_thi,
        "peak_theta_r_deg": round(peak_th, 3),
        "eq2_predicted_theta_r_deg": round(predicted, 3) if predicted is not None else None,
        "delta_vs_eq2_deg": round(peak_th - predicted, 3) if predicted is not None else None,
        "peak_abs_unnormalised": peak_raw,
        "conventional_specular_level_rel_own_peak": round(conv_level, 6),
        "conventional_frac_within_1deg": round(conv_frac, 6),
        "energy_fraction_within_4deg": round(frac_band, 4),
    })

base = next(r["peak_abs_unnormalised"] for r in rows
            if abs(r["paper_theta_i_deg"]) < 1e-9)
for r in rows:
    r["peak_vs_theta_i_0_ratio"] = round(r["peak_abs_unnormalised"] / base, 6)

rows.sort(key=lambda r: r["paper_theta_i_deg"])

# ---- combined figure / csv ----
for label, lum_deg in RUNS:
    if label not in curves:
        continue
    paper_thi = -lum_deg
    r = next(q for q in rows if q["label"] == label)
    ax.plot(th_grid, curves[label], lw=1.15,
            label=r"$\theta_i$=%+.0f$^\circ$: peak %.1f$^\circ$ (Eq.2 %.1f$^\circ$)"
                  % (paper_thi, r["peak_theta_r_deg"],
                     r["eq2_predicted_theta_r_deg"]
                     if r["eq2_predicted_theta_r_deg"] is not None else float("nan")))
ax.axvline(0, color="#999", ls=":", lw=1)
ax.set_xlabel(r"reflection angle $\theta_r$ (deg)")
ax.set_ylabel(r"$P(\theta_r)$ / own peak")
ax.set_title("P04 (Sun 2012) anomalous reflection, 850 nm, five incidence angles")
ax.set_xlim(-89, 89)
ax.set_ylim(0, 1.08)
ax.grid(alpha=0.3)
ax.legend(fontsize=7.5, loc="upper left")
fig.tight_layout()
png_all = os.path.join(DEST, "farfield_fullangle_all_incidences.png")
fig.savefig(png_all)
plt.close(fig)

def _fmt_angle(v):
    """'+10', '-10', '0' -- never '-0'."""
    v = 0.0 if abs(v) < 1e-9 else v
    return "%+g" % v if v else "0"


csv_all = os.path.join(DEST, "farfield_fullangle_all_incidences.csv")
with open(csv_all, "w", encoding="utf-8") as fh:
    fh.write("# P04 Sun 2012 full-angle complex-field DFT; one column per incidence angle\n")
    fh.write("# each column peak-normalised within itself\n")
    fh.write("# columns ordered by paper theta_i\n")
    ordered = [r for r in rows if r["label"] in curves]  # already sorted
    fh.write("theta_r_deg," + ",".join("theta_i_%s" % _fmt_angle(r["paper_theta_i_deg"])
                                       for r in ordered) + "\n")
    for j in range(th_grid.size):
        fh.write("%.4f," % th_grid[j]
                 + ",".join("%.8g" % curves[r["label"]][j] for r in ordered) + "\n")

# ---- standalone normal-incidence figure / csv ----
if "thi00" in curves:
    p0 = curves["thi00"]
    fig2, ax2 = plt.subplots(figsize=(8.4, 4.4), dpi=160)
    ax2.plot(th_grid, p0, lw=1.4, color="#c0392b")
    ax2.axvline(45.10, color="#2980b9", ls="--", lw=1,
                label=r"Eq.(2) $\theta_r=45.10^\circ$")
    ax2.axvline(0, color="#7f8c8d", ls=":", lw=1, label=r"specular $0^\circ$")
    ax2.set_xlabel(r"$\theta_r$ (deg)")
    ax2.set_ylabel(r"$P(\theta_r)$ / peak")
    ax2.set_title("P04 normal incidence 850 nm: single anomalous reflection peak")
    ax2.set_xlim(-89, 89)
    ax2.set_ylim(0, 1.06)
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=8)
    fig2.tight_layout()
    png0 = os.path.join(DEST, "farfield_fullangle_850nm.png")
    fig2.savefig(png0)
    plt.close(fig2)

    row0 = next(r for r in rows if r["label"] == "thi00")
    csv0 = os.path.join(DEST, "farfield_fullangle_850nm_thi00.csv")
    with open(csv0, "w", encoding="utf-8") as fh:
        fh.write("# P04 Sun 2012, theta_i = 0, 850 nm, complex-Ey DFT over full angle range\n")
        fh.write("# x-position raw data: R monitor Linear X, z = 100 nm\n")
        fh.write("theta_r_deg,P_normalised,P_arbitrary\n")
        for j in range(th_grid.size):
            fh.write("%.4f,%.8g,%.8g\n"
                     % (th_grid[j], p0[j],
                        p0[j] * row0["peak_abs_unnormalised"]))
    json.dump({"theta_i_deg": 0.0,
               "peak_theta_r_deg": next(r["peak_theta_r_deg"] for r in rows
                                        if r["label"] == "thi00"),
               "eq2_predicted_deg": round(float(np.degrees(np.arcsin(XI))), 3),
               "specular_level_rel_peak": next(
                   r["conventional_specular_level_rel_own_peak"] for r in rows
                   if r["label"] == "thi00"),
               "png": png0, "csv": csv0},
              open(os.path.join(DEST, "farfield_fullangle_850nm_summary.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=2)

out = {
    "paper": "Sun et al., Nano Lett. 2012, 12, 6223-6228",
    "lambda_m": LAMBDA,
    "supercell_period_m": PERIOD,
    "xi_over_k0": round(XI, 6),
    "theta_r_normal_incidence_eq2_deg": round(float(np.degrees(np.arcsin(XI))), 3),
    "theta_ic_eq2_deg": round(float(np.degrees(np.arcsin(1.0 - XI))), 3),
    "sign_convention": "paper theta_i = -(Lumerical 'angle theta'); "
                       "verified against Eq.(2) at four non-zero angles",
    "rows": rows,
    "png_all": png_all, "csv_all": csv_all,
}
with open(os.path.join(DEST, "incidence_scan_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print(json.dumps(out, ensure_ascii=False, indent=2))
