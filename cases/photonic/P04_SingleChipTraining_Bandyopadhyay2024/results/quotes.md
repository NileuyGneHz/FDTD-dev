# 原文摘录 — P04 Single chip photonic DNN with accelerated training（arXiv 版）

> **本包是 arXiv 预印本（arXiv:2208.01623）**，标题与数字均与 Nature Photonics
> 正式版不同。引用时必须注明版本。差异见 `README.md` §5。

## 核心结论（单片集成线性 + 非线性是核心挑战）

> However, demonstrating systems that co-integrate both linear and nonlinear processing units in a single chip remains a central challenge.

[Introduction]

## 方法 / 架构（三要素）

> Here we introduce such a system in a scalable photonic integrated circuit (PIC), enabled by several key advances: (i) high-bandwidth and low-power programmable nonlin- ear optical function units (NOFUs); (ii) coherent matrix multiplication units (CMXUs); and (iii) in situ training with optical acceleration.

[Abstract]

## 关键数字（预印本口径）

> Using in situ training on a vowel classiﬁcation task, the FICONN achieves 92.7% accuracy on a test set, which is identical to the accuracy obtained on a digital computer with the same number of weights.

[Abstract]

## 时延（预印本口径）

> For the FICONN, τlatency is dom- inated by the optical propagation delay, which we esti- mate from the PIC subsystems (as described in the SI) as 3τCMXU + 2τNOFU +τTX to U1 +τU3 to RX +τU-turn≈ 435 ps.

[Discussion]

## 作者对前人工作的限定（forward-only 的动机）

> Previous work on in situ train- ing has focused on developing optical implementations of "backpropagation," which is the standard for training elec- tronic DNNs [28, 39]. However, these approaches train only the linear layers of a photonic system and require evaluat- ing gradients of activation functions on a

[Discussion]

---

## 核对记录

| 引文 | 是否 grep 到 | 日期 |
|---|---|---|
| 核心结论 | yes | 2026-11-12 |
| 三要素 | yes | 2026-11-12 |
| 92.7% | yes | 2026-11-12 |
| 435 ps | yes | 2026-11-12 |
| 前人限定 | yes | 2026-11-12 |

> **待办**：拿到 Nature Photonics 正式版后，核对 `forward-only` 与 92.5% / 410 ps，
> 并把正式版引文补进本文件（标注 `[published]` 以区别）。
