---
name: fdtd-lumerical-fsp-build
description: >
  从 JSON model spec 一键生成 Lumerical FDTD 工程（.fsp），**不跑仿真**。
  覆盖材料（builtin / drude / constant_nk / constant_eps / sampled_nk / conductive_3d /
  graphene_kubo_1nm）、几何（box / polygon / cylinder / sphere / ellipse / ring / 2drect / group）、
  求解区与边界（含 2D 声明）、平面波源（波长或频率口径）、监视器（power / field / index）。
  build 与 solve 分离：30 秒内拿到可交付模型，不再为了一个 .fsp 先付一次完整机时。
  触发词：建 fsp、一键建模、build-only、生成工程、spec 转 fsp、加场监视器、频域源、石墨烯材料。
agent_created: true
---

# fdtd-lumerical-fsp-build（stage 2）

## 1. 什么时候用它

| 想做的事 | 用这个技能 |
|---|---|
| 我有一份 spec，想先拿到 `.fsp` 看结构 / 交付 / 别人接手 | ✅ `build_fsp.py` |
| 建完之后要跑谱（R/T/A） | 不在这里 —— 转 `fdtd-lumerical-unitcell-simulation` |
| 已有 `.fsp`，只想改几个尺寸接着算 | 不在这里 —— 转 `fdtd-lumerical-session-control` |
| 已有 `.fsp`，想读它的对象树 / 材料 / 存谱 | 不在这里 —— 转 `fdtd-lumerical-fsp-introspection` |

**边界**：本技能只写文件，不 `run`、不产生 `_p0.log`。`layoutmode` 保持 1（layout 模式）。
这不是缺陷，是定义：留下"还没算"的状态，让下游的 `assert_ran` 有意义。

## 2. 核心工作流

```bash
# ① 先看计划（不开会话，0.2 s）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/build/p01 --dry-run --json

# ② 建 + 自检（读回文件，逐字段与 spec 比对）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec cases/metasurface/P01_Absorber_042/config/spec_p01.json \
  --out _scratch/build/p01 --tag p01 --check --json

# ③ 只检查一个已有工程与 spec 是否一致（不重建）
python skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
  --spec <spec.json> --only-check <某.fsp> --out _scratch/build/p01 --json
```

退出码：`0` 成功 / `1` `--check` 发现字段不一致（会逐条打印 object、property、expected、actual）
/ `2` 参数或 spec 错误。

## 3. CRITICAL（违反即停止）

1. **本技能不 `run()`**。`run()` 一调用就产生 `_p0.log`、`layoutmode` 变 0，下游的
   `assert_ran` 立刻失去意义（它会以为这是"跑过并且有结果"的工程）。要谱请转 stage 2/3。
2. **`--check` 不一致时不许交付**。exit 1 表示"文件与 spec 不符"，先弄清是哪一侧错，
   不许"反正差 10%、可以解释"就放行（EXP-43 的两个 mismatch 正是这么被抓到的）。
3. **石墨烯只走 1 nm box**（D-2）。`2drect` + 石墨烯材料必然报
   `value supplied is not acceptable for the property 'material'`；这不是 bug，是对象类型限制。
4. **不要复制 builder 进来**。改行为请改 `library/py/fsp_build.py`，两个调用方（本技能与
   `run_fdtd_sweep.py`）必须始终指向同一份实现。

## 4. 三条硬规则

1. **`--check` 不是可选项而是习惯**。它读回刚保存的 `.fsp`，把每个 span / center / radius /
   mesh accuracy 与 spec 求值结果比对，容差 `max(1e-9, |值|·1e-9)`。不一致就 exit 1。
   事件：EXP-43 把 spec 里 `l` 改大 10%，`--check` 报出
   `cross_x x span expected=1.87e-06 actual=1.7e-06`（两处），exit 1。
2. **不要把 builder 复制进本技能**。实现在 `library/py/fsp_build.py`，本技能只是 CLI 外壳；
   `run_fdtd_sweep.py` 也 import 同一份。D-005 / D-006 / EXP-02 三次事故都是"复制一份再各自改"。
3. **石墨烯只走 1 nm box**（D-2）。2D 面对象不接受任意材料：`2drect` 只支持 RLC / PEC /
   2D 材料表，给石墨烯会报 `value supplied is not acceptable for the property 'material'`。
   用 `kind: graphene_kubo_1nm` + 一个 `thickness_nm: 1` 的 `box`。

