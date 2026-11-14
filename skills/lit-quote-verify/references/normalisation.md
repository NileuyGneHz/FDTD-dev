# 归一化规则

## 做两件事

```python
def norm(s):
    s = s.replace("\u00ad", "")      # 去掉软连字符
    s = re.sub(r"-\s+", "-", s)      # 跨行连字符："compre- hensive" -> "comprehensive"
    return " ".join(s.split())       # 空白折叠
```

## 为什么只做这两件

PDF 提取的文本与「论文上看到的」有两类系统性差异：

1. **换行断词**：`compre-` + 换行 + `hensive`。PDF 提取后变成 `compre- hensive`。
   去掉 `- ` 就还原了。
2. **软连字符**：某些字体嵌入会产生 U+00AD，肉眼不可见但会让 grep 失败。

除这两类，**不做任何其它归一化**。理由是：一旦开始做同义词替换、大小写折叠、
模糊匹配，就会出现「引文其实对不上但检测说对上了」——那比漏检更糟。

## 宽松模式（norm_loose）

当 PDF 文本层缺词间空格时（如 P02 的 PMC 版），普通 `norm` 会失败。
`norm_loose` 只保留 `[a-z0-9]`，即完全去掉空格与标点：

```python
def norm_loose(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())
```

代价：会掩盖大小写与标点差异。所以只在严格模式失败后才用，并且结果里
`matched_chars` 会显示实际命中的前缀长度——**短前缀命中要人看**。

## 逐级截短

```python
for n in (len(q), head_chars, 60, 50, 40, 30):
    if norm(q[:n]) in text:
        return n   # 命中的字符数
```

**为什么截短**：论文里的长句在 PDF 里常被图表、脚注打断，整句 grep 会失败。
截短到可 grep 的片段是务实做法。

**为什么报告 matched_chars**：如果一条 200 字的引文只在前 30 字符命中，
说明后半句与 PDF 不符——可能手打了、可能跨了版本。这时需要人回 PDF 确认，
不能因为「found=True」就放心。

## 不算失败的三种情况

| 状态 | 含义 | 处置 |
|---|---|---|
| `no-pdf` | 包里没有 PDF | 正常（P05/P07）。§2 应标 `abstract-only` |
| `no-readme` | 包还没写 README | 归档流程没走完 |
| `missing-dir` | 路径写错了 | 改 spec 里的包路径 |
