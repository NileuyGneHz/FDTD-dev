# EXP-59 — 端到端真值：正对照 + 已知可实现目标

## 假设
用解析透镜相位生成目标场（因此存在精确解），GS 必须把强度还原回来。
相位本身不可作为判据：单强度面只约束 |E|，相位不唯一（PLAN §7.2-④）。

## 判据
① 正对照：解析相位回灌 `eval_recon` → FFT 残差 0.0，角谱残差 0.00386（倏逝损耗）；
② 透镜目标（角谱，n=128）：GS 强度 RMSE 0.0323、eta 0.884；
③ 恢复相位与解析相位差 1.187 rad —— 记录但**不**作为验收量。

## 负对照
变异 M2：删掉 `target_amplitude()` 里的 `np.sqrt`（把强度当振幅）→ 正对照读
0.311 / 0.349 并 FAIL。修复前的历史值 0.597 与之一致（当时归一化也不同）。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --self-test                                   # 11 / 11b 两行
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --config _scratch/regress/2026-11-11/holo/holo_p05_lens.json \
  --out _scratch/regress/2026-11-11/holo/run_p05
```

## 结论
正对照精确为 0（FFT），GS 对已知可实现目标达 0.0323；相位差不作判据。
