# -*- coding: utf-8 -*-
r"""
migrate_classes_to_packages.py —— 把 Classes\FDTD 的论文与 .fsp 复制进打包区
================================================================================

策略（已与 Nileuy 确认 2026-09-30）：
  * 全部【复制】，原文件在 Classes\FDTD 保留不动
  * 含大文件（348MB 红外吸收器.fsp / 83MB 石墨烯.fsp）
  * 课程视频 mp4 也搬进工作空间（不放包内，放 course_media\）
  * 非 ASCII 文件名【自动改名】为 ASCII，并记录新旧对照

产物
  1. 各包 paper\ 与 fsp\ 下放入文件
  2. 各包 fsp\_rename_map.json —— 新名 -> 原名 的对照
  3. 工作空间根 _migration_report.md —— 全量搬迁报告
  4. 跳过清单（.bak / .m1v / _p0.log 等派生文件）

⚠️ 本脚本只复制，不删除任何源文件。
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SRC_ROOT = Path(r"F:\Lumercial_WS\Classes\FDTD")
WS_ROOT = Path(r"F:\Lumercial_WS\FDTD_WS")
PKG_ROOT = WS_ROOT / "packages"
MEDIA_DIR = WS_ROOT / "course_media"

# ---- 讲次 -> 包 ID -------------------------------------------------------

LECTURE_TO_PKG = {
    "041": "P07_BrokenSymmetry_041",
    "042": "P01_Absorber_042",
    "043": "P08_BroadbandAbsorber_043",
    "044": "P09_GrapheneAbsorber_044",
    "045": "P02_PolarizationControl_045",
    "046": "P10_SHG_046",
    "047": "P04_AnomalousReflection_047",
    "048": "P05_Metalens_048",
    "049": "P06_Vortex_049",
}

# ---- .fsp 改名映射（非 ASCII / 特殊字符 -> 安全 ASCII）-------------------
# key = 原名（不含扩展名）, value = 新名（不含扩展名）
FSP_RENAME = {
    # 041
    "我的第一个模型（加密网格）": "first_model_mesh_refined",
    "我的第一个模型（只做必做步骤）": "first_model_minimal",
    # 042
    "红外完美吸收器": "infrared_perfect_absorber",
    # 043
    "wide angle": "wide_angle",
    "斜入射BFAST": "oblique_BFAST",
    "斜入射Bloch": "oblique_Bloch",
    "正入射": "normal_incidence",
    # 044
    "石墨烯完美吸收器": "graphene_perfect_absorber",
    # 047
    "fig2c&3": "fig2c_and_3",
    "fig2c&3_method2": "fig2c_and_3_method2",
    # 049 的 fig2g-N 已是 ASCII，无需改
}

# ---- 跳过规则 ------------------------------------------------------------

SKIP_SUFFIX = (".bak", ".m1v", ".fsp.bak")
SKIP_NAMES = {"课件.rar"}

# 视频主题名 -> 输出名
VIDEO_RENAME = {
    "第一讲 基础课程.mp4": "L041_basics.mp4",
    "第二讲 红外十字完美吸收器.mp4": "L042_infrared_cross_absorber.mp4",
    "第三讲 宽角度完美吸收器.mp4": "L043_wide_angle_absorber.mp4",
    "第四讲 石墨烯完美吸收器.mp4": "L044_graphene_absorber.mp4",
    "第五讲 偏振转换.mp4": "L045_polarization_control.mp4",
    "第六讲 二次谐波.mp4": "L046_second_harmonic.mp4",
    "第七讲 异常反射1.mp4": "L047_anomalous_reflection_1.mp4",
    "第七讲 异常反射2.mp4": "L047_anomalous_reflection_2.mp4",
    "第八讲 圆偏振超透镜.mp4": "L048_metalens.mp4",
    "第九讲 涡旋光1.mp4": "L049_vortex_1.mp4",
    "第九讲 涡旋光2.mp4": "L049_vortex_2.mp4",
}


def is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def safe_name(stem: str, ext: str) -> tuple[str, str | None]:
    """返回 (新文件名, 原名或None)。None 表示未改名。"""
    orig = stem + ext
    if stem in FSP_RENAME:
        new = FSP_RENAME[stem] + ext
        return new, orig
    # 只含空格/& 的情况：统一替换
    if not is_ascii(stem) or any(c in stem for c in " &（）()"):
        cleaned = stem.replace(" ", "_").replace("&", "and")
        cleaned = "".join(c if (c.isalnum() or c in "_-") else "_" for c in cleaned)
        cleaned = cleaned.strip("_") or "unnamed"
        if cleaned != stem:
            return cleaned + ext, orig
    return orig, None


def lecture_of(path: Path) -> str | None:
    """从路径中提取讲次号，如 042。"""
    for part in path.parts:
        if len(part) >= 3 and part[:3].isdigit() and part[:3] in LECTURE_TO_PKG:
            return part[:3]
    return None


def main() -> int:
    if not SRC_ROOT.is_dir():
        print(f"[ERROR] 源目录不存在: {SRC_ROOT}", file=sys.stderr)
        return 1
    if not PKG_ROOT.is_dir():
        print(f"[ERROR] 包目录不存在: {PKG_ROOT}", file=sys.stderr)
        return 1

    report: list[str] = []
    log: list[dict] = []
    skipped: list[tuple[str, str]] = []

    def rec(action, src, dst, note=""):
        log.append({"action": action, "src": str(src), "dst": str(dst), "note": note})
        line = f"  [{action}] {src.name}"
        if note:
            line += f"   -> {dst.name}  ({note})"
        report.append(line)

    # ================= 1. 论文 PDF =================
    print("=" * 78)
    print("1/3  复制论文 PDF")
    print("=" * 78)
    paper_files = sorted(SRC_ROOT.glob("课件/*/*.pdf"))
    n_paper = 0
    for f in paper_files:
        name = f.name
        # 只挑论文（排除 ppt）
        if "ppt" in name.lower() or "上课" in name:
            continue
        lec = lecture_of(f)
        if not lec:
            skipped.append((str(f), "无法识别讲次"))
            continue
        pkg = PKG_ROOT / LECTURE_TO_PKG[lec] / "paper"
        pkg.mkdir(parents=True, exist_ok=True)
        # 论文名保留语义但去特殊字符
        new_stem = name.rsplit(".", 1)[0]
        new_stem = new_stem.replace(" ", "_").replace("&", "and")
        new_stem = "".join(c if (c.isalnum() or c in "_-.") else "_" for c in new_stem)
        dst = pkg / (new_stem + ".pdf")
        shutil.copy2(f, dst)
        report.append(f"  [复制] {lec} {name}")
        report.append(f"         -> {pkg.parent.name}/paper/{dst.name}")
        n_paper += 1
        print(f"  {lec}  {name}")
        print(f"       -> {pkg.parent.name}\\paper\\{dst.name}")

    # ================= 2. fsp 工程 =================
    print()
    print("=" * 78)
    print("2/3  复制 .fsp 工程（含改名）")
    print("=" * 78)
    fsp_files = sorted(SRC_ROOT.glob("课件/*/*.fsp"))
    fsp_log: dict[str, dict[str, str]] = {}   # pkg -> {new: orig}
    n_fsp = 0
    total_bytes = 0
    for f in fsp_files:
        if f.name.endswith(".bak"):
            skipped.append((str(f), ".bak 派生文件"))
            continue
        lec = lecture_of(f)
        if not lec:
            skipped.append((str(f), "无法识别讲次"))
            continue
        pkg_name = LECTURE_TO_PKG[lec]
        pkg = PKG_ROOT / pkg_name / "fsp"
        pkg.mkdir(parents=True, exist_ok=True)
        new_name, orig = safe_name(f.stem, ".fsp")
        dst = pkg / new_name
        shutil.copy2(f, dst)
        size = f.stat().st_size
        total_bytes += size
        fsp_log.setdefault(pkg_name, {})
        if orig:
            fsp_log[pkg_name][new_name] = orig
        tag = f"  <-- 原 {orig}" if orig else ""
        report.append(f"  [复制] {lec} {f.name}  ({size / 1e6:.1f}MB){tag}")
        # 打印时显示【目标文件名】，避免误以为改名没生效
        print(f"  {lec}  {f.name:42s} -> {new_name:34s} ({size / 1e6:7.1f}MB){tag}")
        n_fsp += 1

    # 写每包的改名对照
    for pkg_name, mapping in fsp_log.items():
        if mapping:
            mp = PKG_ROOT / pkg_name / "fsp" / "_rename_map.json"
            mp.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  改名对照 -> {pkg_name}\\fsp\\_rename_map.json  ({len(mapping)} 条)")

    # ================= 3. lsf 脚本 =================
    print()
    print("=" * 78)
    print("3/3  复制 .lsf 脚本")
    print("=" * 78)
    lsf_files = sorted(SRC_ROOT.glob("课件/*/*.lsf"))
    n_lsf = 0
    for f in lsf_files:
        lec = lecture_of(f)
        if not lec:
            continue
        pkg = PKG_ROOT / LECTURE_TO_PKG[lec] / "scripts"
        pkg.mkdir(parents=True, exist_ok=True)
        dst = pkg / f.name
        shutil.copy2(f, dst)
        n_lsf += 1
        print(f"  {lec}  {f.name}")

    # ================= 4. 视频 =================
    print()
    print("=" * 78)
    print("4/4  复制课程视频（较慢，6GB）")
    print("=" * 78)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    mp4s = sorted(SRC_ROOT.glob("*.mp4"))
    n_video = 0
    for f in mp4s:
        new_name = VIDEO_RENAME.get(f.name)
        if not new_name:
            new_name = "".join(c if c.isascii() and (c.isalnum() or c in "_-.") else "_"
                               for c in f.name).strip("_")
        dst = MEDIA_DIR / new_name
        if dst.exists() and dst.stat().st_size == f.stat().st_size:
            print(f"  跳过（已存在且大小一致）: {new_name}")
            continue
        print(f"  复制 {f.name}  ({f.stat().st_size / 1e9:.2f}GB) -> {new_name} ...", flush=True)
        shutil.copy2(f, dst)
        n_video += 1

    # ================= 报告 =================
    lines = [
        "# 搬迁报告 — Classes\\FDTD → FDTD_WS",
        "",
        f"> 生成时间：2026-09-30",
        f"> 源：`{SRC_ROOT}`",
        f"> 目标：`{WS_ROOT}`",
        "",
        "## 策略",
        "",
        "- **只复制，不删除**：源目录所有文件保持不动",
        "- 非 ASCII / 含特殊字符的文件名自动改为 ASCII，对照见各包 `fsp\\_rename_map.json`",
        "- 跳过派生文件：`.bak` / `.m1v` / `_p0.log`",
        "",
        "## 汇总",
        "",
        f"| 类别 | 数量 |",
        f"|---|---|",
        f"| 论文 PDF | {n_paper} |",
        f"| .fsp 工程 | {n_fsp} |",
        f"| .lsf 脚本 | {n_lsf} |",
        f"| 课程视频 | {n_video} |",
        f"| .fsp 总体积 | {total_bytes / 1e6:.0f} MB |",
        "",
        "## 明细",
        "",
        "```",
    ] + report + ["```", ""]
    if skipped:
        lines += ["## 跳过（未复制）", "", "| 文件 | 原因 |", "|---|---|"]
        lines += [f"| `{Path(p).name}` | {r} |" for p, r in skipped]
        lines += [""]

    (WS_ROOT / "_migration_report.md").write_text("\n".join(lines), encoding="utf-8")
    print()
    print("=" * 78)
    print(f"完成：论文 {n_paper} / fsp {n_fsp} / lsf {n_lsf} / 视频 {n_video}")
    print(f"报告：{WS_ROOT / '_migration_report.md'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
