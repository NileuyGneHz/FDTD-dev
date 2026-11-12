# EXP-68 传播器与 holo 的 `propagate()` 逐点一致

## 假设

`library/py/angular_spectrum.propagate()` 与
`skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py::propagate()` 是同一数学，
同一输入下 max|diff| 必须为 0（<1e-12 即判过）。

这条存在的意义：本仓库被"两份实现随改名腐烂"坑过三次（D-005、D-006、EXP-02），
新增传播器时先把一致性钉死，避免第三次。

## 判据

`max|diff| < 1e-12`。

## 命令

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py --self-test
```

## 负对照

把负距离当正向（符号反）：与 holo 的差跳到 **3.386e-01**，远大于 1e-12——
说明这条一致性检查对符号错误敏感，不是"两边都调用同一个库"的空转。
