# EXP-04 [R4] 允许「参考工程从未跑过」，但必须自证

## 假设

四个 `.fsp` 全是 layoutmode=1 时，逼人填 shutoff 等于逼人编数字。豁免必须带可核验证据，否则门禁变摆设。

## 输入

check_convergence() 三组输入：无日志 / 有日志却声明 unrun / 声明 unrun 不给 layoutmode

## 对照与负对照

正：`unrun=true` + `layoutmode=1` + 日志不存在 → 放行；负：日志存在仍声明 unrun → 必须报「伪造豁免」；不给 layoutmode → 必须报缺证据。

## 判据

三组分别 OK / 伪造豁免 / 缺 layoutmode=1 证据。

## 重跑命令

```bash
$PY tools/check_reproduction.py --case P05  # 或其他未跑过的参考工程
```
