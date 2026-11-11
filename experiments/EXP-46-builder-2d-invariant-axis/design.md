# EXP-46 — builder 支持 2D 仿真（z 为不变轴）

## 假设

`_shared/fsp_build.py` 把「沿 z 传播」写死：`z min/max bc`、源 `injection axis=z`、
监视器 `2D Z-normal`、堆栈范围用 `cz ± sz/2`。而 Lumerical 的 `dimension="2D"` 里
**z 是不变轴**，`z min bc` 可读不可写（D-008）。把「传播轴」抽成参数后，
同一份 builder 应能建出 P09 那类 2D 模型（堆栈沿 y、石墨烯是 y 法向面），
不必再手写 ~250 行脚本。

## 输入

- 新增 spec 字段：`simulation.propagation_axis`（3D 默认 `z`，2D 默认 `y`）
- 2D 规格：`_scratch/regress/2026-11-10/EXP-46/p09_2d_spec.json`（按 P09 论文参数手写）

## 方法

1. 探针 `probe_2d_api.py`：在空会话里逐条试写 `dimension="2D"` 下的
   `z min/max`、`z min/max bc`、`z span`、源 `injection axis`、监视器 `monitor type`、
   `add2drect(surface normal)`、`addmesh`，记录哪些可写、哪些报 `inactive`，
   以及 2D 下 power 监视器的 `monitor type` 默认值。
2. 按传播轴泛化 `build_objects` / `build_simulation`；不变轴上的跨度不参与几何范围、
   不写边界、不写 monitor type。
3. 建 `--check` 只建不跑，`layoutmode` 必须仍是 1（0 次求解）。

## 判据

| 指标 | 期望 |
|---|---|
| `layoutmode` | `1.0`（只建未跑） |
| 回读 `FDTD.dimension` | `2D` |
| 回读源 `injection axis` | `y` |
| 回读 R/T 监视器位置 | 与源同轴（y），间距 = `air_above/below` 推导值 |
| 回读 `monitor type` | `2D Y-normal` |
| 2D spec 里出现 `polygon` | **FAIL**（z 法向多边形在 2D 里退化成线，必须拒绝） |
| `dimension="2D"` + `propagation_axis="z"` | **FAIL**（不变轴不能当传播轴） |
| 3D 回归（P01 spec 重建） | 逐字段与改前一致（`z min bc=PML`、源轴 z） |

## 负对照

- 做法 A：2D spec 里放一个 `polygon`（z 法向）→ 期望 builder 抛 `ValueError`，
  提示 2D 只支持 box/2drect/group。若静默建出来，模型是一条线，后续每个数都错。
- 做法 B：`dimension="2D"` 且 `propagation_axis="z"` → 期望抛 `ValueError`。
- 做法 C：用改前的 builder 建同一份 2D spec → 期望
  `in setnamed, the requested property 'z min bc' is inactive`（复现 D-008 原文）。

三条都必须「按预期失败」，缺一不算通过。

## 可重跑命令

```bash
python _scratch/regress/2026-11-10/EXP-46/probe_2d_api.py
python _scratch/regress/2026-11-10/EXP-46/probe_2d_monitors.py
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py --spec _scratch/regress/2026-11-10/EXP-46/p09_2d_spec.json --out _scratch/regress/2026-11-10/EXP-46/build --tag p09_2d --check
python _scratch/regress/2026-11-10/EXP-46/compare_2d_reference.py
python _scratch/regress/2026-11-10/EXP-46/neg_controls.py
```

## 实测

```json
{
  "2d_z_min_bc": "inactive: in setnamed, the requested property 'z min bc' is inactive",
  "2d_z_span_default": 1.7e-06,
  "2d_addrect_z_span_default": 6e-07,
  "addpower_no_type_in_2d": "Linear X",
  "addpower_y_span_in_2d": "FAIL: Type added by 'addpower' doesn't have 'y_span' property",
  "addprofile_xy_in_2d": "2D Z-normal",
  "build": {"layoutmode": 1.0, "solves": 0, "wall_s": 6.5, "span_range_um": [-7.0, 15.0]},
  "check": {"checked": 27, "mismatches": 0},
  "reference": {"compared": 14, "identical": 12},
  "regress_3d": {"objects": 10, "diffs": 0}
}
```

两条与预期不同的实测，都已写进代码注释：

1. **2D 的 power 监视器不是面，是线**。`addpower(x_span=...)` 在 2D 里默认类型是
   `Linear X`，而不是 `2D Y-normal`；给法向 span（`y_span`）直接报「属性不存在」。
   手建的 P09 基准正是 `Linear X`，所以 builder 在 2D 里**不写 monitor type**，
   只给横向 span，让引擎自己命名。field/index 相反：仍是 x-y 面（`2D Z-normal`，
   两个面内 span 都要给）。
2. **2D 里 z 的缺省跨度非零**（FDTD 1.7 µm、rect 0.6 µm），所以不变轴不需要
   发明数字，builder 直接不传该轴，交给引擎缺省。

## 负对照

- 做法 A：`dimension=2D` + `propagation_axis=z` → 预期 `ValueError`
- 做法 B：2D 里写 `z min bc` → 预期引擎报 `inactive`（D-008 原文）
- 做法 C：2D 里放 z 法向 `2drect` → 预期 `ValueError`；同一张面放 3D → 预期正常建出
- 实测：A `REJECTED: 2D 仿真的 z 是不变轴…`；B
  `"in setnamed, the requested property 'z min bc' is inactive"`；
  C `REJECTED: 对象 sheet 是 z 法向的 2D 面…`，3D 对照 `built (as expected)`
- 负对照是否按预期失败：是（3/3）

## 结论

builder 现在能表达 2D：`propagation_axis` 决定堆栈测量轴、边界写在哪两个轴上、
源的注入轴、监视器法向；2D 的 z 从不写边界（写就报 inactive）。
D-008 的「只能手写 250 行」不再成立。

顺带修掉两个静默失真：
- `ellipse` 的 `center` x/y 以前被丢弃（多边形建在原点），现烘进顶点；P02 的
  `center=(0,0,…)` 结果不变。
- `ev()` 以前不接受数字字符串参数，`"d": "4.7e-6"` 时 `d/2` 抛 TypeError；现在先把
  参数表里的字符串转成数字（非法值给明确报错）。

未做：2D 下的相位提取（`run_phase_sweep.py` 已在轴向非 z 时显式
`NotImplementedError`，不再静默建错模型）。

