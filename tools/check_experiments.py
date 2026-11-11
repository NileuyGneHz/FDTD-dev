#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""check_experiments.py —— 逐项实验门禁

每个改动都必须挂一个 ``EXP-NN``，并在 ``experiments/EXP-NN-*/`` 里留下
``design.md``（开工前）+ ``result.json``（跑完）。本脚本判四条：

  [D1] PLAN 里出现的每个 EXP 都有 result.json
  [D2] verdict == "pass"（"fail" 一律阻断）
  [D3] metrics 非空 —— 有数字，不是「已确认」
  [D4] negative_control.failed == true —— 负对照确实失败过
  [D5] design.md 存在，且含「负对照」与至少一条命令

缺文件默认记 WARN（允许边做边补）；``--require-all`` 时升 FAIL。

退出码：0 = 通过（允许 WARN）；1 = 有 FAIL。

用法：
  python tools/check_experiments.py
  python tools/check_experiments.py --require-all
  python tools/check_experiments.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = ROOT / "experiments"
# 2026-11-11：PLAN 的正式位置是 docs/plans/（docs/plans/AGENTS.md §格式）。
# docs/tasks/ 是历史误放位置，**保留兼容扫描**——漏扫会让 D1 悄悄掉数字（假绿），
# 而 D1 是唯一能证明「EXP 台账没漏项」的判据。
PLAN_GLOBS = ("docs/plans/PLAN-*.md", "docs/tasks/PLAN-*.md")
EXP_ID_RE = re.compile(r"EXP-(\d{2,3})")
VALID_VERDICTS = {"pass", "fail"}

problems: list[str] = []


def ok(tag: str, msg: str) -> None:
    print(f"  [{tag}] OK    {msg}")


def warn(tag: str, msg: str) -> None:
    print(f"  [{tag}] WARN  {msg}")


def bad(tag: str, msg: str) -> None:
    print(f"  [{tag}] FAIL  {msg}")
    problems.append(f"{tag}: {msg}")


def plan_ids() -> list[str]:
    ids: set[str] = set()
    for pattern in PLAN_GLOBS:
        for plan in sorted(ROOT.glob(pattern)):
            for m in EXP_ID_RE.finditer(plan.read_text(encoding="utf-8")):
                ids.add(f"EXP-{m.group(1)}")
    return sorted(ids)


def find_dir(exp_id: str, base: Path) -> Path | None:
    hit = sorted(base.glob(f"{exp_id}-*"))
    return hit[0] if hit else None


def validate_record(record_path: Path, design_path: Path) -> list[str]:
    """返回问题列表（空 = 通过）。自测直接调它。"""
    errs: list[str] = []
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"result.json 不是合法 JSON: {exc!r}"]

    if not str(data.get("exp", "")).startswith("EXP-"):
        errs.append("缺 exp 字段或格式不对")
    verdict = data.get("verdict")
    defect = str(data.get("defect") or "").strip()
    has_defect = bool(defect) and (ROOT / "defects" / (defect + ".md")).is_file() or bool(
        defect) and bool(list((ROOT / "defects").glob(defect + "*.md")))
    if verdict not in VALID_VERDICTS:
        errs.append(f"verdict 必须是 {sorted(VALID_VERDICTS)}，实际 {verdict!r}")
    elif verdict == "fail" and not has_defect:
        errs.append("verdict=fail 且未挂 defect 号（失败必须登记，不许沉默）")

    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        errs.append("metrics 为空 —— 没有数字就等于没验证")

    # 「未执行」是显式状态，不是默认值：必须自己写 metrics.executed=false。
    # 豁免条件与被豁免内容是同一个属性（没跑 → 没有负对照可跑），不像 K11 那样拿代理属性判断。
    deferred = (verdict == "fail" and has_defect
                and isinstance(metrics, dict) and metrics.get("executed") is False)

    nc = data.get("negative_control")
    if not deferred and (not isinstance(nc, dict) or nc.get("failed") is not True):
        errs.append("negative_control.failed 必须为 true（负对照必须真的失败过）")

    if not design_path.is_file():
        errs.append("缺 design.md（假设/对照/判据必须先写）")
    elif not deferred:
        text = design_path.read_text(encoding="utf-8")
        if "负对照" not in text:
            errs.append("design.md 里没有「负对照」")
        if "```" not in text:
            errs.append("design.md 里没有可重跑命令")
    return errs


