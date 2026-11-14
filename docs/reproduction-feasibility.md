# 哪些论文可以用 FDTD_WS + Lumerical 复现

> 判断依据：`library/paper_lib/` 里 12 篇 PDF 的**实际几何参数**（从 PDF 内 grep 得到），
> 对照 FDTD_WS 现有 13 个技能的能力边界。
> 编制日期：2026-11-13

---

## 0. 结论先行

**12 篇里，真正能"单元胞级复现"的只有 3 篇。**

| 论文 | 能否复现 | 级别 | 关键原因 |
|---|---|---|---|
| Metapinhole（2025） | ✅ **最推荐** | 单元胞 | 几何参数全给（周期 680 nm / 高 288 nm / 金 78 nm / 间隙 80 nm） |
| 单片超表面微分器（2020） | ✅ 可行 | 单元胞 | 周期 4.8 µm / 高 7 µm / 硅 / 10.6 µm，参数齐 |
| 介质超表面边缘检测（PNAS 2019） | ⚠️ **部分可行** | 单元胞 | 是**激光直写玻璃**（form birefringence），不是常规纳米柱，建模方式特殊 |
| 11 TOPS 卷积加速器（Nature 2021） | ❌ 不可行 | 全器件 | 需要集成光子 + 色散模块 + 多波长，非 FDTD 能覆盖 |
| PRX 光电乘法（2019） | ❌ 不可行 | 系统级 | 是架构理论 + 自由空间系统，没有可复现的单元结构 |
| MRR crossbar（2024） | ⚠️ 理论可行 | 器件 | 需要波导 + 微环 + 端口，**现有技能不支持波导** |
| Photonic Tensor Core（2026） | ❌ 不可行 | 集成器件 | WDM + 相变材料 + 波导，缺 3 样能力 |
| Lightening-Transformer（HPCA 2024） | ❌ 不可行 | 体系结构 | 纯架构论文，无器件仿真 |
| 量子边缘检测（Sci. Adv. 2020） | ⚠️ 部分可行 | 单元胞 | 几何需从 SI 找，正文参数不全 |
| 可编程 PCM 波导（Nat. Commun. 2021） | ❌ 不可行 | 波导 | 需波导 + GST 相变材料，**两样都缺** |
| 分数阶傅里叶变换（JOSA A 1993） | ❌ 不可行 | 系统 | 纯理论 + 透镜系统，无亚波长结构 |
| 光子矩阵乘法综述（LSA 2022） | — | 综述 | 无原创器件 |

---

## 1. 最推荐：Metapinhole（arXiv 2025）

### 为什么推荐

**它是唯一一篇把几何参数给全的**，而且正好落在现有技能的舒适区（周期单元胞 + R/T 谱）。

**原文参数**（PDF 内可 grep）：

> The structure has a **period of 680 nm** and, at three distinct wave- lengths, it performs three distinct angular operations: low-pass, high-pass, and angular-invariant responses.

> The metagrating features a **period of 680 nm**, with a **reversed parabolic height of 288 nm**. The **gold layer has a thickness of 78 nm**, while the **gap between the two hat-shaped elements measures 80 nm**.

### 复现目标

| 项 | 值 |
|---|---|
| 结构 | 金帽（hat-like）+ 二氧化硅反向抛物面，周期 680 nm |
| 关键尺寸 | 抛物高 288 nm，金 78 nm，间隙 80 nm |
| 基底 | 硅 + 热氧化硅 |
| 工作波长 | 三个波长对应三种角响应（低通/高通/角不变） |
| 可复现的图 | Fig. 4（0 阶透射率 vs 角度，TM 偏振） |

### 用哪个技能

```powershell
# 1. 抽参数（从 PDF 生成 spec）
python skills/fdtd-paper-parameter-extraction/scripts/extract_pdf_text.py ...

# 2. 建工程 + 扫参
python skills/fdtd-lumerical-unitcell-simulation/scripts/run_fdtd_sweep.py ...
```

### 风险

- **金在近红外有损耗**，材料模型要用 Palik 或 Johnson-Christy，不能用 Drude 简化
- 「角度响应」需要**斜入射**，要用 Bloch 边界（技能支持）
- 反向抛物面几何，`fsp-build` 的 polygon 能否精确表达，需要试

