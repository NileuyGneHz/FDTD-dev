# -*- coding: utf-8 -*-
r"""
lumapi_common.py —— FDTD 会话与校验的共享工具
================================================================================

把 SKILL.md §8.4 的实测片段固化下来，避免每个包各写一遍。
**逻辑均来自本机已验证的实测片段**（2026-09-24 ~ 09-30）。

用法
    import sys
    sys.path.insert(0, r"F:\Lumercial_WS\FDTD_WS\_shared")
    from lumapi_common import (
        setup_env, open_fdtd, ascii_gate, assert_ran,
        mesh_report, n_at, run_sim,
    )

    setup_env()                    # 必须先调，设置 license + import lumapi
    f = open_fdtd()                # 带重试的会话工厂
    try:
        f.load(fsp)
        ...
    finally:
        f.close()

⚠️ 所有函数都不吞异常。失败就抛，不要把垃圾值当结果。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Lumerical 安装路径（本机实测）
LUMERICAL_API = r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python"
LICENSE_FILE = "1055@localhost"

_lumapi = None  # 模块级缓存


# ---- 环境与导入 ----------------------------------------------------------


def setup_env(verbose: bool = True):
    """设置 license 环境变量并把 Lumerical API 加进 sys.path，然后 import lumapi。

    ⚠️ 必须在 import lumapi 之前调用。系统 Python 3.14 无 numpy 会崩，
       请用托管 Python：
       C:\\Users\\saber\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe
    """
    global _lumapi
    os.environ.setdefault("ANSYSLMD_LICENSE_FILE", LICENSE_FILE)
    if LUMERICAL_API not in sys.path:
        sys.path.insert(0, LUMERICAL_API)
    try:
        import lumapi  # noqa
    except Exception as e:
        raise RuntimeError(
            f"import lumapi 失败: {e}\n"
            f"  检查 1) ANSYSLMD_LICENSE_FILE={LICENSE_FILE}"
            f"  2) API 路径存在: {LUMERICAL_API}"
            f"  3) 用的是托管 Python（3.13.x + numpy），不是系统 Python 3.14"
        ) from e
    _lumapi = lumapi
    if verbose:
        print(f"[env] lumapi OK  license={os.environ['ANSYSLMD_LICENSE_FILE']}")
    return lumapi


def get_lumapi():
    if _lumapi is None:
        raise RuntimeError("请先调用 setup_env()")
    return _lumapi


# ---- 会话工厂（含端口 TIME_WAIT 重试）------------------------------------


def open_fdtd(n: int = 8, delay: float = 6.0, hide: bool = True):
    """建 headless 会话，带重试。

    频繁新建/关闭会话时会撞 ansyscl 端口 TIME_WAIT，报
    'Failed to set up Ansys license sharing ... Could not bind socket on port xxx'。
    这是瞬时故障，重试即可（SKILL.md §1.4）。
    """
    lumapi = get_lumapi()
    for i in range(n):
        try:
            return lumapi.FDTD(hide=hide)
        except Exception as e:
            s = str(e)
            hint = "端口 TIME_WAIT（重试即可）" if "bind socket" in s else s[:100]
            print(f"  [会话重试 {i + 1}/{n}] {hint}")
            time.sleep(delay)
    raise RuntimeError("会话创建连续失败（已重试 %d 次）" % n)


def n_sessions() -> int:
    """数当前 fdtd-solutions.exe 进程数 = 占用几个 license 席位。

    ⚠️ 要在脚本存活期间调用。脚本跑完后再数，GC 已收拾干净，会得出错误结论。
    """
    try:
        out = subprocess.run(
            ["tasklist"], capture_output=True, text=True, errors="replace"
        ).stdout
    except Exception:
        return -1
    return sum(1 for line in out.splitlines() if "fdtd-solutions" in line.lower())


# ---- 闸门与校验 ----------------------------------------------------------


def ascii_gate(p, verbose: bool = True) -> bool:
    """路径 ASCII 闸门。返回 True = 安全；False = 必须先复制到 ASCII 路径。

    GPU 引擎 (fdtd-engine.exe) 遇非 ASCII 字符必崩，报错是乱码（错误码 1113）。
    空格无关；CPU 引擎没这个问题（SKILL.md §6.2）。
    """
    try:
        str(p).encode("ascii")
        return True
    except UnicodeEncodeError:
        if verbose:
            print(f"[ASCII 闸门] 路径含非 ASCII -> GPU 引擎必崩: {p}")
        return False


def assert_ran(fdtd, fsp_path, verbose: bool = True) -> bool:
    """三判据确认"仿真真的算了"。任一不过就抛异常。

    ① layoutmode == 0.0    （1.0 = 还在 layout，即 run() 静默失效）
    ② 存在 <工程名>_p0.log （引擎真的被拉起来）
    ③ 日志含 'Completed'   （算到底了）

    另会扫 'diverging' —— 发散是"不报错的错"，只看到 R=0 很容易误判。
    """
    # ① 模式
    fdtd.eval("lm = layoutmode;")
    lm = float(fdtd.getv("lm"))
    if lm != 0.0:
        raise RuntimeError(
            f"layoutmode={lm} → run() 静默失效。"
            f"headless 新建会话必须先 save → 新会话 load → 再 run（SKILL.md §2.1）"
        )

    # ② 日志存在
    log = Path(str(Path(fsp_path).with_suffix("")) + "_p0.log")
    if not log.exists():
        raise RuntimeError(
            f"没有 {log.name} → 引擎压根没启动。检查：路径非 ASCII？GPU 资源未激活？"
        )

    # ③ 内容
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Completed" not in txt:
        raise RuntimeError(f"{log.name} 无 'Completed' → 中途死掉，见日志末尾")
    if "diverging" in txt.lower():
        raise RuntimeError(
            f"{log.name} 出现 diverging（场发散）→ "
            f"dt stability factor 0.99→0.95，或改 CPU 双精度（SKILL.md §6.3）"
        )

    if verbose:
        for line in txt.splitlines():
            if "Simulation size in gridpoints" in line:
                print("   网格:", line.split(":")[-1].strip())
            if "total iterations" in line:
                print("   迭代:", line.strip())
    return True


def mesh_report(log_path) -> dict:
    """从 _p0.log 抽关键数字，判断网格规模是否健康（耗时异常时先用这个）。

    健康范围：网格 1e5~1e6 / 内存 < 80% 显存 / 迭代 1e4~1e5 / 剩余 分钟级
    """
    keys = [
        "Simulation size in gridpoints",
        "Estimate of memory required",
        "total iterations",
        "Max time remaining",
        "Detected GPU",
        "Using datatype",
    ]
    found = {}
    p = Path(log_path)
    if not p.exists():
        print(f"[mesh_report] 找不到 {p}")
        return found
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        for k in keys:
            if k in line:
                found[k] = line.strip()
                print("  ", line.strip())
    return found


# ---- 材料折射率（绕开 getindex 频率坑）-----------------------------------


def n_at(fdtd, mat_name, lam_m, verbose: bool = False):
    """查材料在给定波长下的复折射率。内部自动把波长换成频率。

    ⚠️ 直接给 getindex 传波长不报错，但会返回荒谬值
       （TiO2 传 532e-9 → n=5.99，正确 2.45）。
       getindex 收的是频率(Hz)，且必须传矩阵（SKILL.md §5.2）。

    返回 (n, k)。
    """
    import numpy as np

    C0 = 299792458.0
    freq = C0 / float(lam_m)
    res = fdtd.getindex(mat_name, np.array([[freq]]))
    z = complex(np.array(res).ravel()[0])
    if verbose:
        print(f"  {mat_name} @{lam_m * 1e9:.0f}nm: n={z.real:.4f} k={z.imag:.4f}")
    return z.real, z.imag


def check_material(fdtd, mat_name, lam_m, expect_n, tol=0.15):
    """带期望值的材料校验（防频率坑）。expect_n 来自文献/论文。"""
    n, k = n_at(fdtd, mat_name, lam_m)
    if abs(n - expect_n) > tol:
        raise RuntimeError(
            f"{mat_name} @{lam_m * 1e9:.0f}nm 读到 n={n:.3f}，期望 {expect_n}±{tol}。"
            f"→ 大概率传了波长而非频率，或材料数据源不同（四套差 ~15%）"
        )
    return n, k


# ---- 推荐的完整运行序列 --------------------------------------------------


def run_sim(fsp_path, verbose: bool = True):
    """照抄这个序列，别自己发明（SKILL.md §2.1 / §2.2）。

    返回 (fdtd, should_close) —— 调用方负责 finally close。
    """
    lumapi = get_lumapi()
    ascii_gate(fsp_path)

    # ① 载入并切回 layout 才能改参数
    f = open_fdtd()
    try:
        f.load(fsp_path)
        f.switchtolayout()
        if verbose:
            print(f"[run] loaded {Path(fsp_path).name}, switched to layout")
        return f
    except Exception:
        f.close()
        raise


def verify_and_run(fsp_path, verbose: bool = True):
    """save→关→新会话 load→run→三判据。返回已跑完的会话（调用方负责 close）。"""
    lumapi = get_lumapi()
    ascii_gate(fsp_path)

    # 第一段：确保落盘
    f = open_fdtd()
    try:
        f.load(fsp_path)
        f.switchtolayout()
        f.save(fsp_path)
    finally:
        f.close()

    # 第二段：新会话载入后 run 才生效
    f2 = open_fdtd()
    try:
        f2.load(fsp_path)
        f2.eval("switchtolayout;")
        if verbose:
            print(f"[run] running {Path(fsp_path).name} ...")
        t0 = time.time()
        f2.run()
        assert_ran(f2, fsp_path, verbose=verbose)
        if verbose:
            print(f"[run] done in {time.time() - t0:.1f}s")
        return f2
    except BaseException:
        f2.close()
        raise


# ---- 自测 ----------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("lumapi_common 自测")
    print("=" * 70)
    setup_env()
    print(f"[自测] 当前 fdtd-solutions.exe 进程数 = {n_sessions()}")
    print(f"[自测] ASCII 闸门")
    print("  纯 ASCII 路径:", ascii_gate(r"F:\Lumercial_WS\projects\d2\d2_pml.fsp"))
    print("  中文路径    :", ascii_gate(r"F:\Lumercial_WS\测试\工程.fsp"))
    print("[自测] 建一个会话并立即关闭（验证环境可用）")
    f = open_fdtd()
    try:
        print(f"  会话建立成功，进程数 = {n_sessions()}")
    finally:
        f.close()
    time.sleep(1)
    print(f"  关闭后进程数 = {n_sessions()}")
    print("[自测] 完成")
