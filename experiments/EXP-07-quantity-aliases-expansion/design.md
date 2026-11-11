# EXP-07 [R13] 别名表补齐反射率/带宽/峰位/焦距/OAM

## 假设

`QUANTITY_ALIASES` 只有吸收/透射/相位族，反射率型与场型复现没有一条通路能过 R13。

## 输入

6 个新 quantity 名 + 1 个错拼名

## 对照与负对照

正：6 族全部存在且能取到列名集合；负：`peak_reflectence`（错拼）必须不被认识。

## 判据

6/6 存在；错拼被拒。

## 重跑命令

```bash
python -c "from tools.check_reproduction import QUANTITY_ALIASES as q; print(len(q), 'peak_reflectence' in q)"
```
