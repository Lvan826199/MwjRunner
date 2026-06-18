# MEMORY.md

本文件记录可跨会话、跨机器共享的项目记忆，只保存非敏感信息。

- 本项目 AI 助手规则以 `CLAUDE.md` 为唯一完整规则源。
- `AGENTS.md` 只作为 Codex 入口，负责引导 Codex 读取并遵守 `CLAUDE.md`。
- `.claude/skills/` 和 `.agents/skills/` 是项目共享技能目录，可按需入库。
- 本地工具私有配置（如 `settings.local.json`、worktree、cache、`.agent/`、`.codex/`、`.Codex/`）只保存本机私有配置、缓存、权限和机器路径，不入库、不互相同步。
- 不在本文件保存 token、账号、密码、Cookie、私有路径、权限白名单或其他敏感信息。
