# Changelog

本文件记录 MwjRunner 各版本的主要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-05-18

首个正式发布版本。核心 HTTP 接口自动化测试能力达到生产可用。

### 亮点

- **最简 YAML 格式**：一个 YAML 文件就是一个完整用例，无需框架 DSL、fixture 或基类
- **结构化失败诊断**：断言失败直接展示路径、期望值、实际值，零调试成本
- **零配置 CI 集成**：标准退出码 + 一行命令，天然适配任何流水线

### 稳定能力（GA）

#### 执行引擎
- YAML / JSON 用例加载与目录批量发现
- HTTP 请求执行（基于 httpx）
- 变量渲染与提取（json_path、header、cookie、regex）
- 6 种内置变量函数：`__timestamp()`、`__uuid()`、`__random_phone()`、`__random_int()`、`__random_str()`、`__md5()`
- 数据驱动（inline、CSV、JSON）
- 失败重试（默认 2 次）、fail-fast
- 并发执行（ThreadPoolExecutor）
- tags / priority 过滤
- hooks 生命周期钩子（before_run / after_run / before_case / after_case）
- 环境配置加载（envs/*.yaml）
- Bearer / Basic 认证注入

#### 断言体系
- 8 种内置断言：status_code、json_path、body_contains、response_time、json_schema、regex、header、cookie
- 可扩展 Assertion Registry

#### 报告
- Console 摘要报告
- JSON 结构化报告
- 单文件 HTML 报告（template.html + JSON 注入，离线可用）
- 执行历史趋势
- 报告插件接口

#### CLI
- `mwjrunner run` — 执行用例
- `mwjrunner validate` — 校验用例格式
- `mwjrunner init` — 初始化项目结构
- `mwjrunner import` — 导入 Postman / OpenAPI 用例

#### CI 集成
- 标准退出码：0（通过）、1（断言失败）、2（配置错误）、3（引擎错误）、4（质量门禁不通过）
- 质量门禁（failure_rate / error_rate 阈值）
- CI 模板生成（GitHub Actions / GitLab CI / Jenkins）
- Webhook 自动触发

#### 生态
- Postman Collection 导入
- OpenAPI / Swagger 用例生成
- 通知扩展（钉钉、企微、飞书、Slack、邮件）

#### 安全
- 日志和报告自动脱敏（token、password、cookie、secret、authorization）

### 实验性能力（Experimental）

以下功能已实现但不在 1.0.0 稳定性保证范围内，后续版本可能调整 API：

- WebSocket 协议支持
- gRPC 协议支持
- OAuth2 流程（client_credentials / password grant）
- Excel / SQL 数据源
- Web 管理平台（platform/）
- 场景编排
- 性能基线与回归检测

### 文档

- 使用手册拆分为入门篇和进阶篇
- 零依赖 Quick Start（httpbin.org）
- 平台接入指南
- 部署手册
