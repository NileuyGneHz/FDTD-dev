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
    [K11] scripts/*.py 遵守 CLI 契约 —— WARN。按行为分级：开仿真会话要 --out/--dry-run/--json，
          只写文件要 --out，纯打印不要求；无 argparse 的模块（含带自测的库）跳过
    [K12] skills/ 下不得出现 __pycache__ / *.pyc —— WARN（构建产物，不入库）
    [K13] SKILL.md 建议有 Examples / 示例 段 —— WARN
    [K14] agents/*/skills.yaml 必须是**合法 YAML**，且每条 path 都要指向含 SKILL.md 的真实技能
          （2026-11-10 加：正则能判引用对不对，判不了文件能不能被解析）
    [K15] 文档（INDEX/constitution/iterations）声明的 scripts/*.py 必须实存
    [K16] 文档里同一行写在该脚本后面的 --flag，必须被该脚本接受

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
# 2026-11-14：仓库从单一 FDTD 主题扩到「超表面 + 光计算」双轨，
# 技能命名不再全是 fdtd- 前缀。仍要求：全小写 kebab-case、至少两段、
# 且带一个已知前缀，防止随手起名。
NAME_SHAPE_RE = re.compile(r"^(fdtd|lit|core|cut|office)-[a-z0-9]+(?:-[a-z0-9]+)+$")
# 文档里对脚本的声明：`skills/fdtd-x/scripts/y.py` 或 `fdtd-x/scripts/y.py`
DOC_SCRIPT_RE = re.compile(
    r"(?:skills/)?(fdtd-[a-z0-9-]+)/scripts/([A-Za-z0-9_.-]+\.py)")
DOC_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
# INDEX.md 的表格：| `fdtd-x` | stage | scripts 列 | ...
INDEX_ROW_RE = re.compile(r"^\|\s*`?(fdtd-[a-z0-9-]+)`?\s*\|(.*)$")
INDEX_PY_RE = re.compile(r"([A-Za-z0-9_.-]+\.py)")
# INDEX 行里可能同时出现「技能内脚本」（裸文件名，§约定如此）与「仓库级工具」
# （如 tools/xxx.py）。前者拼到 <skill>/scripts/，后者按仓库根核对 —— 混为一谈
# 会把合法的仓库级引用误判成幽灵入口（2026-11-08 实际发生）。
INDEX_PY_PATH_RE = re.compile(r"(?:([A-Za-z0-9_.\-]+)[/\\])?([A-Za-z0-9_.\-]+\.py)")
# 只扫「必须准」的地方；_scratch / journal 允许留历史路径
DOC_SCAN_DIRS = ("docs", "iterations", "agents")
DOC_SCAN_FILES = ("skills/INDEX.md",)

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
        bad("K2", f"name={name} 不符合 <前缀>-<thing> 形状",
            "前缀 ∈ fdtd/lit/core/cut/office；全小写 kebab-case，至少两段")
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

    # [K11] 只查「可执行入口」：无 __main__ 的是纯模块，不要求 CLI。
    #       旗标要求按脚本实际行为分级，避免对纯解析/校验脚本提无关要求：
    #         开仿真会话 → --out + --dry-run + --json（dry-run 存在的唯一理由是不占许可席位）
    #         只写文件   → --out（产物必须能指定落点）
    #         只打印     → 不要求任何旗标
    script_dir = d / "scripts"
    if script_dir.is_dir():
        nospec = []
        modules = 0
        for py in sorted(script_dir.glob("*.py")):
            src = read(py)
            # 无 __main__ 或不用 argparse 的，是模块 / 带自测的库，不是 CLI 入口
            if "__main__" not in src or "argparse" not in src:
                modules += 1
                continue
            opens_session = ("lumapi" in src or "FDTD(" in src) and "runpy" not in src
            writes = any(t in src for t in ("write_text(", "to_csv(", "savefig(",
                                            "json.dump(", ".write("))
            need = []
            if opens_session:
                need = [x for x in ("--out", "--dry-run", "--json") if x not in src]
            elif writes:
                need = [x for x in ("--out",) if x not in src]
            if need:
                nospec.append(f"{py.name}(缺 {'/'.join(need)})")
        if nospec:
            warn("K11", f"CLI 契约不完整: {', '.join(nospec)}")
        else:
            ok("K11", "scripts 满足 CLI 契约" + (f"（{modules} 个纯模块跳过）" if modules else ""))


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
    """[K14] agents/*/skills.yaml 的 path 必须可达，且文件本身必须是合法 YAML。

    来源事件（2026-11-10）：`produces: *.png` 行首的 `*` 是 YAML 别名起始符，
    整份 skills.yaml 因此对任何真正的 YAML 解析器都无效。而 [K14] 一直用
    regex 抽 `path:`，正则不关心语法 —— 一个 10 个技能全读不出来的文件拿满分。
    正则能判「引用对不对」，判不了「文件能不能被解析」，所以先解析再抽。
    """
    print("\n-- 编排")
    yamls = sorted((ROOT / "agents").rglob("skills.yaml"))
    if not yamls:
        ok("K14", "没有 agents/*/skills.yaml（无编排）")
        return

    # 先解语法；没有 PyYAML 时降级为 WARN，绝不静默跳过
    parser_errs = []
    try:
        import yaml  # noqa: PLC0415 - 可选依赖
    except ImportError:
        warn("K14", "未安装 PyYAML，跳过 skills.yaml 语法校验（只做了正则可达性检查）")
    else:
        for y in yamls:
            try:
                yaml.safe_load(read(y))
            except Exception as exc:  # noqa: BLE001 - 任何解析错误都要报出来
                msg = str(exc).splitlines()
                parser_errs.append(
                    f"{y.relative_to(ROOT).as_posix()}: {msg[0]}"
                    + (f" / {msg[-1].strip()}" if len(msg) > 1 else ""))
    if parser_errs:
        bad("K14", f"skills.yaml 不是合法 YAML: {'; '.join(parser_errs)}",
            '常见原因：值以 * & ! % @ ` 开头（YAML 指示符）或未加引号；'
            '把整个值用双引号包起来即可，如 produces: "*.png"')
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
        ok("K14", f"{total} 条编排路径全部可达；skills.yaml 语法合法")


def check_declared_scripts() -> None:
    """[K15]/[K16] 文档声明的脚本必须实存，且同行的 --flag 必须被接受。

    来源事件：P04 报告发现 run_lsf.py 在 script-contract §3 / workspace-layout /
    INDEX.md / acceptance.md 四处被声明为「.lsf 唯一入口」，实体却不存在，
    而 [K9]/skills-doctor 全绿 —— 因为它们只看各技能自己的 SKILL.md。
    """
    print("\n-- 文档声明")

    files: list[Path] = []
    for rel in DOC_SCAN_FILES:
        p = ROOT / rel
        if p.is_file():
            files.append(p)
    for d in DOC_SCAN_DIRS:
        base = ROOT / d
        if base.is_dir():
            files.extend(sorted(base.rglob("*.md")))

    missing: list[str] = []
    bad_flags: list[str] = []
    checked = 0

    def verify(skill: str, script: str, src_file: Path, line: str) -> None:
        nonlocal checked
        checked += 1
        target = SKILLS / skill / "scripts" / script
        rel = f"{src_file.relative_to(ROOT).as_posix()} → {skill}/scripts/{script}"
        if not target.is_file():
            missing.append(rel)
            return
        src = read(target)
        for flag in sorted(set(DOC_FLAG_RE.findall(line))):
            if flag not in src:
                bad_flags.append(f"{src_file.relative_to(ROOT).as_posix()} 写了 "
                                 f"{script} {flag}，但脚本不认这个旗标")

    for f in files:
        for line in read(f).splitlines():
            for skill, script in DOC_SCRIPT_RE.findall(line):
                verify(skill, script, f, line)
            m = INDEX_ROW_RE.match(line.strip())
            if m and f.name == "INDEX.md":
                # INDEX 的脚本列是第 3 列；整行扫描更稳，漏列不会静默跳过
                for pm in INDEX_PY_PATH_RE.finditer(line):
                    prefix, script = pm.group(1), pm.group(2)
                    if prefix and prefix != "scripts":
                        # 仓库级引用（tools/…）：按仓库根核对，别拼到技能内
                        checked += 1
                        repo_rel = f"{prefix}/{script}"
                        if not (ROOT / repo_rel).is_file():
                            missing.append(f"{f.relative_to(ROOT).as_posix()} → "
                                           f"{repo_rel}（仓库级引用）")
                        continue
                    verify(m.group(1), script, f, line)

    if missing:
        bad("K15", f"文档声明了不存在的脚本: {'; '.join(missing)}",
            "要么补实体（这才是契约），要么删声明（幽灵入口会让 agent 走到死路）")
    else:
        ok("K15", f"文档声明的 {checked} 处脚本全部实存")

    if bad_flags:
        bad("K16", f"文档与脚本 CLI 不一致: {'; '.join(bad_flags)}",
            "文档是调用方唯一依据；旗标不认就是运行期崩")
    else:
        ok("K16", "文档里的 --flag 全部被对应脚本接受")


def check_stage_coverage() -> None:
    """[K17] INDEX 里带数字 stage 的技能必须出现在某个 skills.yaml（stage X 可缺）。

    来源事件（2026-11-10）：`fdtd-lumerical-phase-retrieval` 在 INDEX 里是 stage 4，
    但 `agents/fdtd-sim-agent/skills.yaml` 里没有它的条目 —— 编排链从
    `unitcell-simulation` 直接跳到 `figure`，stage 4 在自动流程里**不可达**，
    而 `[K14]` 全绿，因为它只验「yaml 里写下的 path 存不存在」，
    对「该写的没写」完全无感。

    判据：INDEX 的 stage 列含数字 = 流水线环节 = 必须能被编排；
    stage 为 `X` = 横切/按需能力（契约 §6 允许只登记 INDEX，如 `headless`）。
    """
    print("\n-- 编排覆盖")
    index = SKILLS / "INDEX.md"
    if not index.is_file():
        warn("K17", "没有 skills/INDEX.md，跳过编排覆盖检查")
        return
    ids: set[str] = set()
    for y in sorted((ROOT / "agents").rglob("skills.yaml")):
        ids |= set(re.findall(r"^\s*-\s*id:\s*(\S+)", read(y), re.M))
    if not ids:
        warn("K17", "没有任何 skills.yaml 条目，跳过编排覆盖检查")
        return
    missing = []
    for line in read(index).splitlines():
        m = re.match(r"\|\s*`(fdtd-[a-z0-9-]+)`\s*\|\s*([^|]+)\|", line)
        if not m:
            continue
        name, stage = m.group(1), m.group(2).strip()
        if re.search(r"\d", stage) and name not in ids:
            missing.append(f"{name}(stage {stage})")
    if missing:
        bad("K17", f"INDEX 标了数字 stage 但没进编排: {', '.join(missing)}",
            "数字 stage = 流水线环节，必须写进 agents/*/skills.yaml；"
            "只有横切/按需能力才可以标 stage X 并只登记 INDEX")
    else:
        ok("K17", "INDEX 里所有数字 stage 的技能都在编排里")


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
    check_stage_coverage()
    check_declared_scripts()

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
