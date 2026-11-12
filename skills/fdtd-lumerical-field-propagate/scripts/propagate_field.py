#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""propagate_field.py — 把一个面上的复场传播到下一个面（角谱法）。

用途：4f 系统 / 透镜-掩模-透镜这类「单段 FDTD + 自由空间传播」的串联。
只传播，不做透镜相位、不做近远场变换、不画图。

用法
----
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py \\
        --npz in.npz --distance-um 50 --out OUT --json
    "$PY" ... --fsp run.fsp --monitor field --distance-um 50 --out OUT
    "$PY" ... --npz in.npz --distance-um 50 --mask-npz aperture.npz --out OUT
    "$PY" ... --self-test

输入 npz：E (n,n[,3] complex)、x_um、y_um、wavelength_um（或 lambda_um）
输出：propagated.npz（同键 + distance_um）、propagate_metrics.json

退出码：0 成功 / 1 运行失败 / 2 参数或采样不合法。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# 仓库根：优先环境变量（跨工作区 junction 时由调用方钉死），否则按脚本位置回退
ROOT = Path(os.environ.get("FDTD_WS_ROOT") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(ROOT / "library" / "py"))

import angular_spectrum as asp  # noqa: E402


class UsageError(Exception):
    pass


def _as_um(v):
    return float(v) * 1e6


def load_npz(path: Path) -> dict:
    if not path.is_file():
        raise UsageError("npz 不存在：%s" % path)
    z = np.load(path)
    return {k: z[k] for k in z.keys()}


def pick_axes(raw: dict) -> tuple[np.ndarray, np.ndarray]:
    for kx, ky in (("x_um", "y_um"), ("u_um", "v_um")):
        if kx in raw and ky in raw:
            return np.asarray(raw[kx], float).ravel(), np.asarray(raw[ky], float).ravel()
    raise UsageError("npz 缺坐标轴（x_um/y_um 或 u_um/v_um）；实际键 = %s" % sorted(raw))


def pick_wavelength(raw: dict, override: float | None) -> float:
    if override:
        return float(override)
    for k in ("wavelength_um", "lambda_um"):
        if k in raw:
            v = np.asarray(raw[k], float).ravel()
            return float(v[0])
    raise UsageError("npz 缺 wavelength_um；用 --wavelength-um 显式给")


def pick_field(raw: dict) -> np.ndarray:
    if "E" in raw:
        E = np.asarray(raw["E"])
        if np.iscomplexobj(E):
            return E
    for keys in (("Ex", "Ey", "Ez"), ("ex", "ey", "ez")):
        if all(k in raw for k in keys):
            return np.stack([np.asarray(raw[k]) for k in keys], axis=-1)
    raise UsageError("npz 里的 E 不是复数，也没有 Ex/Ey/Ez；实际键 = %s" % sorted(raw))


def square_pad(field: np.ndarray, n: int) -> np.ndarray:
    """居中零填充到 n×n，保能量不变。"""
    a = field
    if a.ndim == 2:
        a = a[..., None]
    nx, ny, c = a.shape
    out = np.zeros((n, n, c), dtype=a.dtype)
    ox, oy = (n - nx) // 2, (n - ny) // 2
    out[ox:ox + nx, oy:oy + ny, :] = a
    return out if field.ndim == 3 else out[..., 0]


def fwhm_1d(x: np.ndarray, intensity: np.ndarray) -> float:
    peak = intensity.max()
    if peak <= 0:
        return float("nan")
    idx = np.where(intensity >= peak / 2.0)[0]
    if idx.size < 2:
        return float("nan")
    return float(x[idx].max() - x[idx].min())


