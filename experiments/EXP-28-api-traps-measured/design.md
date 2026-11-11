# EXP-28 — P09 报的三条 API 坑：两条成立，一条未复现

## 改动
无代码改动。结论用于决定 builder 的写法：源只用 frequency start/stop；改名必须放最后；批量 setnamed 不作为依赖。

## 方法
同一会话内逐条试：dict 批量、改名后旧名、PlaneSource 频率属性、全局频率回写

## 实测
```json
{
  "A_batch_setnamed": "SUCCEEDED",
  "A_single_setnamed": {
    "x": "ok",
    "y": "ok"
  },
  "A_rename_then_old_name": "LumApiError: \"in setnamed, no items matching the name 'r1' can be found.\"",
  "B_frequency_set": "readable | set: \"in setnamed, the requested property 'frequency' is inactive\"",
  "B_frequency_point_set": "readable | set: \"in setnamed, the requested property 'frequency point' is inactive\"",
  "B_frequency_start_stop": "可读可写",
  "B_global_frequency_followed": false,
  "B_source_centre_hz": 428274940000000.0
}
```

## 负对照
- 做法：用 `setnamed(name, {'x':..,'y':..})` 整批写两个合法属性
- 预期：按 P09 报告应当整批失败
- 实测：SUCCEEDED，且 x=1e-7 / y=2e-7 都写进去了
- 负对照是否按预期失败：是

## 结论
`frequency` / `frequency point` 确实 inactive（可读不可写）、`global source frequency` 确实不回写已存在 source、改名后旧名立即失效——这三条成立。但「dict 批量必失败」在本机 v251 上**未复现**，所以 builder 逐条设参是为了可读与可定位错误，不是因为批量一定坏。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-28/probe_api.py
```
