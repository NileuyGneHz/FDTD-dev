# DEPRECATED (2026-11-10, EXP-50): 这份算法已收编进
# skills/fdtd-lumerical-field-map/scripts/field_map.py（唯一实现）。
# 保留本文件只为对应当时的结果，不要再改、不要再调用。
"""Paper Fig.3d analogue: |Ey(x,z)| for paper theta_i = +20 deg (> theta_ic).

Two panels:
  (a) zoom on the surface region  -- the trapped wave hugging the meta-surface
  (b) decay of the lateral modulation amplitude vs z (log scale) + fitted
      1/e length, to be compared with 1/sqrt(kx^2 - k0^2)

The lateral modulation rms(Ey - <Ey>_x) is used because the incident plane
wave contributes an almost x-uniform offset at every z and would otherwise
mask the decay.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.environ["ANSYSLMD_LICENSE_FILE"] = "1055@localhost"
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
import lumapi

ROOT = r"F:\Lumercial_WS\FDTD_WS\_scratch\tmp_p04repro_run"
DEST = r"F:\Lumercial_WS\FDTD_WS\results\P04_AnomalousReflection_047"
FSP = os.path.join(ROOT, "run_sw_p20.fsp")
LAMBDA, PERIOD = 850e-9, 1200e-9
K0 = 2 * np.pi / LAMBDA

s = None
try:
    s = lumapi.FDTD(hide=True)
    s.load(FSP)
    s.eval("lm = layoutmode;")
    lm = float(s.getv("lm"))
    r = s.getresult("field_big", "E")
    x = np.array(r["x"]).ravel()
    z = np.array(r["z"]).ravel()
    E = np.squeeze(np.array(r["E"]))
finally:
    if s is not None:
        s.close()

if E.ndim == 4:
    E = E[:, 0, :, :]
ey = E[:, :, 1].T          # -> (nz, nx)
mag = np.abs(ey)

# ---- isolate the bound mode by its lateral wavevector --------------------
# The propagating orders sit at kx = 0.342 k0 (+ m*2pi/1.2um Bloch harmonics);
# the m = 1 harmonic lands exactly on kx = 1.05 k0, which is evanescent in air.
# Fourier-filtering at kx = k_SW therefore keeps only the bound component.
kx_sw = K0 * (np.sin(np.radians(20)) + LAMBDA / PERIOD)
w = np.gradient(x)
a_sw = np.array([abs(np.sum(ey[k] * w * np.exp(-1j * kx_sw * x)))
                 for k in range(z.size)])

# fit A*exp(-z/L) + C for z > 0; for a fixed L the model is linear in (A, C),
# so a grid search over L + closed-form least squares is enough (no scipy here)
zsel = (z > 0.0) & (z < 1.45e-6)
zz, yy = z[zsel], np.maximum(a_sw[zsel], 1e-12)

best = (np.inf, None, None, None)      # sse, L, A, C
for L in np.linspace(50e-9, 2000e-9, 2000):
    basis = np.exp(-zz / L)
    G = np.column_stack([basis, np.ones_like(zz)])
    coef, *_ = np.linalg.lstsq(G, yy, rcond=None)
    A, C = coef
    if A < 0 or C < 0:
        continue
    sse = float(np.sum((G @ coef - yy) ** 2))
    if sse < best[0]:
        best = (sse, L, A, C)
_, decay_len, A_fit, C_bg = best


def model(zz, A, L, C):
    return A * np.exp(-zz / L) + C


decay_theory = 1.0 / np.sqrt(kx_sw ** 2 - K0 ** 2)

# ---- CSV ----
csv = os.path.join(DEST, "sw_field_ey_xz_theta_i_+20deg.csv")
sx = max(1, x.size // 800)
sz = max(1, z.size // 300)
xs, zs = x[::sx], z[::sz]
with open(csv, "w", encoding="utf-8") as fh:
    fh.write("# |Ey(x,z)|, field_big (2D Y-normal DFT), 850 nm, "
             "paper theta_i = +20 deg (Lumerical angle theta = -20)\n")
    fh.write("# rows = z (m), columns = x (m); decimated %dx%d\n" % (sx, sz))
    fh.write("# companion decay table: z_m, fourier_amplitude_at_kx_sw, "
             "lateral_modulation_rms\n")
    fh.write("z_m," + ",".join("%.6e" % v for v in xs) + "\n")
    for k in range(zs.size):
        fh.write("%.6e," % zs[k] + ",".join(
            "%.6e" % mag[k * sz, j * sx] for j in range(xs.size)) + "\n")
    fh.write("\n# decay of the bound mode (Fourier amplitude at kx = 1.05 k0)\n")
    fh.write("# z_m,kx_sw_amplitude,lateral_modulation_rms\n")
    mod_rms = np.sqrt(((mag - mag.mean(axis=1, keepdims=True)) ** 2).mean(axis=1))
    for k in range(z.size):
        fh.write("%.6e,%.6e,%.6e\n" % (z[k], a_sw[k], mod_rms[k]))

# ---- figure ----
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.0), dpi=160,
                               gridspec_kw={"width_ratios": [1.55, 1]})

zlo, zhi = -0.45, 0.45
sel_z = (z >= zlo * 1e-6) & (z <= zhi * 1e-6)
X, Z = np.meshgrid(x * 1e6, z[sel_z] * 1e6)
sub = mag[np.ix_(sel_z, np.arange(x.size))]
vmax = np.percentile(sub, 99.0)
im = ax1.pcolormesh(X, Z, sub, cmap="inferno", shading="auto", vmin=0, vmax=vmax)
ax1.axhline(-0.29, color="#4fc3f7", lw=0.8, ls="--")
ax1.axhline(-0.32, color="#4fc3f7", lw=0.8, ls=":")
ax1.set_xlabel("x (um)")
ax1.set_ylabel("z (um)")
ax1.set_xlim(0, 12)
ax1.set_title(r"(a) $|E_y(x,z)|$ near the surface, "
              r"$\theta_i=+20^\circ>\theta_{ic}$")
cb = fig.colorbar(im, ax=ax1, pad=0.015)
cb.set_label("|Ey| (V/m)")

ax2.semilogy(z * 1e6, np.maximum(a_sw, 1e-12), "o-", ms=2.5, lw=1.0,
             color="#e74c3c", label=r"$|E_y|$ at $k_x=1.05k_0$")
zz = np.linspace(0.0, 1.45, 60)
ax2.semilogy(zz, model(zz * 1e-6, A_fit, decay_len, C_bg), "--", lw=1.3,
             color="#2980b9",
             label=r"fit: $1/e$ = %.0f nm (theory %.0f nm)"
                   % (decay_len * 1e9, decay_theory * 1e9))
ax2.axvline(0, color="#7f8c8d", ls=":", lw=0.8)
ax2.set_xlabel("z (um)")
ax2.set_ylabel("Fourier amplitude (V m)")
ax2.set_title("(b) bound-mode decay away from the surface")
ax2.grid(alpha=0.3, which="both")
ax2.legend(fontsize=7.5, loc="lower left")

fig.tight_layout()
png = os.path.join(DEST, "sw_field_ey_xz_theta_i_+20deg.png")
fig.savefig(png)
plt.close(fig)

info = {
    "fsp": FSP,
    "layoutmode": lm,
    "paper_theta_i_deg": 20.0,
    "lumerical_angle_theta_deg": -20.0,
    "kx_over_k0": round(float(np.sin(np.radians(20)) + LAMBDA / PERIOD), 4),
    "paper_kx": "2*pi/811 nm^-1 = 1.048 k0",
    "decay_length_measured_m": round(float(decay_len), 9),
    "decay_length_theory_m": round(float(decay_theory), 9),
    "decay_length_note": "fit of A*exp(-z/L)+C to the Fourier amplitude at "
                         "kx = 1.0504 k0 for 0 < z < 1.45 um; the propagating "
                         "orders sit at kx = 0.342 k0 and are filtered out. "
                         "Theory: 1/sqrt(kx^2-k0^2) = 421 nm",
    "png": png, "csv": csv,
    "n_x": int(x.size), "n_z": int(z.size),
    "solved_log": "_p0.log: Detected GPU 0 / real32 / Completed 15296 iterations / "
                   "Early termination (autoshutoff satisfied), 9.38045e-06",
}
with open(os.path.join(DEST, "sw_field_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(info, fh, ensure_ascii=False, indent=2)
print(json.dumps(info, ensure_ascii=False, indent=2))
