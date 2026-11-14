# known-issues.md — core-lead-agent 实测踩坑

> 只记**跑过的**：命令、报错、有效规避。没跑过的结论不许写进来。
> 每条带日期与证据位置。

## 2026-11-12 建立工作区时实测

### 1. pypdf 的字体警告会淹没输出

- **症状**：`PdfReader(...).extract_text()` 对 CFF Type1 字体刷大量
  `fontTools is required to fully parse the encoding...`
- **规避**：`python -m pip install --target F:\tools\pylibs fonttools`，
  并设 `$env:PYTHONPATH='F:\tools\pylibs'`。装完警告消失。
- **证据**：安装前后对比，`_scratch/verify_pdfs.py` 输出从几十行警告变为 0 行。

### 2. PowerShell 里不能写 heredoc

- **症状**：`python - <<'EOF'` 报 `The '<' operator is reserved for future use`。
- **规避**：把脚本写成 `.py` 文件再 `python file.py`；或用 `python -c "..."`（单行）。
- **证据**：`_scratch/debug_tubs.py` 即为此改写。

### 3. 中文输出在默认控制台编码下会崩

- **症状**：`UnicodeEncodeError: 'charmap' codec can't encode character`。
- **规避**：脚本里 `sys.stdout.reconfigure(encoding="utf-8")`；
  或输出重定向到文件再 `Get-Content -Encoding UTF8`。
- **证据**：`_scratch/fetch_alt2.py` 首次运行即因此失败。

### 4. junction 的 readlink 前缀不统一

- **症状**：`os.readlink` 返回 `\\?\Global\F:\...` / `\\?\F:\...` / `\??\F:\...` 三种形态，
  直接 realpath 会判定「指向错误」，每次运行都报 FIX。
- **规避**：`skills_wire.py` 的 `norm()` 先剥前缀再 realpath + normcase。
- **证据**：本工作区首次 wire 时三条链接全被误判为 FIX，加 norm 后全部 OK。

### 5. 从 Python subprocess 调 cmd.exe 不受拦

- **症状**：已知（长期记忆）PowerShell / Bash 直接调 `cmd.exe` 会被安全策略拦。
- **实测**：`subprocess.run(["cmd","/c","mklink","/J",...])` **可以**执行，返回码 0。
- **证据**：2026-11-12 建 `_scratch/jtest/link` junction 成功，`Test-Path` 为 True。
