# EXP-12 session_control 脚本内规则表与 SKILL.md 一致

## 假设

SKILL.md 已订正为「save→run 即可」，但脚本里的规则表仍写「必须新会话 load」，agent 读到脚本注释会照着错的那条做。

## 输入

session_control.py 的 RULES 表 + SKILL.md 的 CRITICAL

## 对照与负对照

正：脚本含「save 再 run」且不含「新会话 load」；负：SKILL.md 不得残留「必须走两段式/静默失效→新会话」。

## 判据

三项布尔全为期望值。

## 重跑命令

```bash
python _scratch/regress/2026-11-09/test_exp09_10_12.py
```
