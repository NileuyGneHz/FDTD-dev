#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Field-monitor post-processing for a periodic unit cell: focus, phase, OAM, k-space.

Before this existed, P05 and P04 each carried its own hand-written analyser
(``_scratch/regress/2026-11-08/P05/analyze_p05.py`` and
``results/P04_AnomalousReflection_047/scripts/field_map_and_decay.py``).
Both worked, neither could run without a license, and "focal length" had two
implementations, so the number that went into a report depended on which file
you opened.  This script is the single implementation.

It reads a field monitor two ways:

    --fsp <run>.fsp --monitor <name>     open one read-only session, getresult, close
    --npz <dump>.npz                     the ``format=npz`` dump from session-control

Four measurement modes (comma-separated):

    focus    on-axis scan -> z_focus, focus_gain, transverse FWHM, DOF
    phase    unwrapped phase on a probe plane, fitted against a design phase
    oam      winding number l on a ring of a transverse plane
    kspace   in-plane FFT -> kx/k0 and exit angle; optional evanescent decay fit

Whatever the monitor is, the loader records the axes it inferred
(``axes.varying``, ``axes.prop``, ``freq.index``).  A multi-frequency monitor
without ``--wavelength-um`` is an error, never a silent ``[0]``.

    python field_map.py --self-test
    python field_map.py --npz a.npz --bg-npz b.npz --mode focus,phase \\
        --wavelength-um 0.74 --design-kind lens --design-f-um 10 \\
        --out out/ --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402

MODES = ("focus", "phase", "oam", "kspace")
AXES = ("x", "y", "z")
C0 = 299792458.0


class FieldError(Exception):
    """Input that cannot be interpreted. Always names what was actually seen."""


# --------------------------------------------------------------------------- loading
def _numeric(raw: dict) -> dict:
    """Keep only numeric arrays; v251 dicts also carry object handles."""
    out = {}
    for k, v in raw.items():
        try:
            a = np.asarray(v)
        except Exception:            # noqa: BLE001 - non-array metadata
            continue
        # "c" must be here: a field monitor's E IS complex. An earlier version of
        # this filter said "fiub", so every E array was dropped and the caller saw
        # only coordinates (D-015).
        if a.dtype.kind in "fiubc":
            out[k] = a
    return out


def load_npz(path: Path) -> dict:
    if not path.is_file():
        raise FieldError("npz not found: %s" % path)
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.keys()}


def load_fsp(fsp: Path, monitor: str, repo_root: Path) -> dict:
    """One read-only session. Imports lumapi and the shared helpers only here."""
    if not fsp.is_file():
        raise FieldError("fsp not found: %s" % fsp)
    shared = repo_root / "library" / "py"   # 2026-11-11: 从 _shared/ 迁入
    if not (shared / "lumapi_common.py").is_file():
        raise FieldError("找不到 %s（本脚本复用共享会话工具，不另写一份）" % shared)
    sys.path.insert(0, str(shared))
    from lumapi_common import get_lumapi, open_fdtd, setup_env  # noqa: E402

    setup_env(verbose=False)
    _ = get_lumapi()
    fdtd = open_fdtd()
    try:
        fdtd.load(str(fsp.resolve()))
        for cand in (monitor, monitor.lower(), monitor.upper()):
            try:
                raw = fdtd.getresult(cand, "E")
                break
            except Exception:      # noqa: BLE001 - try the next spelling
                raw = None
                continue
        if raw is None:
            raise FieldError("监视器 %r 取不到 E；可用名字请先用 "
                             "fdtd-lumerical-fsp-introspection 列一遍" % monitor)
    finally:
        try:
            fdtd.close()
        except Exception:          # noqa: BLE001
            pass
    if not isinstance(raw, dict):
        raise FieldError("getresult(%r,'E') 返回 %s，期望 dict"
                         % (monitor, type(raw).__name__))
    return _numeric(raw)


# --------------------------------------------------------------------------- grid
def _components(raw: dict) -> np.ndarray:
    """Stack the three Cartesian components as the trailing axis."""
    if "E" in raw:
        E = np.asarray(raw["E"])
        if E.dtype.kind != "c":
            E = E.astype(complex)
        if E.ndim < 2 or E.shape[-1] != 3:
            raise FieldError("E 的最后一维不是 3 个分量：shape=%r" % (E.shape,))
        return E
    if all(k in raw for k in ("Ex", "Ey", "Ez")):
        return np.stack([np.asarray(raw["Ex"]), np.asarray(raw["Ey"]),
                         np.asarray(raw["Ez"])], axis=-1).astype(complex)
    raise FieldError("npz 里既没有 E，也没有 Ex/Ey/Ez；实际键 = %s"
                     % ", ".join(sorted(raw)))


def _coord(raw: dict, axis: str) -> np.ndarray:
    a = raw.get(axis)
    if a is None:
        return np.zeros(1)
    a = np.asarray(a, dtype=float).ravel()
    return a if a.size else np.zeros(1)


