#!/usr/bin/env python3
"""check_skill_contract.py — skills/ 变更契约体检。

    python tools/check_skill_contract.py

规则出处：docs/constitution/skill-change-contract.md（逐条对应 [K1]–[K12]）。
与 tools/skills-doctor.py 的分工：
    skills-doctor  = 宿主能不能发现（入口、junction、名字一致）
    check_skill_contract = 内容合不合契约（frontmatter、引用、登记、CLI）

检查项：
    [K1]  SKILL.md 存在，frontmatter 在文件开头（容忍 BOM）
    [K2]  frontmatter.name == 目录名，形状 fdtd-<scope>-<thing>…，<=64 字符
    [K3]  description 非空、>=60 字符、无 <> 占位符
    [K4]  必须有 CRITICAL 段（违反即停止的具体规则）
    [K5]  有 references/ 或 assets/ 时，必须有 References / 按需加载 段
    [K6]  references/*.md 必须在 SKILL.md 正文被点名（否则 Agent 看不见）
    [K7]  references|assets|scripts 子目录里不得出现 SKILL.md（会被误注册成独立技能）
    [K8]  SKILL.md 正文 <= 500 行（超出必须拆进 references/）
    [K9]  正文里的 references/ assets/ scripts/ 相对引用必须可达；跨技能 scripts 引用也必须可达
    [K10] skills/INDEX.md 必须登记该名字
    [K11] scripts/*.py 遵守 CLI 契约（--out / --dry-run / --json）—— WARN
    [K12] skills/ 下不得出现 __pycache__ / *.pyc —— WARN（构建产物，不入库）
    [K13] SKILL.md 建议有 Examples / 示例 段 —— WARN
    [K14] agents/*/skills.yaml 里每条 path 都必须指向含 SKILL.md 的真实技能

退出码：0 = 通过（允许 WARN）；1 = 有 FAIL。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
INDEX = SKILLS / "INDEX.md"

NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)
DESC_INLINE_RE = re.compile(r"^description:\s*(?!>)(\S.*)$", re.M)
DESC_BLOCK_RE = re.compile(r"^description:\s*>\s*$", re.M)
CRITICAL_RE = re.compile(r"^##\s+.*CRITICAL", re.M | re.I)
REFS_SECTION_RE = re.compile(r"^##\s+.*(References|按需加载)", re.M | re.I)
EXAMPLES_RE = re.compile(r"^##\s+.*(Examples|示例)", re.M | re.I)
# 负向后顾：排除 xxx/scripts/foo.py 里的子串（那是跨技能引用，由 CROSS_SKILL_RE 管）
REL_REF_RE = re.compile(
    r"(?<![\w/.-])(?:references|assets|scripts)/[A-Za-z0-9_./-]+\.(?:md|py|json|csv|txt|ya?ml)"
)
CROSS_SKILL_RE = re.compile(r"(fdtd-[a-z0-9-]+)/scripts/([A-Za-z0-9_.-]+\.py)")
AGENT_PATH_RE = re.compile(r"^\s*path:\s*(\S+)\s*$", re.M)
NAME_SHAPE_RE = re.compile(r"^fdtd-[a-z0-9]+(?:-[a-z0-9]+)+$")

fails: list[str] = []
warns: list[str] = []
ok_count = 0


def ok(n: str, msg: str) -> None:
    global ok_count
    ok_count += 1
    print(f"  [{n}] OK    {msg}")


def bad(n: str, msg: str, hint: str = "") -> None:
    fails.append(f"[{n}] {msg}")
    print(f"  [{n}] FAIL  {msg}")
    if hint:
        print(f"        → {hint}")


def warn(n: str, msg: str) -> None:
    warns.append(f"[{n}] {msg}")
    print(f"  [{n}] WARN  {msg}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def split_frontmatter(text: str) -> tuple[str, str] | None:
    """返回 (frontmatter, body)；不在文件开头则 None。容忍 BOM 与 CRLF。"""
    t = text.replace("\r\n", "\n")
    if not t.startswith("---"):
        return None
    end = t.find("\n---", 3)
    if end < 0:
        return None
    fm = t[3:end]
    body = t[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    return fm, body


def get_description(fm: str) -> str:
    m = DESC_INLINE_RE.search(fm)
    if m:
        return m.group(1).strip()
    m = DESC_BLOCK_RE.search(fm)
    if not m:
        return ""
    lines: list[str] = []
    for ln in fm[m.end() :].splitlines():
        if re.match(r"^\S", ln):  # 下一个顶层 key
            break
        lines.append(ln.strip())
    return " ".join(x for x in lines if x)


def check_skill(d: Path) -> None:
    name_dir = d.name
    skill_md = d / "SKILL.md"
    print(f"\n-- {name_dir}")

    # [K1]
    if not skill_md.is_file():
        bad("K1", f"skills/{name_dir}/SKILL.md 不存在", "从 skills/_TEMPLATE/ 复制")
        return
    text = read(skill_md)
    parts = split_frontmatter(text)
    if parts is None:
        bad("K1", f"skills/{name_dir}/SKILL.md 的 frontmatter 不在文件开头",
            "首行必须是 ---，末尾用 --- 闭合；BOM 已容忍，位置不对不行")
        return
    fm, body = parts
    ok("K1", "SKILL.md + frontmatter 位置正确")

    # [K2]
    m = NAME_RE.search(fm)
    if not m:
        bad("K2", f"skills/{name_dir} 的 frontmatter 缺 name", "name 必须显式写且等于目录名")
        return
    name = m.group(1)
    if name != name_dir:
        bad("K2", f"name={name} 与目录名 {name_dir} 不一致",
            "宿主按 name 注册、按目录找文件；两者必须相同（改名字=破坏性变更）")
    elif not NAME_SHAPE_RE.match(name):
        bad("K2", f"name={name} 不符合 fdtd-<scope>-<thing> 形状",
            "scope ∈ lumerical/paper/model/result/package；全小写 kebab-case")
    elif len(name) > 64:
        bad("K2", f"name 长度 {len(name)} > 64")
    else:
        ok("K2", f"name={name} 形状与目录名一致")

    # [K3]
    desc = get_description(fm)
    if not desc:
        bad("K3", "description 缺失或为空",
            "自动触发完全依赖它；必须写「做什么 + 什么时候用 + 触发词」")
    elif len(desc) < 60:
        bad("K3", f"description 只有 {len(desc)} 字符（下限 60）",
            "过短的描述无法命中自动触发")
    elif re.search(r"<[^>]{1,30}>", desc):
        bad("K3", "description 里还有模板占位符 <>", "从 _TEMPLATE 复制后忘了替换")
    else:
        ok("K3", f"description {len(desc)} 字符")

    # [K4]
    if not CRITICAL_RE.search(body):
        bad("K4", "缺 CRITICAL 段", "写「做了就会坏」的规则，不是「最好这样做」")
    else:
        ok("K4", "CRITICAL 段存在")

    # [K5]
    has_side = any((d / x).is_dir() and any((d / x).iterdir()) for x in ("references", "assets"))
    if has_side:
        if not REFS_SECTION_RE.search(body):
            bad("K5", "有 references/assets 但正文没有 References / 按需加载 段",
                "不点名 = Agent 不知道何时读 = 文件等于不存在")
        else:
            ok("K5", "References / 按需加载 段存在")

    # [K6]
    ref_dir = d / "references"
    if ref_dir.is_dir():
        missing = []
        for f in sorted(ref_dir.rglob("*.md")):
            base = f.relative_to(ref_dir).as_posix()
            if base not in body and f.name not in body:
                missing.append(base)
        if missing:
            bad("K6", f"references 未在正文点名: {', '.join(missing)}",
                "逐个写「读 references/xxx.md 当 <场景> 时」")
        else:
            ok("K6", "references 全部在正文点名")

    # [K7]
    intruders = [
        p.relative_to(d).as_posix()
        for sub in ("references", "assets", "scripts")
        if (d / sub).is_dir()
        for p in (d / sub).rglob("SKILL.md")
    ]
    if intruders:
        bad("K7", f"子目录里出现 SKILL.md: {', '.join(intruders)}",
            "宿主递归 5 层扫描，它会被注册成另一个独立技能；改成普通 .md 名")
    else:
        ok("K7", "子目录无 SKILL.md")

    # [K8]
    n_lines = len(text.replace("\r\n", "\n").splitlines())
    if n_lines > 500:
        bad("K8", f"SKILL.md {n_lines} 行 > 500", "正文是索引不是手册；拆进 references/")
    else:
        ok("K8", f"正文 {n_lines} 行")

    # [K9]
    broken: list[str] = []
    for rel in sorted(set(REL_REF_RE.findall(body))):
        if not (d / rel).exists():
            broken.append(rel)
    for skill_name, script in sorted(set(CROSS_SKILL_RE.findall(body))):
        if not (SKILLS / skill_name / "scripts" / script).is_file():
            broken.append(f"{skill_name}/scripts/{script}")
    if broken:
        bad("K9", f"引用不可达: {', '.join(broken)}",
            "路径写死在文档里会腐烂；以仓库根为基准核对后修正")
    else:
        ok("K9", "正文引用全部可达")

    # [K11] 只查「可执行入口」：无 __main__ 的是纯模块，不要求 CLI
    script_dir = d / "scripts"
    if script_dir.is_dir():
        nospec = []
        modules = 0
        for py in sorted(script_dir.glob("*.py")):
            src = read(py)
            if "__main__" not in src:
                modules += 1
                continue
            need = [x for x in ("--out", "--dry-run", "--json") if x not in src]
            if need:
                nospec.append(f"{py.name}(缺 {'/'.join(need)})")
        if nospec:
            warn("K11", f"CLI 契约不完整: {', '.join(nospec)}")
        else:
            ok("K11", f"scripts 满足 CLI 契约" + (f"（{modules} 个纯模块跳过）" if modules else ""))


def check_template_and_cache() -> None:
    print("\n-- 全局")
    # [K10]
    if not INDEX.is_file():
        bad("K10", "skills/INDEX.md 不存在", "它是唯一登记表")
        return
    index_text = read(INDEX)
    registered = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if f"`{d.name}`" in index_text or d.name in index_text:
            registered.append(d.name)
        else:
            bad("K10", f"{d.name} 未登记在 skills/INDEX.md",
                "加一行: name | stage | scripts | consumes | produces | hands_to | 边界")
    if len(registered) == sum(
        1 for d in SKILLS.iterdir() if d.is_dir() and not d.name.startswith("_")
    ):
        ok("K10", f"INDEX.md 已登记 {len(registered)} 个技能")

    # [K12]
    cache = [p for p in SKILLS.rglob("__pycache__") if p.is_dir()]
    pyc = list(SKILLS.rglob("*.pyc"))
    if cache or pyc:
        warn("K12", f"{len(cache)} 个 __pycache__ / {len(pyc)} 个 .pyc 留在 skills/ 下（构建产物）")
        print("        → .gitignore 已覆盖；确认未被跟踪: git ls-files '*.pyc' 应为空")
        print("        → 清理: 删 __pycache__ 目录本身（不要用 git clean -xfd，会误伤 _scratch）")
    else:
        ok("K12", "无 __pycache__ / .pyc")


def check_examples() -> None:
    """[K13] 建议有 Examples 段 —— 只 WARN，避免动老文件。"""
    print("\n-- 建议项")
    missing = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        f = d / "SKILL.md"
        if f.is_file() and not EXAMPLES_RE.search(read(f)):
            missing.append(d.name)
    if missing:
        warn("K13", f"缺 Examples / 示例 段: {', '.join(missing)}")
    else:
        ok("K13", "全部有 Examples 段")


def check_agent_wiring() -> None:
    """[K14] agents/*/skills.yaml 的 path 必须可达。"""
    print("\n-- 编排")
    yamls = sorted((ROOT / "agents").rglob("skills.yaml"))
    if not yamls:
        ok("K14", "没有 agents/*/skills.yaml（无编排）")
        return
    broken, total = [], 0
    for y in yamls:
        for p in AGENT_PATH_RE.findall(read(y)):
            total += 1
            target = (y.parent / p).resolve()
            if not (target / "SKILL.md").is_file():
                broken.append(f"{y.relative_to(ROOT).as_posix()} → {p}")
    if broken:
        bad("K14", f"编排引用了不存在的技能: {'; '.join(broken)}",
            "技能改名/移动后必须同轮改 skills.yaml 的 id 与 path")
    else:
        ok("K14", f"{total} 条编排路径全部可达")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"仓库: {ROOT}")
    print(f"契约: docs/constitution/skill-change-contract.md")

    skill_dirs = [
        d for d in sorted(SKILLS.iterdir())
        if d.is_dir() and not d.name.startswith("_")
    ] if SKILLS.is_dir() else []

    if not skill_dirs:
        bad("K0", "skills/ 下没有合格技能目录")
        return 1

    for d in skill_dirs:
        check_skill(d)
    check_template_and_cache()
    check_examples()
    check_agent_wiring()

    print()
    print(f"合格技能 {len(skill_dirs)} 个 · OK {ok_count} · WARN {len(warns)} · FAIL {len(fails)}")
    if fails:
        print("\nFAIL 明细：")
        for f in fails:
            print(f"  {f}")
        return 1
    print("ALL GREEN" + (f"（{len(warns)} 项 WARN，不阻断）" if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