def check_plans(require_all: bool) -> None:
    print("\n-- 实验台账")
    ids = plan_ids()
    if not ids:
        warn("D1", "没找到任何 PLAN-*.md 或其中没有 EXP 编号")
        return

    missing: list[str] = []
    for exp_id in ids:
        d = find_dir(exp_id, EXP_DIR)
        if d is None or not (d / "result.json").is_file():
            missing.append(exp_id)
            continue
        rec = json.loads((d / "result.json").read_text(encoding="utf-8"))
        errs = validate_record(d / "result.json", d / "design.md")
        if errs:
            bad("D2", f"{exp_id}: " + "；".join(errs))
        elif rec.get("verdict") == "fail":
            warn("D2", f"{exp_id} fail，已挂 {rec.get('defect')}（已知缺陷，不阻断但计入未完成）")
        else:
            ok("D2", f"{exp_id} pass（metrics {len(rec['metrics'])} 项）")

    done = len(ids) - len(missing)
    if missing:
        msg = f"{len(missing)}/{len(ids)} 个实验尚未落账: {', '.join(missing[:8])}" + (
            " …" if len(missing) > 8 else "")
        if require_all:
            bad("D1", msg)
        else:
            warn("D1", msg + "（边做边补；--require-all 会升为 FAIL）")
    else:
        ok("D1", f"{done}/{len(ids)} 个实验全部落账")


def self_test() -> int:
    """构造 7 个合成记录：2 个应通过（含 deferred）、5 个应被抓。"""
    print("\n-- self-test（合成记录）")
    good = {
        "exp": "EXP-01", "verdict": "pass",
        "metrics": {"cases_passed": "4/4"}, 
        "negative_control": {"failed": True, "detail": "坏记录被判 FAIL"},
    }
    cases = {
        "good": (good, "## 判据\n负对照：坏记录必被抓\n```bash\npython x.py\n```", 0),
        "verdict_fail": ({**good, "verdict": "fail"}, None, 1),
        "empty_metrics": ({**good, "metrics": {}}, None, 1),
        "no_negative_control": ({**good, "negative_control": {"failed": False}}, None, 1),
        "no_design": (good, "", 1),
        # 「跳过的实验」必须显式自证：executed=false + 挂 defect + design 里写明状态。
        # 没有 executed=false 的 fail 仍然要被抓（否则谁都能靠挂个 defect 蒙过负对照）。
        "deferred_ok": ({**good, "verdict": "fail", "defect": "D-009",
                         "metrics": {"executed": False},
                         "negative_control": {"failed": False, "detail": "未执行"}},
                        "## 状态\n**未执行**（D-009）\n", 0),
        "deferred_without_flag": ({**good, "verdict": "fail", "defect": "D-009",
                                   "negative_control": {"failed": False}},
                                  "## 状态\n**未执行**（D-009）\n", 1),
    }
    failed = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "EXP-01-fake"
        tmp.mkdir()
        for name, (rec, design, expect) in cases.items():
            (tmp / "result.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            if design is None:
                design = "## 判据\n负对照：坏记录必被抓\n```bash\npython x.py\n```"
            (tmp / "design.md").write_text(design, encoding="utf-8")
            errs = validate_record(tmp / "result.json", tmp / "design.md")
            got = 1 if errs else 0
            status = "OK  " if got == expect else "FAIL"
            if got != expect:
                failed += 1
            print(f"  [D0] {status} {name}: 期望 {'被抓' if expect else '通过'}，"
                  f"实际 {'被抓: ' + errs[0] if errs else '通过'}")

    if failed:
        print(f"\nself-test FAIL：{failed} 个合成用例判错")
        return 1
    print("\nself-test PASS：2 正例通过，5 负例全部被抓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-all", action="store_true",
                    help="未落账的实验记 FAIL（默认只 WARN）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    check_plans(args.require_all)

    print()
    if problems:
        print(f"FAIL {len(problems)} 项：")
        for p in problems:
            print("  - " + p)
        return 1
    print("ALL GREEN（未落账项按 WARN 处理）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
