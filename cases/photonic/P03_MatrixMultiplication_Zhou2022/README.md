# P03_MatrixMultiplication_Zhou2022 — 光到底怎么物理地做矩阵乘法

> **主题轨**：A 综述框架 ｜ **阅读顺序**：第 1 篇
> 这是三条轨里唯一一篇「先讲清物理机制」的综述。读它之前不要碰 MZI 网格的论文，
> 否则会把「酉变换」当成矩阵乘法的全部。

---

## §0 目标与验收

| 项 | 值 |
|---|---|
| **包 ID** | `P03` |
| **主题轨** | `A_review` |
| **任务状态** | 已归档 |
| **这篇为什么读** | 它把「光怎么做矩阵乘法」拆成三条互不替代的物理路线，是后面所有论文的分类坐标系 |
| **验收标准** | §2 的 4 条引文全部可在 PDF 内 grep 到；§4 的 3 个数字全部 `match=yes` |
| **本次目标** | 建立 PLC / MZI / WDM 三路线的判别能力，能一眼看出某篇论文走的是哪条 |

---

## §1 论文

| 项 | 值 |
|---|---|
| 文件 | `paper/Zhou2022_LSA.pdf` |
| 标题 | Photonic matrix multiplication lights up photonic accelerator and beyond |
| 作者 / 年份 | Hailong Zhou, Jianji Dong, Junwei Cheng, ... Xinliang Zhang, 2022 |
| 期刊 / DOI | Light: Science & Applications 11(1), 30 (2022) / 10.1038/s41377-022-00717-8 |
| 本地版本 | 正式版（CC BY，开放获取） |
| 获取来源 | https://www.nature.com/articles/s41377-022-00717-8.pdf （读取 2026-11-12） |
| 许可 | CC BY 4.0 |
| 目标图 | Fig. 1（三路线总览）、Fig. 2（PLC）、Fig. 3（MZI 网格）、Fig. 4（WDM） |

---

## §2 原文引论

> 全部为 PDF 内可 grep 的原句，保留原拼写（含 `ﬁ` 连字与 `–` 连接号）。

**① 三条路线的总纲**（这是全篇最重要的一句，直接给出分类坐标系）：

> In this review, we ﬁrst introduce the methods of photonic matrix multiplication, mainly including the plane light conversion method, Mach–Zehnder interferometer method and wavelength division multiplexing method.

[Abstract]

**② 三条路线的正式命名与缩写**：

> Matrix-vector multiplication The methods for photonic matrix-vector multiplications (MVMs) mainly fall into three categories: the plane light conversion (PLC) method, Mach –Zehnder interferometer (MZI) method and wavelength division multiplexing (WDM) method.

[Sec. 2, Matrix-vector multiplication]

**③ 作者对自身综述范围的界定**：

> Finally, we comment on the challenges and perspectives of photonic matrix multiplication and photonic acceleration.

[Abstract]

**④ MZI 网格怎么实现任意矩阵**（这条纠正了一个常见误读，务必读）：

> Figure 1b shows the con- ﬁguration diagram, which is based mainly on rotation submatrix decomposition and singular value decomposi- tion36.

[Sec. 2]

**⑤ 三条路线各自的定位（我的提炼，非原文）**：

- **PLC（平面光转换）**：用透镜/自由空间传播做傅里叶变换，权重靠掩模或 SLM。
  你说的「透镜做傅里叶变换」属于这一路。
- **MZI 网格**：级联马赫-曾德尔干涉仪。**单个 MZI 只能做酉变换**，
  但整个网格通过**旋转子矩阵分解 + SVD** 可以近似任意矩阵（见上面第 ④ 条原文）。
  把「MZI 只能做酉变换」当成「MZI 网格做不了任意矩阵」是**误读**。
- **WDM**：波长做并行通道，权重靠微环/调制器。

> **纠错记录（2026-11-12）**：本包初稿曾写「MZI 网格只能实现酉变换」，
> 后在 PDF 内 grep 到 SVD 那句，改为上述表述。
> 「酉变换限制」真正的痛点是**编程复杂度与差分路径损耗随维度恶化**（P05 的说法），
> 不是「根本做不了」。这个区别在二手转述里经常被抹掉。

---

## §3 与 AI 痛点的对应

| 痛点 | 这篇做了什么 | 做到了吗 | 代价 / 没解决的 |
|---|---|---|---|
| 精度与稳健性 | 只做路线综述，未深入量化精度 | 否 | 不讨论 DAC/ADC 开销，要读 P01 |
| 训练（反向传播 / 梯度） | 提到训练相关进展，但不是主线 | 部分 | 没有讲「怎么在光域做反向传播」 |
| 光电边界（IO 开销 / 谁做非线性） | 讲了光加速器在信号处理与神经网络的应用 | 部分 | 不量化 IO 开销；非线性未系统讨论 |

**一句话**：这是**坐标系**，不是结论。它告诉你「有三种做法」，
但不告诉你「哪种能训练」「哪种能规模化」——那要读 P01（卡在哪）、P04/P06（怎么训练）、P08（怎么规模化）。

---

## §4 数字核对

| 指标 | 论文值 | 我核到的 | 一致 | 出处 |
|---|---|---|---|---|
| 路线数量 | 3 类（PLC / MZI / WDM） | 3 类 | yes | p.1 Abstract + Sec. 2 |
| MZI 实现任意矩阵的方式 | 旋转子矩阵分解 + SVD | 旋转子矩阵分解 + SVD | yes | Sec. 2（Fig. 1b 说明） |
| 出版年份 | 2022 | 2022 | yes | 页眉 `Light: Science & Applications (2022) 11:30` |

> **修正说明**：初稿曾把「MZI 只能实现酉变换」当作 P03 的结论并标 `unverified`。
> 实际在 Sec. 2 找到原文：MZI 网格靠**旋转子矩阵分解 + SVD** 实现任意矩阵。
> 单层酉限制 ≠ 网格做不了任意矩阵。已改。

---

## §5 偏差与疑点

| 项 | 值 |
|---|---|
| 版本差异 | 无。本地即 CC BY 正式版 |
| 口径差异 | 这是 2022 年的综述，不含 2024–2026 的原位训练进展 |
| 我不确定的 | 「酉变换限制」在 P05 语境下具体指什么（单层？还是整个网格的编程复杂度？）——待 P05 正文 |
| 待问作者 / 待查 | Reck et al. 1994 / Clements et al. 2016 的酉分解理论原文 |
| 是否可引用 | 可引用（CC BY，正式版） |

---

## §6 交接

| 项 | 值 |
|---|---|
| 归档日期 | 2026-11-12 |
| 读完日期 | 待读 |
| 下一步 | 读 Fig. 2/3/4 三张图，能徒手画出三条路线的信号流；然后进 P01 |
| 与其他包的关系 | 是 P01（卡在哪）、P04（相干训练）、P06（衍射训练）、P08（超表面规模化）的共同前置 |
| 自测 | `notes/self-check-5q.md` |

---

## 文件清单

```text
P03_MatrixMultiplication_Zhou2022/
├─ README.md      ← 本文件
├─ paper/         Zhou2022_LSA.pdf（5.64 MB，CC BY）
├─ config/        paper.json
├─ notes/         reading-notes.md / self-check-5q.md
├─ results/       quotes.md / claims.csv
└─ model/         （空，本篇无需复现工程）
```