def _pick_frequency(raw: dict, nf: int, wavelength_um: float | None) -> int:
    """Which frequency slice. Never guess when there is more than one."""
    if nf == 1:
        return 0
    if wavelength_um is None:
        have = ""
        for k in ("lambda", "f"):
            if k in raw:
                have = "（npz 里有 %s，请显式选一个频点）" % k
        raise FieldError(
            "场监视器有 %d 个频点，但没给 --wavelength-um%s。"
            "静默取第 0 个会在另一个波长上算出『看起来合理』的数——"
            "这正是本项目反复出现的假轮次形态。" % (nf, have))
    lam = np.asarray(raw.get("lambda", []), dtype=float).ravel()
    if lam.size == nf:
        return int(np.argmin(np.abs(lam - wavelength_um * 1e-6)))
    if lam.size == 1 and lam[0] > 1e-9:
        lam = np.full(nf, lam[0])
        return int(np.argmin(np.abs(lam - wavelength_um * 1e-6)))
    freqs = np.asarray(raw.get("f", []), dtype=float).ravel()
    if freqs.size == nf:
        target = C0 / (wavelength_um * 1e-6)
        return int(np.argmin(np.abs(freqs - target)))
    cand = [k for k in ("f", "lambda", "freq", "frequency") if k in raw]
    raise FieldError("nf=%d 但 npz 里没有可用的频率/波长轴（有 %s），"
                     "无法把 --wavelength-um 映射到频点索引" % (nf, cand or "无"))


def normalize(raw: dict, prop_axis: str | None = None,
              wavelength_um: float | None = None) -> dict:
    """(nu, nv, 3) complex field on the two varying axes, plus what was inferred."""
    E = _components(raw)
    xyz = {ax: _coord(raw, ax) for ax in AXES}
    base = int(np.prod([xyz[ax].size for ax in AXES]))
    npoints = E.size // 3
    if base <= 0 or npoints % base:
        raise FieldError("E 元素数 %d 与坐标网格 %s 不匹配（%d x %d x %d）"
                         % (E.size, {k: v.size for k, v in xyz.items()},
                            xyz["x"].size, xyz["y"].size, xyz["z"].size))
    nf = npoints // base
    k = _pick_frequency(raw, nf, wavelength_um)
    arr = E.reshape(xyz["x"].size, xyz["y"].size, xyz["z"].size, nf, 3)[:, :, :, k, :]

    varying = [ax for ax in AXES if xyz[ax].size > 1]
    if len(varying) > 2:
        raise FieldError("监视器是三维体（%s 都变化，%d 点）。本技能只处理平面；"
                         "请先在 .fsp 里把监视器改成面。" % ("/".join(varying), arr.size))

    src = "cli"
    if prop_axis is None:
        prop_axis = "z" if "z" in varying else ("y" if "y" in varying else "x")
        src = "default"
    if prop_axis not in AXES:
        raise FieldError("--prop-axis 只能是 x/y/z，收到 %r" % prop_axis)

    if len(varying) == 1:
        raise FieldError("监视器只沿 %s 变化（线监视器），没有横向剖面，"
                         "无法算焦斑/相位面；请用面监视器。旧原型在这里会算出 NaN 而不报错。"
                         % varying[0])

    trans = [ax for ax in varying if ax != prop_axis]
    if not trans:
        raise FieldError("--prop-axis %s 恰好是唯一变化的轴，没有横向轴" % prop_axis)
    trans = trans[0]
    res = {"u": xyz[trans], "v": xyz[prop_axis], "trans_axis": trans,
           "prop_axis": prop_axis, "prop_axis_source": src,
           "prop_varies": xyz[prop_axis].size > 1,
           "axes_varying": varying, "n_freq_total": nf, "freq_index": k}

    def take(i0: int, i1: int) -> np.ndarray:
        """(nx,ny,nz,3) -> (dim_i0, dim_i1, 3). The third spatial axis must be singleton."""
        other = [a for a in (0, 1, 2) if a not in (i0, i1)][0]
        return np.transpose(arr, (i0, i1, other, 3))[:, :, 0, :]

    if res["prop_varies"]:
        res["E"] = take(AXES.index(trans), AXES.index(prop_axis))
    else:
        # transverse plane: both varying axes are in-plane, the propagation axis is a slice
        i0, i1 = AXES.index(varying[0]), AXES.index(varying[1])
        res["E"] = take(i0, i1)
        res["u"], res["v"] = xyz[varying[0]], xyz[varying[1]]
        res["trans_axis"] = varying[0]
        res["prop_axis"] = [a for a in AXES if a not in varying][0]
        res["prop_axis_source"] = "invariant-axis"
    res["wavelength_um"] = wavelength_um
    return res


# --------------------------------------------------------------------------- basis
def cp_channels(E: np.ndarray) -> tuple:
    """c+ = (Ex + i Ey)/sqrt2, c- = (Ex - i Ey)/sqrt2. Same convention as P05."""
    ex, ey = E[..., 0], E[..., 1]
    return (ex + 1j * ey) / np.sqrt(2.0), (ex - 1j * ey) / np.sqrt(2.0)


