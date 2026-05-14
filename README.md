# MwjRunner

让接口自动化，像梦一样流畅执行。

梦无矶·MwjRunner —— 接口自动化的执行引擎。

Run APIs, Run Dreams.

## 项目定位

MwjRunner 是一个基于 Python 的接口自动化测试执行引擎，目标是提供自有的接口测试发现、执行、断言、报告、日志和 CI 集成能力。

本项目不是 pytest + Allure 的封装，而是面向接口自动化场景建设专有执行引擎：

- 自研测试执行调度。
- 自研断言体系。
- 自研测试报告。
- 支持 HTTP、WebSocket 协议，gRPC 预留。

## 核心约束

- 不使用 pytest 作为核心执行或断言框架。
- 不使用 Allure 作为报告框架。
- 断言结果使用项目自有结构化模型。
- 报告由项目自有 Reporter 生成。
- 日志和报告必须对 token、password、cookie、secret、authorization 等敏感信息脱敏。

## 技术栈

| 分类 | 方案 |
| --- | --- |
| 语言 | Python >= 3.13 |
| 依赖管理 | UV |
| HTTP 客户端 | httpx |
| 用例格式 | YAML、JSON |
| CLI | argparse |
| 断言 | 自研 Assertion Registry |
| 报告 | Console、JSON、HTML、插件扩展 |
| 日志 | Python logging + 脱敏 |
| 配置 | YAML 环境文件 + CLI 参数 |
| 并发 | concurrent.futures |
| Schema 校验 | jsonschema |

## 已落地能力

项目已完成 M1-M5 全部 39 个任务，覆盖：

### 执行引擎

- YAML 用例加载、目录批量执行
- 数据驱动（inline / CSV / JSON / Excel）
- 失败重试（默认 2 次，case 级可覆盖）
- fail-fast 快速停止
- 并发执行（`--workers N`）
- hooks 生命周期钩子（before/after_case、before/after_step）
- 环境配置（`--env`）、标签/优先级过滤

### 断言体系

`status_code`、`json_path`、`body_contains`、`response_time`、`json_schema`、`regex`、`header`、`cookie`

### 变量与提取

- 变量渲染：`${var_name}`
- 内置函数：`${__timestamp()}`、`${__uuid()}`、`${__random_phone()}`、`${__random_int()}`、`${__random_str()}`、`${__md5()}`
- 提取器：json_path、header、cookie、regex

### 认证

- Bearer / Basic 自动注入（环境级 + case 级）
- OAuth2 流程（client_credentials / password grant）

### 报告

- Console 终端摘要
- JSON 结构化报告
- 单文件 HTML 报告（template.html + JSON 注入）
- 执行历史和趋势（history.json）
- 报告插件接口（ReporterPlugin）

### 生态集成

- Postman Collection 导入（`mwjrunner import postman.json`）
- OpenAPI / Swagger 用例生成（`mwjrunner import --format openapi swagger.json`）
- 通知扩展（钉钉 / 企业微信 webhook + SMTP 邮件）

### 协议支持

- HTTP（完整）
- WebSocket（基础 send/recv）
- gRPC（骨架预留）

### 质量门禁

- 失败率、错误率、响应时间阈值
- 门禁不通过退出码 4

## CLI 命令

```bash
# 执行用例
mwjrunner run cases/ --env dev --report console,json,html
mwjrunner run cases/login.yaml --base-url http://localhost:8000

# 带过滤和调度参数
mwjrunner run cases/ --tags smoke --priority P0,P1 --workers 4 --retry 2 --fail-fast

# 校验用例格式
mwjrunner validate cases/

# 初始化项目结构
mwjrunner init

# 导入外部用例
mwjrunner import postman_collection.json --format postman --output cases/imported
mwjrunner import swagger.json --format openapi --output cases/generated
```

## 退出码

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部通过 |
| 1 | 存在断言失败 |
| 2 | 用例加载或配置错误 |
| 3 | 执行引擎内部错误 |
| 4 | 质量门禁不通过 |

## 快速开始

```bash
# 安装
uv sync

# 启动示例服务
cd examples/api && uv sync && uv run uvicorn app.main:app --port 8000

# 执行示例用例
uv run mwjrunner run examples/cases/ --base-url http://127.0.0.1:8000 --report console,json,html
```

## 项目结构

```
mwjrunner/
  cli.py              # CLI 入口
  core/               # 执行编排、质量门禁
  cases/              # 用例模型、加载、发现、过滤、数据驱动
  http/               # HTTP 执行器
  assertions/         # 自研断言注册表和内置断言
  variables/          # 变量引擎、内置函数
  reports/            # Console/JSON/HTML 报告、历史、插件接口
  config/             # 配置模型和加载器
  logging/            # 日志初始化和脱敏
  hooks/              # 生命周期钩子
  notifications/      # 通知扩展
  importers/          # Postman/OpenAPI 导入
  protocols/          # 协议适配器（WebSocket/gRPC）
  auth/               # OAuth2 认证
  data/               # 数据源扩展（Excel/SQL）
  utils/              # 脱敏工具
examples/
  api/                # FastAPI 示例服务
  cases/              # 示例 YAML 用例
doc/
  需求规格说明书.md
  技术方案.md
  下一步计划.md
  使用手册.md
  平台接入指南.md
```

## 文档

- `doc/使用手册.md`：面向新手的完整使用手册
- `doc/需求规格说明书.md`：产品需求规格
- `doc/技术方案.md`：架构设计
- `doc/下一步计划.md`：任务管理
- `doc/平台接入指南.md`：CI/CD 平台接入

## 开发测试

```bash
# 运行单元测试（pytest 仅用于项目自身开发测试）
uv run pytest tests/unit/ -q

# 代码格式化和检查
uv run ruff check .
uv run ruff format .
```

## 里程碑

- M1 最小引擎 ✅
- M2 报告能力 ✅
- M3 调度能力 ✅
- M4 可扩展能力 ✅
- M5 生态集成 ✅
- M6 平台化（进行中）— Vue 3 + Element Plus + FastAPI + SQLite

## 平台（M6）

`platform/` 目录为独立的 Web 管理平台，与引擎完全解耦。详见 `platform/README.md`。

当前已完成：用例管理、执行触发、环境配置、分布式执行、Mock 服务、性能压测、CI/CD、多租户权限（T40-T48）。M6 平台化阶段全部完成。
