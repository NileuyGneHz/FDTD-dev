# LD-003 — IOP 的 Radware 保护与 TUBS 的二级指纹挑战，P07 只能留摘要

| 项 | 值 |
|---|---|
| 发现日期 | 2026-11-12 |
| 影响 | P07 正文获取 |
| 状态 | wontfix（纯 HTTP 客户端过不去） |
| 根因 | IOP 用 Radware Bot Manager；TUBS 机构库 PoW 之后还有 canvas 指纹校验 |

## 症状

### IOP 主站

```text
GET https://iopscience.iop.org/article/10.1088/2634-4386/adcbcc/pdf
-> HTTP 200, text/html, 14371 bytes
   <head><title>Radware Bot Manager Captcha</title>
```

正文页、`/meta`、`?download=true`、Crossref TDM link 全部返回同一页。

### TU Braunschweig 机构库

```text
GET https://leopard.tu-braunschweig.de/servlets/MCRFileNodeServlet/dbbs_derivate_00056437/neuromorphic_experiment_paper.pdf
-> 302 -> /pow-challenge?redirect_url=...
```

PoW 页里有 JWT：

```json
{"challenge":"cda7afbc...","difficulty":16,"redirect_url":"/servlets/...pdf",
 "attempt":0,"ip":"210.36.46.223","exp":1794475003}
```

## 排查过程

### 第一层：PoW（bit 级，与 PMC 不同）

页面 JS：

```js
for (nonce = 0; ; nonce++) {
  hash = sha256(challenge + nonce);      // Uint8Array
  if (countLeadingZeroBits(hash) >= difficulty) return nonce;
}
// countLeadingZeroBits：按字节数前导 0 位，非十六进制零
```

**difficulty=16 是 bit，不是 hex 位**。用 Python 实现后解得 nonce=12517 / 19294。

### 第二层：POST 回去

```text
POST /pow-challenge
  pow_solution=19294
  information={"userAgent":..., "webdriver":false, "headless":false, ...}
  pow_challenge_token=<jwt>
-> HTTP 200, text/html, 12015 bytes
   "Security Check / Please enable JavaScript to complete the security check."
   Set-Cookie: （无）
```

试了 `POST` 到 `/pow-challenge` 与 `POST` 到 `/pow-challenge?redirect_url=...`，
两者都返回同一个挑战页，且**不下发任何 cookie**。

### 判断

服务端还在校验浏览器指纹（页面 JS 里有 `canvas` 绘制、`navigator.webdriver`、
`navigator.plugins` 等采集项）。PoW 只是第一道门，指纹是第二道。
纯 `urllib` 客户端过不去。

## 根因

两层反自动化：计算题（可解）+ 浏览器指纹（不可在不启动真实浏览器的前提下伪造）。

## 修复 / 规避

**不绕过。** 按契约走「缺失」流程（同 D-002）：

1. `paper.json` 写 `present=false` + `missing_reason`。
2. 摘要从 OpenAlex 重建，标 `abstract-only`。
3. README §4 的 O(N) 那条**原样保留并标存疑**——摘要字面两边都是 O(N)，
   不许替它圆成「光计算更优」。

## 验证

`python tools/check_packages.py --pkg P07` 无 ERROR。

## 一个额外发现（值得记住）

P07 摘要写：

> the energy requirement scales with O ( N ) , while the energy requirement of
> conventional computers, as well as digital neuromorphic computing approaches,
> scales with O ( N )

**两边都是 O(N)**。这很可能是笔误（本意应为 O(N²) vs O(N)），
但在拿到正文前**不许替它解释**。二手转述常把它说成「光计算能效更优」，那是误读。
这条已写进 `cases/P07_*/results/quotes.md` 与 README §4。

## 升级路径

1. 机构订阅 IOP（NCE 是 CC BY，理论上可免费读，只是被反爬挡住）。
2. 用真实浏览器手动下载（人来做，不是 agent）。
3. 联系作者要 preprint。

## 相关

- `cases/P07_MixedMicroLED_Muller2025/`
- `agents/lit-build-agent/memory/known-issues.md` 第 5、6 条

