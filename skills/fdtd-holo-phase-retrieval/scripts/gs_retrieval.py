#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gerchberg-Saxton phase design for a phase-only metasurface hologram.

Consumes a target intensity image, returns the phase map the hologram plane
must carry (continuous + N-level quantised), plus the reconstruction metrics
that go into an acceptance table.  Zero engine: no lumapi, no licence, no .fsp.

Why this exists as its own skill instead of a stage-4 add-on: stage 4
(``fdtd-lumerical-phase-retrieval``) *extracts* dphi from simulated fields,
this one *designs* the phase a simulation should reproduce.  Opposite
directions; conflating them is how an agent ends up "verifying" a design
against the number it just produced.

Two propagators, both unitary where it matters:

    fourier            unitary FFT, image-plane pitch = lam*z/(N*dx)
                       (lens / k-space geometry; the hologram-design default)
    angular_spectrum   exact scalar transfer function, same grid in and out
                       (near field; refuses dx > lam/2 because that aliases)

Phase 1 of the GS loop is the hologram-plane constraint (amplitude = the
aperture, phase free); phase 2 is the image-plane constraint (amplitude =
target, phase free).  Both are projections, so the amplitude error is
non-increasing — ``rmse_hist`` is the audit trail, not decoration.

    python gs_retrieval.py --self-test
    python gs_retrieval.py --config holo.json --out out/ --json
    python gs_retrieval.py --config holo.json --dry-run
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402

METHODS = ("fourier", "angular_spectrum")
DEFAULT_LEVELS = (2, 4, 8)
EPS = 1e-30


class GSError(Exception):
    """Input that cannot be interpreted. Always names what was actually seen."""


# --------------------------------------------------------------------------- IO guards
def npz_arrays(raw: dict) -> dict:
    """Keep numeric non-empty arrays only; complex MUST survive.

    The ``"c"`` in the whitelist is not decoration: a field that dropped
    complex arrays would silently return coordinates only (D-015 happened
    exactly that way).  An empty array is an error, never a "successful" npz.
    """
    out = {}
    for k, v in raw.items():
        try:
            a = np.asarray(v)
        except Exception as exc:  # noqa: BLE001
            raise GSError("数组 %r 无法转成 ndarray: %r" % (k, exc))
        if a.size == 0:
            raise GSError("数组 %r 是空的；空 npz 看起来像成功，实际什么也没算" % k)
        if a.dtype.kind not in "fiubc":
            raise GSError("数组 %r 的 dtype=%s 不在白名单 fiubc 内" % (k, a.dtype))
        out[k] = a
    if not out:
        raise GSError("没有任何数值数组")
    return out


def load_target(path: Path, key: str | None = None) -> np.ndarray:
    """png (grey/RGB) or npz -> 2-D non-negative intensity."""
    if not path.is_file():
        raise GSError("目标图不存在: %s" % path)
    suffix = path.suffix.lower()
    if suffix == ".npz":
        with np.load(path, allow_pickle=False) as z:
            arrs = npz_arrays({k: z[k] for k in z.keys()})
        if key:
            if key not in arrs:
                raise GSError("npz 里没有键 %r；实际键 = %s" % (key, ", ".join(sorted(arrs))))
            a = arrs[key]
        else:
            pick = [k for k in ("I", "target", "amplitude", "amp") if k in arrs]
            if pick:
                a = arrs[pick[0]]
            else:
                two = [v for v in arrs.values() if v.ndim == 2]
                if len(two) != 1:
                    raise GSError("npz 里 %d 个二维数组，无法确定哪个是目标图；"
                                  "请给 target.key" % len(two))
                a = two[0]
        a = np.asarray(a)
        if a.ndim != 2:
            raise GSError("目标数组维度是 %d，期望 2" % a.ndim)
        if a.dtype.kind == "c":
            raise GSError("目标数组是复数；目标是强度，复数请先取 |E|^2")
    else:
        try:
            from matplotlib import image as mpimg  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise GSError("读 png 需要 matplotlib（已有依赖）：%r" % exc)
        a = np.asarray(mpimg.imread(str(path)))
        if a.ndim == 3:
            if a.shape[2] == 4:
                raise GSError("目标图带 alpha 通道（%s）；本技能不猜透明合成规则，"
                              "请先导出为灰度或 RGB" % (a.shape,))
            if a.shape[2] != 3:
                raise GSError("目标图通道数 %d，期望 1/3/4" % a.shape[2])
            a = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
        elif a.ndim != 2:
            raise GSError("目标图维度是 %d，期望 2 或 3" % a.ndim)
    a = a.astype(float)
    if not np.all(np.isfinite(a)):
        raise GSError("目标图含 NaN/Inf")
    if a.min() < -1e-9:
        raise GSError("目标图含负值（min=%.3g）；强度不能为负" % a.min())
    if a.max() <= 0:
        raise GSError("目标图全零；没有可恢复的内容")
    return np.clip(a, 0.0, None)


def to_square(a: np.ndarray) -> np.ndarray:
    """Centre-pad to square so the aspect ratio survives resampling."""
    ny, nx = a.shape
    if ny == nx:
        return a
    s = max(ny, nx)
    out = np.zeros((s, s), float)
    y0, x0 = (s - ny) // 2, (s - nx) // 2
    out[y0:y0 + ny, x0:x0 + nx] = a
    return out


