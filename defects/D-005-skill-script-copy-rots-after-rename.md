# D-005 技能内的脚本副本随目录改名腐烂成死脚本
**状态**：`resolved`（技能内副本改为转发壳，见正文验证段）
## 根因

`packages/` → `cases/` 的改名（TASK-002）只改了 `tools/check_packages.py`，
`skills/fdtd-package-workspace/scripts/check_packages.py` 作为同一脚本的**旧副本**没跟上：

```python
# 副本（死）
PKG_ROOT = WS_ROOT / "packages"        # WS_ROOT = <skill>/  →  <skill>/packages 永不存在
SUBDIRS = ["paper", "fsp", "scripts", "results", "notes"]   # 旧目录名

# 唯一实现（活）
PKG_ROOT = WS_ROOT / "cases"           # WS_ROOT = 仓库根
SUBDIRS = ["paper", "model", "results", "notes"]
```

后果：技能文档教人「`python .../scripts/check_packages.py`」，实跑直接
`[ERROR] 找不到 packages 目录`。而 SKILL.md 里本来就有一条「副本必须同轮同步并 diff」
的告警——说明这个坑复发过，只是靠人记不管用。

同类腐烂：5 个 md/json 里写着 `packages/`、`PACKAGES.md`、`fsp/`、`scripts/spec_<id>.json`
（spec 实际在 `config/`）。

## 修复

1. 技能内副本**改为转发壳**（`runpy.run_path` 执行 `tools/check_packages.py`，退出码透传），
   使「一份实现、两个入口」成立，杜绝再次漂移。
2. SKILL.md 步骤 6 从「复制脚本并改路径常量」改为「只引用，不要复制」，并写明事故。
3. 结构树与 6 个文档的路径全部订正：`cases/`、`INDEX.md`、`model/`、`config/`。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# ① 壳能跑通且参数透传
"$PY" skills/fdtd-package-workspace/scripts/check_packages.py --pkg P01
#   期望: [OK] P01_Absorber_042 ... 汇总: ERROR=0 WARN=0

# ② 退出码透传（--strict 有 WARN 时应为 1；P01 无 WARN 故为 0）
"$PY" skills/fdtd-package-workspace/scripts/check_packages.py --pkg P01 --strict; echo $?

# ③ 无残留旧路径
grep -rn "packages/\|packages\\\\\|PACKAGES.md" --include=*.md --include=*.json skills/ \
  | grep -v "原 \`packages/PACKAGES.md\` 已迁到这里"
#   期望: 无输出
```

## 影响面

`skills/fdtd-package-workspace`（自检入口）、`fdtd-lumerical-phase-retrieval`、
`fdtd-paper-parameter-extraction`（spec 路径）、`fdtd-lumerical-unitcell-simulation/assets/report_template.md`。
判据侧未变：`tools/check_packages.py` 的检查项与原设计一致。
