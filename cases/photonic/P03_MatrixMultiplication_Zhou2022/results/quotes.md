# 原文摘录 — P03 Photonic matrix multiplication lights up photonic accelerator

> 每条引文都必须是 PDF 里能 grep 到的原句。注意原文用 `ﬁ` 连字与 `–`（en dash）连接号。

## 核心结论（三条路线总纲）

> In this review, we ﬁrst introduce the methods of photonic matrix multiplication, mainly including the plane light conversion method, Mach–Zehnder interferometer method and wavelength division multiplexing method.

[Abstract]

## 方法 / 架构（三条路线的正式命名与缩写）

> Matrix-vector multiplication The methods for photonic matrix-vector multiplications (MVMs) mainly fall into three categories: the plane light conversion (PLC) method, Mach –Zehnder interferometer (MZI) method and wavelength division multiplexing (WDM) method.

[Sec. 2, Matrix-vector multiplication]

## 作者对综述范围的界定

> Finally, we comment on the challenges and perspectives of photonic matrix multiplication and photonic acceleration.

[Abstract]

## 补充：MZI 用旋转子矩阵分解 + SVD

> Figure 1b shows the con- ﬁguration diagram, which is based mainly on rotation submatrix decomposition and singular value decomposi- tion36.

[Sec. 2]

---

## 核对记录

| 引文 | 是否 grep 到 | 日期 |
|---|---|---|
| 核心结论 | yes | 2026-11-12 |
| 方法 / 架构 | yes | 2026-11-12 |
| 范围界定 | yes | 2026-11-12 |
| MZI 分解方式 | yes | 2026-11-12 |

> **重要发现**：第 4 条说明 MZI 网格是通过 **旋转子矩阵分解 + SVD** 实现任意矩阵的，
> 也就是说「MZI 只能做酉变换」是**单层**的限制，**整个网格配 SVD 可以近似任意矩阵**。
> 这个区别很容易被二手转述抹掉。P05 要说的「酉变换限制」需在此语境下理解。
