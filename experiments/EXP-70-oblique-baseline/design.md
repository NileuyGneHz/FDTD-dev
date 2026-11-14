# EXP-70 — 固化基线并登记视频/工程取证

## 假设

改 `library/py/fsp_build.py`（两个调用方共用）之前必须有一个干净的 git 基线，
否则「零破坏回归」分不清差异来自谁。2026-11-12 遗留的未提交工作（EXP-66…69、
`fdtd-lumerical-field-propagate`、`fsp_build.py` 的 source.type 扩展、INDEX/skills.yaml、
journal）本身是有效成果，先落地为 commit，本轮所有改动都从它之后开始。

## 判据

1. `git status --short` 为空（提交后工作区干净）。
2. 四门禁输出逐条存档到 `_scratch/regress/2026-11-13/oblique/baseline/`，退出码写进台账。
3. 门禁**如实记录**，不把计划态的 FAIL 粉饰成 ALL GREEN。
4. 视频解析产物与 P08 课程工程清单登记进台账，路径可重放。

## 负对照

`check_skill_contract.py` 的 K15 在计划态必须 **FAIL**：PLAN 文档声明了
`fdtd-lumerical-oblique-incidence/scripts/angle_sweep.py`，但脚本尚未创建。
若此时 K15 仍然全绿，说明「文档声明了不存在的脚本」这条门禁是死的（D-011 同类假绿）。
实测 FAIL=1，exit 1 —— 门禁确实 load-bearing。

## 可重跑命令

```bash
cd "F:/Lumercial_WS/FDTD_WS"
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
B="_scratch/regress/2026-11-13/oblique/baseline"
git status --short
for g in check_skill_contract skills-doctor check_scripts check_experiments; do
  "$PY" "tools/$g.py" > "$B/$g.txt" 2>&1; echo "$g exit=$?"
done
```

## 实测结果

| 门禁 | exit | 结论 |
|---|---|---|
| `check_skill_contract` | **1** | K15 FAIL：PLAN → `angle_sweep.py` 不存在（计划态预期，实现 EXP-74 后转绿） |
| `skills-doctor` | 0 | ALL GREEN（14 技能） |
| `check_scripts` | 0 | 包内没有 `.py` |
| `check_experiments` | 0 | ALL GREEN（允许 WARN）；D1 WARN = EXP-70…76 共 7 条未落账，本轮逐条补 |

提交：`2f49a7d chore(baseline): land 11-12 work ...`。

## 取证清单

- 视频：`cases/metasurface/P08_BroadbandAbsorber_043/lecture/第三讲 宽角度完美吸收器.mp4`
  25:00.3 / 30 fps / 45010 帧 / 1280×720 / 531,609,288 B
- 音频转写：`_scratch/regress/2026-11-13/lecture_transcript.txt`（1027 段）
- 抽帧：`_scratch/regress/2026-11-13/lecture_frames/`（35 采样 + 21 全分辨率 + 3 总览）
- 课程工程 7 个 `.fsp` + 3 个 `_p0.log`：`cases/metasurface/P08_BroadbandAbsorber_043/model/`
- 材料实测 nk：`model/Ag-nk.txt`、`model/aSi-nk.txt`（40 行，400–790 nm，列 = λ[nm]/n/k）
- 配套 PPT / 论文 / 自测题：`lecture/`、`paper/`
