# 自测题 5 问 — P04 Single-chip photonic DNN with training

> 答不上来就回读指定那一节。这是「读到位」的可判定标准，不是考试。

## Q1. 这篇的核心突破是什么？它解决了前人的什么局限？

**答**：

**回读**：README §2 第 ① ⑤ 条

<details>
<summary>参考答案（先自己想，再展开）</summary>

把线性和非线性处理单元**单片共集成**。前人只训练线性层，且要在电域算激活函数的梯度；它把非线性也搬进光域（NOFU），实现全链路的原位训练。

</details>

---

## Q2. FICONN 的三个关键构件是什么？

**答**：

**回读**：README §2 第 ② 条

<details>
<summary>参考答案（先自己想，再展开）</summary>

NOFU（非线性光功能单元）、CMXU（相干矩阵乘法单元）、原位训练（光学加速）。

</details>

---

## Q3. 本包的 92.7% 和你听说的 92.5% 差在哪？

**答**：

**回读**：README §5 版本差异表

<details>
<summary>参考答案（先自己想，再展开）</summary>

本包是 arXiv 预印本（92.7%、435 ps、标题 accelerated training）；你提供的是 Nature Photonics 正式版（92.5%、410 ps、标题 forward-only training）。正式版在评审中改了术语并重算数字。**引用正式版数字前必须拿到正式版 PDF。**

</details>

---

## Q4. 它 435 ps 的时延是怎么来的？是实测吗？

**答**：

**回读**：README §2 第 ④ 条

<details>
<summary>参考答案（先自己想，再展开）</summary>

是从 PIC 子系统参数**估算**的：3τCMXU + 2τNOFU + τTX→U1 + τU3→RX + τU-turn ≈ 435 ps。原文用词是 estimate，不是 measured。

</details>

---

## Q5. 它证明了「全光训练可行」，那证明了「全光训练划算」吗？

**答**：

**回读**：README §3 一句话 + §4 的能效行

<details>
<summary>参考答案（先自己想，再展开）</summary>

没有。热光移相器 9.8 pJ/OP、总估算 11.7 pJ/OP，比它想替代的电子方案并不低。「可行」与「划算」是两件事——这正是 P08 讨论 IO 开销的起点。

</details>

---

