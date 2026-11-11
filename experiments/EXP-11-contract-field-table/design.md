# EXP-11 契约 §7 字段表补齐

## 假设

P05/P06 报告说 `locked.geometry`、`target.measured_columns` 只能靠试错；§7 表里没有，卡就只能靠猜。字段名不登记，门禁与文档就会各说各话。

## 输入

`docs/constitution/reproduction-contract.md` §7 表

## 对照与负对照

正：4 个报告点名字段（`locked` / `measured_columns` / `numerics_aligned_from` / `caliber`）全部出现；额外 4 个本轮新增字段（`repeat_cost_s` / `repeat_skipped_reason` / `unrun` / `layoutmode`）也出现。
负：拼错的 `measued_columns` 必须不出现（防止检查退化成「包含任意子串」）。

## 判据

8/8 字段在表内；错拼不在表内。

## 重跑命令

```bash
python _scratch/regress/2026-11-09/test_exp11.py
```
