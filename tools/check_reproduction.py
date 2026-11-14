#!/usr/bin/env python3
"""check_reproduction.py — 复现约束体检（机器可读语料门禁）。

    python tools/check_reproduction.py --case P01
    python tools/check_reproduction.py --card <path>    # 草稿卡自检
    python tools/check_reproduction.py --self-test      # 负对照：门禁没退化
    python tools/check_reproduction.py --json
    python tools/check_reproduction.py --emit-template

规则出处：docs/constitution/reproduction-contract.md（逐条对应 [R1]–[R16]；
[R15] 是历史跳号，文本历史里从未出现过，**不要复用**）。
与 tools/check_skill_contract.py 的分工：
    check_skill_contract = 技能内容合不合契约
    check_reproduction   = 一次复现的证据齐不齐、指标测没测、能不能拿来训练技能

检查项：
    [R1]  repro-card 存在，```repro-card JSON 块合法，必填字段齐全
    [R2]  mode=reproduce 时 locked 齐全，verdict.status 不得为 fitted（禁止调参凑数）
    [R3]  口径声明齐全；求解器不同时 verdict 只能判 solver_mismatch / inconclusive
    [R4]  每个参考 .fsp 存在；converged / shutoff 声明与 _p0.log 实测一致
    [R5]  每个 run 的 shutoff_final < threshold；日志在场时与末值一致；diverging 强制 FAIL
    [R6]  same_input_regression.delta <= tolerance，且 runs >= 2；回归量泛型（不绑 peak_A）
    [R7]  excluded[] 每条有 suspect / verdict / 非空 evidence
    [R8]  verdict.stop_reason 非空、gap 有数值、explainable_by 与 status 自洽
    [R9]  所有 runs[].out 不落在只读 cases/
    [R10] defects[] 每个 D 号文件存在且三段（根因/修复/验证）齐全
    [R11] training_items[] 非空，destination 合法，landed=true 时 target_path 存在
    [R12] rerun_commands[] 非空、全卡无绝对路径；命令缺 --out 记 WARN
    [R13] target.quantity 必须真实出现在某条 runs[].out 的 CSV 表头 / metrics 里；
          未测到时必须声明 unmeasured_reason 且 status 只能是 inconclusive/unresolved
    [R14] target.definition 非空，且 target.source 能回查（含 Fig./Eq./Table/p.N/§）
    [R15] —— 未分配（历史跳号，勿复用）
    [R16] rerun_commands 里引用的仓库内文件（skills/ cases/ tools/ docs/ 开头）必须实存；
          _scratch/ 产物允许尚未生成

退出码：0 = 通过（允许 WARN；--self-test 通过亦为 0）；1 = 有 FAIL 或负对照未拦全；
        2 = 参数或卡片枚举错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 非 UTF-8 的 stdout 会让中文 OK/FAIL 行抛 UnicodeEncodeError，门禁自己 exit 1 ——
# 「判违规」和「编码崩了」在退出码上无法区分（D-010 的同类风险，2026-11-10 实测
# PYTHONIOENCODING=cp1252 下 --case P01 必崩）。统一钉死 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:                       # noqa: BLE001 - 已被重定向的流无法 reconfigure
    pass

ROOT = Path(__file__).resolve().parents[1]
# 卡可落在 cases/ projects/ 的 notes/（契约 §7 允许补记），
# 或隔离回归目录 _scratch/regress/（多 agent 并行时避免写只读 assets、避免相互覆盖）。
DRAFT_RE = re.compile(r"draft", re.I)
# 正式卡落在包内 notes/（cases/AGENTS.md 允许补记）；草稿卡落在隔离回归目录，
# 避免多 agent 并行写同一包、也避免碰只读资产。
# 2026-11-14：cases/ 分双轨（metasurface / photonic），卡片在第三层。
# 只保留一层 glob 会让 2 张已存在的卡变成 0 张 —— 门禁显示 ALL GREEN 但其实没查任何东西。
FORMAL_PATTERNS = (
    "cases/*/notes/repro-card.md",              # 扁平布局（兼容）
    "cases/*/*/notes/repro-card.md",            # 双轨布局
    "projects/*/notes/repro-card.md",
    "projects/*/*/notes/repro-card.md",
)
DRAFT_PATTERNS = ("_scratch/regress/**/repro-card*.md",)
# 默认全量门禁只认正式卡（草稿在 _scratch/，gitignored，不算已提交证据）；
# --case / --card 时才把草稿纳入检查，供并行 agent 自检。
CARD_PATTERNS = FORMAL_PATTERNS + DRAFT_PATTERNS
CARD_BLOCK_RE = re.compile(r"```repro-card\s*\r?\n(.*?)\r?\n```", re.S)
SHUTOFF_RE = re.compile(r"Auto Shutoff:\s*([0-9.eE+-]+)", re.I)
# 收紧：P01 正常收敛写 "autoshutoff criteria are satisfied"；
# P03 发散写 "ERROR: Early termination ... electromagnetic fields are diverging"（不得算 early）。
EARLY_RE = re.compile(r"autoshutoff criteria are satisfied", re.I)
DIVERGED_RE = re.compile(r"electromagnetic fields are diverging|fields are diverging", re.I)
P100_RE = re.compile(r"100%\s*complete", re.I)
COMPLETED_RE = re.compile(r"Completed\s+\d+\s+iterations", re.I)
ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
REPEAT_COST_LIMIT_S = 300.0     # 超过这个单次成本才允许豁免「同输入重跑」

# 求解器「族」：只比族，不比版本串。
# 事件：P05/P06 卡写 paper="Lumerical FDTD"、actual="Lumerical FDTD v251"，
# 旧逻辑字符串全等 -> 同一求解器被判 solver_mismatch，逼人改结论。
_SOLVER_FAMILIES = (
    (("lumerical", "fdtd solutions", "fdtd-solutions"), "lumerical-fdtd"),
    (("cst",), "cst"),
    (("comsol",), "comsol"),
    (("fmm", "rcwa"), "fmm-rcwa"),
    (("meep",), "meep"),
)
_ABS_EXE_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'`]*?([A-Za-z0-9_]+)\.exe\b", re.I)
_INTERP_NAMES = {"python", "pythonw", "py", "pwsh", "power" + "shell", "bash", "cmd", "sh"}


def solver_family(name: str) -> str:
    """'Lumerical FDTD v251' / 'FDTD Solutions' / 'Lumerical' -> 'lumerical-fdtd'."""
    t = re.sub(r"\bv?\d+(?:[._]\d+)*\b", " ", str(name).lower())
    t = re.sub(r"\s+", " ", t).strip()
    for keys, fam in _SOLVER_FAMILIES:
        if any(k in t for k in keys):
            return fam
    return "unknown:" + (t.replace(" ", "-") or "empty")


def strip_interpreters(text: str) -> str:
    """去掉解释器可执行文件的绝对路径（C:/.../python.exe）。

    事件：reproduction-contract §6 说「本机解释器路径属运行时约定，不扫」，
    脚本却对整张卡查绝对路径 -> 每张带解释器路径的卡必 FAIL。
    """
    return _ABS_EXE_RE.sub(
        lambda m: "" if m.group(1).lower() in _INTERP_NAMES else m.group(0), text)

DESTINATIONS = {"defects", "notes", "references", "scripts", "SKILL.md"}
STATUSES = {"reproduced", "solver_mismatch", "inconclusive", "unresolved", "fitted"}
UNMEASURED_OK = {"inconclusive", "unresolved"}
REQUIRED_FIELDS = (
    "case", "mode", "date", "target", "actual_solver", "locked",
    "truth_sources", "runs", "same_input_regression", "excluded",
    "verdict", "defects", "training_items", "rerun_commands",
)
REQUIRED_LOCKED = {"materials", "layer_stack", "topology", "geometry"}
# [R13] quantity -> 该量在产物 CSV 表头 / run.metrics 键里可能出现的别名。
# 复合量（如 peak_transmittance_and_dphi）要求每个子量都命中。
QUANTITY_ALIASES = {
    "peak_absorption": [{"a", "peak_a", "absorption", "abs"}],
    "peak_absorbance": [{"a", "peak_a", "absorption", "absorbance", "abs"}],
    "absorption": [{"a", "peak_a", "absorption", "abs"}],
    "peak_transmittance": [{"t", "peak_t", "transmittance", "transmission"}],
    "transmittance": [{"t", "peak_t", "transmittance", "transmission"}],
    "dphi": [{"dphi", "dphi_deg", "dphi_deg_mod360", "phase_difference", "delta_phi"}],
    "phase_difference": [{"dphi", "dphi_deg", "phase_difference", "delta_phi"}],
    "peak_transmittance_and_dphi": [
        {"t", "peak_t", "transmittance", "transmission"},
        {"dphi", "dphi_deg", "dphi_deg_mod360", "phase_difference", "delta_phi"},
    ],
    "pcr": [{"pcr", "polarization_conversion_ratio", "r_cr"}],
    "polarization_conversion_ratio": [{"pcr", "polarization_conversion_ratio", "r_cr"}],
    "conversion_efficiency": [{"conversion_efficiency", "efficiency", "eta"}],
    "peak_angle_deg": [{"peak_angle_deg", "theta_r", "reflection_angle", "angle_deg"}],
    "reflection_angle": [{"peak_angle_deg", "theta_r", "reflection_angle", "angle_deg"}],
    # 2026-11-09 扩：P07 反射率型、P05 场型复现原本没有一条通路能过 [R13]
    "reflectance": [{"r", "peak_r", "reflectance", "reflection"}],
    "peak_reflectance": [{"r", "peak_r", "reflectance", "reflection"}],
    "fwhm": [{"fwhm", "fwhm_um", "fwhm_nm", "bandwidth"}],
    "peak_wavelength": [{"peak_lam", "peak_lambda", "peak_wavelength", "lambda_peak"}],
    "focal_shift": [{"focal_shift", "focal_shift_um", "delta_f", "dz_focus"}],
    "oam_weight": [{"oam", "oam_weight", "l_weight", "topological_charge"}],
}

fails: list[str] = []
warns: list[str] = []
ok_count = 0
QUIET = False


def ok(n: str, msg: str) -> None:
    global ok_count
    ok_count += 1
    if not QUIET:
        print(f"  [{n}] OK    {msg}")


def bad(n: str, msg: str, hint: str = "") -> None:
    fails.append(f"[{n}] {msg}")
    if not QUIET:
        print(f"  [{n}] FAIL  {msg}")
        if hint:
            print(f"        -> {hint}")


def warn(n: str, msg: str) -> None:
    warns.append(f"[{n}] {msg}")
    if not QUIET:
        print(f"  [{n}] WARN  {msg}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def close(a: float, b: float, rel: float = 1e-3) -> bool:
    return abs(a - b) <= max(1e-18, abs(b) * rel)


def pkg_root_of(card: Path) -> Path:
    """卡在 cases/projects 包内时包根是 parent.parent；在 _scratch 隔离目录时是 parent。

    隔离草稿卡里的相对路径是相对该回归目录解释的（P02/P03 卡片用的都是仓库根相对
    路径如 cases/... 或 _scratch/...，由 resolve() 直接命中 ROOT 顶层，不受此影响）。
    """
    try:
        rel = card.relative_to(ROOT).as_posix()
    except ValueError:
        return card.parent
    if rel.startswith(("cases/", "projects/")):
        return card.parent.parent
    return card.parent


def resolve(raw: str, pkg_root: Path) -> Path:
    """卡内路径：顶层目录在仓库根存在则按仓库根解析，否则按包根解析。

    cases/ skills/ defects/ _scratch/ -> ROOT；model/ notes/ config/ -> 单元包内。
    """
    p = Path(raw.replace("\\", "/"))
    if p.parts and (ROOT / p.parts[0]).exists():
        return ROOT / p
    return pkg_root / p


def parse_log(path: Path, threshold: float | None) -> dict:
    txt = read(path)
    vals = SHUTOFF_RE.findall(txt)
    final = None
    for raw in reversed(vals):
        final = num(raw)
        if final is not None:
            break
    diverged = bool(DIVERGED_RE.search(txt))
    early = bool(EARLY_RE.search(txt)) and not diverged
    p100 = bool(P100_RE.search(txt))
    converged = bool(
        not diverged and final is not None and threshold is not None
        and final < threshold and (early or p100)
    )
    return {
        "final": final, "early": early, "p100": p100, "diverged": diverged,
        "completed": bool(COMPLETED_RE.search(txt)), "converged": converged,
    }


def check_convergence(n: str, label: str, entry: dict, pkg_root: Path) -> None:
    """[R4]/[R5] 共用：数值自洽 + 日志在场时与实测比对 + diverging 判定。

    diverging 语义（与 library/py/lumapi_common.py::assert_ran 一致）：
      - 卡片**已诚实声明** converged=false / role=counterexample → WARN（合法反例真相源，
        但绝不可当黄金对照），P03 的 fig1_hwp_paper_materials 就是这种；
      - 卡片声称收敛或没表态 → FAIL（隐瞒发散 = 把不可信结果当证据）。
    """
    final = num(entry.get("shutoff_final", entry.get("shutoff")))
    thr = num(entry.get("threshold"))
    declared = entry.get("converged")
    role = str(entry.get("role") or "").lower()
    if final is None or thr is None:
        if entry.get("unrun") is True:
            log_raw = entry.get("p0_log")
            logp = resolve(str(log_raw), pkg_root) if log_raw else None
            lm = str(entry.get("layoutmode", "")).strip()
            if logp is not None and logp.is_file():
                bad(n, f"{label} 声明 unrun=true 但 _p0.log 存在 —— 伪造豁免")
            elif lm not in {"1", "1.0", "layout"}:
                bad(n, f"{label} 声明 unrun=true 但缺 layoutmode=1 证据"
                       f"（实际 {lm or '未给'}）")
            else:
                ok(n, f"{label} unrun（layoutmode=1 且无 _p0.log）：参考工程从未跑过，不填数值")
        else:
            bad(n, f"{label} 缺 shutoff/threshold 数值",
                "若参考工程从未跑过：改 unrun=true，并给 layoutmode=1 与 p0_log 路径自证")
        return
    log_raw = entry.get("p0_log")
    logp = resolve(str(log_raw), pkg_root) if log_raw else None
    info = parse_log(logp, thr) if logp and logp.is_file() else None
    if info is None:
        if not log_raw:
            warn(n, f"{label} 未登记 p0_log，收敛数值不可复核")
        else:
            warn(n, f"{label} 日志未归档（{log_raw}），换机器不可核验")
        # 日志不在场时仍做纯数值自洽检查
        if declared is not False and not final < thr:
            bad(n, f"{label} shutoff_final={final:g} 不小于阈值 {thr:g}")
        return
    if info["diverged"]:
        honest = declared is False or role in {"counterexample", "negative", "diverged"}
        msg = f"{label} 日志出现 diverging（场发散）：{log_raw}"
        if honest:
            warn(n, f"{msg}；卡片已声明未收敛/作反例，禁止当黄金对照")
        else:
            bad(n, f"{msg}，但卡片未声明未收敛，结果不可信",
                "与 lumapi_common.py::assert_ran 一致；改 converged=false 且 role=counterexample")
        return
    if declared is False:
        # 未收敛的参考工程是合法真相源，只要求与日志一致，不要求末值低于阈值
        if final < thr:
            warn(n, f"{label} 声明未收敛但末值 {final:g} 已低于阈值 {thr:g}，请核对")
    elif not final < thr:
        bad(n, f"{label} shutoff_final={final:g} 不小于阈值 {thr:g}")
        return
    if info["final"] is None:
        bad(n, f"{label} 日志里没有 Auto Shutoff 行：{logp}")
        return
    if not close(info["final"], final):
        bad(n, f"{label} 卡片 shutoff={final} 与日志末值 {info['final']} 不符",
            f"改 {logp} 对应的卡片数值")
        return
    if declared is None and not info["converged"]:
        bad(n, f"{label} run 未收敛（末值 {info['final']:g}），结果不可信")
        return
    if declared is not None and bool(declared) != info["converged"]:
        bad(n, f"{label} converged={declared} 与日志判定 {info['converged']} 不符",
            "检查是否有 autoshutoff criteria are satisfied / 100% complete 行")
        return
    ok(n, f"{label} 收敛数值与日志一致（{info['final']:g}，converged={info['converged']}）")


def regression_pair(reg: dict) -> tuple[float | None, float | None]:
    """[R6] 同输入回归的两个数：泛型优先，兼容旧卡的 _A 后缀。

    泛型键：baseline / repeat；或 metrics: {<quantity>: {baseline, repeat}}。
    旧键：baseline_A / repeat_A（P01 卡）。
    """
    b = num(reg.get("baseline"))
    r = num(reg.get("repeat"))
    if b is None or r is None:
        m = reg.get("metrics")
        if isinstance(m, dict):
            for v in m.values():
                if isinstance(v, dict):
                    bb, rr = num(v.get("baseline")), num(v.get("repeat"))
                    if bb is not None and rr is not None:
                        return bb, rr
    if b is None or r is None:
        b, r = num(reg.get("baseline_A")), num(reg.get("repeat_A"))
    return b, r


def collect_metric_keys(c: dict, pkg_root: Path) -> tuple[set[str], list[str]]:
    """[R13] 收集所有 run 产物里真实存在的指标名（小写）。

    来源：runs[].metrics 键、runs[].out 目录下的 CSV 表头、summary.csv 的列。
    返回 (keys, 找到的产物文件列表)。
    """
    keys: set[str] = set()
    artifacts: list[str] = []
    for run in c.get("runs") or []:
        m = run.get("metrics")
        if isinstance(m, dict):
            keys |= {str(k).strip().lower() for k in m}
        out = str(run.get("out") or "")
        for key in ("columns", "csv_columns"):
            cols = run.get(key)
            if isinstance(cols, list):
                keys |= {str(k).strip().lower() for k in cols}
        if not out:
            continue
        d = resolve(out, pkg_root)
        if not d.is_dir():
            continue
        for csv in sorted(d.glob("*.csv")):
            try:
                head = read(csv).splitlines()[0]
            except (OSError, IndexError):
                continue
            keys |= {x.strip().lower() for x in head.split(",") if x.strip()}
            artifacts.append(csv.relative_to(ROOT).as_posix()
                             if csv.is_relative_to(ROOT) else csv.as_posix())
    return keys, artifacts


def check_metric_presence(c: dict, pkg_root: Path, tag: str) -> None:
    """[R13] 验收量必须真的被测过，否则 stop_reason 必须诚实承认"没测"。

    P03 反例：target.quantity=PCR，两次 run 输出列只有 lam_um,R,T,A，门禁却 ALL GREEN。
    """
    t = c.get("target") or {}
    quantity = str(t.get("quantity") or "").strip().lower()
    verdict = c.get("verdict") or {}
    status = str(verdict.get("status", ""))
    keys, artifacts = collect_metric_keys(c, pkg_root)
    aliases = QUANTITY_ALIASES.get(quantity)
    measured: bool | None = None
    detail = ""
    if aliases is None:
        # 未知 quantity：不猜测，要求卡自己声明 measured_columns 或 measured_in
        declared = t.get("measured_columns") or t.get("measured_in")
        if declared:
            cols = [str(x).strip().lower() for x in
                    (declared if isinstance(declared, list) else [declared])]
            measured = all(x in keys for x in cols)
            detail = f"卡声明 measured_columns={cols}"
        else:
            warn("R13", f"{tag} 未知 quantity={quantity!r}，无法自动核对；"
                        "请在 target.measured_columns 声明产物列名")
            return
    else:
        missing = [sorted(a) for a in aliases if not (a & keys)]
        measured = not missing
        detail = f"产物列名={sorted(keys) or '（空）'}"
        if missing:
            detail += f"；缺 {'; '.join('|'.join(g) for g in missing)}"
    unmeasured_reason = str(t.get("unmeasured_reason")
                            or verdict.get("unmeasured_reason") or "").strip()
    if measured:
        ok("R13", f"{tag} 验收量 {quantity!r} 在产物中可核验（{detail}）")
        return
    if unmeasured_reason and status in UNMEASURED_OK:
        warn("R13", f"{tag} 验收量 {quantity!r} 未测到，已声明原因且 status={status}；"
                    f"{detail}", )
        return
    bad("R13", f"{tag} 验收量 {quantity!r} 从未出现在任何 run 产物里（{detail}）",
        "要么补测并在 runs[].metrics / CSV 里产出该量；要么在 target.unmeasured_reason "
        "写明没测的原因并把 verdict.status 改为 inconclusive / unresolved")


def check_card(card: Path) -> None:
    pkg_root = pkg_root_of(card)
    tag = f"{pkg_root.name}/{card.name}"
    if not QUIET:
        print(f"\n=== {tag} ===")
    text = read(card)
    m = CARD_BLOCK_RE.search(text)
    if not m:
        bad("R1", f"{tag} 没有 ```repro-card JSON 代码块")
        return
    try:
        c = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        bad("R1", f"{tag} 卡片 JSON 解析失败：{e}")
        return
    missing = [k for k in REQUIRED_FIELDS if k not in c]
    if missing:
        bad("R1", f"{tag} 缺必填字段：{', '.join(missing)}")
        return
    ok("R1", f"{tag} 卡片可解析，14 个必填字段齐全")

    # [R2] 锁定项与禁止调参凑数
    locked = set(c.get("locked") or [])
    verdict = c.get("verdict") or {}
    status = str(verdict.get("status", ""))
    if c.get("mode") == "reproduce":
        lack = REQUIRED_LOCKED - locked
        if lack:
            bad("R2", f"{tag} locked 缺 {', '.join(sorted(lack))}")
        elif status == "fitted":
            bad("R2", f"{tag} verdict.status=fitted：把拟合当复现，违反 L1 §3",
                "恢复论文几何参数，重新判定")
        else:
            ok("R2", f"{tag} 锁定项齐全，status={status}（非 fitted）")
    else:
        warn("R2", f"{tag} mode={c.get('mode')}，非 reproduce，跳过锁定项检查")

    # [R3] 口径声明
    t = c.get("target") or {}
    paper_solver = str(t.get("solver") or "")
    actual = str(c.get("actual_solver") or "")
    fam_paper, fam_actual = solver_family(paper_solver), solver_family(actual)
    if (num(t.get("value")) is None or not t.get("quantity")
            or not t.get("source") or not paper_solver or not actual):
        bad("R3", f"{tag} 口径声明不全（quantity/value/source/solver/actual_solver）")
    elif fam_paper != fam_actual and status not in {"solver_mismatch", "inconclusive"}:
        bad("R3", f"{tag} 求解器不同（{paper_solver} vs {actual}；族 {fam_paper} vs {fam_actual}）"
                  f"却判 status={status}",
            "改为 solver_mismatch / inconclusive，差异本身是产出")
    elif fam_paper != fam_actual:
        ok("R3", f"{tag} 求解器族不同（{fam_paper} vs {fam_actual}）-> {status}（口径诚实）")
    else:
        ok("R3", f"{tag} 口径声明齐全；同族（{fam_paper}）-> {status}")

    # [R13] 验收量实存（放在真相源之前：指标没测就不要谈对照）
    check_metric_presence(c, pkg_root, tag)

    # [R4] 真相源
    sources = c.get("truth_sources") or []
    if not sources:
        warn("R4", f"{tag} 没有登记参考 .fsp（若本包确实没有，可忽略）")
    for s in sources:
        label = str(s.get("path") or "<unnamed>")
        fsp = resolve(label, pkg_root)
        if not fsp.exists():
            bad("R4", f"{tag} 参考工程不存在：{label}")
            continue
        ok("R4", f"{tag} 参考工程存在：{label}")
        check_convergence("R4", f"{tag} {fsp.name}", s, pkg_root)

    # [R5] 运行收敛；[R6] 还要求至少两条可对照的 run
    runs = c.get("runs") or []
    if len(runs) < 2:
        bad("R6", f"{tag} runs 只有 {len(runs)} 条，至少需要基线 + 对照两条")
    for r in runs:
        check_convergence("R5", f"{tag} run:{r.get('name', '?')}", r, pkg_root)

    # [R6] 同输入回归（泛型，不绑 peak_A）
    reg = c.get("same_input_regression") or {}
    delta = num(reg.get("delta"))
    tol = num(reg.get("tolerance"))
    b, r = regression_pair(reg)
    if delta is None or tol is None or b is None or r is None:
        cost = num(reg.get("repeat_cost_s"))
        reason = str(reg.get("repeat_skipped_reason") or "").strip()
        if cost is None:
            bad("R6", f"{tag} same_input_regression 缺数值字段"
                      "（需要 baseline/repeat 或 metrics{}），且未给 repeat_cost_s")
        elif cost < REPEAT_COST_LIMIT_S:
            bad("R6", f"{tag} repeat_cost_s={cost:g}s < 门槛 {REPEAT_COST_LIMIT_S:g}s，"
                      "这个成本足以重跑，不许豁免")
        elif not reason:
            bad("R6", f"{tag} 豁免同输入重跑但没写 repeat_skipped_reason")
        else:
            # status 在 verdict.status 里（顶层没有 status 字段），旧写法读到 None 会漏判
            cur = str((c.get("verdict") or {}).get("status") or c.get("status") or "")
            if cur == "reproduced":
                bad("R6", f"{tag} 豁免了同输入重跑却仍判 status=reproduced",
                    "没有重复性证据只能判 inconclusive / solver_mismatch")
            else:
                ok("R6", f"{tag} 未重跑（repeat_cost_s={cost:g}s，理由已写），"
                         f"status={cur}")
    elif delta > tol:
        bad("R6", f"{tag} 同输入回归 delta={delta} 超过容差 {tol}，先查脚本")
    elif not close(delta, abs(b - r), 1e-6):
        bad("R6", f"{tag} delta={delta} 与 |{b}-{r}|={abs(b-r):g} 不自洽")
    else:
        ok("R6", f"{tag} 同输入回归通过（delta={delta:g} <= {tol:g}）")

    # [R7] 排除清单
    excluded = c.get("excluded") or []
    if not excluded:
        bad("R7", f"{tag} excluded[] 为空，差异诊断没有排除法证据")
    for i, e in enumerate(excluded):
        ev = str(e.get("evidence") or "").strip()
        if not e.get("suspect") or not e.get("verdict") or not ev or ev in {"已确认", "confirmed"}:
            bad("R7", f"{tag} excluded[{i}] 缺 suspect/verdict/可复跑证据")
        else:
            ok("R7", f"{tag} 排除项 {e.get('suspect')} 有证据")

    # [R8] 结论与停下理由
    gap = num(verdict.get("gap"))
    stop = str(verdict.get("stop_reason") or "").strip()
    explain = verdict.get("explainable_by")
    if status not in STATUSES:
        bad("R8", f"{tag} 非法 verdict.status={status}")
    elif not stop or gap is None:
        bad("R8", f"{tag} verdict 缺 stop_reason 或 gap 数值")
    elif status == "solver_mismatch" and explain and re.search(
            r"tune|fit|调参|凑", str(explain), re.I):
        bad("R8", f"{tag} solver_mismatch 却把差异归因于可调参数：{explain}")
    else:
        ok("R8", f"{tag} verdict={status}，gap={gap:g}，停下的理由已记录")

    # [R14] 判据来源与定义：source 要能定位（Fig./Eq./Table/p./§），definition 不能空
    definition = str(t.get("definition") or "").strip()
    src = str(t.get("source") or "")
    if not definition:
        bad("R14", f"{tag} target 缺 definition（判据用哪个公式/哪个面/哪种平均）",
            "补一行，例如 'arg<Ex>-arg<Ey>，监视器面空间平均'")
    elif not re.search(r"(Fig|Eq\.?|Table|p\.\s*\d|§)", src, re.I):
        bad("R14", f"{tag} target.source={src!r} 无出处定位",
            "写成 'Fig.2c p.5 / Eq.(3)' 这种可回查的形式")
    else:
        ok("R14", f"{tag} 判据来源与定义齐全")

    # [R16] rerun_commands 里引用的仓库内文件必须真实存在（_scratch 产物允许尚未生成）
    for cmd in c.get("rerun_commands") or []:
        for tok in re.findall(r"[A-Za-z0-9_./\\-]+\.(?:py|fsp|lsf|json|md)", str(cmd)):
            norm = tok.replace("\\", "/")
            if norm.startswith("_scratch") or norm.startswith("/"):
                continue
            if not (norm.startswith("skills/") or norm.startswith("cases/")
                    or norm.startswith("tools/") or norm.startswith("docs/")):
                continue
            if not resolve(tok, pkg_root).exists():
                bad("R16", f"{tag} rerun_commands 引用不存在的文件：{tok}")

    # [R9] 输出隔离
    for run in runs:
        out = str(run.get("out") or "")
        if not out:
            bad("R9", f"{tag} run:{run.get('name')} 缺 out")
        elif out.startswith("cases/") or "\\cases\\" in out or "/cases/" in out:
            bad("R9", f"{tag} run:{run.get('name')} 输出写进只读 cases/：{out}",
                "改用 _scratch/regress/<date>/...")
        else:
            ok("R9", f"{tag} run:{run.get('name')} 输出隔离 OK（{out}）")

    # [R10] 缺陷三段
    for d in c.get("defects") or []:
        hits = sorted((ROOT / "defects").glob(f"{d}-*.md"))
        if not hits:
            bad("R10", f"{tag} 找不到 {d} 对应的 defect 文件")
            continue
        body = read(hits[0])
        groups = [
            ("根因", r"^##\s*.*(根因|Root\s+Cause)", re.M | re.I),
            ("修复", r"^##\s*.*(修复|Fix|Resolution)", re.M | re.I),
            ("验证", r"^##\s*.*(验证|Verification|Validation)", re.M | re.I),
        ]
        lack = [name for name, pat, flags in groups if not re.search(pat, body, flags)]
        if lack:
            bad("R10", f"{tag} {hits[0].name} 缺三段：{', '.join(lack)}")
        else:
            ok("R10", f"{tag} {hits[0].name} 三段齐全")

    # [R11] 训练条目
    items = c.get("training_items") or []
    if not items:
        bad("R11", f"{tag} training_items 为空，本次复现没有产出可训练语料")
    for i, it in enumerate(items):
        dest = str(it.get("destination") or "")
        if not it.get("id") or not it.get("observation") or not it.get("evidence"):
            bad("R11", f"{tag} training_items[{i}] 缺 id/observation/evidence")
        elif dest not in DESTINATIONS:
            bad("R11", f"{tag} training_items[{i}] 非法 destination={dest}")
        elif it.get("landed"):
            tp = it.get("target_path")
            if not tp or not resolve(str(tp), pkg_root).exists():
                bad("R11", f"{tag} {it.get('id')} 标 landed=true 但 target_path 不存在：{tp}")
            else:
                ok("R11", f"{tag} {it.get('id')} 已落地 {dest}")
        else:
            ok("R11", f"{tag} {it.get('id')} 归属 {dest}（待落地）")

    # [R12] 可重跑命令与相对路径
    cmds = c.get("rerun_commands") or []
    if not cmds:
        bad("R12", f"{tag} rerun_commands 为空")
    for cmd in cmds:
        if "--out" not in str(cmd):
            warn("R12", f"{tag} 命令未显式 --out：{str(cmd)[:70]}")
    if ABS_PATH_RE.search(strip_interpreters(text)):
        bad("R12", f"{tag} 卡片里出现绝对路径（数据/工程路径），换机器即死",
            "改为仓库相对路径；解释器路径允许（见 reproduction-contract §6）")
    else:
        ok("R12", f"{tag} {len(cmds)} 条可重跑命令，全卡无绝对路径")


TEMPLATE = """# <CASE> 复现卡（<DATE>）

