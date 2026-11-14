# LD-001 — PMC 的 PDF 端点返回 PoW 挑战页，不是 PDF

| 项 | 值 |
|---|---|
| 发现日期 | 2026-11-12 |
| 影响 | P02 的正文获取（Wiley 直连 403 后改走 PMC） |
| 状态 | fixed（已解出 PoW） |
| 根因 | PMC 的 cloudpmc-viewer 对 PDF 下载加了 JS proof-of-work 门禁 |

## 症状

```text
GET https://pmc.ncbi.nlm.nih.gov/articles/PMC13549287/pdf/ADMA-38-e08029.pdf
-> HTTP 200, Content-Type: text/html, 1817 bytes
   <title>Preparing to download ...</title>
```

用浏览器 UA + `Accept: application/pdf` 也一样。

## 排查过程

1. 以为是 UA 被拦 → 换完整浏览器头（Accept / Accept-Language / Referer）→ 仍是 HTML。
2. 抓下 HTML 看内容 → 里面是 `POW_CHALLENGE` / `POW_DIFFICULTY` / `POW_COOKIE_NAME`，
   并 `import` 一个 `pow-*.js`。
3. 下载并 gunzip 该 JS → 逻辑是：
   ```js
   for (nonce = 0; ; nonce++) {
     hash = sha256(challenge + nonce).hex();
     if (hash.startsWith("0".repeat(difficulty))) return nonce;
   }
   setCookie(POW_COOKIE_NAME, challenge + "," + nonce);
   location.reload();
   ```
4. 即：**difficulty 是十六进制前导零个数**，不是 bit。

## 根因

PMC 用 proof-of-work 挡自动化下载。它不是验证码（不需要人看），
而是一道计算题：解出来就能过。

## 修复 / 规避

用纯 Python 复现同一算法：

```python
nonce = 0
target = "0" * difficulty
while True:
    if hashlib.sha256(f"{challenge}{nonce}".encode()).hexdigest().startswith(target):
        break
    nonce += 1
# 设 cookie: cloudpmc-viewer-pow = f"{challenge},{nonce}"，然后重试同一 URL
```

脚本：`_scratch/fetch_pmc_pow.py`（一次性，不进库）。

## 验证

```text
[P02] P02_pmc_ADMA-38-e08029.pdf
    pow solved: difficulty=4 nonce=49860 hash=0000696a02e5...
    {'ok': True, 'bytes': 8797127, 'note': 'after-pow'}
```

pypdf 打开确认 23 页，首段为
`REVIEW www.advmat.de IntegratedNeuromorphicPhotonicComputingforAI Acceleration:...`。

## 副作用（已记录）

PMC 版 PDF 的文本层**缺词间空格**，长句连写。这会影响 grep 引文，
已在 `cases/P02_*/README.md` §2 与 `results/quotes.md` 注明。

## 相关

- `cases/P02_NeuromorphicPhotonic_Wang2025/`
- `agents/lit-build-agent/memory/known-issues.md` 第 2 条

