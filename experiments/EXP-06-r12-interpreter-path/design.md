# EXP-06 [R12] 解释器绝对路径不算「卡片里的绝对路径」

## 假设

contract §6 说本机解释器路径属运行时约定，脚本却对整张卡查绝对路径 → 每张卡必 FAIL。

## 输入

两条文本：含 `C:/Users/.../python.exe` 的命令；含 `F:/.../a.fsp` 的数据路径

## 对照与负对照

正：解释器路径被剥离后不再命中；负：数据绝对路径必须仍被判违规。

## 判据

前者无命中；后者有命中。

## 重跑命令

```bash
python -c "from tools.check_reproduction import strip_interpreters as s, ABS_PATH_RE as r; print(bool(r.search(s('python C:/x/python.exe'))))"
```
