# 光学滤波与光学矩阵运算：文献进展

> 基于 `library/paper_lib/` 里 12 篇已归档 PDF，所有数字均从 PDF 内 grep 得到（可复核）。
> 编制日期：2026-11-12

---

# 第一部分：光学滤波的进展

## 1. 一句话判断

**光学滤波的进展方向不是"滤得更好"，而是"把整个 4f 系统压成一片"。**

三条演进线：

| 代际 | 形态 | 代表 | 代价 |
|---|---|---|---|
| 第一代 | 透镜 + 光阑（4f 系统） | 经典傅里叶光学 | 体积大、需对准 |
| 第二代 | 超表面替代掩模/透镜 | PNAS 2019、Nanophotonics 2020 | 仍需光路 |
| 第三代 | **单片超表面，去掉 4f** | Nanophotonics 2020 单片微分器 | 功能单一、不可调 |

---

## 2. 第一代：4f 系统仍是基准

**分数阶傅里叶变换**（`10_Fractional Fourier transforms...pdf`，JOSA A 1993）

这篇 1993 年的老论文值得归档，因为它给出了**4f 系统的连续可调版本**：在透镜之间移动掩模，
可以得到 0 到 1 之间的任意分数阶傅里叶变换。**这比"只做整数阶 FFT"灵活得多。**

**为什么重要**：如果你的滤波任务需要在"空间域"和"频域"之间找一个中间态（比如局部滤波），
分数阶傅里叶变换就是那个旋钮。这是纯光学实现，不需要数字计算。

---

## 3. 第二代：超表面做边缘检测（2019–2020 的两个代表作）

### 3.1 高效率介质超表面（PNAS 2019）

`05_Optical edge detection based on high-efficiency dielectric metasurface.pdf`

**关键数字**（PDF 内可 grep）：

> The optical efficiency of our metasur- face is defined as η = PLCP + PRCP PINPUT , which can reach around **90%** in our experiments.

**突破点**：之前的等离激元方案效率很低（吸收损耗大）。这篇用**介质**（玻璃基底内激光直写）
把效率做到 ~90%。

**机制**：利用几何相位（PB 相位），对 LCP / RCP 两个圆偏振分量施加不同响应，
两者干涉后形成"边缘增强"的传递函数。

### 3.2 量子边缘检测（Sci. Adv. 2020）

`07_Metasurface enabled quantum edge detection.pdf`

**新意**：把边缘检测用在**纠缠光子**上，而不是经典光。

**为什么值得看**：它证明了超表面滤波在**单光子级别**仍然有效。这对极弱信号探测有意义——
正好对上"微弱信号"这个主题。

---

## 4. 第三代：去掉 4f 系统（这是真正的进展）

### 4.1 单片超表面微分器（Nanophotonics 2020）

`09_Monolithic metasurface spatial differentiator...pdf`

**关键数字**（PDF 内可 grep）：

> our experimental setup is free of the 4F system, which means that the system volume along the optical axis can be reduced by **50%**

**这是整个领域最重要的一步**：不需要两个透镜 + 一个掩模，**一片超表面就完成微分**。

**代价**：功能固定（只能做一阶微分），不可重构。

### 4.2 Metapinhole：连透镜都不要了（arXiv 2025）

`Metapinhole_PlanarFourierOptics_2025.pdf`

**原文摘要**（PDF 内可 grep）：

> ...ar invariance across the entire spatial Fourier space enables tunable band-pass filtering in reflection. This lens-free approach provides a compact, alignment-insensitive solution for spatial filtering in electromagnetic regimes where conventional lenses or pinholes are impractical or costly

**它做了什么**：用**平面结构**替代"透镜 + 小孔"这个组合，实现傅里叶域滤波。
**不需要透镜，也不需要小孔**，且对对准不敏感。

**这是 2025 年的最新进展**，代表"平面化"这条线的极限形态。

---

## 5. 光学滤波的核心权衡（没变过）

