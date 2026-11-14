# P01_PhotonicElectronicIC_Ning2024 — 光电协同到底卡在哪

> **主题轨**：A 综述框架 ｜ **阅读顺序**：第 2 篇
> 这是八篇里对「光电协同」梳理得最系统的一篇，也是**唯一一篇明确把两个稳健性痛点写进正文**的。
> 它不回避问题：有限控制分辨率 + 高精度 DAC/ADC 的功耗开销。

---

## §0 目标与验收

| 项 | 值 |
|---|---|
| **包 ID** | `P01` |
| **主题轨** | `A_review` |
| **任务状态** | 已归档 |
| **这篇为什么读** | 它把「模拟光计算的痛点」写成了可引用的话，而不是散落在各篇的讨论里 |
| **验收标准** | §2 的 4 条引文全部可在 PDF 内 grep 到；§4 的 4 个数字全部核对过 |
| **本次目标** | 拿到「DAC/ADC 开销」这条痛点的原文出处，能直接引用 |

---

## §1 论文

| 项 | 值 |
|---|---|
| 文件 | `paper/Ning2024_JLT.pdf` |
| 标题 | Photonic-Electronic Integrated Circuits for High-Performance Computing and AI Accelerators |
| 作者 / 年份 | Shupeng Ning, Hanqing Zhu, Chenghao Feng, ... David Z. Pan, Ray T. Chen, 2024 |
| 期刊 / DOI | Journal of Lightwave Technology 42(22), 7834-7859 (2024) / 10.1109/JLT.2024.3427716 |
| 本地版本 | **arXiv 预印本 v2**（IEEE 正式版付费墙） |
| 获取来源 | https://arxiv.org/pdf/2403.14806v2 （读取 2026-11-12） |
| 许可 | arXiv non-exclusive |
| 目标图 | Fig. 12（精度与 DAC/ADC 开销）、Fig. 7（WDM 架构） |

> **版本提醒**：本地是 arXiv 预印本，正文结构与 IEEE 正式版可能有差异（章节编号、
> 图号）。引用页码时以本 PDF 为准，并在引用处注明「arXiv v2」。

---

## §2 原文引论

> 全部为 PDF 内可 grep 的原句，保留原拼写（含 `ﬁ` 连字与 `- ` 断行）。

**① 两个稳健性痛点，一句话写全**（这是全篇最有价值的一句，直接可引用）：

> (2) Limited precision of inputs and outputs arises from the finite control resolution and the substantial overhead associated with high- precision DACs and ADCs.

[Sec. III-A, 非理想性讨论]

**② 综述的三大分析维度**（它把软硬件协同列为与硬件、架构并列的一等公民）：

> Additionally, we propose a comprehensive analysis of photonic AI from the per- spectives of hardware implementation, accelerator architecture, and software-hardware co-design.

[Abstract]

**③ 软硬件协同被当作独立的效率手段**（对找动手方向的人最重要）：

> Beyond improvements at the device level, another promising approach enhances hardware efficiency at the circuit level by software-hardware co-design approaches.

[Sec. V 引言]

**④ 章节分工自述**：

> Beyond a review from the device and circuit level, Sections IV and V provide a comprehensive analysis of recent photonic AI efforts from the perspectives of accelerator architectures and software- hardware co-design, respectively.

[Sec. I Introduction]

---

## §3 与 AI 痛点的对应

| 痛点 | 这篇做了什么 | 做到了吗 | 代价 / 没解决的 |
|---|---|---|---|
| 精度与稳健性 | **明确点出**有限控制分辨率 + DAC/ADC 开销，并列为两大稳健性挑战之一 | 是（识别层面） | 只给方向性缓解策略，没有给出「多少 bit 够用」的定量结论 |
| 训练（反向传播 / 梯度） | 讨论了光计算的训练路径，但不是主线 | 部分 | 原位训练的工程细节不如 P04/P06 具体 |
| 光电边界（IO 开销 / 谁做非线性） | 系统梳理了 E-O / O-E 转换的代价，并提出减少转换的架构 | 是 | 结论偏架构层，缺实测数据 |

**一句话**：这是**痛点词典**。后面读 P04/P06 时，你会反复回到这篇的这句话来对照：
「它解决了 DAC/ADC 开销吗？还是只是绕开了？」

---

## §4 数字核对

| 指标 | 论文值 | 我核到的 | 一致 | 出处 |
|---|---|---|---|---|
| 期刊卷期页 | 42(22), 7834-7859 | 42(22), 7834-7859 | yes | Crossref 元数据（PDF 为预印本，无卷期） |
| 稳健性挑战条数 | 2 类（器件非理想性 / 精度与非理想性） | 2 类 | yes | Sec. III-A |
| DAC/ADC 相关提及次数 | — | DAC ×23 / ADC ×25 | unverified | 全文 grep 计数，非论文自述数字 |
| 分析维度 | 3 个（硬件实现 / 加速器架构 / 软硬件协同） | 3 个 | yes | Abstract |

> **口径说明**：DAC/ADC 计数是我 grep 出来的，不是论文声称的数字，
> 只用于说明「这篇确实反复讨论这件事」，不可当作论文结论引用。

---

## §5 偏差与疑点

| 项 | 值 |
|---|---|
| 版本差异 | 本地 arXiv v2（2024-07-11），正式版 2024-11。章节号/图号可能不一致 |
| 口径差异 | 综述类，无统一实验口径；数字均为转述他人工作 |
| 我不确定的 | 「substantial overhead」的具体量级（多少 pJ/bit）本文是否给了数 |
| 待问作者 / 待查 | DAC/ADC 能耗的权威定量文献（可查 Walden 1999 / Murmann 综述） |
| 是否可引用 | 可引用（标注 arXiv v2） |

---

## §6 交接

| 项 | 值 |
|---|---|
| 归档日期 | 2026-11-12 |
| 读完日期 | 待读 |
| 下一步 | 读 Fig. 12，把「控制分辨率 → 有效位数 → 精度损失」这条链条画出来 |
| 与其他包的关系 | 为 P04/P06（它们怎么绕开 DAC/ADC）、P08（IO 开销何时反噬）提供问题定义 |
| 自测 | `notes/self-check-5q.md` |

---

## 文件清单

```text
P01_PhotonicElectronicIC_Ning2024/
├─ README.md      ← 本文件
├─ paper/         Ning2024_JLT.pdf（13.95 MB，arXiv v2）
├─ config/        paper.json
├─ notes/         reading-notes.md / self-check-5q.md
├─ results/       quotes.md / claims.csv
└─ model/         （空）
```
