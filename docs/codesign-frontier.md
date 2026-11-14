# 极致光电协同（Co-design）：前沿在做什么

> 主要依据：`cases/P01_PhotonicElectronicIC_Ning2024/`（UT Austin，David Z. Pan + Ray T. Chen 组）
> 的 Section V 原文，加上 2023–2026 的可查文献线索。
> 编制日期：2026-11-14

---

## 0. 先纠正一个误解

**Co-design 不是「光和电一起设计」。**

如果只是「光做矩阵乘、电做非线性」，那叫分工，不叫 co-design。

**真正的 co-design 是：把光的物理缺陷当成算法的硬约束，在设计算法时就知道它要跑在什么硬件上。**

一句话区分：

| | hardware-agnostic | hardware-aware |
|---|---|---|
| 做法 | 先设计网络，再想办法塞进光硬件 | 先知道硬件有什么毛病，再设计网络 |
| 结果 | 精度掉、跑不动、或者要大量补偿 | 精度可预期、面积可承受 |
| 谁在做 | 早期工作 | 现在的顶级组 |

P01 原文（可 grep）：

> solely focusing on progress at the individual component level is insufficient to fully unlock the vast potential of photonic computing. Instead, a **holistic approach across multiple levels** is crucial for maximizing the performance of photonic AI systems, necessitating a **software-hardware co-design perspective**.

---

## 1. P01 给出的四轴框架（这是目前最系统的梳理）

Section V 的标题就是：

> V. TOWARD EFFICIENT PHOTONIC AI COMPUTING: **A SOFTWARE-HARDWARE CO-DESIGN PERSPECTIVE**

它把光计算的 co-design 拆成**四条轴**，每条都是「问题 → co-design 进展」的结构：

> In this section, we will delve into the key challenges of current photonic AI systems, specifically in terms of **area density, energy efficiency, noise robustness, and trainability**.

| 轴 | 光的问题 | co-design 的解法 |
|---|---|---|
| **A. 面积** | 光器件比晶体管大几百到几千倍，塞不下大矩阵 | 不做通用矩阵乘，做「受限矩阵」 |
| **B. 能耗** | DAC/ADC + 存储占 >80% 能耗 | 光学广播，减少转换次数 |
| **C. 精度/噪声** | ADC 只有 8 bit，模拟噪声累积 | 量化感知训练（QAT） |
| **D. 可训练性** | 片上拿不到梯度 | 无梯度优化 / 硬件友好的学习算法 |

**这四条轴是理解整个领域的坐标系。** 后面所有工作，基本都能归到其中一条或几条。

---

## 2. 四条轴的具体做法（附原文）

### 轴 A：面积 —— 不追求通用，改做「受限矩阵」

**问题原文**：

> The large spatial footprint of PICs is a significant concern, as optical devices typically have much larger physical dimensions compared to nanometer-scale transistors, spanning hundreds or thousands of square micrometers.

**解法原文**：

> researchers are exploring holistic **device-circuit-algorithm co-design** efforts in two promising directions: (1) **domain-specific photonic computing engines** to trade off between matrix expressivity and hardware efficiency; (2) **AI-assisted automatic compact PTC design**.

**具体案例（butterfly-style PTC）**：

> By parameter pruning, this architecture could be implemented using significantly **fewer MZIs with a scale factor of O(n log n)** rather than the **O(n²)** required by an MZI mesh for GEMM. This study experimentally showcases a measured accuracy of over **94%** on the MNIST

**这是最典型的 co-design**：
- 标准 MZI 网格做 N×N 矩阵需要 O(N²) 个 MZI → 面积爆炸
- butterfly 结构用 O(N log N) → 面积骤降
- **代价**：只能表示一类受限矩阵（蝶形分解能表示的）
- **收益**：面积降一个量级，精度还够用

**思想内核**：神经网络本来就过参数化，不需要满秩矩阵。所以「牺牲矩阵表达力换硬件效率」是划算的。

---

### 轴 B：能耗 —— 用「光学广播」减少转换

**问题原文**：

> This transition can occupy more than **80%** of the overall energy consumption [160], [171]

（注意：这里的 80% 是**数字-模拟转换 + 存储数据搬运**的合计，不是单指光电转换。这点很容易被二手转述说错。）

**解法原文**：

> **Optical broadcast** is a widely-used technique that enables spatial sharing of encoded signals [121], thereby saving on **DAC and E-O modulation costs**.

