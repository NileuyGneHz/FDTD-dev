# EXP-54 — 解析真值自检（原计划 9 条，实落 15 条）

## 假设
「算得对」必须由不依赖引擎、不依赖输入文件的解析真值钉死。
新增 10/10b/11/11b 的理由见 PLAN §7.2-①。

## 判据
15 行全 PASS：Parseval 往返 3.73e-16、平面相位→delta 泄漏 0、透镜+倾斜焦点
位置误差 0.735 px（<1）、量化 Strehl 与 sinc² 最大偏差 1.42e-10、pad 窗外能量
3.10e-4、欠采样拒绝、二值量化恰 2 档、网格对称 1.78e-15、空数组拒绝、
复数白名单、GS 收敛、消融不收敛、正对照 FFT/角谱。

## 负对照
变异 M1：把 `npz_arrays` 的 dtype 白名单从 `"fiubc"` 改成 `"fiub"`，
复数字段应被判非法并中止。若不中止，说明白名单不是承重的。

## 命令
```bash
python skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py --self-test
cp skills/fdtd-holo-phase-retrieval/scripts/gs_retrieval.py _scratch/regress/2026-11-11/holo/mut/m1_drop_c.py   # 改白名单后
python _scratch/regress/2026-11-11/holo/mut/m1_drop_c.py --self-test
```

## 结论
15/15 pass。变异体在 self-test 9 处抛
`GSError: 数组 'E' 的 dtype=complex128 不在白名单 fiubc 内` 并中止 —— 该条是承重的。
