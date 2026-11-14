# 自测题 5 问 — P06 Multimodal on-chip diffractive optics

> 答不上来就回读指定那一节。这是「读到位」的可判定标准，不是考试。

## Q1. TDONN 的层数结构是什么？为什么「一次前向」很重要？

**答**：

**回读**：README §2 第 ① 条

<details>
<summary>参考答案（先自己想，再展开）</summary>

1 输入层 + 5 隐藏层 + 1 输出层。一次前向传播就能出推理结果，不需要在层间反复做光电转换——这正是它绕开 DAC/ADC 开销的方式。

</details>

---

## Q2. 它用什么算法实现原位训练？

**答**：

**回读**：README §2 第 ② 条

<details>
<summary>参考答案（先自己想，再展开）</summary>

定制的随机梯度下降（SGD）+ 为光子神经元设计的 dropout 机制。

</details>

---

## Q3. 217.6 TOPS 是实测吞吐吗？

**答**：

**回读**：README §4 的口径警告

<details>
<summary>参考答案（先自己想，再展开）</summary>

不是。原文写的是 **potential** throughput，是按器件带宽推算的上限。引用时必须带 potential，否则会误导成实测。

</details>

---

## Q4. 85.7% 是在什么任务上测的？

**答**：

**回读**：README §2 第 ④ 条

<details>
<summary>参考答案（先自己想，再展开）</summary>

四分类，跨三种模态（视觉、音频、触觉）的多模态测试集。不是 ImageNet 级任务，也不是十分类。

</details>

---

## Q5. 衍射路线相比 P04 的相干 MZI 路线，优劣各是什么？

**答**：

**回读**：README §3 一句话 + §5

<details>
<summary>参考答案（先自己想，再展开）</summary>

优：一次前向、结构简单、CMOS 兼容、可大规模制造。劣：类别数上去后精度会掉（P02 也提到衍射网络的扩展性问题）。P04 的优势是相干矩阵运算精度高，劣势是热光移相器能耗高。

</details>

---