**什么意思**：一个信号编码一次，在空间上广播给多个计算单元复用。这样每个单元不用各自做一次 DAC。

**思想内核**：能耗瓶颈不在「算」，在「搬」。所以 co-design 的重点是**减少数据搬运次数**，而不是提高计算速度。

---

### 轴 C：精度 —— 把量化写进训练

**问题原文**：

> achieving this desired precision often exceeds the capabilities of affordable ADCs, typically within **8 bits** [177]. For instance, a 4-bit weight and 4-bit activation in a length-32 dot product computation would ideally yield an output precision of **13 bits**. The **5-bit overhead** underscores a notable difference between photonic computing and traditional low-precision arithmetic units

**解法原文**：

> previous efforts have often drawn inspiration from quantization, either employing **Quantization-aware Training (QAT)** [128], [146], [175], [179], [180]

**思想内核**：既然硬件只能给 8 bit，那就在**训练时**就模拟这个 8 bit，让网络学会在低精度下工作。这叫 QAT。

**这是最纯粹的 co-design**：硬件的缺陷直接进入损失函数。

---

### 轴 D：可训练性 —— 放弃反向传播

**问题原文**：

> Achieving self-learnability on neuromorphic photonic processors is indeed challenging due to various on-chip restrictions, such as **inaccessible gradients for control variables** and a **lack of full observability for in-situ light fields**.

**解法原文**：

> **Generic gradient-free optimization methods**, e.g., evolutionary algorithms and brute-force device tuning [28], [116], [189], have been used to optimize on-chip par...

**思想内核**：片上拿不到梯度（因为光场不可全观测、控制变量与梯度不对应），那就用**不需要梯度的方法**——进化算法、暴力搜索、或者物理感知的训练。

**这也是 P04 的 forward-only training 要解决的问题。**

---

## 3. 谁在做（可查的作者线）

我核对了手上 PDF 的作者列表，能确认这几条线：

### 线 1：UT Austin，David Z. Pan + Ray T. Chen 组

**这是最典型的「EDA 视角看光计算」的组。**

| 论文 | 作者 | 年份 |
|---|---|---|
| P01 综述 | Shupeng Ning, Hanqing Zhu, ... David Z. Pan, Ray T. Chen | 2024 |
| Lightening-Transformer | Hanqing Zhu, Jiaqi Gu, Hanrui Wang | HPCA 2024 |
| ENLighten | Hanqing Zhu, Zhican Zhou, Shupeng Ning | 2025-10 |

**特点**：
- David Z. Pan 是 EDA 背景（物理设计、光刻优化）
- 所以他们做光计算，天然带「编译器 / 布局 / 调度」的视角
- **这是最接近你 C++ 背景的一条线**

**ENLighten（2025-10）** 标题就很说明问题：`Lighten the Transformer, Enable Efficient Optical Acceleration`——它做的是「怎么把 Transformer 映射到光硬件上」，不是「造一个更好的光器件」。

### 线 2：MIT，Dirk Englund 组

| 论文 | 作者 | 年份 |
|---|---|---|
| P04 单片训练 | Bandyopadhyay, Sludds, Krastanov, ... Englund | 2024 |
| PRX 光电乘法 | Hamerly, Bernstein, Sludds, Soljačić, Englund | 2019 |

**特点**：
- 强项是**单片集成 + 原位训练**
- P04 做到了「线性 + 非线性都进光域」
- 代价：热光移相器能耗 9.8 pJ/OP，能效不占优

### 线 3：GWU，Volker Sorger 组

| 论文 | 作者 | 年份 |
|---|---|---|
| Photonic Tensor Core | Miscuglio, Sorger | 2020 |
| P07 microLED 混合 | Müller et al. | 2025 |

**特点**：器件-系统垂直整合，相变材料 + WDM。

### 线 4：国内

| 单位 | 代表 | 特点 |
|---|---|---|
| 上海交大 | 周海龙、董建绩（P03） | 矩阵乘法三路线综述 |
| 华中科大 | 张新亮（P02、P06 合作者） | 衍射光计算 + 原位训练 |
| 复旦 | 周鹏、程增光（P02） | 神经形态器件 |

---

## 4. 2024–2026 的新方向（P01 的四轴之外）

P01 是 2024 年的综述，之后出现了**第五条轴**：

### 新轴：运行时自适应 / 自校正

