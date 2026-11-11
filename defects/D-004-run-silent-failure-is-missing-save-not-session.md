# D-004 「`run()` 必须在新会话」是误归因：真前提是 `save`
**状态**：`resolved`（归因订正为「缺 save」，见正文验证段）
## 根因

`fdtd-lumerical-headless` CRITICAL #1 曾断言「直接在建模会话里 `run()` 会静默失效——
不抛异常、立刻返回、什么都没算；必须 `save` → `close` → 新会话 `load` → `run`」。

现象是真的，**归因错了**。2026-11-08 三组对照（本机 v251）：

| 序列 | `layoutmode` | `_p0.log` | `getresult` | 耗时 |
|---|---|---|---|---|
| 建模 → `run()`（**未 save**） | 仍为 1 | **无** | `Can not find result 'T'` | 4.9 s |
| 建模 → `save` → `run()`（同会话） | 0 | 4181 B | 正常 | 3.2 s |
| `save` → `close` → 新会话 `load` → `run` | 0 | 4181 B | 正常 | 2.0 s |

后两行 **T_max 逐位相同**（`-0.016196939809399034`）、同为 `Completed 43 iterations`。
机制：`run()` 需要工程在磁盘上有落点才能写 `<工程名>_p0.log`；没有就不算，且不报错。
当时之所以「换新会话就好了」，是因为那个修法里**同时补了 `save`**。

代价：这条旧结论被写进 `fdtd-lumerical-session-control/references/session-contract.md` §3，
并以「本项目实测与 `lumopt` 冲突」为由，把 L1 的 **C4（同 session 迭代）** 判成不可行。

## 修复

- `fdtd-lumerical-headless/SKILL.md` CRITICAL #1 重写为「`run` 前必须 `save`」，并附三组对照表。
- `fdtd-lumerical-session-control/SKILL.md`（CRITICAL #3 / 故障表 / 触发词）与
  `references/session-contract.md` §3 同步订正：两段式保留为默认（可复算/可重放），
  **同会话迭代允许**，每轮必须 `switchtolayout` → 改参 → `save` → `run` → 读回。
- 顺带记录第二种假轮次：`setnamed` 成功且 `getnamed` 回读一致，**不等于参数在指标因果链上**
  （source `x span` 0.30→0.45 µm，`T` 一位没动）。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" _scratch/regress/_gate/probe_session_rule.py      # S1 同会话 / S2 新会话
"$PY" _scratch/regress/_gate/probe_session_rule2.py     # S3 未 save → layoutmode 仍 1、无 _p0.log
"$PY" _scratch/regress/_gate/probe_session_rule3.py     # 逐位一致：T_max 相同、迭代数相同
"$PY" _scratch/regress/_gate/probe_c4b.py               # 同会话两轮改参：T 改变、迭代 43→68
```

期望：`equivalence.json` 中两条 `T_max` 相等；`c4b.json` 中两轮 `T` 数组不同、
`last_completed` 分别 43 与 68 iterations。

## 影响面

`fdtd-lumerical-session-control`（执行器）、`fdtd-lumerical-design-loop`（C4 闭环决策）、
`fdtd-package-workspace/scripts/lumapi_common.py::verify_and_run`（保留两段式，注释里的理由需改）。
未改动的是判据本身：`assert_ran` 三判据照旧有效。
