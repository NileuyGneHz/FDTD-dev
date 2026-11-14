# D-006 迁移脚本双份副本、路径全失效，且被 [K11] 静默豁免
**状态**：`resolved`（单一实现归位 tools/，技能内副本删除）
## 根因

`migrate_classes_to_packages.py` 在仓库里**有两份逐字节相同的副本**（D-005 是同一病灶的第二次发作）：

```
tools/migrate_classes_to_packages.py                          10551 B  09-30 15:54
skills/fdtd-package-workspace/scripts/migrate_classes_to_packages.py  10551 B  09-30 16:01
```

`diff` 无输出 → 两份完全一致，说明当初是「复制过去一份」而非「引用」。两份都停在
TASK-002 改名**之前**的结构上：

```python
PKG_ROOT = WS_ROOT / "packages"   # packages/ 已改名为 cases/ → 目标目录永不存在
pkg = PKG_ROOT / pkg_name / "fsp" # 包内 fsp/ 已改名为 model/
```

实测：`packages/` 目录不存在（`[ -d packages ]` → NO），`cases/metasurface/P01_Absorber_042/` 下是
`config/ model/ notes/ paper/ results/`。所以脚本一跑就在第一道 `if not PKG_ROOT.is_dir()`
处 `[ERROR] 包目录不存在` 退出 —— 它是**死代码**，但 INDEX.md 仍把它列为该技能的 scripts。

### 为什么门禁没抓到（更值得记的一条）

`[K11]` 要求「可执行入口」具备 `--out/--dry-run/--json`，实现里有一条早先加的豁免：

```python
if "argparse" not in src:      # 没有 argparse 的当纯模块跳过
    modules += 1; continue
```

而本脚本有 `if __name__ == "__main__":` 却**完全没有 argparse**（全靠模块级常量），
于是被当作「纯模块」静默跳过。同一条豁免还放过了 `check_packages.py`（转发壳，真 CLI）
与 `lumapi_common.py`（真模块）——三者的差别在「有没有 argparse」上根本区分不出来。

结论：**豁免条件与被豁免对象不是同一个属性**。这类门禁比没门禁更危险，因为它给出
「已检查」的错觉。2026-11-08 上一轮把 WARN 0 当成「修好了」，正是被它骗了。

## 修复

1. **单一实现留在 `tools/`**（协作章程 §命令行 本来就指定这里），补齐 CLI：

   ```bash
   python tools/migrate_classes_to_packages.py --src <课程目录> --out <工作区根> --dry-run
   ```

   `--src` / `--out` 在 `main()` 里重绑模块级根目录，`--dry-run` 通过 `ensure_dir()` /
   `copy2()` 两个助手实现「不建目录、不复制、不写报告」。
2. **路径对齐现结构**：`PKG_ROOT = WS_ROOT / "cases"`、`MODEL_SUBDIR = "model"`，
   报告文案与 `_rename_map.json` 路径同步。
3. **删除技能内副本**，`INDEX.md` / `SKILL.md` / `references/advanced-workflows.md`
   改为指向 `tools/`，不再复制。
4. 段号从 `1/3…4/4` 统一为 `1/4…4/4`（原来第一段写 `1/3`、最后一段写 `4/4`，自相矛盾）。
5. **附带修正 `[K15]`**：删掉副本后它反而 FAIL 了 —— 因为它把 INDEX 行里任何 `*.py` 都
   拼成 `<skill>/scripts/<basename>`，连 `tools/migrate_classes_to_packages.py` 这种
   仓库级引用也照拼。现改为区分两种引用：裸名或 `scripts/` 前缀 → 技能内核对；
   其它前缀 → 按仓库根核对。同一处误判会让「合法引用」和「幽灵入口」长得一样，
   必须分开，否则下次真幽灵出现时人会以为又是误报。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# ① 已无第二份副本
ls skills/fdtd-package-workspace/scripts/
#   期望: check_packages.py  lumapi_common.py   （不再有 migrate_*）

# ② CLI 存在且可解析
"$PY" tools/migrate_classes_to_packages.py --help
#   期望: usage ... [--src SRC] [--out OUT] [--dry-run]

# ③ dry-run 不写盘（对真实源目录跑，6GB 视频也不会被复制）
"$PY" tools/migrate_classes_to_packages.py --dry-run | tail -3
#   期望: 完成：论文 9 / fsp 40 / lsf 17 / 视频 0
ls -l _migration_report.md        # 期望: No such file（dry-run 未写报告）

# ④ 技能侧不再声明这个脚本
grep -rn "migrate_classes_to_packages" skills/ | grep -v "_scratch"
#   期望: 只剩「它在 tools/ 里」这类指引，没有 scripts/ 路径

# ⑤ [K15] 两种引用各留一个阴性对照（恢复后必须转 OK 12 处）
mv tools/migrate_classes_to_packages.py tools/_m.bak
"$PY" tools/check_skill_contract.py | grep K15
#   期望: FAIL ... → tools/migrate_classes_to_packages.py（仓库级引用）
mv tools/_m.bak tools/migrate_classes_to_packages.py
```

## 影响面

`tools/migrate_classes_to_packages.py`（唯一实现，新增 3 个参数）、
`skills/fdtd-package-workspace`（少一个脚本、INDEX 与两处文档改指 `tools/`）。
**不涉及任何仿真判据**：该脚本只做文件复制，不产出 R/T/A。

## 遗留

`[K11]` 的豁免条件本身没改（改成「有 `__main__` 但无 argparse 就 WARN」会同时误伤
转发壳与纯模块）。真正的判据应是「脚本是否声明了可调用入口」，这需要一个比字符串匹配
更硬的检测（例如 `ast` 解析 `argparse` 构造或 `sys.argv` 使用），留作下一步。