> 本卡是结构化索引，长表格与推导放同目录 notes 里，不在此复制。
> 生成骨架：python tools/check_reproduction.py --emit-template
> 占位符 <CASE> / <DATE> / <...> 必须全部替换，否则门禁判 FAIL。

```repro-card
{
  "case": "<CASE>",
  "mode": "reproduce",
  "date": "<DATE>",
  "target": {
    "quantity": "<peak_absorption | peak_transmittance | dphi | PCR | ...>",
    "value": 0.0,
    "wavelength_um": 0.0,
    "source": "<figure / text / experiment>",
    "solver": "<paper solver>",
    "unmeasured_reason": null
  },
  "actual_solver": "Lumerical FDTD v251",
  "locked": ["materials", "layer_stack", "topology", "geometry"],
  "numerics_aligned_from": null,
  "truth_sources": [
    {
      "path": "model/<ref>.fsp",
      "role": "reference",
      "converged": false,
      "shutoff": 0.0,
      "threshold": 1e-05,
      "p0_log": "model/<ref>_p0.log"
    }
  ],
  "runs": [
    {
      "name": "baseline",
      "out": "_scratch/regress/<date>/<case>/baseline",
      "p0_log": "_scratch/regress/<date>/<case>/baseline/point_00_base_p0.log",
      "shutoff_final": 0.0,
      "threshold": 0.0001,
      "metrics": {"<quantity>": 0.0}
    },
    {
      "name": "repeat_or_reference_calibrated",
      "out": "_scratch/regress/<date>/<case>/repeat",
      "p0_log": "_scratch/regress/<date>/<case>/repeat/point_00_base_p0.log",
      "shutoff_final": 0.0,
      "threshold": 1e-05,
      "metrics": {"<quantity>": 0.0}
    }
  ],
  "same_input_regression": {
    "baseline": 0.0,
    "repeat": 0.0,
    "delta": 0.0,
    "tolerance": 0.005
  },
  "excluded": [
    {
      "suspect": "<suspect>",
      "verdict": "excluded",
      "evidence": "<command + output, or notes path>",
      "rerun": "<command>"
    }
  ],
  "verdict": {
    "status": "inconclusive",
    "gap": 0.0,
    "explainable_by": null,
    "stop_reason": "<why stopped here>"
  },
  "defects": ["D-003"],
  "training_items": [
    {
      "id": "R-001",
      "observation": "<what breaks or how to judge correctly>",
      "evidence": "<command + output, or defects/D-xxx path>",
      "destination": "references",
      "landed": false,
      "target_path": null
    }
  ],
  "rerun_commands": [
    "python skills/<name>/scripts/<script>.py --config <json> --out _scratch/regress/<date>/<case>/x"
  ]
}
```

