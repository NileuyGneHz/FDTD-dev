# EXP-05 [R6] 单次成本过高可豁免重跑，但不能判 reproduced

## 假设

876 s/次的仿真无法要求重复两遍；但豁免后仍判 `reproduced` 就是把单次结果当结论。

## 输入

4 张卡：876 s+理由+inconclusive / 876 s+reproduced / 60 s+理由 / 876 s 无理由

## 对照与负对照

正：第一张放行；负：其余三张分别因「判 reproduced」「成本未达门槛」「没写理由」被拒。

## 判据

R6 行分别为 OK / FAIL(reproduced) / FAIL(门槛) / FAIL(reason)。

## 重跑命令

```bash
$PY tools/check_reproduction.py --card _scratch/regress/2026-11-09/EXP-05/ok/card.md
```
