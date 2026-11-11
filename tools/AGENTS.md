# tools/ — 仓库级自检

## 职责

把 `docs/constitution/` 里的规范变成**可判真假的命令**。工具本身不是技能，也不被技能调用。

## 清单

| 脚本 | 检查什么 | 何时跑 |
|---|---|---|
| `check_packages.py` | 归档单元结构、论文↔`.fsp` 一一对应、README 四段 | 每次交付前 |
| `check_scripts.py` | 包内出现 `.py` → FAIL，并给出该迁往的技能 | 每次提交前 |
| `check_git_limits.py` | 单文件 > 100 MB、总体积 | `git push` 前 |
| `skills-wire.py` | 重建 `.agents/skills` 与 `.workbuddy/skills` 的 junction | 增删技能后 |
| `skills-doctor.py` | 六项宿主接入检查 | 增删技能后 / 换机器后 |
| `check_skill_contract.py` | 技能内容契约 K1–K17（frontmatter / 引用可达 / INDEX 登记 / CLI / 编排 path **且 skills.yaml 必须是合法 YAML** / pycache / **文档声明的脚本实存** / **文档 `--flag` 与实际 argparse 一致** / **INDEX 里数字 stage 的技能必须进编排**） | 改任何技能、改 `skills.yaml` 或改 constitution 里的命令示例后 |
| `check_reproduction.py` | 复现卡 **R1–R13 + R14 + R16**（口径 / 收敛数值 / 同输入回归 / 输出隔离 / 训练条目 / **目标指标必须真的出现在产出列里** / **判据来源与定义必填** / **rerun_commands 引用的仓库内文件必须存在**）。`R15` 是历史跳号，**不要复用**；`R16` 目前没有对应的 `--self-test` 用例（已知缺口，见 journal 2026-11-10） | 每次复现交付前；改本脚本后 |
| `check_acceptance.py` | 验收表 `config/acceptance.json` 结构（status 枚举 / FAIL 必带 cause / N/A 必带原因且无 measured / 出处定位），并与复现卡 target 双向比对；自带 `--self-test` | 每次复现交付前 |
| `check_results_layout.py` | `results/<论文名>/<YYYY-MM-DD>/index.json` 落位规则；平铺文件直接 FAIL；自带 `--self-test` | 每次写结果后 |
| `probe_gpu_eligibility.py` | 判定每个 `.fsp` 走 `gpu` / `gpu_risky` / `cpu_only`（TFSF、2D、色散金属、显存），产出 `gpu_matrix.json` 与批次 | 并行跑批之前 |
| `gpu_mode.py` | 读/切 `FDTD\GPU-mode`（改 ini，不碰 `setresource`）；改前备份、改后读回、GUI 在跑时拒绝；自带 `--self-test` | 要切全局 GPU/CPU 时 |
| `gpu_guard.py` | 按工程资格**自动**切 GPU/CPU 并包住一次运行，跑完（含异常）必还原；判据复用 `probe_gpu_eligibility.classify`，`gpu_risky` 需 `--allow-risky` 或 `--probe-log`；自带 `--self-test` | 每次要用 GPU 跑单工程时 |
| `check_experiments.py` | 逐项实验台账 D1–D5：PLAN 里每个 `EXP-NN` 都要有 `result.json`，且 `verdict=pass`、`metrics` 非空、`negative_control.failed=true`、`design.md` 含负对照与命令 | 每个批次收尾；改 PLAN 后 |

### 已知 WARN（C 档遗留，不阻断）

- `check_packages.py` 有约 34 条 `_p0.log` 缺失 WARN：多为「工程从未实跑」，
  不等于结构缺陷，需人工判读后再决定是否降噪。
- **`[K11]` 的豁免条件本身不可靠**：它以「源码里有没有 `argparse`」代替「脚本是不是
  可调用入口」，会把有 `__main__` 但无 argparse 的脚本当纯模块跳过
  （`migrate_classes_to_packages.py` 就是这么躲过检查的，见 D-006）。
  转发壳与真模块又确实应当豁免，所以不能简单收紧。当前**依赖人工**；
  改判据前先读 D-006 的「遗留」段。

### 已清历史 WARN（2026-11-08）

- ~~`run_fdtd_sweep.py` 缺 `--json`~~ → 已补，且默认输出与改动前**逐字节一致**（P01/P02 双 case）。
- ~~`migrate_classes_to_packages.py` 缺 `--out`~~ → 已补 `--src/--out/--dry-run`，
  并归位到仓库级 `tools/`，技能内副本删除（D-006）。

## 约束

1. **一个规范一条检查**。`constitution` 里判不了的规则，不要在这里假装能查。
2. **退出码即结论**：`0` 通过，非 `0` 失败，输出必须指出"改哪个文件"。
3. **幂等**。重复跑不改变结果；`--apply` 类操作必须先 dry-run。
4. **不写业务逻辑**。这里只做检查与布线，不碰仿真。
5. 新增检查脚本必须在 `docs/constitution/AGENTS.md` 的表格里登记。
