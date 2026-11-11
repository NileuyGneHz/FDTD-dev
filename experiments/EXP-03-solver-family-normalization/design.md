# EXP-03 [R3] 只比求解器族，不比版本串

## 假设

`Lumerical FDTD` 与 `Lumerical FDTD v251` 是同一求解器，旧逻辑字符串全等 → 同族被判 solver_mismatch，逼人改结论。

## 输入

6 组求解器名：3 组同族（含版本号差异）、3 组异族

## 对照与负对照

正：`Lumerical FDTD` / `Lumerical FDTD v251` / `FDTD Solutions` 判同族；负：`CST` / `FMM (101 orders)` / `COMSOL` 必须判异族。

## 判据

同族 3/3 判同，异族 3/3 判异。

## 重跑命令

```bash
python -c "from tools.check_reproduction import solver_family as f; print(f('Lumerical FDTD'), f('Lumerical FDTD v251'), f('CST'))"
```
