# -*- coding: utf-8 -*-
r"""
migrate_classes_to_packages.py â€”â€” æŠŠ Classes\FDTD çš„è®ºæ–‡ä¸Ž .fsp å¤åˆ¶è¿›æ‰“åŒ…åŒº
================================================================================

ç­–ç•¥ï¼ˆå·²ä¸Ž Nileuy ç¡®è®¤ 2026-09-30ï¼‰ï¼š
  * å…¨éƒ¨ã€å¤åˆ¶ã€‘ï¼ŒåŽŸæ–‡ä»¶åœ¨ Classes\FDTD ä¿ç•™ä¸åŠ¨
  * å«å¤§æ–‡ä»¶ï¼ˆ348MB çº¢å¤–å¸æ”¶å™¨.fsp / 83MB çŸ³å¢¨çƒ¯.fspï¼‰
  * è¯¾ç¨‹è§†é¢‘ mp4 ä¹Ÿæ¬è¿›å·¥ä½œç©ºé—´ï¼ˆä¸æ”¾åŒ…å†…ï¼Œæ”¾ course_media\ï¼‰
  * éž ASCII æ–‡ä»¶åã€è‡ªåŠ¨æ”¹åã€‘ä¸º ASCIIï¼Œå¹¶è®°å½•æ–°æ—§å¯¹ç…§

äº§ç‰©
  1. å„åŒ… paper\ ä¸Ž fsp\ ä¸‹æ”¾å…¥æ–‡ä»¶
  2. å„åŒ… fsp\_rename_map.json â€”â€” æ–°å -> åŽŸå çš„å¯¹ç…§
  3. å·¥ä½œç©ºé—´æ ¹ _migration_report.md â€”â€” å…¨é‡æ¬è¿æŠ¥å‘Š
  4. è·³è¿‡æ¸…å•ï¼ˆ.bak / .m1v / _p0.log ç­‰æ´¾ç”Ÿæ–‡ä»¶ï¼‰

âš ï¸ æœ¬è„šæœ¬åªå¤åˆ¶ï¼Œä¸åˆ é™¤ä»»ä½•æºæ–‡ä»¶ã€‚

å•ä¸€å®žçŽ°å£°æ˜Žï¼ˆ2026-11-08ï¼‰ï¼š
  æœ¬æ–‡ä»¶æ˜¯**å”¯ä¸€**å®žçŽ°ï¼Œä½äºŽä»“åº“ `tools\`ï¼ˆåä½œç« ç¨‹æŒ‡å®šçš„ä½ç½®ï¼‰ã€‚
  `skills\fdtd-package-workspace\scripts\` ä¸‹æ›¾æœ‰ä¸€ä»½é€å­—èŠ‚ç›¸åŒçš„å‰¯æœ¬ï¼Œå·²åˆ é™¤ â€”â€”
  ä¸¤ä»½å‰¯æœ¬ä¸€èµ·çƒ‚æŽ‰æ­£æ˜¯ D-005 è®°å½•çš„å‘ï¼ˆé‡å‘½ååŽ `packages/`ã€`fsp/` å…¨å¤±æ•ˆï¼‰ã€‚
  è·¯å¾„å·²å¯¹é½ TASK-002 ä¹‹åŽçš„ç»“æž„ï¼šåŒ…æ ¹ `cases/`ã€å·¥ç¨‹å­ç›®å½• `model/`ã€‚
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SRC_ROOT = Path(r"F:\Lumercial_WS\Classes\FDTD")  # 2026-11-12: 该目录已删除，本脚本仅作历史参考
WS_ROOT = Path(r"F:\Lumercial_WS\FDTD_WS")
PKG_ROOT = WS_ROOT / "cases"          # 2026-11-08: packages/ å·²æ”¹åä¸º cases/
MEDIA_DIR = WS_ROOT / "course_media"
MODEL_SUBDIR = "model"                # 2026-11-08: åŒ…å†… fsp/ å·²æ”¹åä¸º model/

# ---- è®²æ¬¡ -> åŒ… ID -------------------------------------------------------

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

# ---- .fsp æ”¹åæ˜ å°„ï¼ˆéž ASCII / ç‰¹æ®Šå­—ç¬¦ -> å®‰å…¨ ASCIIï¼‰-------------------
# key = åŽŸåï¼ˆä¸å«æ‰©å±•åï¼‰, value = æ–°åï¼ˆä¸å«æ‰©å±•åï¼‰
FSP_RENAME = {
    # 041
    "æˆ‘çš„ç¬¬ä¸€ä¸ªæ¨¡åž‹ï¼ˆåŠ å¯†ç½‘æ ¼ï¼‰": "first_model_mesh_refined",
    "æˆ‘çš„ç¬¬ä¸€ä¸ªæ¨¡åž‹ï¼ˆåªåšå¿…åšæ­¥éª¤ï¼‰": "first_model_minimal",
    # 042
    "çº¢å¤–å®Œç¾Žå¸æ”¶å™¨": "infrared_perfect_absorber",
    # 043
    "wide angle": "wide_angle",
    "æ–œå…¥å°„BFAST": "oblique_BFAST",
    "æ–œå…¥å°„Bloch": "oblique_Bloch",
    "æ­£å…¥å°„": "normal_incidence",
    # 044
    "çŸ³å¢¨çƒ¯å®Œç¾Žå¸æ”¶å™¨": "graphene_perfect_absorber",
    # 047
    "fig2c&3": "fig2c_and_3",
    "fig2c&3_method2": "fig2c_and_3_method2",
    # 049 çš„ fig2g-N å·²æ˜¯ ASCIIï¼Œæ— éœ€æ”¹
}

# ---- è·³è¿‡è§„åˆ™ ------------------------------------------------------------

SKIP_SUFFIX = (".bak", ".m1v", ".fsp.bak")
SKIP_NAMES = {"è¯¾ä»¶.rar"}

# è§†é¢‘ä¸»é¢˜å -> è¾“å‡ºå
VIDEO_RENAME = {
    "ç¬¬ä¸€è®² åŸºç¡€è¯¾ç¨‹.mp4": "L041_basics.mp4",
    "ç¬¬äºŒè®² çº¢å¤–åå­—å®Œç¾Žå¸æ”¶å™¨.mp4": "L042_infrared_cross_absorber.mp4",
    "ç¬¬ä¸‰è®² å®½è§’åº¦å®Œç¾Žå¸æ”¶å™¨.mp4": "L043_wide_angle_absorber.mp4",
    "ç¬¬å››è®² çŸ³å¢¨çƒ¯å®Œç¾Žå¸æ”¶å™¨.mp4": "L044_graphene_absorber.mp4",
    "ç¬¬äº”è®² åæŒ¯è½¬æ¢.mp4": "L045_polarization_control.mp4",
    "ç¬¬å…­è®² äºŒæ¬¡è°æ³¢.mp4": "L046_second_harmonic.mp4",
    "ç¬¬ä¸ƒè®² å¼‚å¸¸åå°„1.mp4": "L047_anomalous_reflection_1.mp4",
    "ç¬¬ä¸ƒè®² å¼‚å¸¸åå°„2.mp4": "L047_anomalous_reflection_2.mp4",
    "ç¬¬å…«è®² åœ†åæŒ¯è¶…é€é•œ.mp4": "L048_metalens.mp4",
    "ç¬¬ä¹è®² æ¶¡æ—‹å…‰1.mp4": "L049_vortex_1.mp4",
    "ç¬¬ä¹è®² æ¶¡æ—‹å…‰2.mp4": "L049_vortex_2.mp4",
}


def is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def safe_name(stem: str, ext: str) -> tuple[str, str | None]:
    """è¿”å›ž (æ–°æ–‡ä»¶å, åŽŸåæˆ–None)ã€‚None è¡¨ç¤ºæœªæ”¹åã€‚"""
    orig = stem + ext
    if stem in FSP_RENAME:
        new = FSP_RENAME[stem] + ext
        return new, orig
    # åªå«ç©ºæ ¼/& çš„æƒ…å†µï¼šç»Ÿä¸€æ›¿æ¢
    if not is_ascii(stem) or any(c in stem for c in " &ï¼ˆï¼‰()"):
        cleaned = stem.replace(" ", "_").replace("&", "and")
        cleaned = "".join(c if (c.isalnum() or c in "_-") else "_" for c in cleaned)
        cleaned = cleaned.strip("_") or "unnamed"
        if cleaned != stem:
            return cleaned + ext, orig
    return orig, None


def lecture_of(path: Path) -> str | None:
    """ä»Žè·¯å¾„ä¸­æå–è®²æ¬¡å·ï¼Œå¦‚ 042ã€‚"""
    for part in path.parts:
        if len(part) >= 3 and part[:3].isdigit() and part[:3] in LECTURE_TO_PKG:
            return part[:3]
    return None


def main() -> int:
    global SRC_ROOT, WS_ROOT, PKG_ROOT, MEDIA_DIR
    ap = argparse.ArgumentParser(
        description="æŠŠè¯¾ç¨‹ç›®å½•çš„è®ºæ–‡ / .fsp / .lsf / è§†é¢‘å¤åˆ¶è¿› cases/ åŒ…ç»“æž„ï¼ˆåªå¤åˆ¶ï¼Œä¸åˆ é™¤æºï¼‰ã€‚")
    ap.add_argument("--src", default=str(SRC_ROOT), help=f"æºç›®å½•ï¼ˆé»˜è®¤ {SRC_ROOT}ï¼‰")
    ap.add_argument("--out", default=str(WS_ROOT), help=f"å·¥ä½œåŒºæ ¹ç›®å½•ï¼ˆé»˜è®¤ {WS_ROOT}ï¼‰")
    ap.add_argument("--dry-run", action="store_true",
                    help="åªæ‰“å°è®¡åˆ’ï¼šä¸å»ºç›®å½•ã€ä¸å¤åˆ¶ã€ä¸å†™æŠ¥å‘Š")
    args = ap.parse_args()

    SRC_ROOT = Path(args.src)
    WS_ROOT = Path(args.out)
    PKG_ROOT = WS_ROOT / "cases"
    MEDIA_DIR = WS_ROOT / "course_media"
    dry = args.dry_run

    if not SRC_ROOT.is_dir():
        print(f"[ERROR] æºç›®å½•ä¸å­˜åœ¨: {SRC_ROOT}", file=sys.stderr)
        return 1
    if not PKG_ROOT.is_dir():
        print(f"[ERROR] åŒ…ç›®å½•ä¸å­˜åœ¨: {PKG_ROOT}ï¼ˆå…ˆå»º cases/ æˆ–ä¼  --outï¼‰", file=sys.stderr)
        return 1

    def ensure_dir(p: Path) -> None:
        if not dry:
            p.mkdir(parents=True, exist_ok=True)

    def copy2(src: Path, dst: Path) -> None:
        if not dry:
            shutil.copy2(src, dst)

    report: list[str] = []
    log: list[dict] = []
    skipped: list[tuple[str, str]] = []

    def rec(action, src, dst, note=""):
        log.append({"action": action, "src": str(src), "dst": str(dst), "note": note})
        line = f"  [{action}] {src.name}"
        if note:
            line += f"   -> {dst.name}  ({note})"
        report.append(line)

    # ================= 1. è®ºæ–‡ PDF =================
    print("=" * 78)
    print("1/4  å¤åˆ¶è®ºæ–‡ PDF")
    print("=" * 78)
    paper_files = sorted(SRC_ROOT.glob("è¯¾ä»¶/*/*.pdf"))
    n_paper = 0
    for f in paper_files:
        name = f.name
        # åªæŒ‘è®ºæ–‡ï¼ˆæŽ’é™¤ pptï¼‰
        if "ppt" in name.lower() or "ä¸Šè¯¾" in name:
            continue
        lec = lecture_of(f)
        if not lec:
            skipped.append((str(f), "æ— æ³•è¯†åˆ«è®²æ¬¡"))
            continue
        pkg = PKG_ROOT / LECTURE_TO_PKG[lec] / "paper"
        ensure_dir(pkg)
        # è®ºæ–‡åä¿ç•™è¯­ä¹‰ä½†åŽ»ç‰¹æ®Šå­—ç¬¦
        new_stem = name.rsplit(".", 1)[0]
        new_stem = new_stem.replace(" ", "_").replace("&", "and")
        new_stem = "".join(c if (c.isalnum() or c in "_-.") else "_" for c in new_stem)
        dst = pkg / (new_stem + ".pdf")
        copy2(f, dst)
        report.append(f"  [å¤åˆ¶] {lec} {name}")
        report.append(f"         -> {pkg.parent.name}/paper/{dst.name}")
        n_paper += 1
        print(f"  {lec}  {name}")
        print(f"       -> {pkg.parent.name}\\paper\\{dst.name}")

    # ================= 2. fsp å·¥ç¨‹ =================
    print()
    print("=" * 78)
    print("2/4  å¤åˆ¶ .fsp å·¥ç¨‹ï¼ˆå«æ”¹åï¼‰")
    print("=" * 78)
    fsp_files = sorted(SRC_ROOT.glob("è¯¾ä»¶/*/*.fsp"))
    fsp_log: dict[str, dict[str, str]] = {}   # pkg -> {new: orig}
    n_fsp = 0
    total_bytes = 0
    for f in fsp_files:
        if f.name.endswith(".bak"):
            skipped.append((str(f), ".bak æ´¾ç”Ÿæ–‡ä»¶"))
            continue
        lec = lecture_of(f)
        if not lec:
            skipped.append((str(f), "æ— æ³•è¯†åˆ«è®²æ¬¡"))
            continue
        pkg_name = LECTURE_TO_PKG[lec]
        pkg = PKG_ROOT / pkg_name / MODEL_SUBDIR
        ensure_dir(pkg)
        new_name, orig = safe_name(f.stem, ".fsp")
        dst = pkg / new_name
        copy2(f, dst)
        size = f.stat().st_size
        total_bytes += size
        fsp_log.setdefault(pkg_name, {})
        if orig:
            fsp_log[pkg_name][new_name] = orig
        tag = f"  <-- åŽŸ {orig}" if orig else ""
        report.append(f"  [å¤åˆ¶] {lec} {f.name}  ({size / 1e6:.1f}MB){tag}")
        # æ‰“å°æ—¶æ˜¾ç¤ºã€ç›®æ ‡æ–‡ä»¶åã€‘ï¼Œé¿å…è¯¯ä»¥ä¸ºæ”¹åæ²¡ç”Ÿæ•ˆ
        print(f"  {lec}  {f.name:42s} -> {new_name:34s} ({size / 1e6:7.1f}MB){tag}")
        n_fsp += 1

    # å†™æ¯åŒ…çš„æ”¹åå¯¹ç…§
    for pkg_name, mapping in fsp_log.items():
        if mapping:
            mp = PKG_ROOT / pkg_name / MODEL_SUBDIR / "_rename_map.json"
            mp.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  æ”¹åå¯¹ç…§ -> {pkg_name}\\fsp\\_rename_map.json  ({len(mapping)} æ¡)")

    # ================= 3. lsf è„šæœ¬ =================
    print()
    print("=" * 78)
    print("3/4  å¤åˆ¶ .lsf è„šæœ¬")
    print("=" * 78)
    lsf_files = sorted(SRC_ROOT.glob("è¯¾ä»¶/*/*.lsf"))
    n_lsf = 0
    for f in lsf_files:
        lec = lecture_of(f)
        if not lec:
            continue
        pkg = PKG_ROOT / LECTURE_TO_PKG[lec] / "scripts"
        ensure_dir(pkg)
        dst = pkg / f.name
        copy2(f, dst)
        n_lsf += 1
        print(f"  {lec}  {f.name}")

    # ================= 4. è§†é¢‘ =================
    print()
    print("=" * 78)
    print("4/4  å¤åˆ¶è¯¾ç¨‹è§†é¢‘ï¼ˆè¾ƒæ…¢ï¼Œ6GBï¼‰")
    print("=" * 78)
    ensure_dir(MEDIA_DIR)
    mp4s = sorted(SRC_ROOT.glob("*.mp4"))
    n_video = 0
    for f in mp4s:
        new_name = VIDEO_RENAME.get(f.name)
        if not new_name:
            new_name = "".join(c if c.isascii() and (c.isalnum() or c in "_-.") else "_"
                               for c in f.name).strip("_")
        dst = MEDIA_DIR / new_name
        if dst.exists() and dst.stat().st_size == f.stat().st_size:
            print(f"  è·³è¿‡ï¼ˆå·²å­˜åœ¨ä¸”å¤§å°ä¸€è‡´ï¼‰: {new_name}")
            continue
        print(f"  å¤åˆ¶ {f.name}  ({f.stat().st_size / 1e9:.2f}GB) -> {new_name} ...", flush=True)
        copy2(f, dst)
        n_video += 1

    # ================= æŠ¥å‘Š =================
    lines = [
        "# æ¬è¿æŠ¥å‘Š â€” Classes\\FDTD â†’ FDTD_WS",
        "",
        f"> ç”Ÿæˆæ—¶é—´ï¼š2026-09-30",
        f"> æºï¼š`{SRC_ROOT}`",
        f"> ç›®æ ‡ï¼š`{WS_ROOT}`",
        "",
        "## ç­–ç•¥",
        "",
        "- **åªå¤åˆ¶ï¼Œä¸åˆ é™¤**ï¼šæºç›®å½•æ‰€æœ‰æ–‡ä»¶ä¿æŒä¸åŠ¨",
        "- éž ASCII / å«ç‰¹æ®Šå­—ç¬¦çš„æ–‡ä»¶åè‡ªåŠ¨æ”¹ä¸º ASCIIï¼Œå¯¹ç…§è§å„åŒ… `model\\_rename_map.json`",
        "- è·³è¿‡æ´¾ç”Ÿæ–‡ä»¶ï¼š`.bak` / `.m1v` / `_p0.log`",
        "",
        "## æ±‡æ€»",
        "",
        f"| ç±»åˆ« | æ•°é‡ |",
        f"|---|---|",
        f"| è®ºæ–‡ PDF | {n_paper} |",
        f"| .fsp å·¥ç¨‹ | {n_fsp} |",
        f"| .lsf è„šæœ¬ | {n_lsf} |",
        f"| è¯¾ç¨‹è§†é¢‘ | {n_video} |",
        f"| .fsp æ€»ä½“ç§¯ | {total_bytes / 1e6:.0f} MB |",
        "",
        "## æ˜Žç»†",
        "",
        "```",
    ] + report + ["```", ""]
    if skipped:
        lines += ["## è·³è¿‡ï¼ˆæœªå¤åˆ¶ï¼‰", "", "| æ–‡ä»¶ | åŽŸå›  |", "|---|---|"]
        lines += [f"| `{Path(p).name}` | {r} |" for p, r in skipped]
        lines += [""]

    if not dry:
        (WS_ROOT / "_migration_report.md").write_text("\n".join(lines), encoding="utf-8")
    print()
    print("=" * 78)
    print(f"å®Œæˆï¼šè®ºæ–‡ {n_paper} / fsp {n_fsp} / lsf {n_lsf} / è§†é¢‘ {n_video}")
    print(f"æŠ¥å‘Šï¼š{WS_ROOT / '_migration_report.md'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
