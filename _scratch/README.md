# _scratch\ —— 临时脚本区（本地，不进版本库）

## 用途
放**一次性**的探查 / 验证 / 迁移脚本与它们的输出。用完即弃，不需要长期维护。

## 铁律（2026-10-01 起）
1. **所有临时脚本一律写在这里**，不要写到 `%TEMP%`（C 盘）或仓库根目录。
   - 原因：写在 C 盘会散落、难找、不受仓库管理，且每次会话后无人清理。
   - 只有 `_scratch\` 是"允许脏"的地方，其余目录必须保持整洁。
2. 临时脚本**不进 git**（`.gitignore` 已排除 `_scratch/*`，仅保留本 README）。
3. 一次性脚本**用完请删**；若要留作参考，移入 `archive\` 并在本文件登记一行。

## 目录
| 子目录 | 内容 |
|---|---|
| `_scratch\`（本级） | 正在用的临时脚本 |
| `_scratch\archive\` | 值得留档的一次性脚本 / 快照 |
| `_scratch\logs\` | 临时脚本的输出（stdout 重定向等） |

## 命名
前缀 `_`，能看出用途：`_probe_*.py`（探查）、`_fix_*.py`（修复）、
`_verify_*.py`（校验）、`_migrate_*.py`（搬迁）。

## 与正式脚本的边界
写完之后如果发现有复用价值 → 按下列归属**提升**为正式脚本：
- 单包专用 → 该包 `scripts\`
- 两包以上共用 → `_shared\`
- 通用大工具 → 留在 `F:\Lumercial_WS\scripts\`（引用不复制）

## 留档登记
| 日期 | 文件 | 说明 |
|---|---|---|
| 2026-10-01 | `archive\SKILL_old_user_level.bak-20260930.md` | 用户级 skill `lumerical-fdtd-headless` 的旧版快照（40KB，含已被推翻的结论），仅作回溯用 |
| 2026-10-01 | `archive\_probe_model_script.py` / `archive\_probe_optimization_ns.py` | O&S「model 脚本 → A 结果」诊断的取证脚本（对应 `SKILL.md` §5.4） |
| 2026-10-01 | `archive\_verify_i18n.py` | 英文化一致性校验：§ 引用是否可解析 / 小节编号是否与中文原版一致 / README 中英章节对齐 / frontmatter 完好。改动文未来再动结构时可复跑 |