| 论文 | 作者 | 时间 | 做什么 |
|---|---|---|---|
| **DOCTOR** | Haotian Lu, Sanmitra Banerjee, Jiaqi Gu | 2024-03 | Dynamic On-Chip Temporal Variation Remediation Toward **Self-Corrected** Photonic Tensor Accelerators |
| **SKYLIGHT** | Meng Zhang, Ziang Yin, Nicholas Gangi | 2026-02 | Scalable Hundred-Channel **3D Photonic In-Memory** Tensor Core |
| **Light-Bound Transformers** | Xuming Chen, Deniz Najafi | 2026-04 | **Hardware-Anchored Robustness** for Silicon-Photonic CV Systems |
| **TRON** | Salma Afifi, Febin Sunny, Mahdi Nikdast | 2023-03 | Transformer 加速 with **Non-Coherent** Silicon Photonics |

**为什么这是新轴**：P01 的四轴都是「设计时」的 co-design（面积、能耗、精度、可训练性都是静态属性）。
DOCTOR 这类工作处理的是「**部署后**」的问题——温度漂移、器件老化、工作点偏移。

**标题里的关键词说明了一切**：
- `Self-Corrected` → 系统自己补偿漂移
- `Hardware-Anchored Robustness` → 鲁棒性锚定在硬件特性上，不是通用鲁棒性

**这是 co-design 的下一站**：从「设计时协同」走向「运行时协同」。

---

## 5. 他们共同做的三件事

看完这些工作，共同点不是「光算得多快」，而是：

### 1. 先承认硬约束，再设计算法

没有一个是「我有个好算法，想办法塞进光硬件」。
全都是「光硬件有这些毛病，所以我设计这样的算法」。

### 2. 每一层都让一步

| 层 | 让什么 |
|---|---|
| 算法 | 让精度（QAT）、让通用性（受限矩阵） |
| 架构 | 让并行度（光学广播）、让数据流（output-stationary） |
| 器件 | 让面积（紧凑器件）、让速度（相变材料） |

**没有哪一层是「完美」的，但整体可用。** 这就是 co-design 的本质。

### 3. 用仿真闭环验证，不靠单一指标

P01 里反复出现 Table II / Table III 这类汇总表，横向对比不同方案在**多个指标**（面积、能耗、精度、训练方式）上的表现。

**单一指标（比如「多少 TOPS」）在这个领域没有意义**，因为瓶颈在不同地方。

---

## 6. 对你的意义

### 你能切入的是哪一段

**不是器件层**（需要流片、需要洁净室），**不是物理层**（需要电磁场功底）。

**是「算法-硬件映射」这一段**：
- 把一个神经网络映射到给定的光硬件拓扑上
- 决定哪个算子放光域、哪个放电域
- 调度数据流，减少 DAC/ADC 次数

**这正好是 C++ 能发挥的地方**——本质是一个编译器/调度问题。

### 具体能做什么

| 任务 | 难度 | 需要什么 |
|---|---|---|
| 复现 butterfly PTC 的面积模型 | 低 | 纯数学，C++ 可做 |
| 写一个「光/电算子划分」的启发式调度器 | 中 | 懂神经网络图，懂硬件约束 |
| 复现 QAT 在光计算上的精度损失 | 中 | Python + PyTorch |
| 做一个光计算硬件的 cost model | 中 | 读 P01 的 Table II/III，抽象成公式 |

**最后一条最像「前沿组在做的事」**，而且不需要任何硬件。

---

## 7. 一句话总结

> **极致的 co-design，不是让光算得更多，是让算法知道光哪里不行。**
>
> 前沿组的共同动作是：把光的物理缺陷（面积大、ADC 位数低、梯度拿不到、会漂移）
> 写进算法设计的第一行，而不是最后再想办法补偿。

---

## 8. 证据等级说明

| 内容 | 证据等级 |
|---|---|
| P01 的四轴框架与所有引文 | ✅ 从 PDF 内 grep 得到，可复核 |
| 作者与单位归属 | ✅ 从 PDF 作者列表核对 |
| 2024–2026 新论文的标题/作者/日期 | ✅ arXiv API 可查 |
| 新论文的**具体方法** | ⚠️ **未读正文**，仅从标题推断，不可当结论引用 |

**最后一行必须说清**：DOCTOR / SKYLIGHT / Light-Bound 这些我只看到了标题和作者，
没有读正文。它们的「具体怎么做」我不知道，不能编。
