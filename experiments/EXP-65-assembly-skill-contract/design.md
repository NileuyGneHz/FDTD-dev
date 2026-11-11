# EXP-65 — 新技能注册后的门禁全绿

## 假设

新技能 `fdtd-metasurface-assembly` 注册（INDEX + skills.yaml + junction）后，
四道门禁全部 exit 0，且既有 12 个技能的检查项数量不下降（不是靠改小分母变绿）。

## 判据

- `check_skill_contract.py`：技能数 13，`FAIL 0`，`OK` 项数 ≥ 改动前（121）。
- `skills-doctor.py`：ALL GREEN。
- `check_experiments.py`：EXP-60…65 全部 `pass`，无 FAIL。
- `check_scripts.py`：通过。
- junction 直读：`C:\Users\saber\.workbuddy\skills\fdtd-metasurface-assembly\SKILL.md` 可读，
  `lstat` 显示 `S_ISDIR=True`（junction 而非 symlink，防 WinError 5）。

## 负对照

从 `skills.yaml` 里删掉 assembly 条目：`check_skill_contract` 必须报 FAIL（或 WARN 升高），
不能全绿。若删了还绿，说明门禁没覆盖注册表完整性（D-011 同款：分母被悄悄缩小）。

## 命令

```bash
python tools/check_skill_contract.py
python tools/skills-doctor.py
python tools/check_experiments.py
python tools/check_scripts.py
```

## 结论

（执行后补）
