# cases/ — 只读知识资产

## 职责

存放 **10 个已完成并学透的复现包**（P01–P10）。它们是"参照系"：
新课题遇到同类结构时，先来这里找已知答案。

## 状态：只读

- **不新增**单元（新研究去 `projects/`）。
- **不改**内容。发现错误 → 开 `defects/D-xxx`，在 `notes/` 记，**不在原地改**。
- 唯一的例外是补 `notes/` 里的说明与 `README.md` 的偏差诊断——那是"当时的判断"，允许补记。

## 结构

每个单元严格遵循 `docs/constitution/archive-contract.md`：

```
P0N_<Topic>_<AuthorYear>/
├─ README.md    §0 目标与验收 §1 论文 §2 参数 §3 偏差诊断
├─ paper/       论文 PDF + SI
├─ model/       .fsp + .lsf + spec_<id>.json
├─ config/      sweep_*.json
├─ results/
└─ notes/
```

## 约束

1. **`INDEX.md` 是唯一索引**。新增单元必须登记一行：ID / 主题 / 论文 / 关键结论 / 可复用点。
2. **论文与 `.fsp` 同包**，不跨目录引用。
3. **包内无 `.py`**（`tools/check_scripts.py` 会拦）。
4. 复用这里的结构时，**复制 `_TEMPLATE` 到 `projects/`**，不要直接在 `cases/` 里改。

## 读的顺序

`INDEX.md` → 目标单元的 `README.md` → 需要时再翻 `results/` 与 `notes/`。
没读完 README 就打开 `.fsp`，等于放弃这个单元最有价值的判断记录。
