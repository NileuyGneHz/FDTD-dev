# LD-002 — Optica (OFC 2026) 无合法开放副本，P05 只能留摘要

| 项 | 值 |
|---|---|
| 发现日期 | 2026-11-12 |
| 影响 | P05 正文获取 |
| 状态 | wontfix（合法渠道不可得） |
| 根因 | Optica 付费墙 + 反爬挑战；Unpaywall 确认无 OA 副本 |

## 症状

```text
GET https://opg.optica.org/viewmedia.cfm?URI=OFC-2026-Th2A.31&seq=0
-> HTTP 202, text/html, 583 bytes
   <noscript><meta http-equiv="Refresh" content="0;URL=/viewmedia.cfm?r=1&...">
GET https://opg.optica.org/abstract.cfm?URI=OFC-2026-Th2A.31
-> HTTP 202, 同类挑战页
```

## 排查过程

| # | 路线 | 结果 |
|---|---|---|
| 1 | `opg.optica.org/viewmedia.cfm` | 202 + 挑战页 |
| 2 | `opg.optica.org/abstract.cfm` | 202 + 挑战页 |
| 3 | `https://doi.org/10.1364/OFC.2026.Th2A.31` 重定向 | 落到同一个挑战页 |
| 4 | Unpaywall `api.unpaywall.org/v2/10.1364/ofc.2026.th2a.31` | `is_oa=false`, `oa_status=closed` |
| 5 | OpenAlex `works/doi:` | 只有一条 publisher 落地页，`locations[].pdf_url` 全为 null |
| 6 | arXiv 作者检索 `au:Asimopoulos_O` | 0 条 |
| 7 | arXiv 作者检索 `au:Kovaios_S` / `au:Tsakyridis_A` | 有别的论文，无本篇 |
| 8 | Wayback CDX | 本机 DNS 解析 `web.archive.org` 失败 |
| 9 | fatcat API / scholar.archive.org | 连接超时 |

## 根因

OFC 会议论文由 Optica 出版，非开放获取。2026 年的会议刚开，
既没有机构库副本，也没有 arXiv 预印本。

## 修复 / 规避

**不绕过。** 按 `docs/constitution/paper-case-contract.md` §8：

1. `paper.json` 写 `present=false` + `missing_reason`。
2. 摘要从 OpenAlex `abstract_inverted_index` 重建，标 `abstract_source`。
3. README §2 明确标 `abstract-only`，并单列「无法核实的内容」表。
4. `claims.csv` 全部 `unverified`。

## 验证

`python tools/check_packages.py --pkg P05` 无 ERROR；
`present=false` 与 `paper/` 为空一致；`missing_reason` 非空。

## 升级路径

1. 机构订阅（广西大学图书馆是否订阅 Optica？值得查）。
2. 直接邮件联系作者（TU Delft / WinPhos 组）。
3. 等 OFC 2026 论文集上线后重试。

## 相关

- `cases/P05_InSituBackprop_Asimopoulos2026/`
- `cases/INDEX.md` 的「缺失与待办」