## 5. spec 扩展字段（相对 MIM 单胞 schema 新增）

阵列（EXP-60…64，PLAN-2026-11-11-percell-fsp）：

```json
{"id": "meta", "type": "array", "material": "TiO2", "mesh_order": 2,
 "grid": {"nx": 64, "ny": 64, "pitch": ["0.4e-6", "0.4e-6"], "origin": ["-12.8e-6", "-12.8e-6"]},
 "element": {"type": "box", "center": ["0", "0", "h/2"], "span": ["d1", "d2", "h"]},
 "cell_params": [{"i": 0, "j": 0, "d1": "0.16e-6", "d2": "0.16e-6"}, ...]}
```

- 作用域：每格求值时 `全局 parameters ⊕ {i, j} ⊕ cell_params[k]`（后者优先），
  复用 `ev()`，无新求值器；`cell_params` 为空/省略 = 所有格子共用全局参数。
- 行主序：`divmod(k, nx)`，y 外层 x 内层；显式 `i`/`j` 标注与位置不一致会**报错**。
- `engine` 只支持 `"objects"`；脚本引擎（group_script）未实现（PLAN §10-1）。
- 规模：>2000 格警告、>8192 格硬拒绝（`_MAX_CELLS_OBJECTS` / `_HARD_LIMIT_CELLS`）。
- 想从相位 CSV 自动生成 cell_params：转 `fdtd-metasurface-assembly`（stage 1.9）。
- `--check`：逐格全量断言（box/cylinder/ring/2drect），ellipse/ polygon 单元降级为
  z/z span（引擎侧无 x/y/x span 属性，EXP-64）；改一格尺寸必红、且指名
  `{id}_r{i}c{j}` 与属性名（EXP-61）。
- 64×64 实测：build 383 s、6.9 MB、layoutmode=1、无 `_p0.log`，check 12298 项 0 mismatch。

材料：

```json
"Au_cond":   {"kind": "conductive_3d", "conductivity": 40000000.0},
"graphene":  {"kind": "graphene_kubo_1nm", "mu_c_ev": 0.1, "gamma_ev": 0.0001,
              "thickness_nm": 1.0, "wavelength_start_um": 37.5,
              "wavelength_stop_um": 100.0, "points": 50}
```

- `conductive_3d` → 读回 `type = "Conductive 3D"`，`conductivity` 逐位等于给定值。
- `graphene_kubo_1nm` → 读回 `type = "Sampled 3D data"`、`sampled data` 形状 `(points, 2)`、
  `max coefficients = 6`。σ 由 Kubo 现算：`ε = 1 + iσ/(ε0 ω Δ)`。
  `gamma_ev` 是**能量尺度**的散射率（论文里的 `2Γ`）；传 `Γ/ħ` 会让每个峰移一半。
  ⚠️ **`sampled data` 属性收的是复介电常数 ε，不是 (n,k)**（D-013 实测：灌 `4+0i`
  用 `getindex` 读出 `2.0`）。builder 内部已把 (n,k) 换成 `(n+ik)²`；自己手写
  `setmaterial(name,"sampled data",[f, n+1j*k])` 会让引擎再开一次方——石墨烯
  的 ε≈2611i 会变成 51i，吸收弱 51 倍。验证方法：`getindex(name, f_Hz)` 反查一个点。
  ⚠️ **1 nm 层必须配网格覆盖**：粗网格（acc 2，dy≈200 nm）会把 1 nm 的 ε 摊薄到
  0.5%，A 从 1 掉到 0.01；`mesh_override.dy ≤ 1e-9` 才行。

几何：`2drect`（零厚度片，不参与 z 堆栈计算）、`group`（可带 `script`，原样写入工程）。

源：

```json
"source": {"frequency_range_thz": [3.0, 8.0], "npts": 51}
```

THz 论文按频率写。**`frequency` / `frequency point` 在 PlaneSource 上是 inactive**
（EXP-28 实测：可读不可写），唯一可行路径是 `frequency start/stop`（Hz），本技能替你换算。
`global source frequency` 不会回写已存在的 source，别指望它改源。

监视器：