---

## 2. 可行：单片超表面微分器（Nanophotonics 2020）

**原文参数**（PDF 内可 grep）：

> The **period P of the unit cell and the height H of the pillar are 4.8 and 7 μm**, respectively.

> silicon is chosen as the dielectric material ... **works at 10.6 μm**

> The pillars with the same height of **H = 7 μm** but different transverse sizes (width W and length L) and orientations θ are mounted on the **hexagonal unit cells**

### 复现目标

| 项 | 值 |
|---|---|
| 结构 | 硅柱（chamfered pillar，倒角）在六角晶格上 |
| 周期 | 4.8 µm |
| 高度 | 7 µm |
| 材料 | 硅（10.6 µm 处损耗可忽略） |
| 波长 | 10.6 µm（中红外） |
| 关键 | 旋转角度 θ 对应 PB 相位 |

### 难度评估

**中等偏低**，因为：
- 参数完整
- 材料简单（硅，中红外）
- 周期单元 + 旋转角扫描，正好是 `unitcell-simulation` + `session-control` 的组合

**风险**：
- 7 µm 高的柱子在 4.8 µm 周期上，**深宽比 1.46**，网格要细
- 六角晶格 vs 技能支持的方形周期，可能需要调整
- 倒角（chamfer）几何，polygon 表达较复杂

---

## 3. 部分可行：PNAS 介质超表面（2019）

**这篇要特别说明，因为它看起来最像"常规超表面"，实际不是。**

**原文**（PDF 内可 grep）：

> The metasurface pattern is fabricated by a **femtosecond pulse laser inside of glass**, 50 μm beneath the surface.

> the slow-axis distribution φ(x, y) of **laser-induced form birefringence**

> The nanostructures are on the order of **30 ∼100 nm**

### 为什么"部分可行"

| 项 | 说明 |
|---|---|
| 不是纳米柱 | 是**玻璃内部激光诱导的形状双折射**（form birefringence） |
| 结构尺度 | 30–100 nm 的纳米光栅，不是可分辨的柱子 |
| 建模方式 | 需要**有效介质理论**（effective medium），不是直接建几何 |
| 基底 | 2.5 cm 直径、3 mm 厚的玻璃 |

**结论**：如果你要复现，不能直接建柱子，得建"亚波长光栅"并提取有效双折射。
这在 FDTD 里可做（建细光栅，算相位延迟），但**和论文的"激光直写"工艺对不上**。

**建议**：**跳过这篇**，除非你专门想学有效介质建模。

---

## 4. 明确不可行的（4 类原因）

### 原因 A：需要波导（现有技能不支持）

| 论文 | 缺什么 |
|---|---|
| MRR crossbar（2024） | 波导 + 微环 + 模式源 + 端口监视器 + S 参数 |
| 可编程 PCM 波导（2021） | 波导 + GST 相变材料 |
| Photonic Tensor Core（2026） | WDM + 波导 + PCM |

**我上次实测确认过**：13 个技能里没有一个支持波导建模。这不是"难"，是"没有这个能力"。

### 原因 B：系统级，无单元结构

| 论文 | 为什么 |
|---|---|
| PRX 光电乘法（2019） | 架构理论 + 自由空间系统，没有可复现的亚波长单元 |
| Lightening-Transformer（2024） | 体系结构论文，仿真对象是整个处理器 |
| 分数阶傅里叶变换（1993） | 纯透镜系统，无亚波长结构 |

### 原因 C：需要集成光子工艺

| 论文 | 为什么 |
|---|---|
| 11 TOPS 卷积加速器（2021） | 需要色散模块 + 多波长源 + 调制器阵列，是系统集成，不是 FDTD 单元 |

### 原因 D：参数不全

| 论文 | 缺什么 |
|---|---|
| 量子边缘检测（2020） | 正文没给完整几何，要查 SI |

---

## 5. 复现能力边界（必须说清）

### 现在能做到的

| 能力 | 技能 | 状态 |
|---|---|---|
| 周期单元胞 R/T/A 谱 | `unitcell-simulation` | ✅ 成熟 |
| 双偏振相位差 | `phase-retrieval` | ✅ 成熟 |
| 斜入射（Bloch） | `unitcell-simulation` | ✅ 支持 |
| 参数扫描 | `session-control` | ✅ 成熟 |
| 出谱图/场图 | `figure` | ✅ 成熟 |

