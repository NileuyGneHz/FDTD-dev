# paper_lib — 光学滤波与光学矩阵运算文献库

> 由 `search_papers` / `download_papers` 插件抓取 + arXiv 直连补齐。
> 每篇都经 `pypdf` 校验页数与首页文本，确认不是 HTML 冒充。
> 归档日期：2026-11-12

## 目录

```
paper_lib/
├─ INDEX.md              ← 本文件
├─ lens_filter/          光学滤波（空间滤波 / 边缘检测 / 微分）
└─ matrix_compute/       光学矩阵运算（MVM / 卷积加速器 / tensor core）
```

## lens_filter — 6 篇

| 文件 | 标题 | 出处 | 页 | 状态 |
|---|---|---|---|---|
| `Metapinhole_PlanarFourierOptics_2025.pdf` | Metapinhole: Planar Fourier Optics Without Lenses | arXiv 2509.05555 (2025) | 13 | ✅ |
| `05_Optical edge detection based on high-efficiency dielectric metasurface.pdf` | Optical edge detection based on high-efficiency dielectric metasurface | PNAS 116 (2019) | 4 | ✅ |
| `07_Metasurface enabled quantum edge detection.pdf` | Metasurface enabled quantum edge detection | Sci. Adv. 6, eabc4385 (2020) | 8 | ✅ |
| `09_Monolithic metasurface spatial differentiator...pdf` | Monolithic metasurface spatial differentiator (asymmetric PSOI) | Nanophotonics (2020) | 8 | ✅ |
| `10_Fractional Fourier transforms and their optical implementation II.pdf` | Fractional Fourier transforms and their optical implementation. II | JOSA A 10(12), 2522 (1993) | 10 | ✅ |
| — | Optical computing metasurfaces: applications and advances | Nanophotonics (2024) | — | ❌ 无 OA |

## matrix_compute — 7 篇

| 文件 | 标题 | 出处 | 页 | 状态 |
|---|---|---|---|---|
| `01_11 TOPS photonic convolutional accelerator...pdf` | 11 TeraFLOPs/s photonic convolutional accelerator | Nature 589 (2021) | 21 | ✅ |
| `02_Programmable phase-change metasurfaces on waveguides...pdf` | Programmable PCM metasurfaces for multimode photonic CNN | Nat. Commun. 12 (2021) | 8 | ✅ |
| `03_Large-Scale Optical Neural Networks Based on Photoelectric Multiplication.pdf` | Large-scale ONN based on photoelectric multiplication | PRX 9, 021032 (2019) | 12 | ✅ |
| `04_Lightening-Transformer...pdf` | Lightening-Transformer: photonic transformer accelerator | HPCA 2024 | 18 | ✅ |
| `07_Photonic matrix multiplication lights up photonic accelerator and beyond.pdf` | Photonic matrix multiplication（与 cases/P03 同篇） | LSA 11:30 (2022) | 21 | ✅ |
| `MicroringCrossbar_Ohno2022.pdf` | Symmetric Si MRR optical crossbar for inference + training | arXiv 2401.16072 (2024) | 12 | ✅ |
| `PhotonicTensorCore_MVM_2026.pdf` | Photonic Tensor Cores for Machine Learning | arXiv 2002.03780 | 16 | ✅ |

## 未获取（已记录，不伪造）

| 标题 | DOI | 卡在哪 |
|---|---|---|
| Optical analog computing of spatial differentiation and edge detection with dielectric metasurfaces | 10.1364/ol.386986 | Optica 付费墙，无 OA 副本 |
| Laplace metasurfaces for optical analog computing based on qBIC | 10.1364/prj.426827 | 同上 |
| Advances in spatial analog optical computing devices | 10.7498/aps.69.20200283 | 中文期刊，无 OA |
| Study on SAR data processing based on optical 4f system | 10.1364/oe.471716 | Optica 付费墙 |
| Optical computing metasurfaces: applications and advances | 10.1515/nanoph-2023-0871 | De Gruyter 付费墙 |
| Si Microring Resonator Crossbar（ACS Photonics 版） | 10.1021/acsphotonics.1c01777 | HTTP 403；已用 arXiv 版替代 |
| Matrix-vector multiplication for photonic tensor core | 10.1088/1402-4896/ae8345 | IOP，无 OA |
| Metasurfaces for Edge Detection and Spatial Differentiation | 10.1002/adfm.74788 | Wiley，无 OA |
| 11 TOPS（Nature 正式版） | 10.1038/s41586-020-03063-0 | 已用 arXiv 版替代 |

## 关键数据（全部从 PDF 内 grep 到，可复核）

| 论文 | 数字 | 原文片段 |
|---|---|---|
| 11 TOPS 卷积加速器 | >10 Tera-FLOPS，8-bit，10 kernels 并行，88% 手写数字识别 | 见 `matrix_compute/01_*` |
| Hamerly PRX | 可扩展到 N ≳ 10⁶，亚阿焦/ MAC | 见 `matrix_compute/03_*` |
| MRR crossbar (Ohno) | 4×4，推理 93.3%，片上反向传播训练后 91.1% | 见 `MicroringCrossbar_Ohno2022` |
| Photonic Tensor Core (Miscuglio/Sorger) | 2 Peta-ops/s，0.5 POPS/s 实测，25 TOPS/J | 见 `PhotonicTensorCore_MVM_2026` |
| 介质超表面边缘检测 | 效率 ~90% | 见 `lens_filter/05_*` |
| 单片超表面微分器 | 去掉 4f 系统，轴向体积减少 50% | 见 `lens_filter/09_*` |

## 校验命令

```powershell
$env:PYTHONPATH='F:\tools\pylibs'
python _scratch\verify_lib.py
```

## 约束

1. **PDF 只读**，归档后不改名不移动。
2. **不伪造**：拿不到就写「无 OA」，不拿二手转述冒充。
3. 引用数字必须回 PDF grep，不许从摘要页转述。
