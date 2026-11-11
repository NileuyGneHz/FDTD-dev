# D-012：`phase-retrieval` 没进编排，stage 4 在自动流程里不可达

**状态**：`resolved`（2026-11-10）

## 根因

`skills/INDEX.md` 把 `fdtd-lumerical-phase-retrieval` 定义为 **stage 4**（消费 spec + 偏振角，
产出 `phase.csv` / `dphi_deg`，交给 `figure`），但 `agents/fdtd-sim-agent/skills.yaml`
里**没有它的条目**。于是编排链是：

```
unitcell-simulation (2) --hands_to--> figure (5)      # stage 4 被整个跳过
```

`[K14]` 全绿且**在缺项时反而更绿**——它的判据是「yaml 里写下的 `path` 是否可达」，
删掉的条目不会留下不可达的 `path`，所以删得越干净越合规。这是单向门禁的典型形态：
只验「写了的东西对不对」，不验「该写的有没有写」。

契约 `skill-change-contract.md` §6 确实允许「只登记 INDEX 不进编排」，但那条豁免是给
**横切 / 按需能力**的（`headless` 是典型：它是会话底座，不是流水线环节）。
`phase-retrieval` 带数字 stage，属于流水线环节，不能套用这条豁免。

后果不是「少一个可选步骤」，而是：波片 / 圆偏振器件的验收量是 `φx − φy`，
跳过 stage 4 时**两个偏振的透射率都 ≈ 1**，`T` 看起来很完美，而器件完全不对。
这类「漏掉一个环节反而指标变好看」的路径，靠人记是靠不住的。

## 修复

1. **补条目**（stage 4，`hands_to: fdtd-lumerical-figure`），并写清它是**条件环节**：
   只有当验收量是相位（`dphi` / `phase` / 偏振态）时才插在 2/3 与 5 之间；
   纯功率复现直接走 `unitcell → figure`。
   `exit_criteria` 里写明两条硬判据：两个偏振必须读同一监视面（公共传播相位才能抵消），
   空结构对照必须给 `dphi = 0 (mod 360°)` 之后才允许采信器件数字。
2. **在 `rules:` 里显式写出 `headless` 为什么没有条目**（横切底座，永远不是流水线环节，
   也永不进 `load_order`），把「刻意缺席」和「漏了」区分开——否则下一个人会再来问一次。
3. **新增 `[K17]`**：`INDEX.md` 里 stage 列**含数字**的技能必须出现在某个 `skills.yaml`；
   stage 为 `X` 才可只登记 INDEX。这样「数字 stage = 流水线环节」从口头约定变成机器判据。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS

"$PY" -c "import yaml;d=yaml.safe_load(open('agents/fdtd-sim-agent/skills.yaml',encoding='utf-8'));print([s['id'] for s in d['skills']])"
# 期望包含 fdtd-lumerical-phase-retrieval

"$PY" tools/check_skill_contract.py | grep K17
# 期望：[K17] OK    INDEX 里所有数字 stage 的技能都在编排里
```

**负对照**（删掉 phase 条目，`[K17]` 必须 FAIL，而 `[K14]` 仍然 OK）：

```bash
"$PY" - <<'PY'
import pathlib
p = pathlib.Path("agents/fdtd-sim-agent/skills.yaml")
s = p.read_text(encoding="utf-8")
a = s.index("  - id: fdtd-lumerical-phase-retrieval")
b = s.index("  - id: fdtd-lumerical-figure")
p.write_text(s[:a] + s[b:], encoding="utf-8")
PY
"$PY" tools/check_skill_contract.py | grep -E "K14|K17"
```

实测（2026-11-10）：

| 状态 | K14 | K17 |
|---|---|---|
| 删掉 phase 条目 | **OK**（8 条路径全可达） | **FAIL** `fdtd-lumerical-phase-retrieval(stage 4)` |
| 恢复后 | OK（9 条，语法合法） | **OK** |

`K14` 在缺项时依然 OK，正是这条缺陷存在的理由。

## 影响面

- 任何「验收量是相位」的复现（P02 相位差、P03 半波片、P05 圆偏振旋向）在自动编排下都会
  绕过 stage 4，得到一份「T 很漂亮但没有相位」的报告。
- 同类风险：`INDEX.md` 与 `skills.yaml` 是两张表，靠人同步。已有 `[K14]`（引用可达）
  与 `[K17]`（覆盖完整）分别管两个方向：**写了的不许指向空，该写的不许漏**。