### 现在做不到的

| 能力 | 缺什么 | 影响 |
|---|---|---|
| 有限尺寸器件（PML + 大口径） | 无对应技能 | 做不了透镜聚焦、整个衍射层 |
| 波导 / MZI / 定向耦合器 | 无波导建模 | 做不了集成光子器件 |
| 多层传播（角谱） | 无传播建模 | 做不了 4f 系统的层间传播 |
| 相变材料（GST 双态） | 材料类型缺失 | 做不了 PCM 器件 |
| 电光材料（Pockels） | 材料类型缺失 | 做不了 LiNbO3 调制器 |

---

## 6. 我的建议顺序

| 优先 | 论文 | 理由 | 预计工作量 |
|---|---|---|---|
| **1** | Metapinhole | 参数最全，最接近现有技能舒适区 | 2–3 天 |
| **2** | 单片微分器 | 参数全，材料简单，能练旋转角扫描 | 3–5 天 |
| **3** | 量子边缘检测 | 需要查 SI 补参数 | 1 周+ |
| 跳过 | PNAS 介质超表面 | 建模方式和论文工艺对不上 | — |
| 跳过 | 其余 5 篇 | 能力缺口太大 | — |

---

## 7. 一个重要提醒

**这三篇都是"空间域滤波"，不是时间域。**

你上次和黄老师讨论的方向是"用色散代替透镜做时间域滤波"。**这三篇复现不了那个方向**——它们能帮你练熟 FDTD 单元胞流程，但不能直接产出时间域滤波的结果。

**所以复现这三篇的价值是**：
1. 练熟 FDTD 工作流（这是真需求，你现在还没跑通过一次完整仿真）
2. 积累"光学滤波器件长什么样"的直觉
3. 万一将来要做空间域滤波，有现成模板

**但不是**直接推进你的创新点。

---

## 8. 当前 FDTD 环境的真实状态

我实测过（2026-11-12/13）：

| 项 | 状态 |
|---|---|
| Lumerical v251 | ✅ `F:\Lumercial_WS\ANSYS Inc\v251` |
| 许可服务 | ✅ `ansyslmd` 在跑，`1055@localhost` |
| lumapi 导入 | ✅ 托管 python 3.13.14 + numpy 2.5.3 |
| 开 FDTD 会话 | ✅ |
| 建几何 + 存 .fsp | ✅ |
| **跑仿真** | ✅ **能跑**（21 频点，1200–1800 nm） |
| **读 R/T 结果** | ✅ **已修**（2026-11-13，见 `defects/D-004`） |

**2026-11-13 更新（D-004 resolved）**：原先的 T 越界不是归一化算法问题，
而是**监视器法线设反**——2D 里传播沿 y，却写了 `2D X-normal`，三个监视器覆盖同一片区域，
R 恒等于 1。改成 `2D Y-normal` 后，裸 `addpower` 自带的归一化 `"T"` 结果即可用
（**不需要 analysis group**）。

当前实测（`_scratch/fdtd_proof.py`，五个算例全 PASS）：

| 算例 | T | R | 说明 |
|---|---|---|---|
| main | [0.0049, 0.9672] | [0.0332, 0.9969] | T+R∈[0.9982,1.0019] |
| vacuum | 1.0000 | −0.0000 | 正对照 |
| xnormal | [0,0] | **1.0000** | 负对照：复现原 bug |
| nearsrc | [0.8970,0.9994] | [0.4361,0.5554] | 负对照：ref 贴源被污染 |
| metal | ≈0 | 中位数 0.974 | 负对照：不透明背板 |

**仍然成立的那句话**：能跑不等于结论正确。R/T 现在物理自洽（T+R=1），
但复现论文时仍要按论文自己的归一化口径（是否含基底反射、是否含衍射级次）。

---

## 9. 相关文件

| 内容 | 路径 |
|---|---|
| 文献库 | `library/paper_lib/` |
| 文献综述 | `docs/paper-lib-review.md` |
| 信号处理机制 | `docs/photonic-signal-processing.md` |
| 仿真测试脚本 | `_scratch/fdtd_proof.py` |
