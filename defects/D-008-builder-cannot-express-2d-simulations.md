# D-008：builder 无法表达 2D 仿真（z 是不变轴）
**状态**：`resolved`（2026-11-10，EXP-46：`resolve_axes` 问轴而非假定 z）
- 状态：**已修**（2026-11-10，EXP-46）
- 发现：2026-11-09，EXP-42 准备阶段
- 影响技能：`fdtd-lumerical-fsp-build`、`_shared/fsp_build.py`

## 现象

给 spec 设 `"dimension": "2D"` 后建模型，`build_simulation` 在

```python
f.setnamed("FDTD", "z min bc", bc["z"])
```

抛：

```
lumapi.LumApiError: "in setnamed, the requested property 'z min bc' is inactive"
```

同一时刻 `getnamed("FDTD", "z min bc")` **能读到** `PML`——即属性存在但不可写。

## 根因（实测）

```text
addfdtd(dimension="2D") 之后：
  x min bc / x max bc  可读可写
  y min bc / y max bc  可读可写
  z min bc / z max bc  可读，不可写
```

2D FDTD 的不变轴是 **z**：仿真在 x–y 平面内传播，z 方向没有网格、没有边界可设。
而 `_shared/fsp_build.py` 整条链路都按"沿 z 传播"写死：

- `build_simulation` 的 `z_max/z_min`、`z min/max bc`
- 源 `injection axis = z`、监视器 `monitor type = 2D Z-normal`
- 监视器 z 位置由 `air_above` / `below_structure` 推导
- `build_objects` 用 `min/max(cz ± sz/2)` 算堆栈范围（2D 时应沿 y）

P09 的模型正是"堆栈沿 y、石墨烯是 2D 面"这一类，所以它当时只能手写 ~250 行脚本。

## 影响

- 2D 周期结构（P09 石墨烯吸收器、ribbon 阵列）**不能**用 spec 建，只能手写。
- `build_fsp.py --check` 对 2D 也无意义（字段根本建不出来）。
- 与 D-2（石墨烯走 1 nm box）不冲突：1 nm box 仍是 3D 材料，但若整个仿真要 2D 化省机时，就撞上这条。

## 第二轮建议做法

1. spec 增 `simulation.invariant_axis`（`z` 默认 / `y`），把"传播轴"与"不变轴"分开。
2. **轴通用化**：`build_objects` 返回 `(lo, hi)` 沿 `propagation_axis`；`build_simulation` 按轴
   拼属性名（`x/y/z span`、`* min bc`、`injection axis`、`2D {X,Y,Z}-normal`）。
3. 2D 时跳过不变轴的 BC 设置（不是"设成 PML"，是不设）。
4. 判据：P09 的 spec 用 2D 建出来后，`inspect_fsp` 读到 `dimension=2D`，且峰位与 11-08 手写脚本
   一致（3.511 THz / 7.188 THz，误差 ≤ 采样步长 10 GHz）。

## 复现命令

```bash
python - <<'PY'
import json, os, sys
sys.path.insert(0, r"F:\Lumercial_WS\FDTD_WS\_shared")
os.environ.setdefault("ANSYSLMD_LICENSE_FILE", "1055@localhost")
sys.path.insert(0, r"F:\Lumercial_WS\ANSYS Inc\v251\Lumerical\api\python")
import lumapi
f = lumapi.FDTD(hide=True)
try:
    f.addfdtd(dimension="2D")
    print(f.getnamed("FDTD", "z min bc"))          # 可读
    f.setnamed("FDTD", "z min bc", "PML")          # 可写吗？
except Exception as e:
    print("setnamed ->", str(e).splitlines()[0])
finally:
    f.close()
PY
```

## 修复（2026-11-10，EXP-46）

`_shared/fsp_build.py` 新增 `resolve_axes(sim)`，返回
`(dimension, propagation_axis, lateral_axes, invariant_axis)`；
`build_objects` / `build_simulation` 全部改成「问轴」而不是「假定 z」：

| 位置 | 3D | 2D（p=y） |
|---|---|---|
| 堆栈范围 | min/max over z | min/max over y |
| 区域中心/跨度 | z 中心、z span | y 中心、y span；x 用晶格周期 |
| 边界 | x/y/z 都写 | **只写 x/y**，z 不写 |
| 源 | `injection axis=z`，x/y span | `injection axis=y`，x span（法向不给 span） |
| power 监视器 | `2D Z-normal`，x/y span | **不写 type**（引擎给 `Linear X`），只给 x span |
| field/index 监视器 | `2D {X,Y,Z}-normal` | 不写 type（引擎给 `2D Z-normal`），x/y span 都给 |
| mesh override | `z_range` | `y_range`（旧键 `z_range` 仍认） |

判据与结果见 `experiments/EXP-46-builder-2d-invariant-axis/`：
2D 建出 `layoutmode=1.0`、`--check` 27 项 0 mismatch、
P09 手建基准逐字段对比 12/14 一致（差额是源/监视器横向跨度，基准用 10 µm 宽于
2 µm 周期胞）、P01 3D 回归 10 个对象 0 diff。

两条实测订正写进了代码注释，避免下一个人再猜：
- 2D 的 power 监视器是**线**，默认类型 `Linear X`，给法向 span 直接报属性不存在；
- 2D 里 z 的缺省跨度非零（FDTD 1.7 µm、rect 0.6 µm），所以不变轴不传 span 也不会得到 0。

未修：2D 的相位提取。`run_phase_sweep.py` 在轴向非 z 时显式
`NotImplementedError`，不再静默建错模型。
