# EXP-29 — --dump-npz：场/谱数组完整落盘，JSON 只留元数据

## 改动
read_monitors 支持 format=npz（npz + sha256 + shape/dtype），并过滤 dtype=object 的句柄

## 方法
对 P01 的 T 监视器同时用 npz 与 json 取回，比较完整性与体积

## 实测
```json
{
  "npz_keys": [
    "lambda",
    "f",
    "T"
  ],
  "npz_dtypes": [
    "float64",
    "float64",
    "float64"
  ],
  "npz_bytes": 3382,
  "T_points_in_npz": 100,
  "json_bytes": 6685,
  "object_arrays_filtered": [
    "Lumerical_dataset"
  ],
  "max_array_items_would_truncate_at": 2000
}
```

## 负对照
- 做法：未过滤 dtype=object 时把结果存 npz
- 预期：npz 里出现 Lumerical_dataset(object)，读回需要 allow_pickle
- 实测：首版确实写入了 Lumerical_dataset(dtype=object)；过滤后只剩数值数组
- 负对照是否按预期失败：是

## 结论
100 点的功率谱仍小于 max_array_items，真正的价值在场监视器（9 万点）；过滤器避免 npz 退化成 pickle。

## 可重跑命令
```bash
python skills/fdtd-lumerical-session-control/scripts/session_control.py --config _scratch/regress/2026-11-09/sc_reuse_npz.json --out _scratch/regress/2026-11-09/EXP-30/out --json
```