def pick_channel(E_struct: np.ndarray, E_bg: np.ndarray | None,
                 basis: str, channel: str) -> tuple:
    """Return (field, label). For cpol the cross channel is decided on the background."""
    if basis == "cartesian":
        if channel not in ("total", "ex", "ey"):
            raise FieldError("cartesian 基下 --component 只能是 total/ex/ey")
        if channel == "ex":
            return E_struct[..., 0], "Ex"
        if channel == "ey":
            return E_struct[..., 1], "Ey"
        return np.sqrt(np.sum(np.abs(E_struct) ** 2, axis=-1)), "|E|"
    if basis != "cpol":
        raise FieldError("--basis 只能是 cartesian/cpol")
    sp, sm = cp_channels(E_struct)
    if channel in ("plus", "minus"):
        return (sp, sm)[0 if channel == "plus" else 1], "c_%s" % channel
    if E_bg is None:
        raise FieldError("--cp-channel auto 需要背景组（--bg-npz/--bg-fsp）："
                         "没有背景就无法判断哪一路是转换通道，猜错会得到一条"
                         "「看着像焦斑」的同偏振场。")
    bp, bm = cp_channels(E_bg)
    mp = float(np.mean(np.abs(bp) ** 2))
    mm = float(np.mean(np.abs(bm) ** 2))
    idx = 0 if mp <= mm else 1
    return (sp, sm)[idx], ("c_plus=(Ex+iEy)/sqrt2" if idx == 0 else "c_minus=(Ex-iEy)/sqrt2")


# --------------------------------------------------------------------------- focus
def _cross(u: np.ndarray, c: np.ndarray, i0: int, i1: int, half: float) -> float:
    if c[i1] == c[i0]:
        return float(u[i0])
    return float(u[i0] + (half - c[i0]) * (u[i1] - u[i0]) / (c[i1] - c[i0]))


def fwhm_contiguous(u: np.ndarray, cut: np.ndarray) -> float:
    """Half-width around the peak only.

    The old prototype took the outermost half-max crossings, so any side lobe
    above 50% inflated the number. Here we walk outward from the peak and stop
    at the first crossing, then interpolate linearly.
    """
    c = np.asarray(cut, dtype=float)
    if c.size < 3 or not np.any(np.isfinite(c)):
        return float("nan")
    c = c - np.nanmin(c)
    k = int(np.nanargmax(c))
    if c[k] <= 0:
        return float("nan")
    half = 0.5 * c[k]
    i = k
    while i > 0 and c[i] >= half:
        i -= 1
    left = float(u[k]) if c[i] >= half else _cross(u, c, i, i + 1, half)
    j = k
    while j < c.size - 1 and c[j] >= half:
        j += 1
    right = float(u[k]) if c[j] >= half else _cross(u, c, j - 1, j, half)
    return float(right - left)


def focus_metrics(E: np.ndarray, u: np.ndarray, v: np.ndarray,
                  half_width_um: float, z_start_um: float) -> dict:
    if v.size < 4:
        raise FieldError("沿传播轴只有 %d 个采样点，算不出焦斑" % v.size)
    u_um, v_um = u * 1e6, v * 1e6
    I = np.abs(E) ** 2
    on_axis = np.abs(u_um) <= half_width_um
    if not on_axis.any():
        raise FieldError("|u| <= %.3f um 内没有采样点（横向步长 %.4f um）"
                         % (half_width_um, float(np.mean(np.diff(u_um)))))
    prof = I[on_axis, :].mean(axis=0)

    pos = v_um > z_start_um
    out = {"z_start_um": z_start_um, "half_width_um": half_width_um,
           "n_on_axis": int(on_axis.sum())}
    if not pos.any():
        out.update(z_focus_um=float("nan"), focus_gain=float("nan"),
                   has_real_focus=False, fwhm_um=float("nan"), dof_um=float("nan"))
        return out
    i_start = int(np.where(pos)[0][0])
    i_focus = int(np.where(pos)[0][np.argmax(prof[pos])])
    z_focus = float(v_um[i_focus])
    gain = float(prof[i_focus] / prof[i_start]) if prof[i_start] > 0 else float("nan")

    cut = I[:, i_focus]
    fwhm = fwhm_contiguous(u_um, cut)

    dof = float("nan")
    if prof[i_focus] > 0:
        half = 0.5 * prof[i_focus]
        a = i_focus
        while a > 0 and prof[a] >= half:
            a -= 1
        b = i_focus
        while b < prof.size - 1 and prof[b] >= half:
            b += 1
        dof = float(v_um[b] - v_um[a])

    neg = v_um < -abs(z_start_um)
    # An off-axis focus is the failure mode this metric cannot see: the on-axis scan
    # looks at x=0 while the beam focuses at x=2 um, and "no focus" is reported for a
    # lens that does focus. Publish the ratio so the wrong answer is visible.
    off_peak = 0.0
    if (~on_axis).any():
        off = I[~on_axis][:, pos]
        off_peak = float(off.max()) if off.size else 0.0
    on_peak = float(prof.max())
    out.update(
        z_focus_um=z_focus,
        focus_gain=gain,
        has_real_focus=bool(np.isfinite(gain) and gain > 1.2 and np.isfinite(fwhm)),
        fwhm_um=fwhm,
        dof_um=dof,
        peak_I_on_axis=on_peak,
        off_axis_ratio=(off_peak / on_peak) if on_peak > 0 else float("nan"),
        z_virtual_um=float(v_um[np.argmax(prof[neg])]) if neg.any() else float("nan"),
    )
    if not out["has_real_focus"] and out["off_axis_ratio"] > 2.0:
        out["warning"] = ("横向 |u|>%.2f um 处的峰值是轴上的 %.1f 倍：焦点不在轴上，"
                          "本指标的 on-axis 扫描看不到它。请换 --half-width-um 或"
                          "把横向窗口挪到峰位附近再判。" % (half_width_um, out["off_axis_ratio"]))
    return out


