# experiments/ — 逐项实验台账

## 职责

每个**改动**都要有一个可重跑的实验，证明它「真的修对了」，而不只是「代码看起来对」。
本目录只放**结论**；原始数据（`.fsp` / `_p0.log` / `.npz`）留在 `_scratch/regress/<date>/EXP-NN/`。

## 结构

```
experiments/
├─ AGENTS.md                     本文件
└─ EXP-NN-<slug>/
   ├─ design.md                  开工前写：假设 / 输入 / 对照 / 负对照 / 判据 / 命令
   └─ result.json                跑完写：verdict + metrics + artifacts
```

## result.json 必备字段

```json
{
  "exp": "EXP-07",
  "verdict": "pass",
  "metrics": { "delta_peak_nm": 0.0, "cases_passed": "4/4" },
  "negative_control": { "failed": true, "detail": "错列名卡按预期 FAIL" },
  "artifacts": ["_scratch/regress/2026-11-09/EXP-07/out.txt"],
  "ran_at": "2026-11-09T16:00:00+08:00",
  "wall_s": 1.2
}
```

## 三条通过条件（缺一不可，由 `tools/check_experiments.py` 判）

1. **有数字**：`metrics` 非空，且至少一个可比较的量（Δ / 比值 / 退出码 / 耗时）。
2. **有负对照，且它确实失败**：`negative_control.failed == true`。
   只有正例的实验一律判 `fail` —— 否则无法区分「通过了」和「根本没检查」。
3. **可重跑**：`design.md` 里有一条命令（```bash 代码块），别人照抄能得到同一 verdict。

### 唯一例外：显式「未执行」

真的没跑（等机器、等前置技能、等裁决）时，**不许编数字**，按这个形状登记：

```json
{"exp": "EXP-27", "verdict": "fail", "defect": "D-009",
 "metrics": {"executed": false, "cost_not_spent": "12 min"},
 "negative_control": {"failed": false, "detail": "未执行：没有可跑的负对照"}}
```

判据是**同一个属性**（`metrics.executed is False`），不是代理指标：写了才豁免
「负对照 / 可重跑命令」两项；漏写就照常被抓（自测里的 `deferred_without_flag` 就是这条）。
`verdict=fail` 的意思是「这项没有结论」，不是「验失败了」——两者在报告里必须分开写。

## 纪律

- `design.md` **必须在动手改代码之前写**，判据不许事后改。
- 判据要能反向：例如「修好 `validate_spec`」的正确判据是「带 `PLACEHOLDER` 的旧 spec
  从 **通过** 变成 **失败**」，不是「新 spec 能过」。
- 报告里禁止写「已确认」「应该没问题」；只写数字与退出码。
- 实验失败不是丢人的事，**把失败写成 pass 才是**。
