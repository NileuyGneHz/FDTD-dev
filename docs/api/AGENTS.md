# docs/api/ — 外部接口索引

## 职责

给"外部系统怎么调、返回什么"建索引。**本目录不存放实现，也不复制技能里的参考文档。**

## 内容

| 对象 | 索引指向 | 版本 |
|---|---|---|
| Lumerical `lumapi`（属性名、材料类型、结果布局） | `docs/constitution/field-manual.md`（八章技术正文，唯一权威） | `v251` |
| Lumerical 会话生命周期 / `.lsf` 执行 | `skills/fdtd-lumerical-headless/SKILL.md`（该技能**只有** `SKILL.md` + `scripts/`，无 `references/`） | `v251` |
| Python 运行时（托管解释器路径） | `docs/constitution/path-conventions.md` §2 | — |
| 宿主接口（DSH / WorkBuddy 扫描规则） | `docs/constitution/host-integration.md` | — |

> 2026-11-11 订正：本表原先指向 `skills/fdtd-lumerical-headless/references/`，
> 但该目录**不存在**（实测该技能下只有 `SKILL.md` 与 `scripts/run_lsf.py`）。
> 指向不存在的路径比不写更糟——读者会以为是自己找错了地方。

## 约束

1. **只放指针，不放副本**。复制一份 API 文档 = 制造第二份真相。
2. 新增外部依赖时，在这里加一行"是什么、在哪读、版本"。
3. 版本相关的事实必须写版本号（`v251`），否则半年后无法判断是否还成立。
