# EXP-01 实验门禁本身必须能抓错

## 假设

门禁如果只检查「文件存在」，就无法区分「实验通过了」和「根本没做实验」。
本实验验证 `tools/check_experiments.py` 能抓住四类伪造/残缺记录。

## 输入

5 个合成记录（`--self-test` 在临时目录里构造，不污染 `experiments/`）：

| 用例 | 构造 | 期望 |
|---|---|---|
| `good` | 完整记录 + 负对照 + 可重跑命令 | 通过 |
| `verdict_fail` | `verdict: "fail"` | 被抓 |
| `empty_metrics` | `metrics: {}` | 被抓 |
| `no_negative_control` | `negative_control.failed: false` | 被抓 |
| `no_design` | 缺 `design.md` 的负对照段 | 被抓 |

## 负对照

上表后四行即负对照：它们**必须**被抓。若其中任何一个通过，说明门禁形同虚设，本实验判 `fail`。

## 判据

- 正例 1/1 通过；
- 负例 4/4 被抓，且报错信息指出具体原因（不是一句「不合法」）。

## 重跑命令

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" tools/check_experiments.py --self-test; echo "exit=$?"
```

期望：`self-test PASS：1 正例通过，4 负例全部被抓`，exit=0。
