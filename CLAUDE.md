# CLAUDE.md

必须使用简体中文输出。

本文件为 Claude Code 在本仓库中工作的项目级指南。所有修改、建议、审查和提交操作都必须遵守本文件约束。

## 项目概述

MwjRunner 是一个基于 Python 的接口自动化测试执行引擎。

项目口号：

- 中文：让接口自动化，像梦一样流畅执行
- English: Run APIs, Run Dreams

项目目标是建设自有的接口自动化执行引擎，覆盖用例发现、用例加载、执行调度、HTTP 请求、变量提取、断言、报告、日志和 CI 集成。

## 硬性约束

- 不得使用 pytest 作为核心执行框架。
- 不得使用 pytest 作为核心断言机制。
- 不得使用 Allure 作为报告框架。
- 必须实现项目自有断言体系。
- 必须实现项目自有测试报告。
- 优先使用简单、可维护的 Python 模块，避免过早抽象。
- 第一阶段聚焦 HTTP API 功能自动化测试。
- 日志和报告可能包含敏感信息，必须对 token、password、cookie、secret、authorization 等字段脱敏。

## 当前技术方向

- 语言：Python。
- Python 版本：遵循 `pyproject.toml`，当前为 `>=3.13`。
- 三方库管理：统一使用 UV，通过 `uv add`、`uv sync`、`uv run` 管理依赖和命令执行。
- 推荐 HTTP 客户端：`httpx`。
- 推荐用例格式：YAML 和 JSON。
- 推荐报告输出：控制台摘要、JSON 报告、单文件 HTML 报告。
- 推荐 CLI 形态：`mwjrunner run`、`mwjrunner validate`、`mwjrunner init`。

## 文档约定

主要规划文档位于 `doc/`：

- `doc/需求规格说明书.md`：产品需求和功能需求。
- `doc/技术方案.md`：技术方案和架构设计。

当需求、架构、CLI、用例格式、报告格式或核心约束发生变化时，必须同步更新相关文档。

## 工程准则

- 修改前必须先阅读已有文件。
- 不要新增与当前目标无关的依赖；新增三方库必须通过 UV 管理。
- 执行逻辑与报告生成逻辑必须分离。
- 协议执行逻辑与调度逻辑必须分离。
- 断言逻辑应通过 registry 或等价机制保持可扩展。
- 执行结果应优先使用结构化结果模型表达。
- 不要为了单一场景创建复杂 helper、抽象层或插件机制。
- 不要添加无必要的兼容性 shim、特性开关或未来预留代码。

## 项目技能引用

本项目使用以下 Claude Code 技能和插件：

- `.claude/code-review/SKILL.md`：MwjRunner 专用代码与文档审查技能。每次提交前必须使用。
- 官方 `superpowers@claude-plugins-official` 插件：已安装并启用，当前项目可直接使用；如需项目作用域安装，使用 `claude plugin install -s project superpowers@claude-plugins-official`。
- `.claude/req-doc-generator/SKILL.md`：需求文档生成相关技能，可用于需求补充和文档结构化。
- `.claude/ui-ux-pro-max/SKILL.md`：UI/UX 设计相关技能，后续设计 HTML 报告页面时可参考。

必须使用 `superpowers@claude-plugins-official` 的场景：

- 复杂功能实现，例如 CLI、执行引擎、调度、断言、报告、变量、HTTP 协议等核心模块。
- 需求、架构、核心约束或里程碑发生变化。
- 修改 `README.md`、`CLAUDE.md`、`doc/需求规格说明书.md`、`doc/技术方案.md` 等项目指导文档。
- 提交前质量门禁、跨文件重构、风险较高或影响范围不明确的任务。

如果用户要求使用 skill、审查、提交前检查、复杂工作流或需求文档生成，优先使用对应技能或插件。

## Git 提交操作规范

### 基本原则

- 未经用户明确要求，不得提交代码。
- 未经用户明确要求，不得推送代码。
- 不得使用 `git add .` 或 `git add -A` 进行宽泛暂存，优先按文件精确暂存。
- 不得使用 `--no-verify` 跳过 hook。
- 不得在提交失败后使用 amend 覆盖上一个提交，除非用户明确要求。
- 不得执行破坏性 Git 操作，例如 `reset --hard`、`checkout .`、强推、删除分支，除非用户明确要求。

### 提交前必须执行

每次提交代码前必须进行 code review：

1. 使用 `.claude/code-review/SKILL.md` 对当前变更进行审查。
2. 检查 `git status`、`git diff`、`git diff --cached`。
3. 确认没有引入 pytest / Allure 作为核心能力。
4. 确认文档与实现一致。
5. 确认日志、报告、错误信息不泄露敏感字段。
6. 如存在 Python 代码，运行可用的格式化、静态检查或测试命令；若项目尚未配置，需在回复中说明。
7. P0/P1 问题未解决前不得提交。

### Commit Message 规范

推荐使用 Conventional Commits：

- `feat: ...`：新增功能。
- `fix: ...`：修复问题。
- `docs: ...`：文档更新。
- `refactor: ...`：重构。
- `test: ...`：测试相关。
- `chore: ...`：工程配置或杂项。

提交信息应说明为什么修改，而不仅是修改了什么。

## 推荐里程碑

1. 最小引擎：CLI run、YAML 加载、HTTP 请求、基础断言、JSON 报告、控制台摘要。
2. 变量与报告：环境配置、变量渲染、提取、单文件 HTML 报告、敏感信息脱敏。
3. 调度能力：tags、priority、retry、fail-fast、数据驱动、有限并发。
4. 可扩展能力：断言、提取器、报告器、数据源、协议插件接口。
