# EXP-10 监视器-PML 最小间距在建模阶段拒绝

## 假设

SKILL.md 一直写「≥0.3 µm」，代码却按 `0.85*below` 直接摆，`below=0.15` 时压进 PML。

## 输入

P01 的 simulation 块（air 2.5 / below 1.0 µm）+ 故意收紧的 below=0.15 µm

## 对照与负对照

正：P01 口径放行；负：0.15 µm 必须报错并给出「≥0.300 µm」的具体数字。

## 判据

前者不抛；后者抛且错误信息含 0.300。

## 重跑命令

```bash
python _scratch/regress/2026-11-09/test_exp09_10_12.py
```