def resample_bilinear(a: np.ndarray, n: int) -> np.ndarray:
    ny, nx = a.shape
    yi = (np.arange(n) + 0.5) * ny / n - 0.5
    xi = (np.arange(n) + 0.5) * nx / n - 0.5
    y0 = np.clip(np.floor(yi).astype(int), 0, ny - 1)
    x0 = np.clip(np.floor(xi).astype(int), 0, nx - 1)
    y1 = np.clip(y0 + 1, 0, ny - 1)
    x1 = np.clip(x0 + 1, 0, nx - 1)
    wy = np.clip(yi - y0, 0.0, 1.0)
    wx = np.clip(xi - x0, 0.0, 1.0)
    return (a[np.ix_(y0, x0)] * (1 - wy)[:, None] * (1 - wx)[None, :]
            + a[np.ix_(y1, x0)] * wy[:, None] * (1 - wx)[None, :]
            + a[np.ix_(y0, x1)] * (1 - wy)[:, None] * wx[None, :]
            + a[np.ix_(y1, x1)] * wy[:, None] * wx[None, :])


# --------------------------------------------------------------------------- config
def _need(d: dict, key: str, where: str):
    if key not in d:
        raise GSError("%s 缺字段 %r" % (where, key))
    return d[key]


def resolve_config(cfg: dict) -> dict:
    """Validate once; every later module reads this dict, never the raw file."""
    if not isinstance(cfg, dict):
        raise GSError("config 顶层必须是对象")
    tgt = _need(cfg, "target", "config")
    grd = _need(cfg, "grid", "config")
    gs = cfg.get("gs", {})
    q = cfg.get("quantize", {})
    sig = cfg.get("signal", {})

    method = str(grd.get("method", "fourier"))
    if method not in METHODS:
        raise GSError("grid.method 只能是 %s，收到 %r" % (list(METHODS), method))
    n = int(_need(grd, "n", "grid"))
    pad = int(grd.get("pad", 2))
    dx = float(_need(grd, "dx_um", "grid"))
    lam = float(_need(grd, "wavelength_um", "grid"))
    z = float(_need(grd, "distance_um", "grid"))
    if n < 16:
        raise GSError("grid.n=%d 太小（下限 16）" % n)
    if pad < 1:
        raise GSError("grid.pad=%d 必须 >= 1；pad=1 时信号窗与周期复制贴在一起" % pad)
    if dx <= 0 or lam <= 0 or z < 0:
        raise GSError("grid 的 dx_um/wavelength_um 必须 >0，distance_um 必须 >=0")
    if method == "angular_spectrum" and dx > lam / 2:
        raise GSError("angular_spectrum 要求 dx <= lambda/2（%.4g um），实际 dx=%.4g um；"
                      "这不是警告，超过就是空间混叠" % (lam / 2, dx))
    max_iter = int(gs.get("max_iter", 200))
    n_seed = int(gs.get("n_seed", 4))
    if max_iter < 1 or n_seed < 1:
        raise GSError("gs.max_iter 与 gs.n_seed 必须 >= 1（无界循环是红线，0 次也不叫设计）")
    levels = q.get("levels", list(DEFAULT_LEVELS))
    if isinstance(levels, int):
        levels = [levels]
    levels = [int(x) for x in levels]
    if not levels or any(x < 2 for x in levels):
        raise GSError("quantize.levels 每项必须 >= 2，收到 %r" % (levels,))
    rect = sig.get("rect")
    if rect is not None:
        if (not isinstance(rect, (list, tuple)) or len(rect) != 4
                or any(float(v) < 0 or float(v) > 1 for v in rect)
                or float(rect[0]) >= float(rect[1]) or float(rect[2]) >= float(rect[3])):
            raise GSError("signal.rect 必须是 [x0,x1,y0,y1]，0<=值<=1 且 x0<x1、y0<y1；"
                          "收到 %r" % (rect,))
    return {
        "target": {"path": str(_need(tgt, "path", "target")),
                   "key": tgt.get("key"),
                   "threshold_frac": float(tgt.get("threshold_frac", 0.01)),
                   "uniform": bool(tgt.get("uniform", False))},
        "grid": {"n": n, "pad": pad, "dx_um": dx, "wavelength_um": lam,
                 "distance_um": z, "method": method,
                 "dx_img_max_um": (None if grd.get("dx_img_max_um") is None
                                   else float(grd["dx_img_max_um"]))},
        "gs": {"max_iter": max_iter, "n_seed": n_seed,
               "seed": int(gs.get("seed", 0)),
               "window": int(gs.get("window", 20)),
               "rel_improve": float(gs.get("rel_improve", 1e-4)),
               "patience": int(gs.get("patience", 3))},
        "quantize": {"levels": sorted(set(levels))},
        "signal": {"rect": None if rect is None else [float(v) for v in rect]},
    }


