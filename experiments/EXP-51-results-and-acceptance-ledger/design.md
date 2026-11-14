# EXP-51 — 四个复现的账落位（`results/` 两级 + `acceptance.json`）

## 假设

盘点时两项门禁是红的，且都不是代码问题：

- `check_results_layout` FAIL=49：P02 的 20 个、P03 的 8 个、P04 的 17 个 csv/png
  直接躺在 `results/<Pkg>/` 根下，没有日期子目录与 `index.json`
  （`path-conventions.md` §6 要求两级）；P04 还有 4 个名字不是日期的子目录。
- `check_acceptance` FAIL=4：P01–P04 都有复现报告，却没有
  `cases/<Pkg>/config/acceptance.json`（`reproduction-contract.md` §7.1）。

后果不是「目录不好看」：`R.csv` 到底是 11-03 还是 11-09 的，只能靠文件时间戳猜；
验收结论只存在于散文里，于是出现「论文没给的量被写成数字」「报告写 PASS 而卡里没
有对应 target」两类漂移。

## 输入

| 数据 | 路径 |
|---|---|
| 三包结果文件（mtime 全为 2026-11-09） | `results/P0{2,3,4}_*/` |
| 四份复现报告的验收表 | `docs/P02…/repro_report.md`、`docs/P03…/`、`docs/P04…/`、`cases/P01…/results/repro_2026-11-09_fsp/repro_report_2026-11-09.md` |
| P01 的复现卡（`target.quantity = peak_absorption`） | `cases/metasurface/P01_Absorber_042/notes/repro-card.md` |

## 方法

1. `results/<Pkg>/` 下的散文件搬进 `<YYYY-MM-DD>/`，写 `index.json`
   （`case` / `date` / `verdict` / `solver` / `artifacts` / `note`）。
   日期取实测 mtime（三包各自全在同一天，不存在混批）。
2. P04 的非日期子目录整体并入日期目录：`logs/`（7 个 `_p0.log`，收敛证据）、
   `scripts/`（6 个分析脚本）、`run_thi00_gpu/`（h5）；
   误命名的 `P04_..._repro/` 只有一个 h5，提到日期目录后删空目录。
3. `cases/<Pkg>/config/acceptance.json`：30 项**全部照抄报告验收表**，
   定量项给 `measured` + `tolerance`，定性项一律 `N/A` + `unmeasured_reason`。
   P01 的 `card_target` 只标 C1（`peak_absorption`），与复现卡一致。

## 判据

| 指标 | 期望 |
|---|---|
| `check_results_layout` FAIL | 49 → **0** |
| `check_acceptance --all` FAIL | 4 → **0** |
| 三包日期目录 | 各有 `index.json` 且 `date` 与目录名逐字相等 |
| 30 项验收 | 每项都能追到报告里的同一行；`N/A` 全部带原因 |
| P01 卡-表双向 | `card_target` 恰好 1 条且 `quantity` 一致 |

## 负对照

同一对门禁跑在**搬运前**的树上必须红（49 / 4）；
两个门禁各自的 `--self-test` 负例必须能抓到「缺 `index.json`」「缺 `source` 出处定位」
「`N/A` 无原因」「卡-表 `quantity` 不一致」。

## 可重跑命令

```bash
python _scratch/regress/2026-11-10/EXP-51/migrate_and_accept.py --dry-run
python _scratch/regress/2026-11-10/EXP-51/migrate_and_accept.py
python tools/check_results_layout.py && python tools/check_acceptance.py --all
```

## 停止条件

任何一项验收要求「补一个论文没给的数」就停——那是 `[R2]` 的造假边界，
不写数字，写 `N/A` + 原因。
