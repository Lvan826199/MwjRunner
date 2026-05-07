# MwjRunner

让接口自动化，像梦一样流畅执行。

梦无矶·MwjRunner —— 接口自动化的执行引擎。

Run APIs, Run Dreams.

## 项目定位

MwjRunner 是一个基于 Python 的接口自动化测试执行引擎，目标是提供自有的接口测试发现、执行、断言、报告和 CI 集成能力。

本项目不是 pytest + Allure 的封装，而是面向接口自动化场景建设专有执行引擎：

- 自研测试执行调度。
- 自研断言体系。
- 自研测试报告。
- 首期聚焦 HTTP API 功能自动化测试。

## 核心约束

- 不使用 pytest 作为核心执行或断言框架。
- 不使用 Allure 作为报告框架。
- 断言结果使用项目自有结构化模型。
- 报告由项目自有 Reporter 生成。
- 日志和报告必须对 token、password、cookie、secret、authorization 等敏感信息脱敏。

## 推荐技术方向

| 分类 | 推荐方案 |
| --- | --- |
| 语言 | Python >= 3.13 |
| 依赖管理 | UV |
| HTTP 客户端 | httpx |
| 用例格式 | YAML、JSON |
| CLI | Typer 或 argparse |
| 断言 | 项目自研 Assertion Registry |
| 报告 | Console、JSON、单文件 HTML |
| 配置 | YAML / 环境变量 / CLI 参数 |
| 并发 | concurrent.futures 或 asyncio |

## 核心能力规划

### 1. 用例管理

- 支持 project、suite、case、step 结构。
- 支持 YAML / JSON 用例。
- 支持 tags、priority、skip、retry、fail-fast。
- 支持数据驱动。

### 2. HTTP 执行

- 支持 GET、POST、PUT、PATCH、DELETE、HEAD、OPTIONS。
- 支持 query、headers、cookies、form、json、body、files。
- 支持 timeout、proxy、SSL 验证、重定向控制。
- 支持请求前变量渲染和响应后变量提取。

### 3. 自研断言

计划内置断言：

- status_code。
- json_path。
- body_contains。
- header。
- regex。
- schema。
- response_time。
- equals / not_equals / contains / type / length / range。

### 4. 自研报告

首期报告输出：

- 控制台摘要。
- JSON 结构化报告。
- 单文件 HTML 报告。

报告应包含执行概览、suite/case/step 明细、请求响应、断言结果、失败原因、重试记录和脱敏后的日志信息。

### 5. CLI

推荐命令：

```bash
mwjrunner run tests/api --env test --tags smoke --report html,json
mwjrunner run tests/api/login.yaml --case 用户登录流程
mwjrunner validate tests/api
mwjrunner init
```

推荐退出码：

- `0`：全部通过或仅跳过。
- `1`：存在失败断言。
- `2`：用例加载或配置错误。
- `3`：执行引擎内部错误。

## 文档

项目规划文档位于 `doc/`：

- `doc/需求规格说明书.md`：需求规格说明书。
- `doc/技术方案.md`：技术方案。
- `doc/下一步计划.md`：后续任务计划，所有开发任务必须先进入该文档再执行。
- `doc/使用手册.md`：面向新手的项目使用手册，示例需与 FastAPI 示例服务联动。

Claude Code 项目指南位于：

- `CLAUDE.md`。

项目技能和插件：

- `.claude/skills/code-review/SKILL.md`：提交前代码与文档审查。
- 官方 `superpowers@claude-plugins-official` 插件：复杂任务和质量门禁工作流，当前项目可直接使用；如需项目作用域安装，执行 `claude plugin install -s project superpowers@claude-plugins-official`。
- `.claude/skills/req-doc-generator/SKILL.md`：需求文档生成辅助。
- `.claude/skills/ui-ux-pro-max/SKILL.md`：后续 HTML 报告 UI/UX 设计参考。

必须使用 `superpowers@claude-plugins-official` 的场景：

- 实现或调整 CLI、执行引擎、调度、断言、报告、变量、HTTP 协议等核心能力。
- 修改需求、技术方案、README、CLAUDE.md 或核心约束。
- 进行跨文件重构、提交前质量门禁、风险较高或影响范围不明确的任务。

## 示例服务与使用手册

`examples/api/` 已提供一个独立 FastAPI 示例接口服务，并使用 UV 单独管理环境。该服务用于支撑项目使用手册、示例 YAML 用例和 MwjRunner 引擎开发验证。

示例服务已提供：

- `GET /health`：健康检查。
- `POST /api/login`：登录并返回 token。
- `GET /api/profile`：携带 token 获取用户信息。
- `GET /api/items`：查询示例数据。
- `POST /api/items`：创建示例数据。
- `GET /api/error`：固定错误响应，用于演示断言失败。

使用手册位于 `doc/使用手册.md`，要求面向新手，包含操作说明、命令示例、预期结果、常见问题，并与 `examples/api/` 的接口保持一致。

## 开发测试边界

MwjRunner 不得使用 pytest 作为核心执行框架或核心断言机制。pytest 仅允许作为项目自身 Python 代码和 `examples/api/` 示例服务的开发测试工具，不得进入 MwjRunner 的用户用例发现、执行、断言或报告链路。

## 提交规范

提交代码前必须进行 code review。

推荐流程：

1. 查看变更范围。
2. 使用 `.claude/skills/code-review/SKILL.md` 审查。
3. 处理 P0/P1 问题。
4. 运行可用的静态检查或测试命令。
5. 精确暂存相关文件。
6. 使用 Conventional Commits 提交。

推荐提交信息：

```bash
git commit -m "docs: initialize MwjRunner requirements and guidance"
```

## 里程碑

1. 最小引擎：CLI run、YAML 加载、HTTP 请求、基础断言、JSON 报告、控制台摘要。
2. 变量与报告：环境配置、变量渲染、提取、HTML 报告、脱敏。
3. 调度能力：tags、priority、retry、fail-fast、数据驱动、有限并发。
4. 可扩展能力：断言、提取器、报告器、数据源和协议插件。

## 当前状态

当前项目已完成基础规划文档、FastAPI 示例服务、示例 YAML 用例、M1 最小包骨架、`mwjrunner run` CLI help，以及 YAML 用例加载和校验；核心 HTTP 执行引擎尚未实现。下一步按 `doc/下一步计划.md` 执行 T6，实现 HTTP 请求执行。
