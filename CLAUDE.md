# CLAUDE.md

本仓库的 AI 运行契约以 `@AGENTS.md` 为唯一事实来源，本文件只做指向，避免两份规则漂移。

```md
@AGENTS.md
```

补充（Claude Code 特有）：

- 细则放在各目录的 `AGENTS.md`，不在本文件重复。
- 需要路径作用域加载时，用 `.claude/rules/*.md` 的 `paths:` frontmatter，而不是往本文件堆内容。
- 本文件超过 200 行即视为失败——索引可以长，规则不行。