```json
"monitors": [
  {"name": "R", "kind": "power", "z": "auto"},
  {"name": "Efield", "kind": "field", "z": 0.6e-6, "n_freq": 1},
  {"name": "nidx",  "kind": "index", "z": 0.6e-6, "n_freq": 1}
]
```

`kind` ∈ `power` / `field` / `index`；缺省 `power`。也接受旧式 dict 写法
`{"R": {"z": "auto"}, "T": {"z": "auto"}}`（P01 就是这种，两种都能读）。

**2D 模型**（EXP-46）：`dimension: "2D"` + `propagation_axis: "y"`，堆栈沿 y 排、
z 是不变轴。此时 `z` 位置（源、监视器、`mesh_override.y_range` 同理按轴名）
写成 `y`；监视器可以显式给 `span: {"x": "10e-6", "y": "1.6e-6"}` 覆盖缺省跨度。

```json
"simulation": {
  "dimension": "2D", "propagation_axis": "y",
  "bc": {"x": "Periodic", "y": "PML", "z": "PML"},
  "air_above": 15e-6, "below_structure": 1.3e-6,
  "source": {"frequency_range_thz": [3, 8], "plane_wave_type": "Bloch/periodic"},
  "monitors": [{"name": "R", "kind": "power"}, {"name": "T", "kind": "power"},
               {"name": "field", "kind": "field", "y": 0, "span": {"x": "10e-6", "y": "1.6e-6"}}]
}
```

## 6. 已知边界（不假装支持）

- **2D 的三条硬约束**（实测，别猜）：
  1. `z min/max bc` 在 2D 里**可读不可写**，builder 因此从不写不变轴的边界；
  2. **2D 的 power 监视器是一条线，不是面**——`addpower(x_span=...)` 的默认类型
     是 `Linear X`，给它法向 `y_span` 直接报「属性不存在」。builder 在 2D 里
     **不写 `monitor type`**，只给横向 span，让引擎命名；field/index 相反，
     仍是 x-y 面（`2D Z-normal`，两个面内 span 都要给）。
  3. `propagation_axis="z"` 与 `dimension="2D"` 同时出现会被拒绝；2D 里 z 法向的
     `2drect` 也会被拒绝（那张面在结果里不存在）——两者都是**静默出错**的来源，
     所以选择报错而不是猜。
- **结构组只写 `script` 与名字**，不展开子对象；`number` 这类参数留给 introspection 读。

## 7. Examples

**给 P06 那种 30×30 结构组建模型**（组内几何由脚本生成）：

```json
{"objects": [
  {"id": "vortex", "type": "group",
   "script": "addrect; set('name','ant'); set('x',i*1.5e-6); ..."}
]}
```

**交付前的最小验证链**：

```bash
build_fsp.py --spec ... --out ... --check --json      # 字段与 spec 一致
inspect_fsp.py --config <cfg> --out ... --json        # 对象树 / 材料 / 存谱
```

两条都过，才把 `.fsp` 交给人。

## 8. References / 按需加载

| 文件 | 什么时候读 |
|---|---|
| `references/spec_extensions.md` | 写新材料 / 新监视器 / 频域源 / gaussian·mode 源之前；含每条的读回证据与坑 |
| `references/finite-device.md` | 建有限口径器件（透镜/衍射层）之前：PML 怎么配、为什么 `A=1−R−T` 失效、网格预算 |
| `library/py/fsp_build.py` | 要改建模行为时（唯一实现） |
| `skills/fdtd-lumerical-fsp-introspection/SKILL.md` | 建完要核对对象树 / 材料 / 存谱时 |

按需加载：只有写扩展字段时才读 references；只建 P01 这类旧 schema 的单胞不需要。

## 9. 相关文件

| 文件 | 用途 |
|---|---|
| `scripts/build_fsp.py` | 本技能唯一入口（build / check） |
| `library/py/fsp_build.py` | 唯一 builder 实现（材料 / 几何 / 阵列 / 求解区 / 源 / 监视器） |
| `references/spec_extensions.md` | 扩展字段的完整取值与读回证据 |
| `skills/fdtd-metasurface-assembly/SKILL.md` | 从相位 CSV 装配 array spec 时 |
| `skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py` | 建完反解析核对 |
| `experiments/EXP-38…43, EXP-60…64` | 抽取回归、build-only、监视器、材料、频域源、check、阵列 |
