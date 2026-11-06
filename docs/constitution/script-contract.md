# 脚本契约

> 一句话：**包只存数据，技能才是唯一的可执行入口。**

## 1. 三种归宿

| 类型 | 放哪 | 判定 |
|---|---|---|
| 能力脚本 | `skills/<name>/scripts/` | 会被第二个课题用到，或本身就是流水线一环 |
| 模型脚本（`.lsf`） | 单元内 `model/` | 它是 `.fsp` 的可读源，必须同放 |
| 一次性脚本 | `_scratch/` | 只服务一次，不进包、不入库 |

**纯模块**（无 `__main__`）放 `library/py/`，被技能脚本 import，不直接运行。

## 2. CLI 契约

```
python skills/<name>/scripts/<script>.py --config <json> --out <dir> [--dry-run] [--json]
```

- 不假设工作目录：输入全来自 `--config`，输出全写 `--out`
- 退出码：`0` 成功 / `1` 可诊断失败 / `2` 参数错误
- 必须支持 `--dry-run`（只打印计划）与 `--json`（机器可读摘要）
- 不得写 `stuff/`、不得写包外、不得联网

## 3. `.lsf` 的统一入口

任何单元里的 `.lsf` 都由同一个技能入口执行：

```
python skills/fdtd-lumerical-headless/scripts/run_lsf.py --lsf <path> --config <json>
```

所以"任何脚本都能被技能调用"成立，而模型的可读源不必搬离工程。

## 4. 强制执行

```
python tools/check_scripts.py
```

扫描 `cases/*/scripts/` 与 `projects/*/scripts/`，出现任何 `.py` 即 FAIL，并指出该迁往哪个技能。
历史遗留写 `tools/check_scripts.allowlist`，**只能减不能增**。

## 5. 为什么

同一逻辑写两遍 → 修一处漏一处 → 两条曲线对不上 → 分不清是物理问题还是代码问题。
脚本归技能，等于把"这段逻辑只有一个实现"变成结构上不可违反的事实。
