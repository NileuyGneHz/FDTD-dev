# D-003 四处文档声明的 `.lsf` 唯一入口不存在（幽灵入口 + 门禁盲区）
**状态**：`resolved`（幽灵入口已补或改指，见正文验证段）
## 根因

`skills/fdtd-lumerical-headless/scripts/run_lsf.py` 在四处被当成既有能力引用：

| 位置 | 说法 |
|---|---|
| `docs/constitution/script-contract.md` §3 | 「任何单元里的 `.lsf` 都由同一个技能入口执行」 |
| `docs/constitution/workspace-layout.md` | 「由 `run_lsf.py` 统一执行」 |
| `skills/INDEX.md` | `fdtd-lumerical-headless` 的 `scripts` 列 |
| `iterations/iter-1-foundation/acceptance.md` | 「`run_lsf.py` 能执行任意单元里的 `.lsf` 并落 `_p0.log`」 |

文件从未被创建，而 `check_skill_contract.py` 的 `[K9]` 与 `skills-doctor.py` **全绿**。
原因：`[K9]` 只扫各技能自己的 `SKILL.md` 正文，**不看 `INDEX.md` / `constitution/` / `iterations/`**。
「先写规范、后补实现」在规范层没有任何回声，问题直到 P04 的 agent 照着文档去调用才暴露。

## 修复

1. 补齐实现（三条安全闸 + `--read` 回读 + 每次落 `_p0.log`）。
2. 新增门禁两条：
   - `[K15]` 扫描 `skills/INDEX.md` + `docs/` + `iterations/` + `agents/` 里声明的
     `<skill>/scripts/*.py`，必须实存。
   - `[K16]` 文档同一行写在该脚本后的 `--flag`，必须被该脚本 argparse 接受。
3. 同轮修掉安全闸的正则漏洞：`.lsf` 允许无参语句式 `run;`，原正则只匹配 `run(`，
   导致 `cases/P03_HWP_Ding2015/model/build_tio2_unitcell.lsf:311` 的真求解
   在 `allow_run=false` 下被静默放过。改为 `CALL_RE + BARE_RE` 双模式，并先剥 `#` 注释。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# ① 阴性对照：临时改名，[K15] 必须在两处同时 FAIL
mv skills/fdtd-lumerical-headless/scripts/run_lsf.py{,.bak}
"$PY" tools/check_skill_contract.py | grep K15
#   期望: FAIL  文档声明了不存在的脚本: skills/INDEX.md → ...; docs/constitution/script-contract.md → ...
mv skills/fdtd-lumerical-headless/scripts/run_lsf.py{.bak,}
"$PY" tools/check_skill_contract.py | grep K15
#   期望: OK    文档声明的 12 处脚本全部实存

# ② 安全闸：裸 run; 必须被拦
"$PY" skills/fdtd-lumerical-headless/scripts/run_lsf.py \
      --lsf cases/P03_HWP_Ding2015/model/build_tio2_unitcell.lsf --out _scratch/regress/_gate/gateA
#   期望: exit 2，stderr 含 `["deleteall", "run", "save"]`

# ③ 阴性对照：注释掉的 #run; 不得触发
printf '#run;\nx = 1;\n' > _scratch/regress/_gate/lsf_probe/commented.lsf
"$PY" skills/fdtd-lumerical-headless/scripts/run_lsf.py \
      --lsf _scratch/regress/_gate/lsf_probe/commented.lsf --out _scratch/regress/_gate/x --dry-run
#   期望: "mutating_commands": [], "refusal": null
```

## 影响面

`cases/P03_HWP_Ding2015`（裸 `run;`）、`cases/P06_Vortex_049/model/fig2g_modify_run.lsf`（裸 `run;`）；
任何「照 script-contract §3 去调用 `.lsf` 入口」的 agent 都会直接撞空。
