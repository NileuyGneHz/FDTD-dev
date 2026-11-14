# claim_audit 判定规则

## 六条规则与理由

### R1 列必须齐

`metric` / `value_paper` / `value_checked` / `match` / `source` 五列缺一即 problem。

**理由**：缺 `source` 就无法复查；缺 `match` 就无法判断是否核过。这两列是核对表的骨架。

### R2 `match` 只允许三个值

`yes` / `no` / `unverified`。

**理由**：多一个值（如 `partial`、`likely`）就意味着「可以含糊」。三值制强制二选一：
要么核到了，要么没核到。

### R3 `match=yes` 必须能在 PDF 内找到 `value_checked`

**理由**：这是本技能存在的全部意义。如果 `yes` 不需要证据，那这张表就是自欺欺人。

**容错**：只额外尝试去掉空格与千分位逗号（`1,240` → `1240`）。
不做四舍五入（`92.7` ≠ `92.70` 在某些语境下不等价，但这里数字字符串必须一致）、
不做单位换算（`435 ps` 不能自动匹配 `0.435 ns`）。

### R4 占位符不算已核

`NOT OBTAINED` / `NOT FOUND` / `n/a` / `未获取` / `未找到` 出现在 `value_checked`
而 `match=yes` → problem。

**理由**：这是最容易发生的造假形式——不是故意骗人，而是改表时把 `unverified`
顺手改成了 `yes`，忘了把占位符换掉。检测它成本极低，收益极高。

### R5 `match=no` 必须有 `note`

**理由**：`no` 是最有价值的一行——它记录了「论文说 A，我核到 B」。
但如果不写差异说明，半年后没人知道差在哪、为什么差。

### R6 `unverified` 不判错

**理由**：`unverified` 表示「我知道这里没核」。这是诚实状态，不是缺陷。
如果对 `unverified` 判错，人会倾向于把它改成 `yes` 来「通过检查」——那正好相反。

## 不检查的东西

| 不查 | 为什么 |
|---|---|
| `value_paper` 是否与论文一致 | 那是 `lit-quote-verify` 的活（引文级） |
| 不同包的同一指标能否横比 | 口径不同，本工作区明确不做跨论文横比 |
| `note` 的措辞质量 | 判不了，靠人 |
| CSV 的排序与格式 | 与核对无关 |

## 典型 problem 与修法

| problem | 修法 |
|---|---|
| `match=yes 但 PDF 内找不到 value_checked='435 ps'` | PDF 写的是 `≈ 435 ps`，把 `value_checked` 改成 `435 ps`（不带 ≈），或改成 `unverified` |
| `value_checked 是占位符: 'NOT OBTAINED'` | `match` 改 `unverified` |
| `match=no 但没有 note` | 补：`论文 92.5%，我核到 92.7%，差异来自预印本 vs 正式版` |
| `match=yes 但包内无 PDF` | 该包所有 `yes` 改 `unverified` |
