# D-011：`skills.yaml` 不是合法 YAML，而 [K14] 用正则读它，所以全绿

**状态**：`resolved`（2026-11-10）

## 根因

`agents/fdtd-sim-agent/skills.yaml` 的 `fdtd-lumerical-figure` 条目里写着：

```yaml
    produces: *.png + a meta json carrying every number printed on the figure
```

`*` 是 YAML 的**别名指示符**，不能出现在未加引号的标量开头。`yaml.safe_load` 直接抛
`ScannerError: while scanning an alias ... expected alphabetic or numeric character, but found '.'`。

也就是说：**整份文件对任何真正的 YAML 解析器都无效**，10 个技能的编排一条都读不出来。

而 `[K14]` 全绿，因为它用 `AGENT_PATH_RE`（正则）抽 `path:` 行，**正则不关心语法**。
它验的是「yaml 里写下的 path 存不存在」，不是「这个文件能不能被读」。

引入时间：`fdtd-lumerical-figure` 是 2026-11-09 加的，未提交。`git show HEAD:` 的版本
能正常 `safe_load`（HEAD 没有 figure 条目）——所以这是那次新增带进来的，不是历史遗留。

## 修复

1. 值加引号：`produces: "*.png + a meta json carrying every number printed on the figure"`。
2. **`[K14]` 改为先解析、再抽 path**：有 PyYAML 时 `safe_load` 一遍，失败即 FAIL 并给出
   可操作的提示（「值以 `* & ! % @ \`` 开头时用双引号包起来」）；没装 PyYAML 时降级为
   **WARN 而不是静默跳过**。

另外同轮抓到两处**我自己**在这一轮引入的同类错误（都已修，记录在此以免重复）：
- `note: >-` 块以外的 bullet 里写了 `: `，导致该行被解析成 mapping（`could not find expected ':'`）；
- 同一 bullet 里 `T == 1` 之类本身无害，但把 `: ` 改成 `—` 才是解。

## 验证

```bash
PY="C:/Users/saber/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd F:/Lumercial_WS/FDTD_WS

# ① 文件本身合法
"$PY" -c "import yaml;d=yaml.safe_load(open('agents/fdtd-sim-agent/skills.yaml',encoding='utf-8'));print(len(d['skills']))"
# 期望：9

# ② 门禁覆盖语法
"$PY" tools/check_skill_contract.py | grep K14
# 期望：[K14] OK    9 条编排路径全部可达；skills.yaml 语法合法
```

**负对照**（把 `*` 放回行首，必须 FAIL）：

```bash
"$PY" - <<'PY'
import pathlib
p = pathlib.Path("agents/fdtd-sim-agent/skills.yaml")
p.write_text(p.read_text(encoding="utf-8").replace(
    'produces: "*.png + a meta json carrying every number printed on the figure"',
    'produces: *.png + a meta json'), encoding="utf-8")
PY
"$PY" tools/check_skill_contract.py | grep K14
# 实测：[K14] FAIL  skills.yaml 不是合法 YAML: ... while scanning an alias / ^
```

实测记录（2026-11-10）：修前 `safe_load` 抛 `ScannerError`，门禁 `ALL GREEN`；
修后 `safe_load` 得到 `skills=9`，门禁 `[K14] OK`；负对照 FAIL，恢复后 OK。

## 影响面

- 任何用真正 YAML 解析器读角色包的宿主/工具：整个 `skills.yaml` 读取失败 →
  编排为空 → 10 个技能全都不按 stage 走（不报错，只是「什么也没加载」）。
- 本项目自身的门禁全部看不见：`[K14]` 是正则，`skills-doctor` 查的是入口目录不是编排文件。
- 同类风险：任何「用正则读结构化文件」的检查。判据是**先用该格式的解析器读一遍**，
  再用正则做语义检查——顺序反了，语法错误就永远不出现。
