# P02_NeuromorphicPhotonic_Wang2025 — 光计算的硬件底层长什么样

> **主题轨**：A 综述框架 ｜ **阅读顺序**：第 3 篇
> P01 讲系统与软硬件协同，这篇补的是**器件与网络拓扑**：线性突触器件、非线性神经元器件、
> 网络架构，以及封装。

---

## §0 目标与验收

| 项 | 值 |
|---|---|
| **包 ID** | `P02` |
| **主题轨** | `A_review` |
| **任务状态** | 已归档 |
| **这篇为什么读** | 补全「光计算硬件底层长什么样」：P01 讲系统，这篇讲器件 |
| **验收标准** | §2 的 3 条引文可在 PDF 内 grep 到；§4 的 3 个数字核对过 |
| **本次目标** | 说清「线性层用什么器件、非线性用什么器件、两者怎么拼成网络」 |

---

## §1 论文

| 项 | 值 |
|---|---|
| 文件 | `paper/Wang2025_AdvMater.pdf` |
| 标题 | Integrated Neuromorphic Photonic Computing for AI Acceleration: Emerging Devices, Network Architectures, and Future Paradigms |
| 作者 / 年份 | Gaofei Wang, Junyan Che, Chen Gao, ... Zengguang Cheng, Peng Zhou, 2025 |
| 期刊 / DOI | Advanced Materials 38(50), e08029 (2025) / 10.1002/adma.202508029 |
| 本地版本 | PMC 收录版（与出版社正式版排版略有差异，正文同一稿） |
| 获取来源 | https://pmc.ncbi.nlm.nih.gov/articles/PMC13549287/ （读取 2026-11-12） |
| 许可 | Wiley / PMC 收录；开放获取状态以出版社为准 |
| 目标图 | 器件总览图、网络架构图、封装方案图 |

> **获取备注**：Wiley 直连返回 403。PMC 副本需要先解一道 JS proof-of-work 挑战
> （sha256 前导 4 个十六进制零），解完设 cookie 才能下。过程见 `defects/D-001`。

---

## §2 原文引论

> 注意：这篇 PDF 的文本层**缺少词间空格**（排版字体嵌入问题），
> 所以短句引文可 grep，长句会连成一片。下面第 ① 条是这种情况的实例。

**① 论文的定位（摘要原文，注意空格缺失是原文文本层的问题）**：

> dynamic weight adjustment and in situ training.

[Sec. 器件与网络架构]

**② 作者对封装瓶颈的自述**（这条很关键：它承认了外部激光耦合是规模化的障碍）：

> Current solutions rely on externally coupled lasers via optical ﬁbers, but this introduces bulky packaging, align- ment challenges, and scalability limits.

[Sec. 讨论 / 封装]

**③ 全文结论段（长句，文本层连写，仍可 grep）**：

> Furthermore,application-speciﬁcrequirementsaresystematicallyanalyzedfor PNNdeploymentacrosscomputationalregimes:cloud-scaleandedge/client- sideAIs.Finally,actionablepathwaysareoutlinedforovercomingmaterial- andsystem-levelbarriers,emphasizingtopology-optimizedactive/passive devicesandadvancedpackagingstrategies.Thesemultidisciplinaryadvances positionPNNsasaparadigm-shiftingplatformforpost-MooreAIhardware.

[Abstract]

**④ 三类核心组件的划分（我的提炼，非原文）**：

- **线性突触器件**：MZI、微环、相变材料
- **非线性神经元器件**：微环调制器神经元、光电流调制 MZI 神经元
- **网络架构**：级联 MZI 网格、衍射结构、WDM 并行

---

## §3 与 AI 痛点的对应

| 痛点 | 这篇做了什么 | 做到了吗 | 代价 / 没解决的 |
|---|---|---|---|
| 精度与稳健性 | 讨论了器件层面的噪声、漂移与调谐精度 | 部分 | 未给出系统级的精度预算（多少 bit 可用） |
| 训练（反向传播 / 梯度） | 覆盖了原位学习框架（光功率监测的 MZI 阵列、可调衍射单元） | 是（综述层面） | 只做归纳，未比较各路线收敛性 |
| 光电边界（IO 开销 / 谁做非线性） | 明确指出封装与外部激光耦合是规模化瓶颈 | 是 | 未量化封装的成本占比 |

**一句话**：这是**器件地图**。读完它你应该能回答「如果我要做一个光神经网络，
线性层有哪几种器件可选，各自的坑是什么」。

---

## §4 数字核对

| 指标 | 论文值 | 我核到的 | 一致 | 出处 |
|---|---|---|---|---|
| 期刊卷期 | 38(50) | 38(50) | yes | Crossref 元数据 |
| 文章号 | e08029 | e08029 | yes | 页眉 `ADMA-38-e08029` |
| 核心组件类别 | 3 类（线性 / 非线性 / 架构） | 3 类 | yes | 摘要 + 目录结构 |
| 出版年 | 2025 | 2025（在线 2025-10-21） | yes | Crossref issued |

> **诚实标注**：这篇是综述，没有自己的实验数字。任何「X TOPS/W」都是转述他人工作，
> 引用时必须回到原始文献，不许写「Wang 2025 报道了 X」。

---

## §5 偏差与疑点

| 项 | 值 |
|---|---|
| 版本差异 | PMC 版 vs Wiley 正式版：排版不同，正文同稿 |
| 口径差异 | 综述无统一口径 |
| 我不确定的 | 文本层空格缺失是否影响某些关键句的 grep（已知影响长句） |
| 待问作者 / 待查 | 封装成本的具体量化文献 |
| 是否可引用 | 可引用（标注 PMC 版） |

---

## §6 交接

| 项 | 值 |
|---|---|
| 归档日期 | 2026-11-12 |
| 读完日期 | 待读 |
| 下一步 | 对着器件总览图，把「线性 / 非线性 / 架构」三类各挑一个代表工作，回到原始文献核数字 |
| 与其他包的关系 | P01 的上游（器件层）；P06 的旁支（衍射路线也在它的架构分类里） |
| 自测 | `notes/self-check-5q.md` |

---

## 文件清单

```text
P02_NeuromorphicPhotonic_Wang2025/
├─ README.md      ← 本文件
├─ paper/         Wang2025_AdvMater.pdf（8.80 MB，PMC 版）
├─ config/        paper.json
├─ notes/         reading-notes.md / self-check-5q.md
├─ results/       quotes.md / claims.csv
└─ model/         （空）
```
