# projects/ — 在研课题

## 职责

存放**当前正在做的研究**。与 `cases/` 完全同构，区别只有两条：可写、编号用 `R0N`。

## 结构

```
R0N_<Topic>/
├─ README.md    §0 目标与验收（先写这个）§1 论文/动机 §2 参数 §3 偏差诊断
├─ paper/       参考文献（如果有）
├─ model/       .fsp + .lsf + spec_<id>.json
├─ config/      sweep_*.json
├─ results/
└─ notes/
```

新建时**从 `_TEMPLATE/` 复制**，不要手搓目录。

## 约束

1. **先写 §0 再动手**。"要什么图、判据是什么、容差多少"没写清，不许开仿真理。
2. **一个课题一个目录**。跨课题的东西进 `library/`，别在本目录里放"通用脚本"。
3. **包内无 `.py`**。要新增能力 → 开技能（`skills/AGENTS.md` 的五步）。
4. **结果可追溯**：`results/<run_id>/` 与 `model/` 里的 `.fsp` 必须一一对应，
   `run_id` 建议 `YYYYMMDD_<短名>`。
5. 课题结束：结论进 `README.md` §3，可复用的部分沉淀到 `library/` 或 `cases/`（后者需人工决定）。

## 与 tasks 的关系

`docs/tasks/active/` 里的一条 TASK 指向一个 R 号。**一次会话只烧一个 R 号**。
任务完成时：TASK 移 `recent/`，本目录补 §3 结论，`journal/` 写交接。
