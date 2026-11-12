# EXP-66 角谱传播：真空往返

## 假设

`propagate(+z)` 之后 `propagate(-z)` 必须还原带限场，相对误差 <1e-6。
**必须用边缘平滑的带限场**：硬边孔径含倏逝分量，往返本就不酉（那是物理，不是 bug）。

## 输入 / 对照

- 正例：`exp(-(x²+y²)/12²)`，N=256、dx=0.5 µm、λ=1.55 µm、z=300 µm
- 负例：把倏逝分支写成 `H[~prop]=1`（丢掉衰减）——它保留的能量必须明显高于正确解

## 判据

`round_trip_rel_err < 1e-6`，且 `E_correct < 0.99 · E_no_decay`。

## 命令

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py --self-test
```

## 负对照

`H[~prop]=1` 的错误实现保留 1953，正确解 1890（差 3.2%）——错误实现被区分出来。
