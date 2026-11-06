# docs/api/ — 外部接口索引

## 职责

给"外部系统怎么调、返回什么"建索引。**本目录不存放实现，也不复制技能里的参考文档。**

## 内容

| 对象 | 索引指向 |
|---|---|
| Lumerical `lumapi` | `skills/fdtd-lumerical-headless/references/`（属性名、材料类型、结果布局） |
| Python 运行时 | `docs/constitution/path-conventions.md`（托管解释器路径） |
| 宿主接口 | `docs/constitution/host-integration.md`（DSH / WorkBuddy 扫描规则） |

## 约束

1. **只放指针，不放副本**。复制一份 API 文档 = 制造第二份真相。
2. 新增外部依赖时，在这里加一行"是什么、在哪读、版本"。
3. 版本相关的事实必须写版本号（`v251`），否则半年后无法判断是否还成立。
