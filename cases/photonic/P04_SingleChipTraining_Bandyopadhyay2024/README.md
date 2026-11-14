# P04_SingleChipTraining_Bandyopadhyay2024 — 在光子芯片上直接训练

> **主题轨**：B 训练瓶颈 ｜ **阅读顺序**：第 4 篇
> 这篇的意义不在准确率，而在**证明了「在光子芯片上直接训练」这条路走得通**。
> 但注意：本包拿到的是 arXiv 预印本，与你手上的正式版**标题和数字都不一样**——见 §5。

---

## §0 目标与验收

| 项 | 值 |
|---|---|
| **包 ID** | `P04` |
| **主题轨** | `B_training` |
| **任务状态** | 已归档（**版本存疑，见 §5**） |
| **这篇为什么读** | 首个「线性 + 非线性单片集成 + 原位训练」的完整演示，绕开光电反复转换 |
| **验收标准** | §2 的 4 条引文可在 PDF 内 grep 到；§4 的 5 个数字核对过；§5 的版本差异必须写清 |
| **本次目标** | 说清它到底做了什么、预印本与正式版差在哪、哪些数字可以引用 |

---

## §1 论文

| 项 | 值 |
|---|---|
| 文件 | `paper/Bandyopadhyay2024_arXiv.pdf` |
| 标题（正式版） | Single-chip photonic deep neural network with forward-only training |
| 标题（本地预印本） | Single chip photonic deep neural network with **accelerated** training |
| 作者 / 年份 | Saumil Bandyopadhyay, Alexander Sludds, Stefan Krastanov, ... Dirk Englund, 2024 |
| 期刊 / DOI | Nature Photonics 18(12), 1335-1343 (2024) / 10.1038/s41566-024-01567-z |
| 本地版本 | **arXiv 预印本**（arXiv:2208.01623，2022 首发） |
| 获取来源 | https://arxiv.org/pdf/2208.01623 （读取 2026-11-12） |
| 许可 | arXiv non-exclusive（Nature Photonics 正式版付费） |
| 目标图 | Fig. 1（FICONN 架构）、Fig. 3（训练曲线）、Table I（性能对比） |

---

## §2 原文引论

> 全部为 PDF 内可 grep 的原句。注意原文用 `ﬁ` 连字与 `eﬃcient` 等特殊字符，复制时保留。

**① 核心突破：单片集成线性 + 非线性**（这是它区别于前人的关键）：

> However, demonstrating systems that co-integrate both linear and nonlinear processing units in a single chip remains a central challenge.

[Introduction]

**② 架构三要素**：

> Here we introduce such a system in a scalable photonic integrated circuit (PIC), enabled by several key advances: (i) high-bandwidth and low-power programmable nonlin- ear optical function units (NOFUs); (ii) coherent matrix multiplication units (CMXUs); and (iii) in situ training with optical acceleration.

[Abstract]

**③ 关键数字（预印本口径：92.7%）**：

> Using in situ training on a vowel classiﬁcation task, the FICONN achieves 92.7% accuracy on a test set, which is identical to the accuracy obtained on a digital computer with the same number of weights.

[Abstract]

**④ 时延（预印本口径：435 ps）**：

> For the FICONN, τlatency is dom- inated by the optical propagation delay, which we esti- mate from the PIC subsystems (as described in the SI) as 3τCMXU + 2τNOFU +τTX to U1 +τU3 to RX +τU-turn≈ 435 ps.

[Discussion]

**⑤ 作者对前人工作的限定（这条解释了「forward-only」的动机）**：

> Previous work on in situ train- ing has focused on developing optical implementations of "backpropagation," which is the standard for training elec- tronic DNNs [28, 39]. However, these approaches train only the linear layers of a photonic system and require evaluat- ing gradients of activation functions on a

[Discussion]

---

## §3 与 AI 痛点的对应

