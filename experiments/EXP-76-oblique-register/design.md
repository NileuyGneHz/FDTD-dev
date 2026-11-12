# EXP-76 — 注册、宿主接线、四门禁与收尾

**对应计划**：`docs/plans/PLAN-2026-11-13-oblique-incidence.md` §5 步骤 7 / §4.6 / §6 负对照 N6
**前置**：EXP-70…75 全部 `verdict=pass`

## 1. 做了什么

| # | 动作 | 文件 |
|---|---|---|
| 1 | `skills/INDEX.md` 新增 stage **2.5** 条目；把 `fsp-build` 行里「`dimension: 2D` 暂不支持」订正为「2D 已支持，2D 相位提取仍不支持」（EXP-71/75 已实机跑 2D） | `skills/INDEX.md` |
| 2 | `agents/fdtd-sim-agent/skills.yaml` 新增 stage 2.5 条目（load_when / consumes / produces / exit_criteria / hands_to / note），并订正 `fsp-build` 的同一条过期 note | `agents/fdtd-sim-agent/skills.yaml` |
| 3 | `yaml.safe_load` 校验：14 条 skills、新技能在列、stage=2.5、`load_order` 不变 | 同上 |
| 4 | `tools/skills-wire.py --apply`：`.agents/skills` 与 `.workbuddy/skills` 各 ADD 1 条 junction，共 15 条，错误 0 | 生成物，不手改 |
| 5 | 用户级 junction（Node `fs.symlinkSync(..., 'junction')`）；Python `lstat` 验证 `S_ISDIR=True / S_ISLNK=False / reparse=True`，`SKILL.md` 可读 | `C:\Users\saber\.workbuddy\skills\fdtd-lumerical-oblique-incidence` |
| 6 | K17 负对照：临时从 `skills.yaml` 删掉新条目 → `[K17] FAIL`，恢复后 `[K17] OK` | `_scratch/regress/.../EXP-76/k17_negative.py` |
| 7 | 计划状态改为「已批准并执行完成」，§11 已写入 D-01 / D-02 / D-03 三条偏差 | `docs/plans/PLAN-2026-11-13-oblique-incidence.md` |
| 8 | 会话交接 | `journal/2026-11-13.md` |

`load_order` **故意不加入**新技能：角度扫描是条件环节，和 stage 1.5 `fsp-introspection`、
stage 4 `phase-retrieval` 同类，按需加载；只有 declared stage 会进 K17 检查。

## 2. 判据

1. 四门禁全部 `exit 0`：`check_skill_contract.py`、`skills-doctor.py`、
   `check_scripts.py`、`check_experiments.py --require-all`。
2. `[K17]` 负对照必红且能恢复。
3. `skills-doctor` 报 `.agents/skills` 与 `.workbuddy/skills` 各 15 条、可达、名字一致。
4. `check_experiments.py --require-all` 不再有 `未落账` / `没有可重跑命令`。
5. 新技能 `--self-test` 50/50。

## 3. 负对照

| 操作 | 期望 | 实测 |
|---|---|---|
| 从 `skills.yaml` 删 `fdtd-lumerical-oblique-incidence` 条目 | `[K17] FAIL` | ✅ `INDEX 标了数字 stage 但没进编排: ...(stage 2.5)`，exit 1 |
| 恢复条目 | `[K17] OK`，exit 0 | ✅ |
| 旧 spec 不声明 `opaque_ground_plane` 而 T=−0.003 | 仍被拒 | ✅ EXP-73 amendment A |
| 发散日志（`diverging`） | 被 `check_engine_log` 拒 | ✅ EXP-73 amendment I |

## 4. 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

"$PY" tools/skills-wire.py --apply
"$PY" tools/check_skill_contract.py
"$PY" tools/skills-doctor.py
"$PY" tools/check_scripts.py
"$PY" tools/check_experiments.py --require-all
"$PY" skills/fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py --self-test
"$PY" _scratch/regress/2026-11-13/oblique/EXP-76/k17_negative.py
```

## 5. 边界

- `.agents/skills` / `.workbuddy/skills` 是**生成物**，由 `skills-wire.py` 重建，永不手改。
- 用户级 junction 是全局的，跨 workspace 可见；本轮只加这一条。
- 不顺带重构其它技能；stage 2.5 的 `load_order` 保持不变。
