# spec 扩展字段：取值、读回证据、坑

本文件只记 `fdtd-lumerical-fsp-build` 相对旧 MIM schema **新增**的东西，以及每一条的实测读回值。
旧字段（`builtin` / `drude` / `constant_nk` / `constant_eps` / `sampled_nk`、`box` / `polygon` /
`cylinder` / `sphere` / `ellipse` / `ring`）见 `fdtd-paper-parameter-extraction/assets/spec_template.json`。

## 材料

### `conductive_3d`

```json
{"kind": "conductive_3d", "conductivity": 40000000.0}
```

建法：`addmaterial("Conductive 3D")` → `setmaterial(name, "conductivity", σ)`。

读回（EXP-41，v251）：

| 属性 | 值 |
|---|---|
| `getmaterial(name, "type")` | `Conductive 3D` |
| `getmaterial(name, "conductivity")` | `40000000.0` |

用在哪：论文把金属写成体电导率而不是 Drude 拟合时（P09 的 Au，σ = 4e7 S/m）。
与 Drude 的差别必须在报告里说明，不能当成同一件事（EXP-35 就是为这条准备的，尚未跑）。

### `graphene_kubo_1nm`

```json
{"kind": "graphene_kubo_1nm", "mu_c_ev": 0.1, "gamma_ev": 0.0001,
 "thickness_nm": 1.0, "wavelength_start_um": 37.5, "wavelength_stop_um": 100.0,
 "points": 50, "temp_k": 300}
```

建法：按 Kubo 现算 σ(ω)，再折算成 `ε = 1 + iσ/(ε0 ω Δ)`，把 **(频率, ε)** 直接写进
`Sampled data` 材料（D-013：该属性吃的是 ε，不是 n+ik）。

读回（EXP-41）：

| 属性 | 值 |
|---|---|
| `type` | `Sampled 3D data` |
| `sampled data` 形状 | `(50, 2)` |
| `max coefficients` | `6.0` |
| 频率范围 | 2.998–7.994 THz |

两个必须记住的点：

1. **`gamma_ev` 是能量尺度的散射率**（论文记 `2Γ`）。若把 `Γ_energy/ħ` 传进来，每个峰的位置都会
   偏一半。P09 报告的 2.1e-6 相对误差就是用这个口径对齐的。
2. **读回时别把复数当实数**：`np.asarray(...).astype(float)` 会丢掉 `k`，你会看到
   `n ≈ 2.6e-35` 并以为材料错了。实际上 `n+ik = 2.6e-35 + 61.37j`，是正常的地铁式响应
   （ε ≈ −3766）。

### 为什么不用 2D sheet（D-2）

`add2drect` 建出来的面对象只接受 RLC / PEC / 2D 材料表，给它任意介质会报：

```
in setnamed, the value supplied is not acceptable for the property 'material'
  Expected type is String from this list: "<RLC>", "PEC (Perfect Electrical Conductor)"
```

所以石墨烯走 1 nm box；`2drect` 只用来放 PEC 之类的理想面。

## 几何

### `2drect`

```json
{"id": "patch", "type": "2drect", "material": "PEC",
 "center": ["0", "0", "0.2e-6"], "span": ["0.2e-6", "0.2e-6"], "surface_normal": "z"}
```

零厚度：**不参与 z 堆栈计算**（否则 `build_objects` 会把 z 范围算成 0 附近，导致 air/PML 位置全错）。

### `group`（可带 script）

```json
{"id": "vortex", "type": "group", "script": "addrect; set('name','ant'); ..."}
```

`script` 原样写入工程。P06 的 30×30 涡旋结构、八个八分圆各一种 V 天线，几何真值就在这段脚本里
——反解析（`inspect_fsp`）会把 `script_chars` / `script_sha256` 记进 manifest。

## 源：频率口径

```json
"source": {"frequency_range_thz": [3.0, 8.0], "npts": 51}
```

- 生成时换算成 `frequency start/stop`（Hz）。
- **`frequency` 与 `frequency point` 在 PlaneSource 上是 inactive**（EXP-28：可读不可写，
  `setnamed` 报 `property 'frequency' is inactive`）。只有 start/stop 能设。
- `setnamed("FDTD","global source frequency", ...)` **不会回写已存在的 source**
  （EXP-28 实测：改前改后都是 428.27 THz）。别用它去"统一改源"。

## 监视器

```json
"monitors": [
  {"name": "R", "kind": "power", "z": "auto"},
  {"name": "Efield", "kind": "field", "z": 0.6e-6, "n_freq": 1},
  {"name": "nidx", "kind": "index", "z": 0.6e-6, "n_freq": 1}
]
```

| kind | 建法 | 典型读回键 |
|---|---|---|
| `power` | `addpower` + `monitor type = 2D Z-normal` | `lambda` / `f` / `T` |
| `field` | `addprofile` | `E`（单数组，含分量）、`x`、`y` |
| `index` | `addindex` | `index_x` / `index_y` / `index_z` |

`z: "auto"` 由 `air_above` / `below_structure` 推导（R 在上、T 在下），不要手写死数字：
EXP-25 证明监视器压进 PML **仍会返回数据**，只是非物理，只有几何闸能拦。

旧式 dict 写法 `{"R": {"z": "auto"}, "T": {"z": "auto"}}` 仍然支持（P01 就是这种）。

## 源：plane / gaussian / mode（2026-11-12 新增）

```json
"source": {
  "type": "plane | gaussian | mode",
  "direction": "Backward",
  "polarization_deg": 0,
  "wavelength_range": [1.5e-6, 1.6e-6],
  "gaussian": {"waist_radius_um": 5.0, "distance_from_waist_um": 2.0,
               "lens_diameter_um": 0, "fill_lens": false},
  "mode": {"mode_selection": "fundamental TE", "n_trial_modes": 1}
}
```

| type | 建法 | 写入的属性 |
|---|---|---|
| `plane`（旧名 `plane_wave` 仍认） | `addplane` | injection axis / direction / 位置 / 偏振角 / 波长或频率 / 横向 span |
| `gaussian` | `addgaussian` | 以上 + `waist radius w0`、`distance from waist`、可选 `lens diameter` / `fill lens` |
| `mode` | `addmode` | injection axis / direction / `mode selection` / `number of trial modes` / `frequency start`,`stop` |

**两个实测坑（v251）**：

1. `beam radius wz` 在默认 `beam parameters='Waist size and position'` 下**只读**，
   `setnamed` 抛 `property 'beam radius wz' is inactive`。要写 **`waist radius w0`**。
2. `mode selection` 传 `"fundamental TE"`，引擎会归一成 **`"fundamental TE mode"`**；
   读回比对时别按输入字符串逐字比。

**回归**：旧的 `plane` 路径逐字节不变——P01 spec 重建仍是 **474963 B / 11 对象 / `--check` 39 项 0 mismatch**（EXP-69）。

