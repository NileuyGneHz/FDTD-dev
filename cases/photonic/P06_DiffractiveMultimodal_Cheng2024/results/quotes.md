# 原文摘录 — P06 Multimodal deep learning using on-chip diffractive optics

> 正式版（CC BY），可直接引用。注意原文用 `ﬁ` 连字与 `ﬁ` / `efﬁciency` 等特殊写法。

## 核心结论（一次前向 + 无需频繁光电转换）

> The TDONN chip includes one input layer, ﬁve hidden layers, and one output layer, and only one forward propagation is required to obtain the inference results without frequent optical-electrical conversion.

[Abstract]

## 方法 / 架构（定制 SGD + dropout）

> The customized stochastic gradient descent algorithm and the drop-out mechanism are developed for photonic neurons to realize in situ training and fast convergence in the optical domain.

[Abstract]

## 性能四件套

> The TDONN chip achieves a potential throughput of 217.6 tera-operations per second (TOPS) with high computing density (447.7 TOPS/mm2), high system-level energy efﬁciency (7.28 TOPS/W), and low optical latency (30.2 ps).

[Abstract]

## 多模态结果

> The TDONN chip has suc- cessfully implemented four-class classiﬁcation in different modalities (vision, audio, and touch) and achieve 85.7% accuracy on multimodal test sets.

[Abstract]

## 收敛加速

> The drop-out mechanism is designed for massive trainable neurons to accelerate the convergence speed (36.5% convergence ac- celeration compared to no drop-out) in the optical domain.

[Sec. Results]

---

## 核对记录

| 引文 | 是否 grep 到 | 日期 |
|---|---|---|
| 核心结论 | yes | 2026-11-12 |
| 定制 SGD | yes | 2026-11-12 |
| 性能四件套 | yes | 2026-11-12 |
| 多模态结果 | yes | 2026-11-12 |
| 收敛加速 | yes | 2026-11-12 |

> **引用纪律**：`217.6 TOPS` 与 `447.7 TOPS/mm²` 原文都带 **potential**，
> 引用时必须保留这个词，否则会误导成实测吞吐。
