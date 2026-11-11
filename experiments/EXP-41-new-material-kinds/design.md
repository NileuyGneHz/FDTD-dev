# EXP-41 — 新材料：Conductive 3D 与石墨烯 1 nm box 都能读回

## 改动
build_materials 增 conductive_3d 与 graphene_kubo_1nm（Kubo 现算 σ，转 ε 后写 sampled）

## 方法
建完从文件读回 type / conductivity / sampled data 形状

## 实测
```json
{
  "au_type": "Conductive 3D",
  "au_conductivity": 40000000.0,
  "graphene_type": "Sampled 3D data",
  "graphene_points": 50,
  "graphene_max_coefficients": 6.0,
  "graphene_freq_range_thz": [
    2.9979245800000003,
    7.9944655466666665
  ],
  "material_assignment": {
    "ground": "Au_cond",
    "gr_box": "graphene"
  }
}
```

## 负对照
- 做法：把石墨烯材料挂到 2drect 面对象上
- 预期：必须报错并解释 2D 面只接受 RLC/PEC/2D 材料表
- 实测：LumApiError: value supplied is not acceptable for 'material'，builder 现在会包成 ValueError 并指向 D-2 的 1 nm box 路径
- 负对照是否按预期失败：是

## 结论
读回时若把 sampled data 强转 float 会丢掉 k（n 看似 2.6e-35），实际 n+ik ≈ 2.6e-35 + 61.37j，是正常响应。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-40/verify_40_41_42.py
```
