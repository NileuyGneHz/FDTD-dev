# EXP-69 源类型扩展：gaussian / mode，且 plane 路径逐字节不变

## 假设

在 `fsp_build.build_simulation` 里加 `source.type` 分派后：
① 旧 spec（`type: plane_wave`）的产物必须与改前**逐字节相同**（P01 基线 474963 B / `--check` 0 mismatch）；
② `gaussian` 建出的必须是 `GaussianSource` 且 `waist radius w0` 等于 spec；
③ `mode` 建出的必须是 `ModeSource`。

## 判据

- P01：文件 474963 B、`--check` mismatches=0
- gaussian：`getnamed("source","type") == "GaussianSource"`，w0 = 5.0 µm
- mode：`type == "ModeSource"`
- 负例：`type: hologram` 必须 exit 1 并报 `unsupported source.type`

## 命令

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
    --spec cases/P01_Absorber_042/config/spec_p01.json \
    --out _scratch/regress/2026-11-12/EXP-69/p01 --tag p01 --check
"$PY" skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
    --spec _scratch/regress/2026-11-12/EXP-69/spec_gauss.json \
    --out _scratch/regress/2026-11-12/EXP-69/gauss --tag gauss --check
"$PY" skills/fdtd-lumerical-fsp-build/scripts/build_fsp.py \
    --spec _scratch/regress/2026-11-12/EXP-69/spec_bogus.json \
    --out _scratch/regress/2026-11-12/EXP-69/bogus --tag bogus
```

## 负对照

`source.type = "hologram"` 不是合法类型：脚本 exit 1，报
`unsupported source.type: 'hologram'（可用 plane / gaussian / mode）`，不会静默退化成平面波。
