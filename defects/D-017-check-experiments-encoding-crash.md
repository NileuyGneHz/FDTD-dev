# D-017：`check_experiments.py` 在非 UTF-8 stdout 上崩，且崩法与 D-010 完全同源

**状态**：`resolved`（2026-11-11）

## 根因

`tools/check_experiments.py` 的 `check_plans()` 首行直接 `print("\n-- 实验台账")`，
字符串含中文。**进程 stdout 编码不是 UTF-8 时**，这一行抛
`UnicodeEncodeError: 'charmap' codec can't encode characters`，进程 exit 1。

关键危害：**门禁崩掉与「检出违规」同为 exit 1**，调用方无法区分
「实验台账有问题」和「脚本自己炸了」。这与 D-010 是同一个病灶。

### 为什么 D-010 的修复没覆盖到

D-010（2026-11-10）只修了 `inspect_fsp.py`，并在结论里写「其余 6 个脚本的正常与错误路径
都是 ASCII 输出，**没有**给全部脚本套 `reconfigure`」。

这个判断在当时是对的，但 `check_experiments.py` 是 **2026-11-09 之后新增的门禁**，
不在那 6 个的扫描范围内——**新增脚本没继承已有的编码约定**。

## 修复

在 `tools/check_experiments.py` 头部补上与 `check_results_layout.py` L35–39 同款的守卫：

```python
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
```

## 验证

```powershell
$PY="C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

# 修前：exit 1 + UnicodeEncodeError（charmap 不能编码「实验台账」）
# 修后：
$env:PYTHONIOENCODING=''
& $PY tools/check_experiments.py
# 期望：exit 0，末行 ALL GREEN（未落账项按 WARN 处理）

& $PY tools/check_experiments.py --self-test
# 期望：self-test PASS：2 正例通过，5 负例全部被抓
```

实测（2026-11-11）：默认编码下 exit 0，`[D1] OK 65/65 个实验全部落账`，
`--self-test` PASS。

## 影响面

`tools/check_experiments.py` 一份。不涉及技能、不涉及 `.fsp`。

## 遗留

**同类风险仍在**：`tools/` 下 12 个脚本里，`check_git_limits.py` / `check_scripts.py` /
`check_skill_contract.py` / `skills-doctor.py` / `skills-wire.py` / `migrate_classes_to_packages.py`
**没有** `reconfigure` 守卫。目前它们输出以 ASCII 为主所以没炸，但任何一次「加一句中文提示」
都可能重演本缺陷。

建议（未执行）：抽一个 `tools/_bootstrap.py` 统一做编码守卫，12 个脚本各 import 一行。
这属于批次 B 之外的重构，需单独评估。
