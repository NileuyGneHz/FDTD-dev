# EXP-67 角谱传播：解析高斯 w(z)

## 假设

高斯束传播后的横向 FWHM 比值必须等于解析 `sqrt(1+(z/z_R)²)`，误差 <1%。
w0=20 µm、λ=1.55 µm ⇒ z_R≈811 µm；取 z=500 µm，解析比值 1.17488。

## 判据

`|measured/analytic − 1| < 1e-2`。

## 命令

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" skills/fdtd-lumerical-field-propagate/scripts/propagate_field.py --self-test
```

## 负对照

把 `1/λ²` 项漏掉（`arg = −(fx²+fy²)`，一种常见笔误）：衍射几乎消失，比值退化到 **1.0000**，
与解析 1.1749 差 15%——说明这条判据真的能抓住公式错误。
