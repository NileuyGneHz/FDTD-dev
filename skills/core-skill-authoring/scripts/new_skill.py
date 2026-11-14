#!/usr/bin/env python3
"""new_skill.py — 按契约创建一个新技能的骨架，并登记到 skills/INDEX.md。

    python skills/core-skill-authoring/scripts/new_skill.py --config <spec.json> --out <dir>
    python skills/core-skill-authoring/scripts/new_skill.py --config <spec.json> --dry-run

spec.json 字段（见 references/format.md）：
    name          必填，<pack>-<thing>，小写 kebab
    description   必填，>= 20 字符
    domain        可选，默认取 name 的前缀
    stage         可选，默认 X
    consumes      可选
    produces      可选
    hands_to      可选
    boundary      可选

退出码：0 成功 / 1 可诊断失败 / 2 参数错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"
INDEX = SKILLS / "INDEX.md"
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
MARKER = "<!-- NEW-SKILL-ROW -->"

SKILL_TMPL = """---
name: {name}
description: >
  {description}
domain: {domain}
stage: {stage}
version: 0.1.0
---

# {name}

## 1. 用途

消费 **{consumes}** → 产出 **{produces}** → 在 stage {stage} 被调用。

**什么时候用**：

- <填：什么情况下该加载本技能>

**什么时候别用**：

- <填：什么情况下不该用；边界：{boundary}>

## 2. CRITICAL

1. <填：做了就会坏的规则，最多 6 条>

## 3. 工作流

1. `--dry-run` 看计划
2. 去掉 `--dry-run` 执行
3. 检查产物，确认判据
4. 不满足就停下，写 `defects/D-xxx`

## 4. 示例

**用户：** "<真实请求>"

**动作：**

```powershell
python skills/{name}/scripts/<script>.py --config _scratch/spec.json --out _scratch/out --json
```

**结果：** <产出 + 可验证结论>

## 5. 故障排除

| 症状 | 根因 | 处置 |
|---|---|---|
| <报错片段> | <…> | <…> |

## 6. 按需加载

| 文件 | 何时读 |
|---|---|
| `references/format.md` | 写 spec JSON、需要字段语义时 |
"""

SCRIPT_TMPL = '''#!/usr/bin/env python3
"""{name} — <一句话说清做什么>。

    python skills/{name}/scripts/main.py --config <json> --out <dir>
    python skills/{name}/scripts/main.py --config <json> --dry-run

退出码：0 成功 / 1 可诊断失败 / 2 参数错误
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="{name}")
    ap.add_argument("--config", required=True, help="输入 JSON")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"FAIL config 不存在: {{cfg_path}}", file=sys.stderr)
        return 2
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    out = Path(args.out)

    plan = {{"config": str(cfg_path), "out": str(out), "keys": sorted(cfg)}}
    if args.dry_run:
        print(json.dumps({{**plan, "dry_run": True}}, ensure_ascii=False, indent=2))
        return 0

    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {{out / 'result.json'}}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
'''


def main() -> int:
    ap = argparse.ArgumentParser(description="create a skill skeleton")
    ap.add_argument("--config", required=True, help="skill spec JSON")
    ap.add_argument("--out", required=True, help="(unused; kept for CLI contract)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"FAIL config 不存在: {cfg_path}", file=sys.stderr)
        return 2
    spec = json.loads(cfg_path.read_text(encoding="utf-8-sig"))

    name = (spec.get("name") or "").strip()
    desc = (spec.get("description") or "").strip()
    if not name or not desc:
        print("FAIL spec 必须有 name 与 description", file=sys.stderr)
        return 2
    if not NAME_RE.match(name):
        print(f"FAIL invalid name {name!r}：必须形如 <pack>-<thing>（小写 kebab）", file=sys.stderr)
        return 2
    if len(desc) < 20:
        print("FAIL description 少于 20 字符", file=sys.stderr)
        return 2

    target = SKILLS / name
    if target.exists():
        print(f"FAIL target exists: {target}", file=sys.stderr)
        return 1
    if not INDEX.is_file() or MARKER not in INDEX.read_text(encoding="utf-8-sig"):
        print(f"FAIL INDEX marker missing: {MARKER} in {INDEX}", file=sys.stderr)
        return 1

    domain = spec.get("domain") or name.split("-")[0]
    stage = str(spec.get("stage", "X"))
    files = {
        "SKILL.md": SKILL_TMPL.format(
            name=name, description=desc, domain=domain, stage=stage,
            consumes=spec.get("consumes", "<输入>"),
            produces=spec.get("produces", "<产出>"),
            boundary=spec.get("boundary", "<边界>"),
        ),
        "scripts/main.py": SCRIPT_TMPL.format(name=name),
        "references/format.md": f"# {name} — 输入格式\n\n<填：--config 的字段语义与最小示例>\n",
        "assets/.gitkeep": "",
    }
    row = (f"| `{name}` | {domain} | {stage} | `main.py` | "
           f"{spec.get('consumes', '<输入>')} | {spec.get('produces', '<产出>')} | "
           f"{spec.get('hands_to', 'core-lead-agent')} | "
           f"{spec.get('boundary', '<边界>')} |")

    plan = {"target": str(target), "files": sorted(files), "index_row": row}
    if args.dry_run:
        print(json.dumps({**plan, "dry_run": True}, ensure_ascii=False, indent=2))
        return 0

    for rel, content in files.items():
        p = target / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    text = INDEX.read_text(encoding="utf-8-sig")
    text = text.replace(MARKER, row + "\n\n" + MARKER, 1)
    INDEX.write_text(text, encoding="utf-8")

    if args.json:
        print(json.dumps({**plan, "created": True}, ensure_ascii=False, indent=2))
    else:
        print(f"created {target}")
        print("next: fill SKILL.md body, then run tools/skills_wire.py --apply")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
