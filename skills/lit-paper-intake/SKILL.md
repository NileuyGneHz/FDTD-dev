---
name: lit-paper-intake
description: 为一个新论文包建骨架并写 config/paper.json，把 PDF 复制进 paper/ 并改名为 ASCII。当要把一篇新论文归档进 cases/、或从零建一个论文包时使用。触发词：论文归档、建包、paper.json、intake。
domain: lit
stage: 1
version: 1.0.0
---

# lit-paper-intake

## 1. 用途

消费 **一份 intake spec（JSON，含 DOI / 标题 / PDF 路径）** →
产出 **`cases/P0N_*/` 骨架 + `config/paper.json` + `paper/*.pdf`** → 在 stage 1 被调用。

**什么时候用**：

- 要把一篇新论文归档进 `cases/`。
- 要保证新包从第一天就满足目录与元数据契约。

**什么时候别用**：

- 只是想把 PDF 存起来（直接放 `_scratch/`）。
- 已有包要改元数据（直接改 `config/paper.json`，别重建）。

## 2. CRITICAL

1. **不覆盖已存在的包目录**。目标存在就 `exit 1`，绝不静默合并。
2. **`slug` 必须匹配 `^P\d{2}_[A-Za-z0-9]+_[A-Za-z]+\d{4}$`**，且以 `id` 开头。
3. **`pdf.present=false` 必须给 `missing_reason`**。拿不到就说拿不到，不许留空。
4. **PDF 文件名必须 ASCII**。中文文件名会让后续工具链（含 GPU 求解器）出错。
5. **本技能只建骨架与元数据**，不写 README、不抽引文。那两步交给下游技能。

## 3. 工作流

1. 写 spec JSON（字段见 `references/spec.md`）。
2. `--dry-run` 看计划：包路径、要建的子目录、PDF 复制去向。
3. 去掉 `--dry-run` 执行。
4. 检查 `config/paper.json` 的 `pdf` 段是否与实际文件一致。
5. `python tools/check_packages.py --pkg P0N`，直到只剩 INFO/WARN。
6. 填 `README.md` §0–§2，然后交给 `lit-quote-verify`。

## 4. 示例

```powershell
python skills/lit-paper-intake/scripts/paper_intake.py `
  --config _scratch/intake_P09.json --out _scratch --dry-run

python skills/lit-paper-intake/scripts/paper_intake.py `
  --config _scratch/intake_P09.json --out _scratch --json

python tools/check_packages.py --pkg P09
```

`_scratch/intake_P09.json`：

```json
{
  "id": "P09",
  "slug": "P09_ExamplePaper_Doe2026",
  "track": "B_training",
  "title": "An example photonic paper",
  "doi": "10.1000/example",
  "year": 2026,
  "pdf": {
    "present": true,
    "file": "Doe2026_Example.pdf",
    "version": "published",
    "source_url": "https://example.org/paper.pdf",
    "retrieved": "2026-11-12",
    "license": "CC BY 4.0",
    "source_path": "_scratch/pdf/downloaded.pdf"
  }
}
```

## 5. 故障排除

| 症状 | 根因 | 处置 |
|---|---|---|
| `slug 不合法` | 用了下划线或小写 | 改 `ShortName` 为 PascalCase，且不含下划线 |
| `目标已存在` | 包已建过 | 直接改 `config/paper.json`，别重建 |
| `source_path 不存在` | PDF 没下下来 | 先确认文件；拿不到就把 `present` 改 `false` 并写 `missing_reason` |
| `check_packages` 报 PDF 与 present 不一致 | 手工挪了 PDF | 同步改 `paper.json` 的 `file` 或 `present` |

## 6. 按需加载

| 文件 | 何时读 |
|---|---|
| `references/spec.md` | 写 intake spec、需要字段语义与完整示例时 |
