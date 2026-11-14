# D-001 把「未收敛的历史运行」当成参考工程族的代表，并据此臆测 ts 量取面
**状态**：`resolved`（2026-11-07 反解析两工程后订正；见正文与 EXP 记录）
## 根因

P01 的旧结论（`cases/metasurface/P01_Absorber_042/README.md` §5.4、
`skills/fdtd-lumerical-unitcell-simulation/SKILL.md` Examples Step 2）把
`0.808 @ ts=185 nm` 与论文 `0.97 @ 6.0 µm` 的 16 个百分点差异，归因于
「`t = 0.185 µm` 的量取面可能是十字中面／地平面顶面，差 65 nm ≈ 0.2 rad 相位」，
并建议向作者确认。同时把 `~0.82 @ 6.15 µm` 判为「`d2_perfectCross.fsp` 历史运行、
`Auto Shutoff 0.047` 未收敛、不宜作基准」。

2026-11-07 反解析两个课程参考 `.fsp` 后，两条前提都不成立：

1. **层位定义不存在歧义**。`infrared_perfect_absorber.fsp` 与 `d2_perfectCross.fsp`
   的 Al₂O₃ 都是 `z ∈ [-185, 0] nm`（厚 185 nm），地平面 `[-285, -185] nm`，
   十字 `[0, 100] nm`；自建 `spec_p01.json` / `point_00_base.fsp` 逐层完全相同。
   即 185 nm = **地平面顶面 → 十字底面**，与我们的建模口径一致。
2. **0.82 是收敛的、可重现的 Lumerical 答案**。`infrared_perfect_absorber.fsp`
   （Periodic x/y、acc 8、24 nm override、1 ps、`auto shutoff min = 1e-5`）
   的 `_p0.log` 末值 `Auto Shutoff: 8.87508e-06`，7039 步提前收敛；
   工程内已存谱 `peak A = 0.8196 @ 6.1515 µm`，`A@6 µm = 0.7174`。
   自建模型 `0.8083 @ 5.85 µm`，`A@6 µm = 0.7163` —— **在 6 µm 处只差 0.0011**。
   未收敛的只是 `d2_perfectCross.fsp`（PML x/y，跑满 77813 步、末值 0.046734）。
   把两个不同工程、不同边界条件的运行混成「一个 0.82」，是本次误判的直接来源。
3. **材料也已排除**：`getindex` 对 `user_Au` / `Au_paper` 在 4/6/8/10 µm 给出的
   `(n,k)` 与论文 Drude 解析值逐位相同（6 µm: `2.8026 + 43.2457i`，k 比值 1.000）。

真正的差异属于**求解器口径**：论文 Fig.2(a) 的 0.97 来自 CST Microwave Studio 2009
（实验值同为 97%），而 Lumerical FDTD 在该参数集下由两个独立实现给出一致的 ~0.82。
这不是建模错误，也不该用「改 ts 到 120 nm」去凑 0.962 —— 那是拟合，不是复现。

## 修复

1. `skills/fdtd-lumerical-unitcell-simulation/SKILL.md`：
   - CRITICAL §4 区分两个工程，写明收敛判据与各自的末值；
   - Examples Step 1 表格补上收敛的课程主工程一行；
   - Examples Step 2 的「量取面」推断改为「已被 FSP 反解析证伪」，并给出新的偏差结论。
2. 新增 `skills/fdtd-lumerical-fsp-introspection`：规定引用参考工程前必须先反解析
   对象树 / 层位 / 边界 / 网格 / 收敛日志，再与 spec 做结构化 diff。
3. `cases/metasurface/P01_Absorber_042/notes/` 补证据，`README.md` §5 补一条偏差诊断更正
   （`cases/AGENTS.md` 允许的唯一两类补记）。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS

# ① 反解析两个课程工程，核对层位与边界
"$PY" skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py \
  --config skills/fdtd-lumerical-fsp-introspection/assets/inspect_config.example.json \
  --out _scratch/regress/fsp-20261107 --dry-run
# 期望：列出两个 .fsp、mode=both、不开 lumapi 会话

# ② 读工程内已存谱（不重跑）
"$PY" _scratch/p01_fsp_results.py \
  --fsp cases/metasurface/P01_Absorber_042/model/infrared_perfect_absorber.fsp \
  --fsp cases/metasurface/P01_Absorber_042/results/repro_p01/point_00_base.fsp \
  --out _scratch/regress/fsp-20261107/spectra.json
# 期望：A@6µm 分别为 0.7174 / 0.7163，差 < 0.002

# ③ 收敛判据
grep -E "Auto Shutoff|Completed" cases/metasurface/P01_Absorber_042/model/infrared_perfect_absorber_p0.log | tail -2
# 期望：Auto Shutoff: 8.87508e-06（< 1e-5）；Completed 7039 iterations

# ④ 材料对照
"$PY" _scratch/p01_material_probe.py
# 期望：4 个波长上 getindex 与 Drude 解析值 n,k 一致，ratio k/k_drude = 1.000
```

## 影响面

- `cases/metasurface/P01_Absorber_042`：旧 README §5.4「待确认」项作废。
- `skills/fdtd-lumerical-unitcell-simulation`：CRITICAL §4 与 Examples 结论订正。
- **所有把课程 `.fsp` 当黄金对照的包（P02–P10）**：引用前必须区分「哪个工程、
  哪次运行、是否收敛」，不能只凭一个数字。
