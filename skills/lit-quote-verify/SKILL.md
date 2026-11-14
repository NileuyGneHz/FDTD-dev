---
name: lit-quote-verify
description: 验证论文包 README §2 的每条引用块是否能在对应 PDF 内 grep 到原句，输出 found/missed 清单。当归档新论文包、或怀疑引文被手打改动、或换机器后要确认引文仍然成立时使用。触发词：引文核验、grep 校验、quote verify、引用块。
domain: lit
stage: 2
version: 1.0.0
---

# lit-quote-verify

## 1. 用途

消费 **包目录（`README.md` §2 引用块 + `paper/*.pdf`）** →
产出 **每条引文的 found / missed 报告** → 在 stage 2 被调用。

**什么时候用**：

- 归档新论文包、写完 §2 之后。
- 怀疑引文被手打改动（复制粘贴时丢了连字符或特殊字符）。
- 换机器后确认引文仍然成立。

**什么时候别用**：

- 判断引文选得好不好（那是人的判断）。
- 验证数字（那是 `lit-claim-audit` 的活）。

## 2. CRITICAL

1. **本技能只读，不修改任何文件**。报告写进 `--out`。
2. **无 PDF 的包不算失败**，标 `no-pdf` 并报告，不要静默跳过。
3. **归一化只做两件事**：空白折叠 + 跨行连字符（`- ` → `-`）。不做同义词替换、不做模糊匹配。
4. **逐级截短必须报告** `matched_chars`：如果只在前 30 字符命中，说明后半句可能对不上，要人看。
5. **本技能会读 PDF**，依赖 `pypdf`。缺依赖时明确报错，不许静默返回全部命中。

## 3. 工作流

1. 写 spec JSON：`{"packages": ["cases/P03_...", ...], "head_chars": 70}`
2. `--dry-run` 确认包列表。
3. 执行，看报告：`missed total` 必须为 0。
4. 对 `matched_chars` 明显小于引文长度的条目，人工回 PDF 确认后半句。
5. 有 missed → 回 PDF 重新复制原句，不要改 PDF、不要改检测逻辑。

## 4. 示例

```powershell
# spec
'{"packages":["cases/P03_MatrixMultiplication_Zhou2022"],"head_chars":70}' | Out-File _scratch/qv.json -Encoding utf8

python skills/lit-quote-verify/scripts/quote_verify.py --config _scratch/qv.json --out _scratch/qv_out --json
```

**结果：** `_scratch/qv_out/quote_verify.json`，`missed total: 0` 表示 §2 所有引文都能在 PDF 内找到。

## 5. 故障排除

| 症状 | 根因 | 处置 |
|---|---|---|
| `pypdf 不可用` | 未装或不在 PYTHONPATH | 把 pypdf 装到一个仓库外的依赖目录（见 `iterations/iter-1-foundation/runtime-contract.md` 的「PDF 库」一行），并设 `PYTHONPATH` 指向它 |
| 大量 missed 但引文看着没错 | PDF 文本层缺词间空格（如 P02） | 用 `norm_loose` 路径已覆盖；仍失败就缩短引文到可 grep 的片段 |
| `no-pdf` 状态 | 包里没有 PDF（如 P05/P07） | 正常。这类包的 §2 应标 `abstract-only` |
| `matched_chars` 很小 | 引文后半句与 PDF 不符 | 人工回 PDF 重取原句 |

## 6. 按需加载

| 文件 | 何时读 |
|---|---|
| `references/normalisation.md` | 需要理解归一化规则、或想扩展匹配策略时 |
