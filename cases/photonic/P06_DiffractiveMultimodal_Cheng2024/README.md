# P06_DiffractiveMultimodal_Cheng2024 — 衍射光计算 + 原位训练

> **主题轨**：B 训练瓶颈 ｜ **阅读顺序**：第 6 篇
> 与 P04 的「相干 MZI 网格」路线并列，这是**衍射光学**路线的代表：
> 一次前向传播出结果，不用频繁光电转换，且能训练。

---

## §0 目标与验收

| 项 | 值 |
|---|---|
| **包 ID** | `P06` |
| **主题轨** | `B_training` |
| **任务状态** | 已归档 |
| **这篇为什么读** | 展示了「衍射光计算 + 原位训练」在**多模态**（视觉/音频/触觉）上的可行性 |
| **验收标准** | §2 的 4 条引文可在 PDF 内 grep 到；§4 的 6 个数字全部 `match=yes` |
| **本次目标** | 说清 TDONN 的层数、训练算法、以及 85.7% 是在什么任务上测的 |

---

## §1 论文

| 项 | 值 |
|---|---|
| 文件 | `paper/Cheng2024_NatCommun.pdf` |
| 标题 | Multimodal deep learning using on-chip diffractive optics with in situ training capability |
| 作者 / 年份 | Junwei Cheng, Chaoran Huang, Jialong Zhang, ... Xinliang Zhang, 2024 |
| 期刊 / DOI | Nature Communications 15(1), 6209 (2024) / 10.1038/s41467-024-50677-3 |
| 本地版本 | **正式版（CC BY）** |
| 获取来源 | https://www.nature.com/articles/s41467-024-50677-3.pdf （读取 2026-11-12） |
| 许可 | CC BY 4.0 |
| 目标图 | Fig. 1（TDONN 架构）、Fig. 4（训练收敛）、Table 1（性能对比） |

---

## §2 原文引论

> 全部为 PDF 内可 grep 的原句。

**① 结构规模与「一次前向」**：

> The TDONN chip includes one input layer, ﬁve hidden layers, and one output layer, and only one forward propagation is required to obtain the inference results without frequent optical-electrical conversion.

[Abstract]

**② 训练算法（这是它能「原位」的关键）**：

> The customized stochastic gradient descent algorithm and the drop-out mechanism are developed for photonic neurons to realize in situ training and fast convergence in the optical domain.

[Abstract]

**③ 性能四件套（一句话给出全部关键数字）**：

> The TDONN chip achieves a potential throughput of 217.6 tera-operations per second (TOPS) with high computing density (447.7 TOPS/mm2), high system-level energy efﬁciency (7.28 TOPS/W), and low optical latency (30.2 ps).

[Abstract]

**④ 多模态准确率与任务定义**：

> The TDONN chip has suc- cessfully implemented four-class classiﬁcation in different modalities (vision, audio, and touch) and achieve 85.7% accuracy on multimodal test sets.

[Abstract]

**⑤ 收敛加速的量化**：

> The drop-out mechanism is designed for massive trainable neurons to accelerate the convergence speed (36.5% convergence ac- celeration compared to no drop-out) in the optical domain.

[Sec. 结果]

---

## §3 与 AI 痛点的对应

| 痛点 | 这篇做了什么 | 做到了吗 | 代价 / 没解决的 |
|---|---|---|---|
| 精度与稳健性 | 用 CMOS 兼容工艺做衍射层，热调谐 | 部分 | 85.7% 是四分类；类别数上去后精度会掉（衍射网络已知问题） |
| 训练（反向传播 / 梯度） | **定制 SGD + dropout**，在光域原位训练 | 是 | 只训练衍射层相位；非线性仍靠外部或简化模型 |
| 光电边界（IO 开销 / 谁做非线性） | 一次前向即可出结果，大幅减少 O-E 转换 | 是 | 输入仍需 E-O（调制器），输出仍需 O-E（相机/PD） |

**一句话**：这是**衍射路线的可行性证明**。它的强项是「一次前向 + 可训练」，
弱项是「类别数一多精度就掉」——这一点 P02 的综述里也提到衍射网络的扩展性问题。

---

## §4 数字核对

| 指标 | 论文值 | 我核到的 | 一致 | 出处 |
|---|---|---|---|---|
| 多模态测试准确率 | 85.7% | 85.7% | yes | Abstract |
| 系统级能效 | 7.28 TOPS/W | 7.28 TOPS/W | yes | Abstract |
| 光学时延 | 30.2 ps | 30.2 ps | yes | Abstract |
| 潜在吞吐 | 217.6 TOPS | 217.6 TOPS | yes | Abstract |
| 计算密度 | 447.7 TOPS/mm² | 447.7 TOPS/mm² | yes | Abstract |
| 网络层数 | 1 输入 + 5 隐藏 + 1 输出 = 7 层 | 7 层 | yes | Abstract |
| 分类类别数 | 4 类 | 4 类 | yes | Abstract |
| dropout 收敛加速 | 36.5% | 36.5% | yes | Sec. 结果 |

> **口径警告**：「217.6 TOPS」「447.7 TOPS/mm²」都是 **potential**（潜在）值，
> 是按器件带宽推算的上限，不是实测吞吐。引用时必须带「potential」这个词，
> 否则会误导成「已经跑到了 217.6 TOPS」。

---

## §5 偏差与疑点

| 项 | 值 |
|---|---|
| 版本差异 | 无。本地即 CC BY 正式版 |
| 口径差异 | 85.7% 是**四分类**多模态任务；与 P04 的六分类元音不可直接比较 |
| 我不确定的 | 「217.6 TOPS」的推算假设（每层调制器带宽 × 层数？）需读 Methods 确认 |
| 待问作者 / 待查 | 类别数增加到 10 / 100 时的精度衰减曲线 |
| 是否可引用 | 可引用（CC BY 正式版）；吞吐必须带「potential」 |

---

## §6 交接

| 项 | 值 |
|---|---|
| 归档日期 | 2026-11-12 |
| 读完日期 | 待读 |
| 下一步 | 读 Methods 里的 TOPS 推算过程；对照 P04 的 Table I 做能效横比 |
| 与其他包的关系 | 与 P04 并列（衍射 vs 相干），共同回答「光域训练可行吗」 |
| 自测 | `notes/self-check-5q.md` |

---

## 文件清单

```text
P06_DiffractiveMultimodal_Cheng2024/
├─ README.md      ← 本文件
├─ paper/         Cheng2024_NatCommun.pdf（3.27 MB，CC BY 正式版）
├─ config/        paper.json
├─ notes/         reading-notes.md / self-check-5q.md
├─ results/       quotes.md / claims.csv
└─ model/         （空）
```