# --------------------------------------------------------------------------- grid
def make_grids(cfg: dict) -> dict:
    """The only place that converts um to pixels. Everything downstream trusts it."""
    g = cfg["grid"]
    n, pad, dx = g["n"], g["pad"], g["dx_um"]
    N = n * pad
    lam, z, method = g["wavelength_um"], g["distance_um"], g["method"]
    x = (np.arange(N) - N // 2) * dx
    ap = np.zeros((N, N), bool)
    i0 = (N - n) // 2
    ap[i0:i0 + n, i0:i0 + n] = True
    if method == "fourier":
        if z <= 0:
            raise GSError("fourier 传播需要 distance_um > 0（它是远场/后焦面变换）")
        dx_img = lam * z / (N * dx)
    else:
        dx_img = dx
    if dx_img <= 0 or not np.isfinite(dx_img):
        raise GSError("解出的像面像素 %.4g um 无效" % dx_img)
    xi = (np.arange(N) - N // 2) * dx_img
    grid = {"n_inner": n, "n_canvas": N, "pad": pad, "dx_um": dx,
            "dx_img_um": dx_img, "x_um": x, "x_img_um": xi,
            "aperture": ap, "method": method,
            "wavelength_um": lam, "distance_um": z,
            "extent_um": float(N * dx), "extent_img_um": float(N * dx_img)}
    max_dx = g["dx_img_max_um"]
    if max_dx is not None and dx_img > max_dx:
        raise GSError("像面像素 %.4g um 超过允许的 %.4g um（目标最细特征的一半）；"
                      "提高 grid.pad 或 grid.n，不要靠放大目标图糊过去"
                      % (dx_img, max_dx))
    return grid


def propagate(u: np.ndarray, grid: dict, forward: bool = True) -> np.ndarray:
    N = grid["n_canvas"]
    if grid["method"] == "fourier":
        if forward:
            return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(u))) / N
        return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(u))) * N
    lam = grid["wavelength_um"] * 1e-6
    z = grid["distance_um"] * 1e-6
    fx = np.fft.fftfreq(N, d=grid["dx_um"] * 1e-6)
    FX, FY = np.meshgrid(fx, fx)
    arg = 1.0 / lam ** 2 - FX ** 2 - FY ** 2
    H = np.zeros(FX.shape, complex)
    prop = arg >= 0
    H[prop] = np.exp(2j * np.pi * z * np.sqrt(arg[prop]))
    # Evanescent branch must DECAY forward; conj(H) then grows backward, which is
    # the correct inverse but amplifies noise. Documented, not hidden.
    H[~prop] = np.exp(-2.0 * np.pi * z * np.sqrt(-arg[~prop]))
    return np.fft.ifft2(np.fft.fft2(u) * (H if forward else np.conj(H)))


def target_amplitude(img: np.ndarray, grid: dict, aperture: np.ndarray) -> np.ndarray:
    """Resample to the image grid and normalise to the input energy.

    Returns AMPLITUDE, so the square root is not optional. An earlier version
    returned the scaled intensity; GS then fitted I instead of sqrt(I), and the
    only check that caught it was feeding an analytic phase back through
    eval_recon (self-test 11). Every metric looked plausible, which is exactly
    the failure mode this project keeps paying for.
    """
    a = to_square(img)
    a = resample_bilinear(a, grid["n_canvas"])
    a = np.sqrt(np.clip(a, 0.0, None))
    if a.max() <= 0:
        raise GSError("重采样后目标图全零")
    # Energy budget = what the aperture can actually deliver at the image plane,
    # not the aperture's own sum. With angular_spectrum the evanescent content is
    # damped, so the two differ by ~0.5% and a positive control can never reach 0.
    probe = propagate(aperture.astype(complex), grid, True)
    in_energy = float(np.sum(np.abs(probe) ** 2))
    cur = float(np.sum(a ** 2))
    if cur <= 0 or in_energy <= 0:
        raise GSError("目标图或孔径能量为 0")
    return a * np.sqrt(in_energy / cur)


def signal_mask(A_t: np.ndarray, cfg: dict) -> np.ndarray:
    frac = cfg["target"]["threshold_frac"]
    m = A_t >= frac * float(A_t.max())
    rect = cfg["signal"]["rect"]
    if rect is not None:
        N = A_t.shape[0]
        x0, x1, y0, y1 = rect
        r = np.zeros_like(m)
        r[int(y0 * N):int(y1 * N), int(x0 * N):int(x1 * N)] = True
        m &= r
    if not m.any():
        raise GSError("信号区长这样是空的：threshold_frac=%.3g 与 signal.rect=%r 的交集为空"
                      % (frac, rect))
    return m


# --------------------------------------------------------------------------- GS
def gs_iterate(A_t: np.ndarray, grid: dict, gs: dict, seed: int,
               image_constraint: bool = True) -> dict:
    """Alternating projections. ``image_constraint=False`` is the ablation used by
    the self-test: without it the round trip is the identity, so RMSE cannot move.
    That is what makes the convergence claim falsifiable instead of anecdotal."""
    rng = np.random.default_rng(seed)
    ap = grid["aperture"]
    u = ap * np.exp(1j * rng.uniform(0.0, 2 * np.pi, A_t.shape))
    hist: list[float] = []
    reason = "max_iter"
    flat = 0
    window = max(2, gs["window"])
    at = float(np.linalg.norm(A_t))
    next_check = 2 * window
    for it in range(1, gs["max_iter"] + 1):
        v = propagate(u, grid, True)
        # Same definition as eval_recon: relative L2 norm, not RMS. Mixing the two
        # made the ledger read 0.296 while the metrics read 0.59 on one run.
        err = float(np.linalg.norm(np.abs(v) - A_t) / max(at, EPS))
        hist.append(err)
        if image_constraint:
            v = A_t * np.exp(1j * np.angle(v))
        u = propagate(v, grid, False)
        u = ap * np.exp(1j * np.angle(u))
        # Plateau is judged once per window, `patience` windows in a row. Judging
        # every iteration stopped a run at 27 iterations with window=20.
        if it >= next_check:
            base = hist[-1 - window]
            gain = (base - hist[-1]) / max(base, EPS)
            if gain < gs["rel_improve"]:
                flat += 1
                if flat >= gs["patience"]:
                    reason = "plateau(%d windows < %.1e)" % (flat, gs["rel_improve"])
                    break
            else:
                flat = 0
            next_check = it + window
    return {"phase": np.angle(u), "rmse_hist": hist, "iterations": len(hist),
            "seed": seed, "stop_reason": reason, "rmse_final": hist[-1]}


