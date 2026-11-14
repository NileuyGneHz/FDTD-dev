---
name: lit-claim-audit
description: 核对论文包 results/claims.csv 的每一行：match 取值是否合法、match=yes 的值能否在 PDF 内找到、match=no 是否写了差异说明、value_checked 是否是占位符冒充已核。当交付前要确认数字核对表没有造假、或换机器后要重新验证时使用。触发词：数字核对、claims.csv、核数、claim audit。
domain: lit
stage: 3
version: 1.0.0
---

# lit-claim-audit

## 1. 用途

消费 **`results/claims.csv` + `paper/*.pdf`** →
产出 **逐行核对报告（yes/no/unverified 统计 + problem 清单）** → 在 stage 3 被调用。

**什么时候用**：

- 交付前确认「数字核对表」没有造假。
- 换机器 / 换版本后重新验证。
- 怀疑有人把 `unverified` 偷偷改成 `yes` 却没真核。

**什么时候别用**：

- 抽引文（那是 `lit-quote-verify` 的活）。
- 做跨论文横比（口径不同，本工作区不做）。

## 2. CRITICAL

1. **本技能只读**。报告写进 `--out`，不改 CSV、不改 PDF。
2. **`match=yes` 必须有 PDF 支撑**。包内无 PDF 时，`yes` 一律判 problem。
3. **占位符不算已核**。`NOT OBTAINED` / `未获取` / `n/a` 出现在 `value_checked` 而 `match=yes`，直接判错。
4. **`match=no` 必须有 `note`**，否则判 problem。
5. **数字匹配做最小容错**：只额外尝试去掉空格与千分位逗号，不做四舍五入、不做单位换算。
6. **`unverified` 不判错**。它表示「我知道没核」，这是诚实，不是缺陷。

## 3. 工作流

1. 写 spec：`{"packages": ["cases/P04_...", "cases/P06_..."]}`
2. `--dry-run` 确认包列表。
3. 执行，看 `problems total`。
4. 逐条修 problem：
   - `match=yes` 但找不到 → 改 `unverified`，或回 PDF 重取准确写法
   - 占位符冒充 yes → 改 `unverified`
   - `no` 缺 note → 补差异说明
5. 复跑直到 `problems total: 0`。

## 4. 示例

```powershell
'{"packages":["cases/P06_DiffractiveMultimodal_Cheng2024"]}' | Out-File _scratch/ca.json -Encoding utf8

python skills/lit-claim-audit/scripts/claim_audit.py --config _scratch/ca.json --out _scratch/ca_out --json
```

**结果：** `_scratch/ca_out/claim_audit.json`，`problems total: 0` 且
`stats={"yes":8,"no":0,"unverified":0}` 表示 P06 的 8 个数字全部真实核过。

## 5. 故障排除

| 症状 | 根因 | 处置 |
|---|---|---|
| `match=yes 但 PDF 内找不到` | 数字写法不同（如 `435 ps` vs `≈435 ps`） | 把 `value_checked` 改成 PDF 里的原样写法 |
| `value_checked 是占位符` | 从 `unverified` 抄成了 `yes` | 改回 `unverified` |
| `match=no 但没有 note` | 漏写差异说明 | 补 `note`：差多少、怀疑哪一层 |
| `match=yes 但包内无 PDF` | 无正文包（P05/P07）写了 yes | 全部改 `unverified` |
| `缺列` | CSV 表头不全 | 按 `library/schemas/claims.md` 补齐 |

## 6. 按需加载

| 文件 | 何时读 |
|---|---|
| `references/audit-rules.md` | 需要理解每条判定规则的取舍、或想扩展检查项时 |
