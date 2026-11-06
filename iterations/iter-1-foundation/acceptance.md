# iter-1-foundation · 验收条件

> 每条都必须能判定"过 / 不过"。判不了的，改到能判为止。

## A. 结构

- [ ] `docs/`、`cases/`、`projects/`、`library/`、`defects/`、`journal/`、`iterations/` 七个目录都存在
- [ ] 每个目录都有 `AGENTS.md`，且根 `AGENTS.md` 的目录地图能指到它
- [ ] `cases/` 下恰好 10 个 `P0N_*` 单元，`_TEMPLATE/` 不计
- [ ] 每个单元同时有 `paper/` 与 `model/`，且 `README.md` 四段齐全

## B. 脚本

- [ ] `python tools/check_scripts.py` 退出码 0（包内无 `.py`）
- [ ] 每个技能脚本都支持 `--config / --out / --dry-run / --json`
- [ ] `run_lsf.py` 能执行任意单元里的 `.lsf` 并把 `_p0.log` 落到该单元的 `results/`

## C. 宿主

- [ ] `python tools/skills-doctor.py` 输出 `ALL GREEN`
- [ ] `.agents/skills` 与 `.workbuddy/skills` 是真目录，条数 == `skills/` 下合格技能数
- [ ] 新开 DSH 会话，catalog 列出全部 `fdtd-*` 技能
- [ ] 新开 WorkBuddy 会话，`<available_skills>` 同上

## D. 版本控制

- [ ] `git init` 完成，首次提交包含全部 `skills/` 本体与 `docs/`
- [ ] `git status` 里没有 junction 展开出来的重复文件
- [ ] `python tools/check_git_limits.py` 报 `ERROR=0`

## E. 可接手性（最重要）

- [ ] 随便挑一个单元，**只读它的 `README.md`**，能说清"当时为什么得到这个数"
- [ ] 新会话从零开始，按根 `AGENTS.md` §1 的四步，5 分钟内能定位到一条可执行任务

## 判定

A + B + C + D 全绿 = 结构验收通过。
E 全绿 = 迭代真正完成——**结构只是手段，可接手性才是目的**。