def quantize_phase(phase: np.ndarray, levels: int) -> tuple:
    step = 2.0 * np.pi / levels
    idx = np.round((phase + np.pi) / step).astype(int) % levels
    return -np.pi + idx * step, idx


def theory_eta_max(levels: int) -> float:
    """Uniform-phase assumption: the fraction a phase-only hologram can keep."""
    x = np.pi / levels
    return float((np.sin(x) / x) ** 2)


def eval_recon(phase: np.ndarray, A_t: np.ndarray, grid: dict, cfg: dict,
               support: np.ndarray) -> dict:
    u = grid["aperture"] * np.exp(1j * phase)
    v = propagate(u, grid, True)
    I = np.abs(v) ** 2
    total = float(I.sum())
    eta = float(I[support].sum() / total) if total > 0 else float("nan")
    rmse = float(np.linalg.norm(np.abs(v) - A_t) / max(np.linalg.norm(A_t), EPS))
    out = {"eta": eta, "rmse": rmse, "support_fraction": float(support.mean())}
    if 0.0 < support.mean() < 0.9:
        bg = float(I[~support].mean()) if (~support).any() else 0.0
        out["snr_db"] = (10.0 * np.log10(float(I[support].mean()) / bg)
                         if bg > 0 else None)
        out["snr_note"] = ("信号区均值 / 非信号区均值；相干重建的散斑不是噪声，"
                           "这个比值是对比度口径")
    else:
        out["snr_db"] = None
        out["snr_note"] = ("支持区占比 %.1f%%，非信号区太小，SNR 无定义"
                           % (100 * support.mean()))
    if cfg["target"]["uniform"]:
        s = I[support]
        out["uniformity"] = float((s.max() - s.min()) / (s.max() + s.min()))
    else:
        out["uniformity"] = None
        out["uniformity_note"] = "目标不是均匀图，均匀度无意义（target.uniform=false）"
    ph = phase[grid["aperture"]]
    R = float(np.abs(np.mean(np.exp(1j * ph))))
    out["phase_circ_std_rad"] = float(np.sqrt(max(-2.0 * np.log(max(R, EPS)), 0.0)))
    return out


def phase_over_2pi(phase: np.ndarray, grid: dict) -> float:
    """Phase span of the aperture, row-by-row unwrapped (wrapping is not structure)."""
    ap = grid["aperture"]
    rows = np.where(ap.any(axis=1))[0]
    spans = []
    for r in rows:
        cols = np.where(ap[r])[0]
        seg = phase[r, cols[0]:cols[-1] + 1]
        spans.append(float(np.ptp(np.unwrap(seg))))
    return float(np.max(spans) / (2 * np.pi)) if spans else float("nan")