| 参数 | 变大时 | 变小时 |
|---|---|---|
| 孔径 D | 截止频率高 → 保留细节多，但滤不干净 | 滤得狠，但分辨率掉 |
| 系统长度 | 焦距长 → 频谱分辨率高 | 短 → 紧凑但分辨率低 |

**这个权衡是衍射极限决定的，不是工艺问题。** 三代技术都在同一个约束下做文章：
第一代接受它，第二代缩小体积，第三代去掉整个系统但牺牲可调性。

---

## 6. 对你（黄老师项目）的直接意义

| 发现 | 对你的意义 |
|---|---|
| 单片超表面可去掉 4f | 如果你要做空间滤波，**不需要搭光路**，一片器件即可 |
| 介质超表面效率 ~90% | 损耗可接受，不再是瓶颈 |
| Metapinhole 免对准 | 降低实验门槛 |
| 分数阶傅里叶变换可调 | 提供了"连续调节"的思路 |

**但注意**：这 6 篇全部是**空间域**（图像）。你的六分量系统是**时间序列**。
数学同构，物理载体不同——你要找的是"色散 + 时间门"，不是"透镜 + 光阑"。

---

# 第二部分：光学矩阵运算的前沿进展

## 7. 一句话判断

**光学矩阵运算已经跨过"能不能做"的阶段，进入"怎么规模化、怎么训练、怎么和电子协同"的阶段。**

三个明确的转折点：

| 转折 | 标志 | 时间 |
|---|---|---|
| 证明可行 | Hamerly PRX：理论可扩展到 N ≳ 10⁶ | 2019 |
| 证明够快 | Nature 11 TOPS 卷积加速器 | 2021 |
| 转向训练与协同 | MRR crossbar 片上反向传播、Lightening-Transformer | 2022–2024 |

---

## 8. 规模化的理论基础（PRX 2019）

`03_Large-Scale Optical Neural Networks Based on Photoelectric Multiplication.pdf`

**关键原话**（PDF 内可 grep）：

> ...based on coherent (homodyne) detection that is fast, low power, compact, and readily scalable to large (N ≳ **10⁶**) numbers of neurons. In contrast to previous schemes, here we encode both the inputs and weights in optical s...

> ...can be operated at high (gigahertz) speeds and very low (**subattojoule**) energies per multiply and accumulate (MAC)

**为什么这篇重要**：它给出了**规模化的理论依据**——用相干（零差）探测，把输入和权重都编码在光域，
可以扩展到百万神经元量级，每次 MAC 能耗亚阿焦。

**"光电乘法"（photoelectric multiplication）** 这个词就是这篇提出的：
光做乘法，电做加法（探测器的电流求和天然是加法）。

---

## 9. 性能证明：11 TOPS 卷积加速器（Nature 2021）

`01_11 TOPS photonic convolutional accelerator...pdf`

**关键数字**（PDF 内可 grep）：

> ...demonstrate a universal optical vector convolutional accelerator operating beyond **10 Tera-FLOPS**, generating convolutions of images of **250,000 pixels** with **8-bit** resolution for **10 kernels** simultaneously

> ...achieving successful recognition of full 10 digits with 900 pixel handwritten digit images with **88% accuracy**

**三个关键点**：

1. **10 Tera-FLOPS** —— 这是实打实的算力，不是推算
2. **10 kernels 并行** —— 波长 + 时间 + 空间三维复用
3. **8-bit 分辨率** —— 与 P01 说的"ADC 只有 8 bit"正好对上

**但注意 88% 的准确率**：这是 MNIST 十分类，900 张图。**准确率不是这篇的卖点，吞吐才是。**

---

## 10. 转向训练：MRR crossbar（2024）

`MicroringCrossbar_Ohno2022.pdf`

**关键原话**（PDF 内可 grep）：

> ...the in-situ training of artificial neural networks using photonic accelerators remains challenging due to the difficulty of direct on-chip backpropagation on a photonic chip. In this work, we propose a silicon microring resonator (MRR) optical crossbar array with a **symmetric structure** that allows for simple on-chip backpropagation

