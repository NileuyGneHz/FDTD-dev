# EXP-09 指标按 target.quantity 选键，并对 R/T 做物理区间校验

## 假设

写死 `A` 会让反射率型器件输出 `peak A = 1.5956`；越界是监视器压 PML 的唯一信号。

## 输入

合成数组三组：正常 / T 全为 -0.80 / 三种 quantity

## 对照与负对照

正：`peak_reflectance`→R、缺省 reflection→A、transmission→T；负：`T=-0.80` 必须抛 ValueError 而不是写出数值。

## 判据

选键 R/A/T 正确；越界必抛。

## 重跑命令

```bash
python _scratch/regress/2026-11-09/test_exp09_10_12.py
```