# --------------------------------------------------------------------------- self-test
def self_test() -> int:
    """Nine analytic ground truths. No engine, no license, no input file."""
    rows = []

    def check(name, ok: bool, got, want, tol, note=""):
        rows.append({"case": name, "pass": bool(ok),
                     "got": None if got is None else float(got),
                     "want": float(want), "tol": float(tol), "note": note})

    N = 64
    lam, dx, z = 0.74, 0.3, 20.0
    grid = {"n_canvas": N, "n_inner": N, "pad": 1, "dx_um": dx,
            "dx_img_um": lam * z / (N * dx), "method": "fourier",
            "wavelength_um": lam, "distance_um": z,
            "aperture": np.ones((N, N), bool)}

    # (1) Parseval: forward then inverse is identity, and energy is preserved.
    rng = np.random.default_rng(7)
    u0 = rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))
    v0 = propagate(u0, grid, True)
    back = propagate(v0, grid, False)
    rt = float(np.linalg.norm(back - u0) / np.linalg.norm(u0))
    check("1 Parseval round-trip", rt < 1e-12, rt, 0.0, 1e-12,
          "unitary FFT: 能量与逐点都可逆")
    check("1b energy ratio", abs(np.sum(np.abs(v0) ** 2) / np.sum(np.abs(u0) ** 2) - 1) < 1e-12,
          np.sum(np.abs(v0) ** 2) / np.sum(np.abs(u0) ** 2), 1.0, 1e-12)

    # (2) Uniform phase across a filled canvas -> one delta at the centre.
    vd = propagate(np.ones((N, N), complex), grid, True)
    I = np.abs(vd) ** 2
    k = np.unravel_index(int(np.argmax(I)), I.shape)
    leak = float((I.sum() - I[k]) / I.sum())
    check("2 plane phase -> delta", leak < 1e-12 and k == (N // 2, N // 2),
          leak, 0.0, 1e-12, "峰值像素 %r" % (k,))

    # (3) Converging lens + tilt, propagated by z=f, must focus at (f*tan(theta)).
    g_as = dict(grid, method="angular_spectrum", distance_um=z,
                aperture=np.ones((N, N), bool))
    x = (np.arange(N) - N // 2) * dx * 1e-6
    X, Y = np.meshgrid(x, x)
    k0 = 2 * np.pi / (lam * 1e-6)
    f = 20e-6
    th = np.deg2rad(20.0)
    w = 8e-6
    ph = -k0 * (np.sqrt(f ** 2 + X ** 2 + Y ** 2) - abs(f)) + k0 * np.sin(th) * X
    Ein = np.exp(-(X ** 2 + Y ** 2) / w ** 2) * np.exp(1j * ph)
    foc = np.abs(propagate(Ein, g_as, True)) ** 2
    ii, jj = np.unravel_index(int(np.argmax(foc)), foc.shape)
    x_meas = x[jj]
    x_want = f * np.tan(th)
    px_err = abs(x_meas - x_want) / (dx * 1e-6)
    check("3 lens+tilt focus position", px_err < 1.0, px_err, 0.0, 1.0,
          "实测 x=%.3f um，解析 %.3f um" % (x_meas * 1e6, x_want * 1e6))

    # (4) Quantised efficiency must equal sinc^2(pi/N) when the phase error is
    # uniformly distributed. A dense sawtooth is the only case where the bound is
    # exact: a 2-D lens has a non-uniform phase histogram and lands ~0.2% ABOVE
    # the asymptotic bound (measured 0.4070 vs 0.4053 at L=2). That deviation is
    # sampling, not a bug, so the runtime guard allows 5% and this test pins the
    # exact statement instead of a loose one.
    periods, M = 997, 200000
    ph_ramp = np.linspace(0.0, 2 * np.pi * periods, M, endpoint=False)
    got = {}
    for L in (2, 4, 8):
        pq, _ = quantize_phase(ph_ramp, L)
        got[L] = float(np.abs(np.mean(np.exp(1j * (pq - ph_ramp)))) ** 2)
    bound = {L: theory_eta_max(L) for L in got}
    dev = {L: abs(got[L] - bound[L]) for L in got}
    mono = got[2] < got[4] < got[8]
    check("4 quantised eta == sinc^2 bound", max(dev.values()) < 1e-4 and mono,
          got[8], bound[8], 1e-4,
          "eta=%s bound=%s 最大偏差 %.2e"
          % ({k: round(v, 6) for k, v in got.items()},
             {k: round(v, 6) for k, v in bound.items()}, max(dev.values())))

    # (5) pad=2 keeps a compact field inside its window; pad=1 fails sampling.
    n, pad = 32, 2
    Np = n * pad
    gp = {"n_canvas": Np, "n_inner": n, "pad": pad, "dx_um": dx,
          "dx_img_um": lam * z / (Np * dx), "method": "fourier",
          "wavelength_um": lam, "distance_um": z}
    xp = (np.arange(Np) - Np // 2) * dx * 1e-6
    XP, YP = np.meshgrid(xp, xp)
    ap = np.zeros((Np, Np), bool)
    i0 = (Np - n) // 2
    ap[i0:i0 + n, i0:i0 + n] = True
    gauss = np.exp(-(XP ** 2 + YP ** 2) / (3e-6) ** 2) * ap
    out = np.abs(propagate(gauss.astype(complex), gp, True)) ** 2
    inside = float(out[ap].sum() / out.sum())
    check("5 pad isolates the design window", inside > 0.999, 1.0 - inside, 0.0, 1e-3,
          "窗外能量占比 %.3g（pad=1 时窗与周期复制重合，无从隔离）" % (1 - inside))
    try:
        make_grids(resolve_config({
            "target": {"path": "x"}, "grid": {"n": 64, "pad": 1, "dx_um": dx,
                                              "wavelength_um": lam, "distance_um": z,
                                              "method": "fourier", "dx_img_max_um": 0.05}}))
        raised = False
    except GSError:
        raised = True
    check("5b undersampled image grid is refused", raised, None, 0.0, 0.0,
          "pad=1 解出的 dx_img 超过目标特征的一半时必须报错，不许硬算")

    # (6) levels=2 must produce exactly two levels, pi apart.
    pq, idx = quantize_phase(np.array([-3.0, -1.0, 1.0, 3.0, 0.0]), 2)
    uniq = np.unique(np.round(pq, 9))
    check("6 binary quantisation has 2 levels", len(uniq) == 2
          and abs(abs(uniq[1] - uniq[0]) - np.pi) < 1e-9
          and set(np.unique(idx)) <= {0, 1}, len(uniq), 2.0, 0.0,
          "unique=%s" % (uniq.tolist(),))

    # (7) Grid symmetry: odd N puts a sample exactly on x=0 (even N sits half a
    # pixel off by construction, which is the fftshift convention, not an error).
    Nodd = 65
    xs = (np.arange(Nodd) - Nodd // 2) * dx
    sym = abs(xs.sum()) < 1e-9 and abs(np.ptp(np.diff(xs))) < 1e-12 and xs[Nodd // 2] == 0.0
    check("7 grid symmetry and pitch", sym, np.ptp(np.diff(xs)), 0.0, 1e-12,
          "sum(x)=%.3g，中点在 x=0" % xs.sum())

    # (8) Empty arrays are an error, not a successful npz.
    try:
        npz_arrays({"phase_rad": np.array([])})
        raised = False
    except GSError:
        raised = True
    check("8 empty array is refused", raised, None, 0.0, 0.0)

    # (9) Complex must survive the dtype whitelist (D-015), junk must not.
    kept = npz_arrays({"E": np.ones((2, 2), complex)})
    ok9 = kept["E"].dtype.kind == "c"
    try:
        npz_arrays({"label": np.array(["a"])})
        refused = False
    except GSError:
        refused = True
    check("9 complex survives, str refused", ok9 and refused, None, 0.0, 0.0,
          "丢掉复数 E 正是 D-015 的根因")

    # (10) The convergence claim must be falsifiable: with the image-plane
    # constraint the error drops, with it ablated the round trip is the identity
    # and the error cannot move. Without this control "it converges" is a story.
    Ng, nin = 64, 32
    ap10 = np.zeros((Ng, Ng), bool)
    k0_ = (Ng - nin) // 2
    ap10[k0_:k0_ + nin, k0_:k0_ + nin] = True
    g10 = {"n_canvas": Ng, "n_inner": nin, "pad": 2, "dx_um": 0.4,
           "dx_img_um": 0.74 * 20.0 / (Ng * 0.4), "method": "fourier",
           "wavelength_um": 0.74, "distance_um": 20.0, "aperture": ap10}
    xg = (np.arange(Ng) - Ng // 2) * 0.4e-6
    XG, YG = np.meshgrid(xg, xg)
    img10 = np.exp(-(XG ** 2 + YG ** 2) / (2 * (2.2e-6) ** 2))
    A10 = target_amplitude(img10, g10, ap10)
    gs10 = {"max_iter": 40, "n_seed": 1, "seed": 1, "window": 8,
            "rel_improve": 1e-9, "patience": 9}
    r10 = gs_iterate(A10, g10, gs10, 1, image_constraint=True)
    h = np.asarray(r10["rmse_hist"])
    drop = float((h[0] - h[-1]) / h[0])
    mono = bool(np.all(np.diff(h) <= 1e-12 * max(h[0], EPS)))
    check("10 GS reduces the error", drop > 0.30 and mono, drop, 0.0, 0.0,
          "首末轮 RMSE %.5f -> %.5f，逐轮单调非增；%s"
          % (h[0], h[-1], r10["stop_reason"]))
    r10b = gs_iterate(A10, g10, gs10, 1, image_constraint=False)
    hb = np.asarray(r10b["rmse_hist"])
    drift = float(abs((hb[-1] - hb[0]) / hb[0]))
    check("10b ablation cannot converge", drift < 1e-10, drift, 0.0, 1e-10,
          "去掉像面振幅约束后往返是恒等映射，误差不动（负对照确实失败）")

    # (11) Positive control: a target generated by a known phase must be
    # reproduced by that same phase. Fourier is unitary, so the residual must be
    # machine zero; angular_spectrum damps evanescent content, so a small
    # residual is physics, not a bug. This is the only check that catches a
    # target normalised as intensity instead of amplitude (2026-11-11 actual bug:
    # every downstream metric stayed plausible and read 0.597 instead of 0).
    def _lens_case(method, dx_l, z_l, tol):
        Nl, nl = 128, 64
        apl = np.zeros((Nl, Nl), bool)
        j0 = (Nl - nl) // 2
        apl[j0:j0 + nl, j0:j0 + nl] = True
        gl = {"n_canvas": Nl, "n_inner": nl, "pad": 2, "dx_um": dx_l,
              "dx_img_um": (0.74 * z_l / (Nl * dx_l) if method == "fourier" else dx_l),
              "method": method, "wavelength_um": 0.74, "distance_um": z_l,
              "aperture": apl}
        xl = (np.arange(Nl) - Nl // 2) * dx_l * 1e-6
        XL, YL = np.meshgrid(xl, xl)
        fl = 10e-6
        kl = 2 * np.pi / (0.74e-6)
        phl = -kl * (np.sqrt(fl ** 2 + XL ** 2 + YL ** 2) - abs(fl))
        Il = np.abs(propagate(apl * np.exp(1j * phl), gl, True)) ** 2
        Al = target_amplitude(Il, gl, apl)
        supl = Al >= 0.01 * Al.max()
        cl = eval_recon(phl, Al, gl, {"target": {"uniform": False}}, supl)
        check("11 positive control (%s)" % method, cl["rmse"] < tol,
              cl["rmse"], 0.0, tol,
              "同一相位回灌后 RMSE 应 ~0；0.6 量级说明目标被按强度归一化")

    _lens_case("fourier", 0.3, 20.0, 1e-12)
    _lens_case("angular_spectrum", 0.3, 20.0, 1e-2)

    bad = [r for r in rows if not r["pass"]]
    for r in rows:
        print("%-42s got=%-12s want=%-10s %s"
              % (r["case"],
                 "None" if r["got"] is None else "%.6g" % r["got"],
                 "%.6g" % r["want"], "PASS" if r["pass"] else "FAIL"))
        if r["note"]:
            print("    %s" % r["note"])
    print("\n%d/%d pass" % (len(rows) - len(bad), len(rows)))
    return 0 if not bad else 1


# --------------------------------------------------------------------------- outputs
def write_outputs(out: Path, grid: dict, A_t: np.ndarray, support: np.ndarray,
                  phase: np.ndarray, recon: dict, metrics: dict,
                  qcs: dict, gs_best: dict, debug: bool) -> list:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    ap = grid["aperture"]
    x = grid["x_um"]
    rows_ = np.where(ap.any(axis=1))[0]
    cols_ = np.where(ap.any(axis=0))[0]
    xa = x[cols_]
    ya = x[rows_]
    arrays = {
        "phase_rad": phase[rows_[0]:rows_[-1] + 1, cols_[0]:cols_[-1] + 1],
        "target_amp": A_t[np.ix_(rows_, cols_)],
        "I_recon": (np.abs(propagate(ap * np.exp(1j * phase), grid, True)) ** 2)[
            np.ix_(rows_, cols_)],
        "x_um": xa, "y_um": ya,
        "rmse_hist": np.asarray(gs_best["rmse_hist"], float),
    }
    npz = out / "phase_map.npz"
    np.savez_compressed(npz, **arrays)
    if not npz.stat().st_size:
        raise GSError("phase_map.npz 写出来是空的")
    written.append(str(npz))

    finest = max(qcs)
    for L, qc in qcs.items():
        p = out / ("quantized_phase_L%d.csv" % L)
        ph_q = qc["phase"]
        with p.open("w", encoding="utf-8") as fh:
            fh.write("x_um,y_um,phase_rad,level\n")
            for iy, yy in enumerate(ya):
                for ix, xx in enumerate(xa):
                    fh.write("%.6g,%.6g,%.8g,%d\n"
                             % (xx, yy, ph_q[rows_[0] + iy, cols_[0] + ix],
                                qc["level"][rows_[0] + iy, cols_[0] + ix]))
        written.append(str(p))
        if L == finest:
            twin = out / "quantized_phase.csv"
            twin.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            written.append(str(twin))

    mp = out / "holo_metrics.json"
    mp.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append(str(mp))

    lm = out / "library_map.json"
    lm.write_text(json.dumps(metrics["library_map"], indent=2, ensure_ascii=False),
                  encoding="utf-8")
    written.append(str(lm))

    if debug:
        p = out / "rmse_hist.csv"
        with p.open("w", encoding="utf-8") as fh:
            fh.write("iter,rmse\n")
            for i, v in enumerate(gs_best["rmse_hist"], 1):
                fh.write("%d,%.10g\n" % (i, v))
        written.append(str(p))
    return written


# --------------------------------------------------------------------------- main
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GS 相位恢复：目标图 -> 全息面相位版图")
    ap.add_argument("--self-test", action="store_true", help="跑 9 条解析真值，不读文件")
    ap.add_argument("--config", default=None, help="JSON 配置（见 SKILL.md 的 schema）")
    ap.add_argument("--out", default=None, help="输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只解析配置与网格，不做 FFT")
    ap.add_argument("--json", action="store_true", help="把 metrics 打到 stdout")
    ap.add_argument("--max-iter", type=int, default=None, help="覆盖 gs.max_iter")
    ap.add_argument("--n-seed", type=int, default=None, help="覆盖 gs.n_seed")
    ap.add_argument("--levels", default=None, help="覆盖 quantize.levels，逗号分隔")
    ap.add_argument("--save-debug-frames", action="store_true", help="落 rmse_hist.csv")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.config:
        ap.error("--config 必填（或用 --self-test / --dry-run 看计划）")
    if not (args.out or args.dry_run):
        ap.error("--out 必填（或用 --dry-run 只看会算什么）")

    cfg_path = Path(args.config)
    try:
        if not cfg_path.is_file():
            raise GSError("config 不存在: %s" % cfg_path)
        cfg = resolve_config(json.loads(cfg_path.read_text(encoding="utf-8")))
        if args.max_iter is not None:
            cfg["gs"]["max_iter"] = int(args.max_iter)
        if args.n_seed is not None:
            cfg["gs"]["n_seed"] = int(args.n_seed)
        if args.levels:
            cfg["quantize"]["levels"] = sorted(
                {int(x) for x in args.levels.split(",") if x.strip()})
            if any(x < 2 for x in cfg["quantize"]["levels"]):
                raise GSError("--levels 每项必须 >= 2")

        grid = make_grids(cfg)
        root = _repo_root()
        tgt_path = Path(cfg["target"]["path"])
        if not tgt_path.is_absolute():
            # Relative paths resolve against the repo root, never the cwd.
            tgt_path = root / tgt_path
        img = load_target(tgt_path, cfg["target"]["key"])
        A_t = target_amplitude(img, grid, grid["aperture"])
        support = signal_mask(A_t, cfg)

        need = grid["dx_img_um"]
        if args.dry_run:
            print(json.dumps({
                "dry_run": True,
                "config": cfg,
                "grid": {k: grid[k] for k in ("n_inner", "n_canvas", "pad", "dx_um",
                                              "dx_img_um", "extent_um",
                                              "extent_img_um", "method")},
                "target": {"path": str(tgt_path), "shape": list(img.shape),
                           "support_fraction": float(support.mean())},
                "would_run": {"seeds": cfg["gs"]["n_seed"],
                              "max_iter": cfg["gs"]["max_iter"],
                              "levels": cfg["quantize"]["levels"]},
                "nyquist": {"dx_img_um": need,
                            "dx_img_max_um": cfg["grid"]["dx_img_max_um"],
                            "ok": (cfg["grid"]["dx_img_max_um"] is None
                                   or need <= cfg["grid"]["dx_img_max_um"])},
            }, indent=2, ensure_ascii=False))
            return 0

        runs = []
        for s in range(cfg["gs"]["n_seed"]):
            runs.append(gs_iterate(A_t, grid, cfg["gs"], cfg["gs"]["seed"] + s))
        best = min(runs, key=lambda r: r["rmse_final"])
        phase = best["phase"]
        recon = eval_recon(phase, A_t, grid, cfg, support)

        qcs = {}
        ap = grid["aperture"]
        for L in cfg["quantize"]["levels"]:
            ph_q, idx = quantize_phase(phase, L)
            mq = eval_recon(ph_q, A_t, grid, cfg, support)
            # Quantisation efficiency is the Strehl ratio of the phase error,
            # |<exp(i dphi)>|^2 --- NOT the support energy fraction. Measured on the
            # frame target: Strehl/bound = 1.011 / 1.001 / 1.000 at L=2/4/8, while
            # eta_support/eta_cont reads 0.836 / 0.834 / 0.955 and is not even
            # monotone. Using eta_support here is exactly the "wrong denominator"
            # this field exists to catch.
            strehl = float(np.abs(np.mean(np.exp(1j * (ph_q - phase)[ap]))) ** 2)
            bound = theory_eta_max(L)
            qcs[L] = {"phase": ph_q, "level": idx, "metrics": mq,
                      "theory_eta_max": bound,
                      "eta_loss": float(recon["eta"] - mq["eta"]),
                      "strehl": strehl,
                      "theory_ratio": strehl / bound}

        spread = [r["rmse_final"] for r in runs]
        metrics = {
            "skill": "fdtd-holo-phase-retrieval",
            "config": cfg,
            "grid": {k: grid[k] for k in ("n_inner", "n_canvas", "pad", "dx_um",
                                          "dx_img_um", "extent_um",
                                          "extent_img_um", "method",
                                          "wavelength_um", "distance_um")},
            "target": {"source": str(tgt_path), "shape": list(img.shape),
                       "support_fraction": float(support.mean())},
            "gs": {
                "max_iter": cfg["gs"]["max_iter"],
                "n_seed": cfg["gs"]["n_seed"],
                "iterations": best["iterations"],
                "best_seed": best["seed"],
                "stop_reason": best["stop_reason"],
                "rmse_final": best["rmse_final"],
                "rmse_across_seeds": {"min": min(spread), "max": max(spread),
                                      "all": spread},
                "note": "多种子的极差一并报出；只报最优值属于假轮次",
            },
            "metrics": recon,
            "quantized": {str(L): {"eta": qc["metrics"]["eta"],
                                   "rmse": qc["metrics"]["rmse"],
                                   "snr_db": qc["metrics"]["snr_db"],
                                   "strehl": qc["strehl"],
                                   "theory_eta_max": qc["theory_eta_max"],
                                   "theory_ratio": qc["theory_ratio"],
                                   "eta_loss": qc["eta_loss"],
                                   "levels": L,
                                   "over_strehl_one": bool(qc["strehl"] > 1.0 + 1e-9),
                                   "over_theory_margin": bool(qc["theory_ratio"] > 1.05),
                                   "theory_note": "strehl=|<exp(i dphi)>|^2 才与 sinc^2 可比；"
                                                  "该上限假设相位误差均匀，直方图不均匀时实测可"
                                                  "高出 ~1%，所以硬判据是 strehl<=1"}
                          for L, qc in qcs.items()},
            "phase_span_over_2pi": phase_over_2pi(phase, grid),
            "library_map": {
                "status": "not_implemented",
                "owner": "fdtd-metasurface-assembly",
                "schema": ["x_um", "y_um", "phase_rad", "level"],
                "note": "本技能只给相位档位；单胞库里没有该档是装配技能的 missing[]，"
                        "不在这里硬凑",
            },
        }

        over = [L for L, v in metrics["quantized"].items() if v["over_strehl_one"]]
        if over:
            raise GSError("量化 Strehl 超过 1（levels=%s）：这在数学上不可能，"
                          "归一化或相位误差定义写错了" % over)
        warned = [L for L, v in metrics["quantized"].items() if v["over_theory_margin"]]
        if warned:
            metrics["warnings"] = [
                "levels=%s 的 Strehl 比 sinc^2 渐近上限高 >5%%，多为相位直方图不均匀；"
                "核对该相位分布后再写进报告" % warned]

        written = write_outputs(Path(args.out), grid, A_t, support, phase,
                                recon, metrics, qcs, best, args.save_debug_frames)
        metrics["written"] = written
        mp = Path(args.out) / "holo_metrics.json"
        mp.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

        if args.json:
            print(json.dumps(metrics, indent=2, ensure_ascii=False))
        else:
            print("target : %s  support=%.1f%%" % (tgt_path, 100 * support.mean()))
            print("grid   : n=%d pad=%d dx=%.4g um -> dx_img=%.4g um (%s)"
                  % (grid["n_inner"], grid["pad"], grid["dx_um"],
                     grid["dx_img_um"], grid["method"]))
            print("gs     : seed %d/%d, %d iters (%s), rmse=%.5f"
                  % (best["seed"], cfg["gs"]["n_seed"], best["iterations"],
                     best["stop_reason"], best["rmse_final"]))
            print("eta    : %.4f  rmse=%.5f  snr=%s"
                  % (recon["eta"], recon["rmse"],
                     "n/a" if recon["snr_db"] is None else "%.2f dB" % recon["snr_db"]))
            for L in sorted(qcs):
                v = metrics["quantized"][str(L)]
                print("  L=%-2d eta=%.4f (strehl %.4f / bound %.4f = %.3f)"
                      % (L, v["eta"], v["strehl"], v["theory_eta_max"],
                         v["theory_ratio"]))
            print("out    : %s" % args.out)
        return 0
    except GSError as e:
        print("GSError: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