**关键数字**：
- 4×4 电路（SOI 平台）
- 推理准确率 **93.3%**（Iris 分类）
- 用**模拟的片上反向传播**训练后，准确率 **91.1%**

**这篇的价值**：它点出了"训练难"的根因——**片上反向传播难做**，
并给出解法：**对称结构**让前向和反向可以用同一套硬件。

**诚实标注**：训练是**模拟的**（simulated on-chip backpropagation），不是实验实现的。
这一点很重要，别读成"已经实现片上训练"。

---

## 11. 转向系统协同：Lightening-Transformer（HPCA 2024）

`04_Lightening-Transformer...pdf`

**这是唯一一篇体系结构会议（HPCA）的论文**，其他都是物理/光学期刊。

**意义**：光学矩阵运算开始进入**计算机体系结构**的视野——不再只是"物理学家做器件"，
而是"系统架构师考虑怎么把它集成进处理器"。

**主题**：Transformer 加速。这是 2024 年最热的 AI 工作负载。

---

## 12. 最新形态：光子 Tensor Core（2026）

`PhotonicTensorCore_MVM_2026.pdf`

**关键数字**（PDF 内可 grep）：

> ...high **2 Peta-operations-per second** throughputs enabled by 10's of picosecond-short delays from optoelectronics

> ...delivers a total **0.5-2 Peta operations per second (POPS/s)** throughput ... for ~25...

表格里的对比（PDF 内可 grep）：

| 指标 | 本文 | 对比 |
|---|---|---|
| 吞吐 (POPS/s) | 0.5 (~2) | ~16 / 0.26 / 1.26 |
| 功耗 | 81 W | <2 W / 70 W / 400 W |
| 效率 (TOPS/J) | **25** | ~103 / 3 / 4 |

**注意**：这个表格里本文的效率（25 TOPS/J）**不是最高的**（有一列是 103）。
引用时不能说"效率最高"，只能说"达到 25 TOPS/J"。

**技术路线**：WDM 并行 + 相变材料（PCM）做非易失权重。

---

## 13. 相变材料路线：可编程超表面波导（Nat. Commun. 2021）

`02_Programmable phase-change metasurfaces on waveguides...pdf`

**关键数字**（PDF 内可 grep）：

> ...switching the GST from aGST to cGST phase, the PMMC efficiently converts TE0 mode to TE1 mode, changing the mode purity from βTE0 > **80%** to βTE1 > **85%** over a broad bandwidth

> ...switching extinction ratio ... is ~**16 dB** or 4000%, which is more than 10-fold improvement compared to previously reported switch devices using GST

**意义**：用 GST（相变材料）做**非易失**权重。设置一次，断电后权重还在。
这解决了"光计算权重需要持续供电"的问题。

---

## 14. 三条技术路线的当前格局

| 路线 | 代表 | 现状 | 瓶颈 |
|---|---|---|---|
| **MZI 网格** | 早期 ONN | 成熟，精度高 | 热光调谐慢，损耗随规模增长 |
| **MRR 交叉阵列** | Ohno 2024 | 可片上训练（模拟） | 热漂移，需要闭环控制 |
| **WDM + PCM** | 11 TOPS、Tensor Core | 吞吐最高 | 需要多波长光源，PCM 写入慢 |

**共同趋势**：**从"纯光"转向"光电协同"**。没有一个方案试图把加法、非线性、存储都放在光域。

---

## 15. 前沿的三个未解问题

| 问题 | 现状 | 谁在做 |
|---|---|---|
| **片上训练** | 只有模拟验证（Ohno 91.1% 是 simulated） | 需要真正的原位反向传播 |
| **精度** | 普遍 4–8 bit | 受限于 DAC/ADC 与控制分辨率（P01 的痛点） |
| **规模化后的损耗** | 理论可到 10⁶，实测多在 10²–10³ | 需要新的低损耗材料与封装 |

---

## 16. 对黄老师项目的意义（诚实版）