# --------------------------------------------------------------------------- phase
def design_phase(u_m: np.ndarray, kind: str, wavelength_um: float | None,
                 f_um: float | None, theta_deg: float | None) -> np.ndarray:
    if kind == "none":
        return np.zeros_like(u_m)
    if wavelength_um is None:
        raise FieldError("design-kind=%s 需要 --wavelength-um" % kind)
    k0 = 2 * np.pi / (wavelength_um * 1e-6)
    if kind == "lens":
        if not f_um:
            raise FieldError("design-kind=lens 需要 --design-f-um")
        f = f_um * 1e-6
        return k0 * (np.sqrt(f ** 2 + u_m ** 2) - abs(f))
    if kind == "tilt":
        if theta_deg is None:
            raise FieldError("design-kind=tilt 需要 --design-theta-deg")
        return k0 * np.sin(np.deg2rad(theta_deg)) * u_m
    raise FieldError("design-kind 只能是 lens/tilt/none，收到 %r" % kind)


def phase_metrics(E: np.ndarray, u: np.ndarray, v: np.ndarray, probe_um: float,
                  kind: str, wavelength_um: float | None, f_um: float | None,
                  theta_deg: float | None) -> dict:
    u_um, v_um = u * 1e6, v * 1e6
    j = int(np.argmin(np.abs(v_um - probe_um)))
    amp = E[:, j]
    ph = np.unwrap(np.angle(amp))
    des = design_phase(u, kind, wavelength_um, f_um, theta_deg)
    des_wrapped = np.unwrap(np.angle(np.exp(1j * (des - des[0]))))

    # Weight by amplitude: where |E| -> 0 the phase is noise, and an unweighted
    # fit lets the dark edge decide the slope (measured: -0.743 instead of -1).
    mag = np.abs(amp)
    rel = mag / mag.max() if mag.max() > 0 else mag
    w = rel ** 2
    used = rel > 0.1
    span = (float(np.nanmax(ph[used]) - np.nanmin(ph[used]))
            if used.sum() > 1 else float("nan"))
    out = {"probe_z_um": float(v_um[j]), "design_kind": kind,
           "n_used_frac": float(used.mean()) if used.size else 0.0,
           "phase_swing_rad": span,
           "phase_swing_over_2pi": span / (2 * np.pi) if np.isfinite(span) else float("nan"),
           "fit_note": "残差与斜率按 |E|^2 加权；|E|<10% 峰值的点不参与相位摆幅统计"}
    if kind == "none":
        out.update(fit_slope=None, fit_slope_abs=None,
                   fit_offset_rad=float(np.average(ph, weights=w)) if w.sum() > 0 else float("nan"),
                   fit_rms_rad=float(np.sqrt(np.average((ph - np.average(ph, weights=w)) ** 2,
                                                        weights=w))) if w.sum() > 0 else float("nan"),
                   fit_note="design-kind=none：斜率无定义（设计相位恒为 0），"
                            "只报相位本身的加权离散度")
        return out
    A = np.vstack([des_wrapped, np.ones_like(des_wrapped)]).T
    sw = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(A * sw[:, None], ph * sw, rcond=None)
    pred = A @ coef
    res = float(np.sqrt(np.average((ph - pred) ** 2, weights=w))) if w.sum() > 0 else float("nan")
    out.update(fit_slope=float(coef[0]), fit_slope_abs=abs(float(coef[0])),
               fit_offset_rad=float(coef[1]), fit_rms_rad=res,
               fit_note="measured = slope * design + offset；|slope| 接近 1 才说明"
                        "相位面正确，符号是极性信息（收敛透镜为 -1）")
    return out


