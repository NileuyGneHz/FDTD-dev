# EXP-31 — --out 指进 cases/ 必须 exit 2

## 改动
assert_writable_out() 拒绝 cases/ 内的产物目录，与 run_lsf.py 的 config.fsp 闸对齐

## 方法
同一 config，分别用 _scratch/ 与 cases/P01_.../tmp_out 作为 --out

## 实测
```json
{
  "scratch_exit": 0,
  "cases_exit": 2,
  "cases_dir_untouched": true
}
```

## 负对照
- 做法：--out cases/metasurface/P01_Absorber_042/tmp_out
- 预期：exit 2 并说明 cases/ 只读
- 实测：--out 落在只读参考语料 cases/ 内 ... ; exit 2
- 负对照是否按预期失败：是

## 结论
写入闸按路径解析后的前缀判断，不靠字符串匹配，不会被 ../ 绕过。

## 可重跑命令
```bash
python skills/fdtd-lumerical-session-control/scripts/session_control.py --config _scratch/regress/2026-11-09/sc_repro.json --out cases/metasurface/P01_Absorber_042/tmp_out --dry-run --json
```