| 发现 | 能迁移吗 |
|---|---|
| 光电乘法（光乘电加） | ✅ 概念可迁移：探测器天然做加法 |
| MRR 交叉阵列可片上训练 | ⚠️ 需要集成光子工艺，30 万做不了 |
| WDM 并行 | ✅ 概念可迁移：多波长可以并行处理 6 个通道 |
| PCM 非易失权重 | ❌ 与光纤传感平台不兼容 |
| 11 TOPS 的吞吐 | ❌ 你的信号带宽远低于此，用不上 |

**最实际的迁移点是"光电乘法"这个概念**：
如果她的六分量信号需要做矩阵投影，可以用"光域调制 + 探测器求和"实现一次模拟矩阵乘，
不需要集成光子芯片。

---

# 第三部分：两个主题的交叉

## 17. 滤波与矩阵运算其实是同一件事

**这是最重要的洞察**：

```
滤波 = 用传递函数 H(f) 乘频谱     → 对角矩阵
矩阵乘 = 用矩阵 H 乘向量           → 一般矩阵
```

**所以滤波器是"对角矩阵乘法"的特例。**

在光域里：
- 单点掩模（只改幅度/相位）→ 对角矩阵 → 滤波
- 干涉网络（MZI 网格）→ 一般矩阵 → 矩阵乘

**统一视角**：光学计算就是在实现各种矩阵，从对角（滤波）到满阵（神经网络）。

## 18. 这解释了为什么两条路线在融合

| 早期 | 现在 |
|---|---|
| 滤波用 4f（自由空间） | 用超表面（平面） |
| 矩阵乘用 MZI（集成） | 用 WDM + PCM（集成） |
| 两条线分开 | **都在往"平面化 + 可编程"走** |

`Metapinhole`（2025）和 `Photonic Tensor Core`（2026）虽然一个是滤波一个是矩阵乘，
但**技术手段在收敛**：都靠亚波长结构 + 波长/偏振复用。

---

## 19. 自测题

**Q1. 光学滤波三代演进的核心矛盾是什么？**
<details>答：体积/对准复杂度 vs 功能可调性。第一代 4f 可调但笨重，第二代超表面替代掩模但仍需光路，
第三代单片超表面去掉 4f 但功能固定。回读 §1</details>

**Q2. 介质超表面边缘检测的效率做到多少？为什么比等离激元好？**
<details>答：~90%。因为用介质（低损耗）替代金属（吸收损耗大），且是较厚的玻璃基结构，透射系数高。回读 §3.1</details>

**Q3. 单片超表面微分器省掉了什么？代价是什么？**
<details>答：省掉整个 4f 系统（两个透镜 + 掩模），轴向体积减少 50%。代价是功能固定，不可重构。回读 §4.1</details>

**Q4. Hamerly PRX 的"光电乘法"是什么意思？**
<details>答：光做乘法（把输入和权重都编码在光域，相干探测），电做加法（探测器电流天然求和）。
可扩展到 N ≳ 10⁶ 神经元，亚阿焦/MAC。回读 §8</details>

**Q5. MRR crossbar 的 91.1% 是实验还是模拟？**
<details>答：**模拟**（simulated on-chip backpropagation）。原文明确写 simulated。
不许读成"已实现片上训练"。这是这个领域最常见的误读。回读 §10</details>

**Q6. 为什么说"滤波是矩阵乘的特例"？**
<details>答：滤波 = 用对角矩阵（传递函数）乘频谱；矩阵乘 = 用一般矩阵乘向量。
对角矩阵是一般矩阵的特例。所以单点掩模（改幅度/相位）实现滤波，
干涉网络实现一般矩阵乘。回读 §17</details>

---

## 20. 文件位置

| 内容 | 路径 |
|---|---|
| 文献库索引 | `library/paper_lib/INDEX.md` |
| 光学滤波（6 篇） | `library/paper_lib/lens_filter/` |
| 矩阵运算（7 篇） | `library/paper_lib/matrix_compute/` |
| 校验脚本 | `_scratch/verify_lib.py` |
| 本文件 | `docs/paper-lib-review.md` |
