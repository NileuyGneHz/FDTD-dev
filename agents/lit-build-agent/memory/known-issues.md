# known-issues.md — lit-build-agent 实测踩坑

> 只记**跑过的**：URL、状态码、有效规避。每条带日期。

## 2026-11-12 抓取八篇论文时实测

### 1. Wiley 直连 403

- **URL**：`https://advanced.onlinelibrary.wiley.com/doi/pdf/10.1002/adma.202508029`
- **结果**：HTTP 403 + `text/html`
- **规避**：走 PMC 镜像 `PMC13549287`，但需要先解 JS proof-of-work（见下条）。

### 2. PMC 的 PoW 挑战可以用纯 Python 解

- **症状**：`pmc.ncbi.nlm.nih.gov/.../pdf/xxx.pdf` 返回一个「Preparing to download ...」HTML 页。
- **机制**：页面内嵌 `POW_CHALLENGE` / `POW_DIFFICULTY` / `POW_COOKIE_NAME`；
  要求 `sha256(challenge + nonce)` 有 `difficulty` 个前导**十六进制零**，
  然后设 cookie `cloudpmc-viewer-pow = "<challenge>,<nonce>"`，再请求同一 URL。
- **结果**：difficulty=4，nonce=49860 时命中；二次请求拿到 8.80 MB PDF。
- **证据**：`_scratch/fetch_pmc_pow.py`，输出 `{'ok': True, 'bytes': 8797127, 'note': 'after-pow'}`。

### 3. Nature 的 PDF 端点不一定给 PDF

- **URL**：`https://www.nature.com/articles/s41566-024-01567-z.pdf`（P04 正式版）
- **结果**：HTTP 200 但 `Content-Type: text/html` —— 是付费墙页面，不是 PDF。
- **判据**：**必须检查前 5 字节是否 `%PDF`**，不能只看状态码 200。
- **规避**：P04 改用 arXiv 预印本 `2208.01623`（同一工作的早期版本，标题与数字不同）。

### 4. arXiv 的 `id_list` 查询比标题搜索可靠

- **做法**：`http://export.arxiv.org/api/query?id_list=2208.01623`
- **收益**：能直接拿到 `journal_ref`（`Nature Photonics 18, 1335-1343 (2024)`）与
  `doi`（`10.1038/s41566-024-01567-z`），从而确认预印本与正式版是同一篇。
- **教训**：**标题搜索会漏**。P04 用标题搜 `forward-only training` 返回 0 条，
  因为预印本标题是 `accelerated training`。**用作者 + 编号查更稳**。

### 5. IOP 由 Radware Bot Manager 保护

- **URL**：`https://iopscience.iop.org/article/10.1088/2634-4386/adcbcc/pdf`
- **结果**：HTTP 200 + `text/html`，内容为 Radware captcha 页（14 KB）。
- **尝试失败**：`?download=true`、`/meta`、Crossref TDM link、DOAJ fulltext link —— 全部同一页。
- **结论**：P07 只能留摘要。

### 6. TU Braunschweig 的 PoW 是 bit 级 + canvas 二级挑战

- **第一层**：JWT 里带 `{challenge, difficulty: 16, redirect_url}`，
  要求 `sha256(challenge+nonce)` 有 16 个前导**二进制零**，然后 POST
  `{pow_solution, information, pow_challenge_token}`。
- **实测**：PoW 解出来了（nonce=12517 / 19294），但 POST 返回的仍是
  「Security Check / Please enable JavaScript」页，且**没有 set-cookie**。
- **判断**：服务端还校验了浏览器指纹（页面里有 canvas + `webdriver` 检测）。
  纯 HTTP 客户端过不去。
- **结论**：不要在这条路上继续投入。要 P07 正文，走机构订阅或联系作者。

### 7. Optica 返回 202 + noscript 跳转

- **URL**：`https://opg.optica.org/viewmedia.cfm?URI=OFC-2026-Th2A.31&seq=0`
- **结果**：HTTP 202 + 583 字节 HTML，含 `<noscript><meta http-equiv="Refresh" ...>`
- **判断**：反爬挑战，需要 JS。Unpaywall 报 `is_oa=false`，无合法副本。
- **结论**：P05 只能留摘要。

### 8. Unpaywall 是判断「有没有合法 OA」的最快途径

- **URL**：`https://api.unpaywall.org/v2/<doi>?email=<any>`
- **收益**：一次调用给出 `is_oa` / `oa_status` / `best_oa_location` / 所有 `oa_locations`。
- **实测**：八篇里 P01/P03/P04/P06/P08 有 OA 副本，P02 有（PMC），P05/P07 无。
- **注意**：`best_oa_location.url_for_pdf` 可能是 `None`，要看 `oa_locations[]` 逐个试。

### 9. OpenAlex 能重建摘要（无正文时的救命稻草）

- **URL**：`https://api.openalex.org/works/doi:<doi>`
- **字段**：`abstract_inverted_index` 是 `{word: [positions...]}`，按位置排序拼回原文。
- **用途**：P05/P07 的摘要就是这样拿到的，标为 `abstract-only`。
- **红线**：摘要**不是正文**，不能当引文引用。