| 痛点 | 这篇做了什么 | 做到了吗 | 代价 / 没解决的 |
|---|---|---|---|
| 精度与稳健性 | 训练与推理都在光域，减少 E-O/O-E 往返 | 部分 | 仍用热光移相器（9.8 pJ/OP），能效不占优 |
| 训练（反向传播 / 梯度） | **原位训练**，且不局限于线性层——非线性单元也参与 | 是 | 6 分类元音任务，规模小；未证明能扩展到深层大网络 |
| 光电边界（IO 开销 / 谁做非线性） | 把非线性也搬进光域（NOFU），这是最大胆的一步 | 是 | NOFU 的功耗与带宽是新的瓶颈 |

**一句话**：它证明了「单片全光训练」**可行**，但没证明「划算」。
9.8 pJ/OP 的热光移相器能耗，比它想替代的电子方案并不低——这正是 P08 讨论 IO 开销的起点。

---

## §4 数字核对

| 指标 | 论文值 | 我核到的 | 一致 | 出处 |
|---|---|---|---|---|
| 测试准确率（预印本） | 92.7% | 92.7% | yes | p.1 Abstract |
| 测试准确率（正式版，用户提供） | 92.5% | **未获取正式版** | unverified | 用户口述，待核 |
| 推理时延（预印本） | ≈435 ps | 435 ps | yes | Discussion, τlatency 公式 |
| 推理时延（正式版，用户提供） | 410 ps | **未获取正式版** | unverified | 用户口述，待核 |
| 网络规模 | 3 层 / 12 NOFU / 3 CMXU | 3 层 / 12 NOFU / 3 CMXU | yes | Abstract |
| 能效（本工作，热光） | 11.7 pJ/OP（Etotal,est） | 11.7 pJ/OP | yes | Table I |
| 吞吐 | 0.53 TOPS（N=6） | 0.53 TOPS | yes | Table I |

---

## §5 偏差与疑点

> **本节是本包最重要的部分。** 你给的信息与本机拿到的 PDF 不一致，必须记录，不许抹平。

| 项 | 值 |
|---|---|
| **版本差异（标题）** | 用户：`with forward-only training`；本地 arXiv：`with accelerated training` |
| **版本差异（准确率）** | 用户：92.5%；本地 arXiv：92.7% |
| **版本差异（时延）** | 用户：410 ps；本地 arXiv：435 ps |
| **可能原因** | arXiv:2208.01623 是 2022 年首发、2024 年正式发表；正式版在评审中可能改了术语（forward-only）并重算了数字（92.5% / 410 ps）。**这是正常现象，不是谁错了** |
| 口径差异 | 元音六分类任务；「与数字计算机同权重量精度相同」是论文自述 |
| 我不确定的 | 正式版的 forward-only 是否意味着**完全去掉反向传播**（预印本里仍出现 backpropagation 一词，见 §2 第 ⑤ 条） |
| 待问作者 / 待查 | 正式版 PDF；forward-only 的确切定义 |
| 是否可引用 | **仅可引预印本口径**，并注明 arXiv:2208.01623。引用 92.5%/410 ps 前必须拿到正式版 |

**下一步验证**（可判定）：

1. 通过机构订阅或作者主页拿到 Nature Photonics 正式版 PDF。
2. 核对正式版 Abstract 的准确率数字与 Discussion 的时延数字。
3. 若确认 92.5%/410 ps，回填 §4 并把 `match` 从 `unverified` 改成 `yes`；
   同时把本包 `paper.json` 的 `pdf.version` 改为 `published`。

---

## §6 交接

| 项 | 值 |
|---|---|
| 归档日期 | 2026-11-12 |
| 读完日期 | 待读 |
| 下一步 | 拿正式版 PDF（见 §5 验证步骤）；读 Table I 的横向对比，看热光 vs MEMS 的能效差 |
| 与其他包的关系 | P05 是它的「反向传播派」对照；P06 是「衍射派」对照；P08 接着讨论 IO 开销 |
| 自测 | `notes/self-check-5q.md` |

---

## 文件清单

```text
P04_SingleChipTraining_Bandyopadhyay2024/
├─ README.md      ← 本文件
├─ paper/         Bandyopadhyay2024_arXiv.pdf（15.55 MB，arXiv 预印本）
├─ config/        paper.json（含 version_note）
├─ notes/         reading-notes.md / self-check-5q.md
├─ results/       quotes.md / claims.csv
└─ model/         （空）
```
