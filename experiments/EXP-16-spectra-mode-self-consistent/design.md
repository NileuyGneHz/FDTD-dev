# EXP-16 spectra-mode-self-consistent

## 假设

旧版在 mode=spectra（不采结构）时仍断言「工程处于 layout 模式未保存」，同一份输出里 spectra_status 却是 ok；现在改说「未读取」

## 输入

`cases/metasurface/P01_Absorber_042/model/d2_perfectCross.fsp`

## 负对照

旧版在 mode=spectra（不采结构）时仍断言「工程处于 layout 模式未保存」，同一份输出里 spectra_status 却是 ok；现在改说「未读取」

## 判据

见下方 metrics 与断言

## 结果

```json
{
  "issue": "layoutmode 未读取（本模式未采样结构）：不对「是否已保存结果」下结论",
  "layoutmode": null
}
```

## 重跑命令

```bash
python skills/fdtd-lumerical-fsp-introspection/scripts/inspect_fsp.py --config <cfg.json> --out <dir>
```
