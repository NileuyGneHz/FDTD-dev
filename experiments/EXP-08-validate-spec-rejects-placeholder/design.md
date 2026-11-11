# EXP-08 validate_spec 必须拒绝 PLACEHOLDER 占位值（方向性判据）

## 假设

旧版放过带 PLACEHOLDER 的 spec，与 SKILL.md CRITICAL #2「静默替换」矛盾。修好的标志不是「新 spec 能过」，而是**旧 spec 从通过变成失败**。

## 输入

P01 真 spec（干净）+ 同 spec 注入 PLACEHOLDER 的副本

## 对照与负对照

正：干净 spec exit 0；负：含占位值的 spec 必须 exit≠0 且指出是占位值。

## 判据

exit 0 / exit 1 + 错误含「占位」。

## 重跑命令

```bash
python skills/fdtd-paper-parameter-extraction/scripts/validate_spec.py _scratch/regress/2026-11-09/EXP-08/spec_placeholder.json --strict
```
