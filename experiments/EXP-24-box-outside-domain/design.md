# EXP-24 — 盒子抬到 4 m：三判据全过但结果为空 -> 加第四判据与日志扫描

## 改动
lumapi_common.assert_ran 新增 monitors 参数（getresult 至少一个非空）；新增 assert_has_results()；日志扫 'outside the simulation' 直接判死；新增几何闸 assert_in_domain() / monitor_domain_report()

## 方法
把 FDTD 的 z 从 0 改成 4.0（米），跑完对比：assert_ran 旧三判据 / 新四判据 / 几何闸；再对健康模型做阴性对照

## 实测
```json
{
  "box_at_4m_old_three_criteria": "passed",
  "box_at_4m_getresult": "LumApiError: Can not find result 'T' in the result provider 'monR'",
  "box_at_4m_layoutmode": 0.0,
  "box_at_4m_p0_has_completed": true,
  "box_at_4m_log_warning": "Monitor ::model::monR is outside the simulation and will not record any data",
  "new_gate_on_box_at_4m": "REJECTED: B_box_at_4m_p0.log 报「Monitor ::model::monR is outs",
  "new_geometry_gate_on_box_at_4m": "REJECTED: 监视器与 FDTD 边界不足 0.300 um（或已在盒外）: monR=outside。PML 内",
  "healthy_case_gate": "pass",
  "healthy_case_geometry": "pass (1 monitors)"
}
```

## 负对照
- 做法：健康模型 A_no_resave.fsp
- 预期：两个新闸都放行（否则就是误伤）
- 实测：domain_gate=pass (1 monitor)，assert_ran=pass
- 负对照是否按预期失败：是

## 结论
三判据只能证明「引擎跑过」。日志里其实早有 'outside the simulation' 这行，读它比读 layoutmode 更有信息量。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-22/probe_false_pass.py
python _scratch/regress/2026-11-09/EXP-24/test_guards.py
```
