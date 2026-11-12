# -*- coding: utf-8 -*-
"""angular_spectrum.py — 标量角谱传播（纯模块，无 CLI、不做 I/O）。

为什么单独成模块
----------------
`fdtd-holo-phase-retrieval/scripts/gs_retrieval.py::propagate` 里已经有一份可用实现，
但它是 GS 迭代的内部函数、没有入参校验、也没有对外的数据契约。本模块是
`fdtd-lumerical-field-propagate` 的零件，只做一件事：给定「场 + 间距 + 波长 + 距离」，
返回传播后的场。

**与 holo 的关系**：两者必须逐点一致（EXP-68 断言 <1e-12）。holo 暂不改为 import，
避免动一个已绿的技能；等哪天要动，只改它的 propagate 内部即可。

符号约定
--------
- 时间因子 `exp(-iωt)`，正向传播相位 `exp(+i·kz·z)`；
- 倏逝分支（`kz² < 0`）在**正向**必须衰减 `exp(-|kz|z)`；
  反向用共轭会把它变成放大，噪声会被指数放大——这是刻意的取舍，不是 bug。

边界（写进 SKILL 的 CRITICAL）
------------------------------
1. `dx > λ/2` 时传播函数本身仍能算，但结果是混叠的假象；`sampling_guard` 负责拒绝。
2. 采样窗 `N·dx` 不够大时，场会从一边绕到另一边（FFT 周期性）；`max_distance` 给出
   「在给定 N 下还能传播多远」的估计。
"""

from __future__ import annotations

import numpy as np


class SamplingError(ValueError):
    """采样不满足角谱法的要求——调用方应 exit 2，而不是继续算。"""


def sampling_guard(dx_m: float, lam_m: float) -> None:
    """`dx > λ/2` 直接拒绝。

    FDTD 的场监视器网格通常是 λ/10~λ/20，正常不会触发；但 `--npz` 可能来自任意导出，
    而 dx 一旦超过 λ/2，高频角谱就折叠回低频，结果看起来像"传播了"其实是混叠。
    """
    if dx_m <= 0 or lam_m <= 0:
        raise SamplingError("dx=%.4g m / lambda=%.4g m 必须为正" % (dx_m, lam_m))
    if dx_m > lam_m / 2.0:
        raise SamplingError(
            "dx=%.4g um > lambda/2=%.4g um：角谱会混叠。最小要求 dx <= %.4g um；"
            "请先对场做降采样或换一个监视器。"
            % (dx_m * 1e6, lam_m * 0.5e6, lam_m * 0.5e6)
        )


def max_distance(n: int, dx_m: float, lam_m: float) -> float:
    """在 N×N 网格上可靠的传播距离上限（米）。

    取 `N·dx²/λ`：这是"相邻两点相位差不超过一个周期"的经验界，超过它，
    传递函数的相位在频域里周期化，结果会绕回来。返回值只用于告警，不强制。
    """
    return float(n * dx_m ** 2 / lam_m)


def transfer_2d(n: int, dx_m: float, lam_m: float, z_m: float) -> np.ndarray:
    """返回 N×N 的角谱传递函数（与 `np.fft.fft2` 的未移位频率顺序一致）。"""
    fx = np.fft.fftfreq(n, d=dx_m)
    FX, FY = np.meshgrid(fx, fx)
    arg = 1.0 / lam_m ** 2 - FX ** 2 - FY ** 2
    H = np.zeros(FX.shape, dtype=complex)
    prop = arg >= 0
    H[prop] = np.exp(2j * np.pi * z_m * np.sqrt(arg[prop]))
    H[~prop] = np.exp(-2.0 * np.pi * abs(z_m) * np.sqrt(-arg[~prop]))
    return H


def evanescent_fraction(n: int, dx_m: float, lam_m: float) -> float:
    """网格里倏逝分量的占比（按频点数），用于报告可信度。"""
    fx = np.fft.fftfreq(n, d=dx_m)
    FX, FY = np.meshgrid(fx, fx)
    arg = 1.0 / lam_m ** 2 - FX ** 2 - FY ** 2
    return float(np.count_nonzero(arg < 0)) / float(arg.size)


def propagate(field: np.ndarray, dx_m: float, lam_m: float, z_m: float,
              forward: bool = True) -> np.ndarray:
    """对 `(n, n)` 或 `(n, n, c)` 的复场做角谱传播，逐分量独立处理。"""
    a = np.asarray(field)
    if a.ndim == 2:
        return _propagate_one(a, dx_m, lam_m, z_m, forward)
    if a.ndim == 3:
        return np.stack([_propagate_one(a[..., i], dx_m, lam_m, z_m, forward)
                         for i in range(a.shape[2])], axis=-1)
    raise SamplingError("场必须是 (n,n) 或 (n,n,c)，实际形状 %r" % (a.shape,))


def _propagate_one(u: np.ndarray, dx_m: float, lam_m: float, z_m: float,
                   forward: bool) -> np.ndarray:
    if u.ndim != 2 or u.shape[0] != u.shape[1]:
        raise SamplingError("角谱当前只接受方阵网格，实际 %r" % (u.shape,))
    n = u.shape[0]
    H = transfer_2d(n, dx_m, lam_m, abs(z_m))
    # 反向（显式 forward=False，或给了负距离）用共轭：倏逝分支随之变成放大，
    # 这是逆传播的数学事实，调用方要自己限制距离。
    if (not forward) or (z_m < 0):
        H = np.conj(H)
    return np.fft.ifft2(np.fft.fft2(u) * H)
