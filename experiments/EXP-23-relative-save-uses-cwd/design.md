# EXP-23 — 绝对化 --out：相对路径 save 的失败真因是引擎 cwd

## 改动
session_control.assert_writable_out() 把 --out 转成绝对路径后才交给 f.save()

## 方法
同一 session 内换 cwd 做配对实验：cwd=仓库根 / cwd=上级目录 / 绝对路径，字符串完全相同

## 实测
```json
{
  "cwd_repo_relative": "SUCCEEDED",
  "cwd_parent_relative": "LumApiError: You may not have permission to write to this directory",
  "absolute_after_chdir": "SUCCEEDED",
  "stray_file_in_parent": false,
  "error_message_reproduced_verbatim": true
}
```

## 负对照
- 做法：cwd=上级目录时用相对路径 save（未绝对化）
- 预期：报错，且错误文案指向「权限」而不是「路径不存在」
- 实测：LumApiError: 'Failed to save _scratch\regress\...\rel2.fsp. You may not have permission to write to this directory.'
- 负对照是否按预期失败：是

## 结论
P05 报告的失败真实存在，但归因（权限 / 非 ASCII）错误。真因是相对路径按引擎 cwd 解析。绝对化是必要修复：脚本可能在任意 cwd 下被启动。

## 可重跑命令
```bash
python _scratch/regress/2026-11-09/EXP-23/probe_relpath.py
python _scratch/regress/2026-11-09/EXP-23/probe_cwd.py
```
