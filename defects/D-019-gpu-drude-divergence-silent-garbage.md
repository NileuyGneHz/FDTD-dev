# D-019：GPU 跑含 Drude 金属的工程会发散，但**脚本不报错**，产物是垃圾数据

**状态**：`resolved`（2026-11-11，靠 `tools/gpu_guard.py` 判据拦截；物理不可修复，只能规避）

## 根因

GPU 引擎是 **real32 单精度**。Drude 模型的金属在某个频段实部 ε 落在 `0 < ε < 1`，
real32 的舍入误差在这里会被放大 → 场发散。引擎确实检测到了，但：

1. 日志里只有 `ERROR: Early termination ... fields are diverging`
2. 紧接着还有一行 `Simulation completed successfully at: ...` ← **误导**
3. `run()` 正常返回，**不抛异常**
4. 监视器结果变成 0 或垃圾值

结果就是「看起来跑完了，数字全错」。

## 实测对照（2026-11-11，同一 spec 同一机器）

工程：`cases/metasurface/P01_Absorber_042/config/spec_p01.json`（Au Drude + Al2O3 + Si）

| 引擎 | wall | 迭代数 | peak A | 日志 | 结论 |
|---|---|---|---|---|---|
| **CPU**（8 proc，`fdtd-engine-msmpi`） | **29 s** | 完整跑完 | **0.8069 @ 5.850 µm** | 无 `0<ε<1` 警告 | ✅ 与历史基线一致 |
| **GPU**（RTX 3070，`fdtd-engine` real32） | **12 s** | **303**（早停） | **1.0000 @ 4.400 µm** | 有 `0 < permittivity < 1` + `diverging` | ❌ 垃圾数据 |

**GPU 快了 2.4 倍，但答案是错的**：A = 1.0000 意味着「完美吸收全波段」，物理上不可能；
FWHM 4.5 µm 覆盖了整个扫描范围，也是发散后的平坦曲线特征。

这正是「快 ≠ 对」的教科书案例，也是为什么本工作区的铁律里有
「不隐瞒失败轮次、不替人下物理正确的结论」。

## 修复

物理上**不可修复**（real32 是硬件限制）。只能规避，已落地为两道闸：

### 1. `tools/gpu_guard.py`：跑前判定，跑完还原

```powershell
$PY="C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

# 包住一次运行：跑前按判据切，跑完（含异常）自动切回
& $PY tools/gpu_guard.py --fsp <工程.fsp> --run "python skills/.../run_fdtd_sweep.py --spec ..."
```

判据复用 `probe_gpu_eligibility.classify`，**不另写一套**：

| 判据 | 结论 |
|---|---|
| 路径非 ASCII | `cpu_only`（GPU 1113） |
| 含 TFSFSource | `cpu_only`（D-011） |
| dimension=2D | `cpu_only`（D-008） |
| 含 Drude / Conductive / 强损耗金属 | `gpu_risky` → **默认走 CPU** |
| 显存 > 85% VRAM | `cpu_only` |
| 其余（全介质） | `gpu` |

`gpu_risky` 要上 GPU 必须显式 `--allow-risky`（接受风险）或 `--probe-log`
（用已有 `_p0.log` 证明历史上没发散）。

### 2. `--probe-log` 的真判据：`0 < permittivity < 1`

「含金属」不等于「一定发散」。实测对照：

| 工程 | 金属模型 | GPU 日志 | 结果 |
|---|---|---|---|
| P04 `fig4` | Au **(n,k) 采样** | 无 `0<ε<1` | ✅ 12165 iter / 340 s / Shutoff 8.4e-6 |
| P03 `fig1_hwp_paper_materials` | **Drude** | 有 `0<ε<1` | ❌ 51523 iter 后 diverging |
| P01 `spec_p01` | **Drude** | 有 `0<ε<1` | ❌ 303 iter 后 diverging |

**发散前兆是那条警告，不是材料名**。所以 `log_says_safe()` 检查：
有 `0 < permittivity < 1` → 拒绝；有 `diverging` → 拒绝；无 `Completed`/`Auto Shutoff` → 拒绝。

### 3. `tools/gpu_mode.py`：安全切全局开关

不碰 `setresource`（它持久化并会污染配置，见 `field-manual.md` §6.3），
直接改 ini 的 `FDTD\GPU-mode` 一行，改前备份、改后读回确认、GUI 在跑时拒绝改。

## 验证

```powershell
$PY="C:\Users\saber\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

# 判据正例：全介质工程应放行 GPU
& $PY tools/gpu_guard.py --fsp cases/metasurface/P03_HWP_Ding2015/model/t4_tio2_unitcell.fsp --dry-run
# 期望：GPU ... 3D + 平面波源 + 介质/低显存 -> 可走 GPU

# 判据负例：Drude 工程必须拦下
& $PY tools/gpu_guard.py --fsp cases/metasurface/P01_Absorber_042/model/d2_perfectCross.fsp --dry-run
# 期望：CPU ... 金属/有损材料 ['user_Au'] ... 走 CPU

# 负例：日志有发散前兆必须拦下
& $PY tools/gpu_guard.py --fsp cases/metasurface/P03_HWP_Ding2015/model/fig1_hwp_paper_materials.fsp --dry-run --probe-log
# 期望：CPU ... --probe-log 未放行：日志有 `0 < permittivity < 1` → 实测会发散

# 全局开关可逆
& $PY tools/gpu_mode.py --status      # 期望 GPU-mode=false
& $PY tools/gpu_mode.py --self-test   # 期望 2 正例 + 3 负例通过
& $PY tools/gpu_guard.py --self-test  # 期望 5 例通过
```

实测（2026-11-11）：上述全部符合预期。

## 影响面

- `cases/P01` 与 `cases/P03` 的 Drude 工程：**禁止上 GPU**
- `cases/P04` 的 Au 采样工程：GPU 可用（历史实测成功）
- 全介质工程（TiO2/Si 超表面）：GPU 可用
- `tools/probe_gpu_eligibility.py` 的 `gpu_risky` 判定现在有了实测依据（不再是「可能」）

## 遗留

1. **引擎不报错**这一点改不了。所有走 GPU 的跑批必须**事后**检查 `_p0.log` 有无
   `diverging` 或 `0 < permittivity < 1`——`gpu_guard` 目前只做跑前判定，
   没有做跑后校验。建议后续给 `run_fdtd_sweep.py` 加一条「产物有效性」检查。
2. `dt stability factor` 调到 0.95 能缓解（`field-manual.md` §6.3 实测：
   404 步发散 → 8777 步跑完），但 real32 精度问题仍在，非物理值（层吸收和 > 1）仍可能出现。
   **本工作区结论一律以 CPU 双精度为准**，GPU 只用于「快速探索 / 粗筛」。