> [R13] `target.quantity` 必须真实出现在 `runs[].metrics` 或 `runs[].out` 下的 CSV 表头里。
> 若确实没测到：在 `target.unmeasured_reason` 写明原因，且 `verdict.status` 只能是
> `inconclusive` / `unresolved`；否则门禁 FAIL（P03 的 PCR 就是这么漏过去的）。
> `same_input_regression` 用泛型 `baseline` / `repeat`（旧卡的 `baseline_A` / `repeat_A` 仍兼容）。
"""


BAD_CARD = {
    "case": "NEGATIVE-CONTROL",
    "mode": "reproduce",
    "date": "2026-11-07",
    "target": {"quantity": "PCR", "value": 0.95, "wavelength_um": 1.2,
               "source": "Fig.1c", "solver": "FEM"},
    "actual_solver": "Lumerical FDTD v251",
    "locked": ["materials"],
    "truth_sources": [],
    "runs": [{"name": "only_one", "out": "cases/P01/results",
              "shutoff_final": 0.5, "threshold": 1e-05,
              "metrics": {"A": 0.9}}],
    "same_input_regression": {"baseline": 0.9, "repeat": 0.1,
                              "delta": 0.8, "tolerance": 0.005},
    "excluded": [],
    "verdict": {"status": "fitted", "gap": 0.07,
                "explainable_by": None, "stop_reason": ""},
    "defects": ["D-999"],
    "training_items": [],
    "rerun_commands": [],
}


def self_test() -> int:
    """负对照：喂一张故意违规的卡，确认门禁真的会 FAIL 而不是永远 ALL GREEN。

    额外两个定向负对照：
      (a) diverging 日志必须被判 FAIL，不能被 Early termination 蒙过去；
      (b) target.quantity 未出现在产物里必须被 [R13] 拦下。
    """
    import os
    import tempfile

    global QUIET, ok_count
    QUIET = True
    fails.clear()
    warns.clear()
    ok_count = 0
    fd, name = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text("```repro-card\n" + json.dumps(BAD_CARD, ensure_ascii=False)
                       + "\n```\n", encoding="utf-8")
        check_card(tmp)
        base_caught = {f.split("]")[0].lstrip("[") for f in fails}
        base_rules = {"R2", "R3", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "R13",
                      "R14"}
        missed = sorted(base_rules - base_caught)
        for r in missed:
            print(f"negative control missed rule {r}", file=sys.stderr)

        # (a) diverging：单独造一份日志，验证 parse_log + check_convergence 都判 FAIL
        fails.clear()
        ok_count = 0
        div = tmp.with_name(tmp.stem + "_div.log")
        div.write_text(
            "60% complete. Auto Shutoff: 3182.28\n"
            "ERROR: Early termination of simulation, the electromagnetic fields are diverging.\n"
            "Completed 5000 iterations\n", encoding="utf-8")
        info = parse_log(div, 1e-5)
        div_ok = (info["diverged"] is True and info["early"] is False
                  and info["completed"] is True and info["converged"] is False)
        if not div_ok:
            print("negative control: parse_log failed to flag divergence", file=sys.stderr)
        check_convergence("R5", "diverging-control",
                          {"shutoff_final": 52139.6, "threshold": 1e-5,
                           "converged": True, "p0_log": div.as_posix()}, tmp.parent)
        divergence_failed = any("diverging" in f for f in fails)
        if not divergence_failed:
            print("negative control: check_convergence did not FAIL on divergence",
                  file=sys.stderr)
        div.unlink(missing_ok=True)

        # (b) 未测量豁免：有 unmeasured_reason + inconclusive 时应 WARN 而非 FAIL
        fails.clear()
        ok_count = 0
        honest = dict(BAD_CARD)
        honest["target"] = dict(BAD_CARD["target"])
        honest["target"]["unmeasured_reason"] = "stage 4 能力缺失，PCR 从未被测量"
        honest["verdict"] = {"status": "inconclusive", "gap": 0.95,
                             "explainable_by": None,
                             "stop_reason": "指标未测，人做裁决"}
        tmp.write_text("```repro-card\n" + json.dumps(honest, ensure_ascii=False)
                       + "\n```\n", encoding="utf-8")
        check_metric_presence(honest, tmp.parent, "honest-control")
        honest_r13_failed = any("R13" in f for f in fails)
        if honest_r13_failed:
            print("negative control: honest unmeasured_reason should WARN, not FAIL",
                  file=sys.stderr)
    finally:
        tmp.unlink(missing_ok=True)

    print(f"self-test: {len(base_caught)} rules caught in base card "
          f"({len(base_caught & base_rules)}/{len(base_rules)} expected)")
    print(f"self-test: diverging={'CAUGHT' if div_ok and divergence_failed else 'MISSED'}, "
          f"unmeasured-honesty={'OK' if not honest_r13_failed else 'BROKEN'}")
    good = (not missed and div_ok and divergence_failed and not honest_r13_failed)
    if not good:
        print("SELF-TEST FAILED", file=sys.stderr)
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    global QUIET
    ap = argparse.ArgumentParser(description="复现约束体检（reproduction-contract.md R1-R13）")
    ap.add_argument("--case", help="只查指定包，如 P01；按目录名或卡内 case 字段匹配")
    ap.add_argument("--card", help="只检查指定卡片文件（草稿自检 / 负对照）")
    ap.add_argument("--json", action="store_true", help="只输出机器可读 JSON")
    ap.add_argument("--emit-template", action="store_true", help="打印复现卡骨架后退出")
    ap.add_argument("--self-test", action="store_true", help="负对照：验证门禁能拦下违规卡")
    args = ap.parse_args()
    if args.emit_template:
        print(TEMPLATE)
        return 0
    if args.self_test:
        return self_test()
    QUIET = args.json

    cards: list[Path] = []
    if args.card:
        p = Path(args.card)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"Card not found: {p}", file=sys.stderr)
            return 2
        cards = [p]
    else:
        # 默认全量门禁只认正式卡；--case 定位草稿时也纳入 _scratch/ 的草稿卡。
        patterns = CARD_PATTERNS if args.case else FORMAL_PATTERNS
        seen: set[Path] = set()
        for pat in patterns:
            for c in sorted(ROOT.glob(pat)):
                if c not in seen:
                    seen.add(c)
                    cards.append(c)
        if args.case:
            key = args.case.lower()
            case_re = re.compile(r'"case"\s*:\s*"%s"' % re.escape(key), re.I)
            cards = [c for c in cards
                     if c.parent.parent.name.lower().startswith(key)
                     or key in c.as_posix().lower() or case_re.search(read(c))]
            if not cards:
                print(f"No repro-card found for case={args.case}", file=sys.stderr)
                return 2
        if not cards:
            warn("R1", "仓库里还没有任何 repro-card，本契约尚未被使用")

    for card in cards:
        if DRAFT_RE.search(card.name) and not QUIET:
            print(f"\n[draft] {card.relative_to(ROOT).as_posix()} "
                  f"— 草稿卡只自检，不算正式门禁通过")
        check_card(card)

    result = {
        "cards": len(cards), "ok": ok_count,
        "warn": len(warns), "fail": len(fails),
        "fails": fails, "warns": warns,
        "verdict": "ALL GREEN" if not fails else "FAILED",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'-' * 60}")
        print(f"{len(cards)} card(s) · OK {ok_count} · WARN {len(warns)} · FAIL {len(fails)}"
              f" · {result['verdict']}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