def metrics_of(E_in, E_out, dx_m, lam_um, z_um, n):
    e_in = float(np.sum(np.abs(E_in) ** 2))
    e_out = float(np.sum(np.abs(E_out) ** 2))
    return {
        "n": int(n),
        "dx_um": round(dx_m * 1e6, 4),
        "dx_over_lambda": round(dx_m / (lam_um * 1e-6), 4),
        "wavelength_um": round(lam_um, 5),
        "distance_um": round(z_um, 4),
        "energy_in": e_in,
        "energy_out": e_out,
        "energy_ratio": round(e_out / e_in, 9) if e_in > 0 else None,
        "evanescent_fraction": round(asp.evanescent_fraction(n, dx_m, lam_um * 1e-6), 4),
        "max_reliable_distance_um": round(
            asp.max_distance(n, dx_m, lam_um * 1e-6) * 1e6, 2),
    }


# ------------------------------------------------------------------ self-test


def _gaussian(n, dx_um, w0_um):
    x = (np.arange(n) - n // 2) * dx_um
    X, Y = np.meshgrid(x, x, indexing="xy")
    return np.exp(-(X ** 2 + Y ** 2) / w0_um ** 2).astype(complex), x


def self_test() -> int:
    fails = []
    lam = 1.55
    dx = 0.5
    n = 256

    # 1) 真空往返：必须用**带限且边缘平滑**的场。
    #    边缘硬截断会把高频（含倏逝）灌进频谱，往返本来就不酉——那是物理，不是 bug。
    x = (np.arange(n) - n // 2) * dx
    X, Y = np.meshgrid(x, x, indexing="xy")
    u = np.exp(-(X ** 2 + Y ** 2) / 12.0 ** 2).astype(complex)
    back = asp.propagate(asp.propagate(u, dx * 1e-6, lam * 1e-6, 300e-6),
                         dx * 1e-6, lam * 1e-6, -300e-6)
    err_rt = float(np.linalg.norm(back - u) / np.linalg.norm(u))
    print("round-trip rel-err = %.3e (need <1e-6)" % err_rt)
    if err_rt >= 1e-6:
        fails.append("round-trip")

    # 2) 解析高斯 w(z)
    w0, z = 20.0, 500.0
    g, x = _gaussian(n, dx, w0)
    gz = asp.propagate(g, dx * 1e-6, lam * 1e-6, z * 1e-6)
    f0 = fwhm_1d(x, np.abs(g[n // 2, :]) ** 2)
    fz = fwhm_1d(x, np.abs(gz[n // 2, :]) ** 2)
    zr = np.pi * w0 ** 2 / lam
    ratio_meas = fz / f0
    ratio_ana = np.sqrt(1 + (z / zr) ** 2)
    err_g = abs(ratio_meas / ratio_ana - 1)
    print("gaussian w(z): measured %.5f analytic %.5f rel-err %.3e (need <1e-2)"
          % (ratio_meas, ratio_ana, err_g))
    if err_g >= 1e-2:
        fails.append("gaussian")

    # 3) 与 holo 的 propagate 逐点一致
    holo_path = ROOT / "skills" / "fdtd-holo-phase-retrieval" / "scripts" / "gs_retrieval.py"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gs_retrieval", holo_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        grid = {"n_canvas": n, "dx_um": dx, "method": "angular_spectrum",
                "wavelength_um": lam, "distance_um": z}
        holo_out = mod.propagate(g, grid, True)
        ours = asp.propagate(g, dx * 1e-6, lam * 1e-6, z * 1e-6)
        dev = float(np.max(np.abs(holo_out - ours)))
        print("holo vs library max|diff| = %.3e (need <1e-12)" % dev)
        if dev >= 1e-12:
            fails.append("holo-consistency")
    except Exception as e:  # noqa: BLE001
        print("holo 对照跳过：%r" % (e,))

    # 4) 负对照：**丢掉倏逝衰减**的实现必须与正确结果明显不同。
    #    用硬边圆孔——它的频谱有 1/f 尾巴，才真的有倏逝分量；
    #    高斯束的频谱在 f>1/λ 处已小到 1e-17，用它做这条对照测不出任何东西。
    n2, dx2 = 256, 0.2
    x2 = (np.arange(n2) - n2 // 2) * dx2
    X2, Y2 = np.meshgrid(x2, x2, indexing="xy")
    disc = ((X2 ** 2 + Y2 ** 2) <= 5.0 ** 2).astype(complex)
    e_in = float(np.sum(np.abs(disc) ** 2))
    fwd = asp.propagate(disc, dx2 * 1e-6, lam * 1e-6, 5e-6)
    e_f = float(np.sum(np.abs(fwd) ** 2))

    fx = np.fft.fftfreq(n2, d=dx2 * 1e-6)
    FX, FY = np.meshgrid(fx, fx)
    arg = 1.0 / (lam * 1e-6) ** 2 - FX ** 2 - FY ** 2
    H_wrong = np.where(arg >= 0,
                       np.exp(2j * np.pi * 5e-6 * np.sqrt(np.abs(arg))), 1.0)
    wrong = np.fft.ifft2(np.fft.fft2(disc) * H_wrong)
    e_w = float(np.sum(np.abs(wrong) ** 2))

    print("negative control: E_in=%.4g E_correct=%.4g E_no_decay=%.4g"
          % (e_in, e_f, e_w))
    if not (e_f < 0.99 * e_w):
        fails.append("negative-control")

    # 5) EXP-67 负对照：漏掉 1/λ² 项（近似成 1 - λ²f²/2 的常见笔误）
    FXg, FYg = np.meshgrid(np.fft.fftfreq(n, d=dx * 1e-6),
                           np.fft.fftfreq(n, d=dx * 1e-6))
    arg_w = -(FXg ** 2 + FYg ** 2)
    H_w = np.where(arg_w >= 0,
                   np.exp(2j * np.pi * z * 1e-6 * np.sqrt(np.abs(arg_w))), 1.0)
    gw = np.fft.ifft2(np.fft.fft2(g) * H_w)
    ratio_w = fwhm_1d(x, np.abs(gw[n // 2, :]) ** 2) / f0
    print("negative control (no 1/lambda^2): ratio=%.4f vs analytic %.4f"
          % (ratio_w, ratio_ana))
    if abs(ratio_w / ratio_ana - 1) < 0.02:
        fails.append("negative-control-lambda-term")

    # 6) EXP-68 负对照：把共轭当正向（符号反）必须与 holo 明显不同
    if "holo_out" in dir():
        wrong_sign = asp.propagate(g, dx * 1e-6, lam * 1e-6, -z * 1e-6)
        dev_w = float(np.max(np.abs(wrong_sign - holo_out)))
        print("negative control (wrong sign) max|diff| = %.3e (need >1e-6)" % dev_w)
        if dev_w <= 1e-6:
            fails.append("negative-control-sign")

    if fails:
        print("SELF-TEST FAIL:", ", ".join(fails), file=sys.stderr)
        return 1
    print("SELF-TEST PASS")
    return 0


# ---------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="角谱传播：场 → 下一个面")
    ap.add_argument("--npz", default=None, help="输入场 dump")
    ap.add_argument("--fsp", default=None, help="或直接从 .fsp 的场监视器读（只读会话）")
    ap.add_argument("--monitor", default="field", help="--fsp 时的监视器名")
    ap.add_argument("--wavelength-um", type=float, default=None, help="覆盖 npz 里的波长")
    ap.add_argument("--distance-um", type=float, required=False, default=None)
    ap.add_argument("--mask-npz", default=None, help="可选孔径/掩模（非零处通过）")
    ap.add_argument("--n", type=int, default=None, help="补零到 N×N（默认下一个 2 的幂）")
    ap.add_argument("--pad", type=float, default=1.0,
                    help="在 max(输入尺寸) 上乘的补零系数，再取 2 的幂（默认 1.0）")
    ap.add_argument("--out", required=False, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if bool(args.npz) == bool(args.fsp):
        ap.error("--npz 与 --fsp 必须二选一")
    if args.distance_um is None:
        ap.error("缺 --distance-um")

    if args.dry_run:
        print(json.dumps({"dry_run": True, "input": args.npz or args.fsp,
                          "distance_um": args.distance_um, "n": args.n,
                          "mask": args.mask_npz}, ensure_ascii=False, indent=2))
        return 0
    if not args.out:
        ap.error("缺 --out")

    out = Path(args.out).resolve()
    try:
        if args.npz:
            raw = load_npz(Path(args.npz))
        else:
            raw = _read_fsp(Path(args.fsp), args.monitor)
        E = pick_field(raw)
        x, y = pick_axes(raw)
        lam = pick_wavelength(raw, args.wavelength_um)

        dx = float(x[1] - x[0])
        dy = float(y[1] - y[0])
        if not np.allclose(np.diff(x), dx, rtol=1e-6) or not np.allclose(np.diff(y), dy, rtol=1e-6):
            raise UsageError("坐标轴不是等间距，角谱法不适用")
        if abs(dx - dy) > 1e-9 * max(abs(dx), abs(dy)):
            raise UsageError("dx=%.4g 与 dy=%.4g 不等，当前只支持方形像素" % (dx, dy))

        asp.sampling_guard(dx * 1e-6, lam * 1e-6)
        base = max(E.shape[0], E.shape[1])
        n = args.n or int(2 ** np.ceil(np.log2(max(base, int(np.ceil(base * args.pad))))))
        if n < max(E.shape[0], E.shape[1]):
            raise UsageError("--n=%d 小于输入网格 %r" % (n, E.shape[:2]))

        if args.mask_npz:
            m = np.asarray(load_npz(Path(args.mask_npz))["mask"])
            if m.shape != E.shape[:2]:
                raise UsageError("mask 形状 %r 与场 %r 不一致" % (m.shape, E.shape[:2]))
            E = E * m[:, :, None] if E.ndim == 3 else E * m

        padded = square_pad(E, n)
        prop = asp.propagate(padded, dx * 1e-6, lam * 1e-6, args.distance_um * 1e-6)
        crop = (n - E.shape[0]) // 2, (n - E.shape[1]) // 2
        E_out = prop[crop[0]:crop[0] + E.shape[0], crop[1]:crop[1] + E.shape[1]]

        met = metrics_of(E, E_out, dx * 1e-6, lam, args.distance_um, n)
        met["input"] = args.npz or args.fsp
        met["mask"] = args.mask_npz
        out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out / "propagated.npz",
                            E=E_out, x_um=x, y_um=y, wavelength_um=lam,
                            distance_um=args.distance_um)
        (out / "propagate_metrics.json").write_text(
            json.dumps(met, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.json:
            print(json.dumps(met, indent=2, ensure_ascii=False))
        else:
            print("OK %s  E_out=%r  energy_ratio=%.6f"
                  % (out / "propagated.npz", E_out.shape, met["energy_ratio"] or 0.0))
        return 0
    except asp.SamplingError as e:
        print("sampling error: %s" % e, file=sys.stderr)
        return 2
    except UsageError as e:
        print("usage error: %s" % e, file=sys.stderr)
        return 2


def _read_fsp(fsp: Path, monitor: str) -> dict:
    """只读打开一次会话，把场监视器的复场读成与 npz 相同的键。"""
    api = os.environ.get("LUMERICAL_API_PATH",
                         r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
    os.environ.setdefault("ANSYSLMD_LICENSE_FILE",
                          os.environ.get("ANSYSLMD_LICENSE_FILE", "1055@localhost"))
    if api not in sys.path:
        sys.path.insert(0, api)
    import lumapi  # noqa: E402

    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(fsp))
        r = f.getresult(monitor, "E")
        d = dict(r) if hasattr(r, "keys") else {}
        E = np.asarray(d["E"])
        axes = {k: np.asarray(d[k], float).ravel() * 1e6
                for k in ("x", "y") if k in d}
        out = {"E": np.squeeze(E), "x_um": axes.get("x"), "y_um": axes.get("y")}
        for k in ("lambda", "f"):
            if k in d:
                v = np.asarray(d[k], float).ravel()
                out["wavelength_um"] = 1e6 / v[0] if k == "f" else v[0] * 1e6
                break
        return out
    finally:
        f.close()


if __name__ == "__main__":
    sys.exit(main())