# --------------------------------------------------------------------------- oam
def oam_metrics(E: np.ndarray, u: np.ndarray, v: np.ndarray,
                ring_radius_um: float | None, n_theta: int) -> dict:
    u_um, v_um = u * 1e6, v * 1e6
    if u_um.size < 3 or v_um.size < 3:
        raise FieldError("OAM 需要在横向平面上采样（u、v 都要 >=3 点），"
                         "实际 %d x %d；若监视器是 x-z 剖面，OAM 无从谈起"
                         % (u_um.size, v_um.size))
    r0 = ring_radius_um or 0.4 * min(np.abs(u_um).max(), np.abs(v_um).max())
    if r0 <= 0:
        raise FieldError("环半径必须为正，收到 %r" % r0)
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    iu = np.abs(u_um[None, :] - (r0 * np.cos(th))[:, None]).argmin(axis=1)
    jv = np.abs(v_um[None, :] - (r0 * np.sin(th))[:, None]).argmin(axis=1)
    samp = E[iu, jv]
    mag = np.abs(samp)
    good = mag > 0.2 * float(np.median(mag)) if np.median(mag) > 0 else np.zeros_like(mag, bool)
    out = {"ring_radius_um": float(r0), "n_theta": int(n_theta),
           "n_used": int(good.sum())}
    if good.sum() < max(16, n_theta // 4):
        out.update(oam_charge=None, oam_fit_rms=None,
                   note="环上有效点数 %d 太少（振幅接近 0），不给电荷" % int(good.sum()))
        return out
    ph = np.unwrap(np.angle(samp))
    A = np.vstack([th, np.ones_like(th)]).T
    coef, *_ = np.linalg.lstsq(A[good], ph[good], rcond=None)
    l = float(coef[0])
    resid = ph[good] - (A[good] @ coef)
    out.update(oam_charge=l, oam_charge_round=int(round(l)),
               oam_fit_rms=float(np.sqrt(np.mean(resid ** 2))),
               note="phi(theta) 的线性斜率；E ~ exp(i*l*theta)")
    return out


# --------------------------------------------------------------------------- kspace
def kspace_metrics(E: np.ndarray, u: np.ndarray, v: np.ndarray, probe_um: float,
                   wavelength_um: float | None, decay_kx: float | None,
                   n_peaks: int) -> dict:
    if wavelength_um is None:
        raise FieldError("kspace 需要 --wavelength-um")
    u_um, v_um = u * 1e6, v * 1e6
    j = int(np.argmin(np.abs(v_um - probe_um)))
    du = float(np.mean(np.diff(u)))
    n = u.size
    k0 = 2 * np.pi / (wavelength_um * 1e-6)
    # Zero-padding (x16) + parabolic peak refinement: a raw FFT on 10 um of grid
    # quantises kx to 0.074 k0 per bin, which is larger than the physics tolerance.
    npad = 16 * n
    F = np.fft.fftshift(np.fft.fft(E[:, j], npad))
    kx = 2 * np.pi * np.fft.fftshift(np.fft.fftfreq(npad, d=du))
    P = np.abs(F) ** 2
    order = np.argsort(P)[::-1]
    peaks = []
    for idx in order[: max(1, n_peaks * 4)]:
        if peaks and any(abs(int(idx) - p["index"]) <= npad // (4 * n) for p in peaks):
            continue
        idx = int(idx)
        shift = 0.0
        if 0 < idx < P.size - 1:
            y0, y1, y2 = np.sqrt(P[idx - 1]), np.sqrt(P[idx]), np.sqrt(P[idx + 1])
            den = y0 - 2 * y1 + y2
            if den != 0:
                shift = 0.5 * (y0 - y2) / den
        kx_pk = float(np.interp(idx + shift, np.arange(kx.size), kx))
        ratio = float(kx_pk / k0)
        peaks.append({"index": int(idx), "kx_over_k0": ratio,
                      "angle_deg": float(np.rad2deg(np.arcsin(ratio)))
                      if abs(ratio) <= 1 else None,
                      "bin_width_kx_over_k0": float(abs(kx[1] - kx[0]) / k0),
                      "power_frac": float(P[idx] / P.sum()) if P.sum() > 0 else float("nan")})
        if len(peaks) >= n_peaks:
            break
    out = {"probe_z_um": float(v_um[j]), "k0_per_um": float(k0 * 1e-6),
           "peaks": peaks, "kx_over_k0_main": peaks[0]["kx_over_k0"],
           "angle_deg_main": peaks[0]["angle_deg"]}
    if decay_kx is None:
        return out
    kx_t = decay_kx * k0
    w = np.gradient(u)
    amp = np.array([abs(np.sum(E[:, i] * w * np.exp(-1j * kx_t * u)))
                    for i in range(v.size)])
    sel = (v > 0) & (v < v.max())
    zz, yy = v[sel], np.maximum(amp[sel], 1e-12)
    best = (np.inf, None, None, None)
    for L in np.linspace(0.05e-6, 2.0e-6, 1200):
        G = np.column_stack([np.exp(-zz / L), np.ones_like(zz)])
        coef, *_ = np.linalg.lstsq(G, yy, rcond=None)
        if coef[0] < 0 or coef[1] < 0:
            continue
        sse = float(np.sum((G @ coef - yy) ** 2))
        if sse < best[0]:
            best = (sse, float(L), float(coef[0]), float(coef[1]))
    out["decay"] = {"kx_over_k0": float(decay_kx),
                    "decay_length_um": best[1] * 1e6 if best[1] else None,
                    "theory_um": (1.0 / np.sqrt(kx_t ** 2 - k0 ** 2) * 1e6)
                    if abs(decay_kx) > 1 else None,
                    "fit_A": best[2], "fit_C": best[3],
                    "note": "A*exp(-v/L)+C 网格搜索；theory 只在 |kx|>k0 时有定义"}
    return out


# --------------------------------------------------------------------------- self-test
def _synth_plane(nx=401, nz=301, x_span=10e-6, z_span=30e-6):
    x = np.linspace(-x_span / 2, x_span / 2, nx)
    z = np.linspace(-z_span / 2, z_span / 2, nz)
    return x, z


def self_test() -> int:
    """Analytic ground truth. No engine, no license, no file."""
    rows = []

    def check(name, got, want, tol, note=""):
        ok = got is not None and np.isfinite(got) and abs(got - want) <= tol
        rows.append({"case": name, "got": None if got is None else float(got),
                     "want": float(want), "tol": float(tol), "pass": bool(ok),
                     "note": note})
        return ok

    x, z = _synth_plane()
    X, Z = np.meshgrid(x, z, indexing="ij")
    lam = 0.74e-6
    k0 = 2 * np.pi / lam
    f = 10e-6

    # Focus truth is an analytic paraxial Gaussian beam whose waist sits at z = f.
    # A phase mask alone is NOT a focus: E(x,z) = mask(x) has the same transverse
    # phase at every z, so its on-axis intensity is flat and argmax lands at the
    # first sample. That was this test's first version, and it failed for the
    # right reason (measured z_focus = 1.0 = z_start).
    w0, zR = 0.8e-6, None
    zR = np.pi * w0 ** 2 / lam
    q = (Z - f) + 1j * zR
    Egb = np.zeros((x.size, z.size, 3), dtype=complex)
    Egb[:, :, 0] = (zR / q) * np.exp(-1j * k0 * X ** 2 / (2 * q))
    fo = focus_metrics(Egb[:, :, 0], x, z, half_width_um=0.5, z_start_um=1.0)
    check("focus_z (gauss waist f=10um)", fo["z_focus_um"], 10.0, 0.25)
    rows[-1]["note"] = "gain=%.2f, fwhm=%.3f um (2w0=%.1f)" % (
        fo["focus_gain"], fo["fwhm_um"], 2 * w0 * 1e6)
    rows.append({"case": "focus_gain>5", "got": fo["focus_gain"], "want": 5.0,
                 "tol": 0.0, "pass": bool(fo["focus_gain"] > 5), "note": "严格大于"})

    # Metalens exit plane: a phase mask, no propagation. Used for the phase test.
    ph = -k0 * (np.sqrt(f ** 2 + X ** 2) - f)
    ap = (np.abs(X) <= 4.5e-6).astype(float)
    E = np.zeros((x.size, z.size, 3), dtype=complex)
    E[:, :, 0] = ap * np.exp(1j * ph)

    # Gaussian transverse profile at the focal plane -> FWHM = 2.3548 sigma
    sig = 1.2
    cut = np.exp(-(x * 1e6) ** 2 / (2 * sig ** 2))
    rows.append({"case": "fwhm (gauss sigma=1.2um)",
                 "got": fwhm_contiguous(x * 1e6, cut),
                 "want": 2 * np.sqrt(2 * np.log(2)) * sig, "tol": 0.03,
                 "pass": abs(fwhm_contiguous(x * 1e6, cut)
                             - 2 * np.sqrt(2 * np.log(2)) * sig) <= 0.03,
                 "note": "旧定义（最外交点）在两瓣场上会虚高"})

    # phase: lens design must be recovered with slope 1
    # design_phase() uses +k0(r-f) (diverging convention), the converging mask is
    # its negative, so the signed slope must be -1: |slope|=1 is the correctness
    # statement, the sign is the polarity statement.
    pm = phase_metrics(E[:, :, 0], x, z, probe_um=2.0, kind="lens",
                       wavelength_um=0.74, f_um=10.0, theta_deg=None)
    check("phase_slope (lens 10um)", pm["fit_slope"], -1.0, 0.05)
    # negative control: with design-kind=none the slope is undefined by design
    pm2 = phase_metrics(E[:, :, 0], x, z, probe_um=2.0, kind="none",
                        wavelength_um=0.74, f_um=10.0, theta_deg=None)
    rows.append({"case": "phase slope None on design=none", "got": np.nan,
                 "want": 0.0, "tol": 0.0,
                 "pass": pm2["fit_slope"] is None, "note": "必须显式 None，不是 0"})

    # OAM: transverse plane, E ~ exp(i l theta)
    nx = 201
    xa = np.linspace(-4e-6, 4e-6, nx)
    ya = np.linspace(-4e-6, 4e-6, nx)
    XA, YA = np.meshgrid(xa, ya, indexing="ij")
    r = np.hypot(XA, YA)
    th = np.arctan2(YA, XA)
    for l_true in (3, -2):
        Et = np.zeros((nx, nx, 3), dtype=complex)
        Et[:, :, 0] = (r < 3.5e-6) * np.exp(1j * l_true * th) * np.exp(-(r / 3e-6) ** 2)
        g2 = normalize({"E": Et.reshape(nx, nx, 1, 1, 3), "x": xa, "y": ya},
                       prop_axis="z")
        om = oam_metrics(g2["E"][:, :, 0], g2["u"], g2["v"], ring_radius_um=None,
                         n_theta=720)
        check("oam_charge (l=%d)" % l_true, om["oam_charge"], l_true, 0.05)

    # k-space: plane wave at 20 deg
    th_deg = 20.0
    E3 = np.zeros((x.size, 1, z.size, 1, 3), dtype=complex)
    E3[:, 0, :, 0, 0] = np.exp(1j * k0 * np.sin(np.deg2rad(th_deg)) * X)
    g3 = normalize({"E": E3, "x": x, "z": z})
    ks = kspace_metrics(g3["E"][:, :, 0], g3["u"], g3["v"], probe_um=0.0,
                        wavelength_um=0.74, decay_kx=None, n_peaks=3)
    check("kspace kx/k0 (20deg)", ks["kx_over_k0_main"], np.sin(np.deg2rad(th_deg)), 0.01)

    # guard: multi-frequency without a wavelength must raise
    raw = {"E": np.zeros((x.size, 1, z.size, 3, 3), dtype=complex), "x": x, "z": z}
    raised = False
    try:
        normalize(raw)
    except FieldError:
        raised = True
    rows.append({"case": "nf=3 without --wavelength raises", "got": None, "want": 0.0,
                 "tol": 0.0, "pass": raised, "note": "静默取 [0] 是旧原型的病"})

    bad = [r for r in rows if not r["pass"]]
    for r in rows:
        print("%-38s got=%-12s want=%-10s %s"
              % (r["case"],
                 "None" if r["got"] is None else "%.6g" % r["got"],
                 "%.6g" % r["want"], "PASS" if r["pass"] else "FAIL"))
    print("\n%d/%d pass" % (len(rows) - len(bad), len(rows)))
    return 0 if not bad else 1


# --------------------------------------------------------------------------- main
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def write_outputs(out: Path, grid: dict, metrics: dict, curves: dict) -> list:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    mp = out / "field_metrics.json"
    mp.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append(str(mp))
    u_um, v_um = grid["u"] * 1e6, grid["v"] * 1e6
    # "I" first: `figure --kind field` takes the first 2-D array it finds.
    arrays = {"I": (np.abs(grid["E"]) ** 2).sum(axis=-1),
              "u_um": u_um, "v_um": v_um,
              "phase_rad": np.angle(grid["E"][..., 0])}
    npz = out / "field_map.npz"
    np.savez_compressed(npz, **arrays)      # "I" is written first: figure --kind field
    written.append(str(npz))
    for name, (hdr, cols) in curves.items():
        p = out / ("%s.csv" % name)
        with p.open("w", encoding="utf-8") as fh:
            fh.write(",".join(hdr) + "\n")
            for i in range(len(cols[0])):
                fh.write(",".join("%.8g" % c[i] for c in cols) + "\n")
        written.append(str(p))
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="场监视器后处理：焦距/相位面/OAM/k 空间")
    ap.add_argument("--self-test", action="store_true", help="跑解析真值自检，不读文件")
    ap.add_argument("--fsp", default=None, help="场监视器所在的 .fsp（开一次只读会话）")
    ap.add_argument("--monitor", default="field", help="监视器名（--fsp 时用）")
    ap.add_argument("--npz", default=None, help="session-control 的 format=npz dump")
    ap.add_argument("--bg-fsp", default=None)
    ap.add_argument("--bg-npz", default=None)
    ap.add_argument("--bg-conj", action="store_true",
                    help="背景场先取共轭（-bk 工程里结构全 disabled，E_LCP_bg=conj(E_RCP_bg)）")
    ap.add_argument("--mode", default="focus", help="focus,phase,oam,kspace 可组合")
    ap.add_argument("--prop-axis", default=None, choices=list(AXES))
    ap.add_argument("--wavelength-um", type=float, default=None)
    ap.add_argument("--basis", default="cartesian", choices=["cartesian", "cpol"])
    ap.add_argument("--component", default="total",
                    help="cartesian: total/ex/ey；cpol: auto/plus/minus")
    ap.add_argument("--cp-channel", default="auto", choices=["auto", "plus", "minus"])
    ap.add_argument("--half-width-um", type=float, default=0.5, help="轴上取平均的横向半宽")
    ap.add_argument("--z-start-um", type=float, default=1.0, help="焦斑扫描起点")
    ap.add_argument("--probe-z-um", type=float, default=0.5, help="相位/k 空间的取样面")
    ap.add_argument("--design-kind", default="lens", choices=["lens", "tilt", "none"])
    ap.add_argument("--design-f-um", type=float, default=None)
    ap.add_argument("--design-theta-deg", type=float, default=None)
    ap.add_argument("--ring-radius-um", type=float, default=None)
    ap.add_argument("--n-theta", type=int, default=720)
    ap.add_argument("--n-peaks", type=int, default=3)
    ap.add_argument("--decay-kx", type=float, default=None,
                    help="在 kx/k0 = 该值处做倏逝衰减拟合（P04 的束缚模）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    modes = [m.strip().lower() for m in args.mode.split(",") if m.strip()]
    bad = [m for m in modes if m not in MODES]
    if bad:
        ap.error("未知 --mode %s（可选 %s）" % (bad, list(MODES)))
    if bool(args.fsp) == bool(args.npz):
        ap.error("--fsp 与 --npz 必须二选一")
    if not (args.out or args.dry_run):
        ap.error("--out 必填（或用 --dry-run 只看会算什么）")

    root = _repo_root()
    try:
        if args.npz:
            src = load_npz(Path(args.npz))
            src_name = str(Path(args.npz))
        else:
            src = load_fsp(Path(args.fsp), args.monitor, root)
            src_name = "%s:%s" % (args.fsp, args.monitor)
        grid = normalize(src, args.prop_axis, args.wavelength_um)

        bg = None
        if args.bg_npz or args.bg_fsp:
            if args.bg_npz:
                bg = normalize(load_npz(Path(args.bg_npz)), args.prop_axis,
                               args.wavelength_um)
            else:
                bg = normalize(load_fsp(Path(args.bg_fsp), args.monitor, root),
                               args.prop_axis, args.wavelength_um)
            if bg["E"].shape != grid["E"].shape:
                raise FieldError("结构组 %s 与背景组 %s 的网格不同，不能相减"
                                 % (grid["E"].shape, bg["E"].shape))
            if args.bg_conj:
                bg["E"] = np.conj(bg["E"])

        if args.basis == "cpol":
            want = args.cp_channel
            if want == "auto" and args.component in ("plus", "minus"):
                want = args.component
            if bg is not None:
                # Subtract per Cartesian component, THEN project: subtracting an
                # already-projected scalar would double-count the CP rotation.
                rel = grid["E"] - bg["E"]
                field, label = pick_channel(rel, bg["E"], "cpol", want)
            else:
                field, label = pick_channel(grid["E"], None, "cpol", want)
        else:
            field, label = pick_channel(grid["E"], None, "cartesian", args.component)

        metrics = {
            "source": src_name, "mode": modes, "component": label,
            "basis": args.basis, "wavelength_um": args.wavelength_um,
            "axes": {"varying": grid["axes_varying"], "prop": grid["prop_axis"],
                     "prop_axis_source": grid["prop_axis_source"],
                     "transverse": grid["trans_axis"],
                     "u_range_um": [float(grid["u"].min() * 1e6),
                                    float(grid["u"].max() * 1e6)],
                     "v_range_um": [float(grid["v"].min() * 1e6),
                                    float(grid["v"].max() * 1e6)]},
            "freq": {"n_total": grid["n_freq_total"], "index": grid["freq_index"]},
            "background_subtracted": bg is not None,
        }
        curves = {}
        u_um, v_um = grid["u"] * 1e6, grid["v"] * 1e6
        I = np.abs(field) ** 2

        if "focus" in modes:
            if not grid["prop_varies"]:
                raise FieldError("focus 需要沿传播轴变化的监视器（x-z 剖面），"
                                 "当前 %s 轴只有一个切片" % grid["prop_axis"])
            metrics["focus"] = focus_metrics(field, grid["u"], grid["v"],
                                             args.half_width_um, args.z_start_um)
            on_axis = np.abs(u_um) <= args.half_width_um
            prof = I[on_axis, :].mean(axis=0)
            curves["focus_profile"] = (["v_um", "I_on_axis"],
                                       [v_um, prof / (prof.max() or 1.0)])
            k = int(np.argmin(np.abs(v_um - metrics["focus"]["z_focus_um"])))
            curves["focus_cut"] = (["u_um", "I_cut"], [u_um, I[:, k]])

        if "phase" in modes:
            if not grid["prop_varies"]:
                raise FieldError("phase 需要在传播轴上有多个切面（x-z 剖面）才能选探针面；"
                                 "当前 %s 轴只有一个切片" % grid["prop_axis"])
            metrics["phase"] = phase_metrics(field, grid["u"], grid["v"],
                                             args.probe_z_um, args.design_kind,
                                             args.wavelength_um, args.design_f_um,
                                             args.design_theta_deg)
            j = int(np.argmin(np.abs(v_um - metrics["phase"]["probe_z_um"])))
            ph = np.unwrap(np.angle(field[:, j]))
            des = design_phase(grid["u"], args.design_kind, args.wavelength_um,
                               args.design_f_um, args.design_theta_deg)
            curves["phase_profile"] = (["u_um", "phase_rad", "phase_design_rad"],
                                       [u_um, ph, np.unwrap(np.angle(np.exp(1j * (des - des[0]))))])

        if "oam" in modes:
            if grid["prop_varies"]:
                raise FieldError("oam 需要横向平面监视器（法向 = 传播轴 %s），"
                                 "当前数据里 %s 也在变化——这是 x-z 剖面，"
                                 "方位角相位无从谈起" % (grid["prop_axis"], grid["prop_axis"]))
            metrics["oam"] = oam_metrics(field, grid["u"], grid["v"],
                                         args.ring_radius_um, args.n_theta)

        if "kspace" in modes:
            metrics["kspace"] = kspace_metrics(field, grid["u"], grid["v"],
                                               args.probe_z_um, args.wavelength_um,
                                               args.decay_kx, args.n_peaks)
            j = int(np.argmin(np.abs(v_um - args.probe_z_um)))
            du = float(np.mean(np.diff(grid["u"])))
            k0 = 2 * np.pi / (args.wavelength_um * 1e-6)
            kx = 2 * np.pi * np.fft.fftshift(np.fft.fftfreq(grid["u"].size, d=du)) / k0
            P = np.abs(np.fft.fftshift(np.fft.fft(field[:, j]))) ** 2
            curves["kspace"] = (["kx_over_k0", "power_norm"], [kx, P / (P.max() or 1.0)])

        if args.dry_run:
            print(json.dumps({"dry_run": True, "would_compute": modes,
                              "axes": metrics["axes"], "freq": metrics["freq"],
                              "component": label}, indent=2, ensure_ascii=False))
            return 0

        written = write_outputs(Path(args.out), grid, metrics, curves)
        metrics["written"] = written
        if args.json:
            print(json.dumps(metrics, indent=2, ensure_ascii=False))
        else:
            print("source : %s" % src_name)
            print("axes   : varying=%s prop=%s (%s) trans=%s"
                  % (metrics["axes"]["varying"], metrics["axes"]["prop"],
                     metrics["axes"]["prop_axis_source"],
                     metrics["axes"]["transverse"]))
            print("freq   : index %d / %d" % (metrics["freq"]["index"],
                                              metrics["freq"]["n_total"]))
            print("comp   : %s" % label)
            for m in modes:
                print("%-7s: %s" % (m, json.dumps(metrics[m], ensure_ascii=False)))
            print("out    : %s" % args.out)
        return 0
    except FieldError as e:
        print("FieldError: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
