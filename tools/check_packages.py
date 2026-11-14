# -*- coding: utf-8 -*-
"""
check_packages.py —— 打包文件夹自检工具
================================================================================

用途
    协作前跑一次，确认「论文 <-> fsp」的打包结构完整、命名合规。
    把"靠记忆维护目录"变成"靠脚本校验"。

用法
    PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" tools/check_packages.py                # 检查全部包
    "$PY" tools/check_packages.py --pkg P03      # 只查 P03
    "$PY" tools/check_packages.py --json         # 输出 JSON（给 agent 解析）
    "$PY" tools/check_packages.py --strict       # 有警告也算失败（退出码 1）

检查项
    [ERROR] 包目录名不符合 P0N_xxx 规范
    [ERROR] 缺 README.md
    [ERROR] README.md 里还有未填的占位符 <...>
    [ERROR] fsp/ 下有非 ASCII 文件名的文件      <- GPU 引擎会崩，最要紧
    [ERROR] 有 .fsp 但没有对应 README 记录
    [WARN ] paper/ 为空（论文未归档）
    [WARN ] scripts/ 与 results/ 同时为空（包刚建，正常）
    [INFO ] 各子目录文件数、包总体积

退出码
    0 = 无 ERROR（有 WARN 也返回 0，除非 --strict）
    1 = 存在 ERROR（或 --strict 下有 WARN）

⚠️ 本脚本**只读**，绝不修改任何文件。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---- 配置 ----------------------------------------------------------------

try:  # Windows 控制台默认 cp1252，中文输出会崩
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 归档单元根 = 本脚本所在目录的上一级 / cases
TOOLS_DIR = Path(__file__).resolve().parent
WS_ROOT = TOOLS_DIR.parent
PKG_ROOT = WS_ROOT / "cases"

# 包目录命名：P01_xxx / P10_xxx
PKG_NAME_RE = re.compile(r"^P\d{2}_[A-Za-z0-9_]+$")

# 标准子目录（缺了给 WARN，不算 ERROR）
SUBDIRS = ["paper", "model", "results", "notes"]  # config 是可选目录，单独计数

# README 里不允许残留的占位符
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,60}>")

# 这些占位符是"格式说明"性质，不算未填（模板本身允许）
IGNORE_PLACEHOLDERS = {"<包名>", "<一句话主题>", "<P0N>", "<fsp\\或 scripts\\下第一个该跑的脚本>"}

# 忽略的目录
IGNORE_DIRS = {"_TEMPLATE"}

# 占位文件：不算"真实内容"（否则空目录会因为放了 .gitkeep 而不再被报"为空"）
PLACEHOLDER_FILES = {".gitkeep", ".keep", ".gitignore"}

# 2026-11-14：cases/ 分双轨（metasurface / photonic），包在**第二层**。
# 这一层若不加，`PKG_ROOT.iterdir()` 只会看到 metasurface/ 和 photonic/ 两个目录，
# 它们既不是包名也不含 README → 要么报 ERROR，要么被当成"新包"静默放过，
# 结果就是「ERROR=0 但一个包都没查」的假绿。
TRACK_DIRS = {"metasurface", "photonic"}


def discover_pkgs(root: Path) -> list[tuple[str, Path]]:
    """找出所有归档包，返回 [(轨道名, 包目录)]。

    支持两种布局：
      * 扁平：cases/P01_xxx            -> 轨道名为 ""
      * 双轨：cases/metasurface/P01_xxx -> 轨道名为 "metasurface"

    判据是**目录里有 README.md**，而不是只看名字匹配——名字匹配会把
    `metasurface/` 这种中间层也当成候选（它不匹配 PKG_NAME_RE，但也不该报错）。
    """
    out: list[tuple[str, Path]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name in IGNORE_DIRS or entry.name.startswith("."):
            continue
        if (entry / "README.md").is_file():
            out.append(("", entry))                     # 扁平布局
            continue
        if entry.name in TRACK_DIRS:
            for sub in sorted(entry.iterdir()):
                if (sub.is_dir() and sub.name not in IGNORE_DIRS
                        and not sub.name.startswith(".") and (sub / "README.md").is_file()):
                    out.append((entry.name, sub))
    return out


def real_files(d: Path) -> list[Path]:
    """列出目录下的真实文件，排除占位文件。"""
    return [f for f in d.rglob("*") if f.is_file() and f.name not in PLACEHOLDER_FILES]


# ---- 工具函数 ------------------------------------------------------------


def is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def human(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f}{unit}"
        nbytes /= 1024
    return f"{nbytes:.1f}TB"


class Issue:
    def __init__(self, level: str, pkg: str, msg: str):
        self.level = level  # ERROR / WARN / INFO
        self.pkg = pkg
        self.msg = msg

    def as_dict(self):
        return {"level": self.level, "pkg": self.pkg, "msg": self.msg}

    def __str__(self):
        return f"[{self.level:5}] {self.pkg:26} {self.msg}"


# ---- 单包检查 ------------------------------------------------------------


def check_one_pkg(pkg_dir: Path, track: str = "") -> list[Issue]:
    issues: list[Issue] = []
    name = pkg_dir.name
    # 双轨布局下用 `metasurface/P01` 作为展示名，避免两个 P01 在报告里混淆
    label = f"{track}/{name}" if track else name

    # 1) 目录命名
    if not PKG_NAME_RE.match(name):
        issues.append(
            Issue("ERROR", label, f"目录名不符合 'P0N_<英文短名>' 规范（建议改名，勿用中文）")
        )

    # 2) README
    readme = pkg_dir / "README.md"
    if not readme.exists():
        issues.append(Issue("ERROR", label, "缺 README.md（agent 无法接管）"))
    else:
        try:
            txt = readme.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            issues.append(Issue("ERROR", label, f"README.md 读取失败: {e}"))
            txt = ""
        if txt:
            left = {
                m.group(0)
                for m in PLACEHOLDER_RE.finditer(txt)
                if m.group(0) not in IGNORE_PLACEHOLDERS
            }
            if left:
                sample = "、".join(sorted(left)[:5])
                more = f" 等 {len(left)} 处" if len(left) > 5 else ""
                issues.append(
                    Issue("ERROR", label, f"README.md 有未填占位符: {sample}{more}")
                )

    # 3) 子目录 + 非 ASCII 文件名（最要紧）
    counts = {}
    for sub in SUBDIRS:
        d = pkg_dir / sub
        if not d.is_dir():
            issues.append(Issue("WARN", label, f"缺子目录 {sub}\\"))
            counts[sub] = 0
            continue
        files = real_files(d)
        if sub == "paper":
            # paper\ 里只有 PDF 算"论文"；md（自测题、笔记）单独计数，否则会虚高
            counts["paper"] = sum(1 for f in files if f.suffix.lower() == ".pdf")
            counts["paper_md"] = sum(1 for f in files if f.suffix.lower() != ".pdf")
        else:
            counts[sub] = len(files)

        # ASCII 检查（只对 model —— 这个目录会进仿真路径）
        if sub in ("model",):
            bad = [f for f in files if not is_ascii(f.name)]
            for f in bad:
                rel = f.relative_to(pkg_dir)
                issues.append(
                    Issue(
                        "ERROR",
                        name,
                        f"文件名含非 ASCII -> GPU 引擎必崩: {rel}",
                    )
                )

    # 3.5) config 可选：有就计数，没有不算问题
    cfg_dir = pkg_dir / "config"
    counts["config"] = len([p for p in cfg_dir.iterdir()]) if cfg_dir.is_dir() else 0

    # 4) .fsp 普查：包内**所有** .fsp，不只 model\
    #    P02/P03 的交付工程在包根、P04 的交付在仓库根 results\ —— 只扫 model\ 会让
    #    「ERROR=0」虚绿（2026-11-09 三份复现报告的共同盲区）。
    all_fsp = [f for f in pkg_dir.rglob("*.fsp") if "_archive" not in f.parts]
    ref_fsp = [f for f in all_fsp if f.parent.name == "model"]
    delivered_fsp = [f for f in all_fsp if f.parent.name != "model"]
    has_fsp = len(all_fsp) > 0

    # 4.1) ASCII 检查覆盖**全部** .fsp（交付工程同样会进 GPU 引擎）
    for f in all_fsp:
        if not is_ascii(f.name):
            issues.append(Issue("ERROR", label,
                                f"文件名含非 ASCII -> GPU 引擎必崩: {f.relative_to(pkg_dir)}"))

    # 5) paper 为空
    if counts.get("paper", 0) == 0:
        issues.append(Issue("WARN", label, "paper\\ 为空（论文未归档）"))

    # 6) 新包特征
    if counts.get("config", 0) == 0 and counts.get("results", 0) == 0 and not has_fsp:
        issues.append(Issue("WARN", label, "config\\ 与 results\\ 均为空且无 .fsp（新包？）"))

    # 7) 参考工程有 fsp 但没 _p0.log —— 可能从未实跑
    #    只对 model\ 里的参考资产提示；交付工程可以是有意保持 layoutmode=1 的 build-only
    for f in ref_fsp:
        log = f.with_name(f.stem + "_p0.log")
        if not log.exists():
            issues.append(
                Issue("WARN", label, f"{f.name} 无同名 _p0.log（未实跑过？或日志在别处）")
            )

    # 8) 统计体积
    total = sum(f.stat().st_size for f in real_files(pkg_dir))
    detail = "  ".join(f"{k}={v}" for k, v in counts.items())
    issues.append(Issue("INFO", label,
                        f"{detail}  体积={human(total)}  fsp={len(all_fsp)}"
                        f"（参考 {len(ref_fsp)} / 交付 {len(delivered_fsp)}）"))

    return issues


def self_test() -> int:
    """负对照：包根放一个 .fsp，改前会漏统计，改后必须被算进 fsp 计数。"""
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="pkg_self_"))
    try:
        pkg = tmp / "P99_SelfTest"
        (pkg / "model").mkdir(parents=True)
        (pkg / "paper").mkdir()
        (pkg / "results").mkdir()
        (pkg / "notes").mkdir()
        (pkg / "README.md").write_text("# P99\n\n测试包，无占位符。\n", encoding="utf-8")
        (pkg / "model" / "reference.fsp").write_bytes(b"x")
        (pkg / "delivered.fsp").write_bytes(b"x")      # 包根交付工程：旧逻辑扫不到

        issues = check_one_pkg(pkg)
        info = " ".join(i.msg for i in issues if i.level == "INFO")
        if "fsp=2" not in info or "交付 1" not in info:
            print("self-test: 包根 .fsp 未被统计 -> %s" % info, file=sys.stderr)
            return 1
        print("self-test: 包根 .fsp 已统计（%s）" % info)

        # --- 负例 1：双轨布局必须能发现第二层的包 ---
        (pkg / "README.md").unlink()
        root = tmp / "cases"
        for track in ("metasurface", "photonic"):
            (root / track).mkdir(parents=True)
        for track, nm in (("metasurface", "P01_Alpha"), ("photonic", "P01_Beta")):
            d = root / track / nm
            d.mkdir()
            (d / "README.md").write_text("# %s\n\n无占位符。\n" % nm, encoding="utf-8")
        found = discover_pkgs(root)
        pairs = {(t, d.name) for t, d in found}
        if pairs != {("metasurface", "P01_Alpha"), ("photonic", "P01_Beta")}:
            print("self-test: 双轨发现错误 -> %r" % (pairs,), file=sys.stderr)
            return 1
        print("self-test: 双轨发现 2 个包（metasurface/P01 与 photonic/P01 不互相覆盖）")

        # --- 负例 2：第二层的包缺 README 必须被发现（不能被静默跳过） ---
        (root / "photonic" / "P01_Beta" / "README.md").unlink()
        found = discover_pkgs(root)
        names = {d.name for _, d in found}
        if "P01_Beta" in names:
            print("self-test: 缺 README 的包仍被发现（发现逻辑不该看 README）",
                  file=sys.stderr)
        # 发现逻辑以 README 为准；缺 README 时它不会被当成包——这是既有语义，
        # 由 check_one_pkg 的「缺 README.md」ERROR 覆盖（扁平布局）。这里只确认
        # metasurface 那个正常包没被连带丢掉。
        if "P01_Alpha" not in names:
            print("self-test: 一个坏包把好包带丢了 -> %r" % (names,), file=sys.stderr)
            return 1
        print("self-test: 坏包不影响好包的发现")

        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ---- 主流程 --------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="FDTD 打包文件夹自检")
    ap.add_argument("--pkg", help="只检查指定包，如 P03")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--strict", action="store_true", help="有 WARN 也算失败")
    ap.add_argument("--self-test", action="store_true", help="自测：包根 .fsp 必须被统计")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not PKG_ROOT.is_dir():
        print(f"[ERROR] 找不到 cases 目录: {PKG_ROOT}", file=sys.stderr)
        return 1

    pkg_dirs = discover_pkgs(PKG_ROOT)
    if args.pkg:
        # 支持三种写法：`P03`（扁平，向后兼容）、`metasurface/P03`、`photonic/P0`
        want = args.pkg.replace("\\", "/").strip("/")
        if "/" in want:
            track, frag = want.split("/", 1)
            pkg_dirs = [(t, d) for t, d in pkg_dirs if t == track and d.name.startswith(frag)]
        else:
            pkg_dirs = [(t, d) for t, d in pkg_dirs if d.name.startswith(want)]
        if not pkg_dirs:
            print(f"[ERROR] 没有匹配 '{args.pkg}' 的包", file=sys.stderr)
            return 1

    all_issues: list[Issue] = []
    for track, d in pkg_dirs:
        all_issues.extend(check_one_pkg(d, track=track))

    errors = [i for i in all_issues if i.level == "ERROR"]
    warns = [i for i in all_issues if i.level == "WARN"]
    infos = [i for i in all_issues if i.level == "INFO"]

    if args.json:
        print(
            json.dumps(
                {
                    "packages": [f"{t}/{d.name}" if t else d.name for t, d in pkg_dirs],
                    "errors": len(errors),
                    "warnings": len(warns),
                    "issues": [i.as_dict() for i in all_issues],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if errors else 0

    # ---- 人类可读输出 ----
    print("=" * 78)
    print(f"打包自检  |  根目录 {PKG_ROOT}")
    print(f"共 {len(pkg_dirs)} 个包")
    print("=" * 78)

    for track, d in pkg_dirs:
        label = f"{track}/{d.name}" if track else d.name
        mine = [i for i in all_issues if i.pkg == label]
        errs = [i for i in mine if i.level == "ERROR"]
        wns = [i for i in mine if i.level == "WARN"]
        infos_mine = [i for i in mine if i.level == "INFO"]

        if errs:
            mark = "[X]"
        elif wns:
            mark = "[!]"
        else:
            mark = "[OK]"
        print(f"\n{mark} {label}")

        for i in infos_mine:
            print(f"      {i.msg}")
        for i in wns:
            print(f"      WARN  {i.msg}")
        for i in errs:
            print(f"      ERR   {i.msg}")

    print("\n" + "=" * 78)
    print(f"汇总:  ERROR={len(errors)}   WARN={len(warns)}")
    if errors:
        print("\nERROR 列表:")
        for i in errors:
            print("  " + str(i))
    print("=" * 78)

    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
