# lit-paper-intake — spec.json 格式

## 必填

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | `P01` 起，两位数字 |
| `slug` | string | 目录名，`^P\d{2}_[A-Za-z0-9]+_[A-Za-z]+\d{4}$`，且以 `id + "_"` 开头 |
| `track` | string | `A_review` / `B_training` / `C_hybrid` |
| `title` | string | 正式版标题 |
| `doi` | string | 不带 `https://doi.org/` 前缀 |
| `pdf.present` | bool | 是否有正文 PDF |

## 强烈建议

| 字段 | 类型 | 说明 |
|---|---|---|
| `authors` | array | 第一作者必须完整；其余可截断 |
| `venue` / `volume` / `issue` / `pages` / `year` | — | 出处；Crossref 可查 |
| `title_local` | string | 本地 PDF 标题与正式版不同时必填 |
| `topics` | array | 小写 kebab 标签 |
| `reading_order` | int | 推荐阅读顺序，从 1 起 |
| `version_note` | string | 预印本与正式版的差异摘要 |

## pdf 段

| 字段 | 必填 | 说明 |
|---|---|---|
| `present` | ✅ | `true` 必须有 `file` + `source_path`（且文件存在） |
| `file` | 当 present=true | `paper/` 下的 ASCII 文件名，建议 `<Author><Year>_<Journal>.pdf` |
| `version` | ○ | `published` / `arxiv-preprint` / `abstract-only` / `publisher-accepted` |
| `source_url` | ○ | 实际下载地址 |
| `retrieved` | ○ | `YYYY-MM-DD` |
| `license` | ○ | 许可说明 |
| `missing_reason` | 当 present=false | **必填**：卡在哪、试过什么 |
| `source_path` | 当 present=true | 本地待复制的 PDF 路径（只用于复制，不写进 paper.json） |

## 无正文时的示例

```json
{
  "id": "P10",
  "slug": "P10_PaywalledPaper_Smith2026",
  "track": "C_hybrid",
  "title": "A paywalled paper",
  "doi": "10.1000/paywalled",
  "year": 2026,
  "abstract_source": "OpenAlex abstract_inverted_index",
  "pdf": {
    "present": false,
    "file": null,
    "version": "abstract-only",
    "source_url": "https://doi.org/10.1000/paywalled",
    "retrieved": "2026-11-12",
    "license": "publisher copyright",
    "missing_reason": "publisher returns 403; Unpaywall is_oa=false; no legal OA copy"
  }
}
```

## 生成物

```text
cases/<slug>/
├─ paper/      （PDF 或只有 .gitkeep）
├─ config/     paper.json
├─ notes/      .gitkeep
├─ results/    .gitkeep
└─ model/      .gitkeep
```

`paper.json` 不含 `source_path`（那是复制来源，不是元数据）。
