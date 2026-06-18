# MwjRunner

**最简 YAML 写用例，最清晰的失败诊断，零配置跑进 CI。**

Run APIs, Run Dreams.

---

### 为什么选 MwjRunner？

**卖点一：业界最简的用例格式**

不需要学框架 DSL、不需要写 fixture、不需要继承基类。一个 YAML 文件就是一个完整用例：

```yaml
name: 健康检查
steps:
  - name: 验证服务存活
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.status
        expected: "ok"
```

对比其他方案需要 30+ 行配置代码，MwjRunner 只要 **声明你要什么**。

**卖点二：失败了，一眼就知道哪里错**

断言失败不再是一堆 traceback，而是结构化诊断——告诉你 **哪条路径、期望什么、实际拿到什么**：

```
失败或错误明细
- 用户列表 / 校验返回数据: json_path 断言失败: path $.data.total 期望 10, 实际 0
- 用户列表 / 校验响应时间: response_time 断言失败: 实际耗时 1523ms 超过阈值 1000ms
- 登录 / 校验 token: json_path 断言失败: path $.token 期望 "abc", 实际 null
```

无需翻日志、无需加 print、无需猜测。**失败即诊断**。

---

## 3 分钟快速开始

适合第一次接触 MwjRunner 的用户：不用启动本地服务，直接使用公共 API 跑通第一个接口用例。

```bash
# 1. 安装依赖
uv sync

# 2. 校验示例用例格式
uv run mwjrunner validate examples/cases/quickstart_httpbin.yaml

# 3. 执行示例用例（使用 httpbin.org，无需本地服务）
uv run mwjrunner run examples/cases/quickstart_httpbin.yaml --base-url https://httpbin.org --report console
```

成功后会在终端看到执行摘要；如果接口返回不符合预期，MwjRunner 会直接展示失败步骤、断言类型、期望值和实际值。

### 小白用户指南

1. **先跑通示例**：执行上面的 3 条命令，确认本机 Python、UV 和 MwjRunner 可用。
2. **复制一个 YAML 用例**：从 `examples/cases/quickstart_httpbin.yaml` 复制出自己的用例文件。
3. **改请求地址和断言**：把 `request.method`、`request.url`、`query/json/body` 和 `assertions` 改成你的接口。
4. **接入自己的服务**：使用 `--base-url https://your-api.com` 指向真实接口环境。
5. **需要报告时再加参数**：用 `--report console,json,html` 生成终端、JSON 和 HTML 报告。

### 新用户下一步读什么

| 你想做什么 | 推荐阅读 |
| --- | --- |
| 第一次写接口用例 | `doc/使用手册.md` |
| 学习断言、变量、提取和报告 | `doc/使用手册.md` |
| 使用数据驱动、并发、hooks、质量门禁 | `doc/使用手册.md` |
| 接入 CI/CD 或测试平台 | `doc/平台接入指南.md` |
| 部署 Web 管理平台 | `doc/部署手册.md`、`platform/README.md` |

---

```bash
# 一行命令，零配置执行
uv run mwjrunner run cases/ --base-url https://your-api.com --report console,json
# 退出码：0=通过 1=断言失败 2=执行错误 3=引擎错误 4=质量门禁不通过
```

## 项目定位

MwjRunner 是一个基于 Python 的接口自动化测试执行引擎，目标是提供自有的接口测试发现、执行、断言、报告、日志和 CI 集成能力。

本项目不是 pytest + Allure 的封装，而是面向接口自动化场景建设专有执行引擎：

- 自研测试执行调度。
- 自研断言体系。
- 自研测试报告。
- 1.0.0 稳定执行链路聚焦 HTTP；WebSocket/gRPC 以实验性协议适配器提供。

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

项目已完成 M1-M7 全部 60 个任务，并通过端到端验证。以下为仓库已落地的总体能力，包含稳定能力、实验性能力和平台能力；1.0.0 发版边界见后文”1.0.0 版本范围”。

### 执行引擎

- YAML 用例加载、目录批量执行
- 数据驱动（inline / CSV / JSON，Excel 为实验性扩展）
- 失败重试（默认 2 次，case 级可覆盖）
- fail-fast 快速停止
- 并发执行（`--workers N`）
- hooks 生命周期钩子（before/after_case、before/after_step）
- 环境配置（`--env`）、标签/优先级过滤
- HTTP body 支持 dict/list 类型（自动序列化为 JSON）

### 断言体系

`status_code`、`json_path`、`body_contains`、`response_time`、`json_schema`、`regex`、`header`、`cookie`

### 变量与提取

- 变量渲染：`${var_name}`
- 内置函数：`${__timestamp()}`、`${__uuid()}`、`${__random_phone()}`、`${__random_int()}`、`${__random_str()}`、`${__md5()}`
- 提取器：json_path、header、cookie、regex

### 认证

- Bearer / Basic 自动注入（环境级 + case 级）
- OAuth2 流程（client_credentials / password grant，实验性）

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
- WebSocket（实验性 send/recv 适配器，非 CLI 主链路）
- gRPC（实验性：Unary + Streaming + Reflection）

### 质量门禁

- 失败率、错误率、响应时间阈值
- 门禁不通过退出码 4
- 示例配置：`examples/mwjrunner.yaml`

### 示例覆盖

`examples/` 目录提供覆盖核心功能的完整示例：

| 目录 | 覆盖能力 |
| --- | --- |
| `examples/cases/data_driven/` | inline / CSV / JSON 数据驱动 |
| `examples/cases/variables/` | 内置变量函数（timestamp/uuid/random/md5） |
| `examples/cases/assertions/` | response_time / regex / header / json_schema |
| `examples/cases/extractors/` | header / regex 提取器 |
| `examples/cases/auth/` | Bearer 认证内置 |
| `examples/cases/hooks/` | before_case / after_case 生命周期 |
| `examples/cases/advanced/` | 重试 / fail-fast 演示 |
| `examples/envs/` | dev / test / prod 环境配置 |

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
| 2 | 执行错误（如用例加载、配置、变量、网络、hook 等） |
| 3 | 执行引擎内部错误 |
| 4 | 质量门禁不通过 |

## 快速开始

README 顶部的“3 分钟快速开始”适合第一次上手；这里补充本地示例服务的完整流程。

### 完整示例（使用本地 FastAPI 服务）

```bash
# 启动示例服务
cd examples/api && uv sync && uv run uvicorn app.main:app --port 8000

# 执行全部示例用例
cd ../.. && uv run mwjrunner run examples/cases/ --base-url http://127.0.0.1:8000 --report console,json,html
```

## 1.0.0 版本范围

**稳定能力（GA）：**

- 核心 HTTP 执行引擎：YAML/JSON 用例加载、目录批量执行
- 断言体系：status_code、json_path、body_contains、response_time、json_schema、regex、header、cookie
- 变量渲染与提取：json_path、header、cookie、regex + 6 种内置函数
- 数据驱动：inline、CSV、JSON
- 调度：retry、fail-fast、并发执行、tags/priority 过滤、hooks
- 环境配置、Bearer/Basic 认证注入
- 报告：Console、JSON、HTML、执行历史趋势、报告插件接口
- CLI：run、validate、init、import
- 质量门禁（退出码 4）
- Postman/OpenAPI 导入
- 通知扩展（引擎：钉钉/企微/邮件）

**实验性能力（Experimental）：**

- WebSocket / gRPC 协议支持
- OAuth2 流程（client_credentials / password）
- Excel / SQL 数据源
- Web 管理平台（platform/）
- 场景编排、性能基线与回归检测

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

- `doc/使用手册.md`：完整使用手册（入门 + 进阶，章节 1-31）
- `doc/需求规格说明书.md`：产品需求规格
- `doc/技术方案.md`：架构设计
- `doc/下一步计划.md`：任务管理
- `doc/平台接入指南.md`：CI/CD 平台接入
- `doc/部署手册.md`：生产环境部署指南

## 开发测试

```bash
# 运行单元测试（pytest 仅用于项目自身开发测试）
uv run pytest tests/unit/ -q

# 运行集成测试（会自动启动 examples/api 示例服务）
uv run pytest tests/integration/ -q

# 代码格式化和检查
uv run ruff check .
uv run ruff format .
```

集成测试中的 FastAPI 示例服务会自动分配空闲端口，并使用 `examples/api/.uv-cache` 作为独立 UV 缓存，避免本机已有 `127.0.0.1:8000` 旧服务或主项目缓存状态影响测试结果。

### Claude / Codex 指南同步

`CLAUDE.md` 与 `.claude/skills/` 是源内容；`AGENTS.md` 与 `.agents/skills/` 由脚本生成：

```bash
uv run python -X utf8 -m scripts.sync_agent_assets --write
uv run python -X utf8 -m scripts.sync_agent_assets --check
```

## 里程碑

- M1 最小引擎 ✅
- M2 报告能力 ✅
- M3 调度能力 ✅
- M4 可扩展能力 ✅
- M5 生态集成 ✅
- M6 平台化 ✅ — Vue 3 + Element Plus + FastAPI + SQLite（T40-T48）
- M7 平台化增强 ✅ — JWT 认证、RBAC 权限、WebSocket、CI/Webhook、gRPC、场景编排（T49-T60）

## 平台（M6-M7）

`platform/` 目录为独立的 Web 管理平台，与引擎完全解耦。详见 `platform/README.md`。

当前已完成：用例管理、执行触发、环境配置、分布式执行、Mock 服务、性能压测、CI/CD、多租户权限、JWT 认证、RBAC 数据隔离、仪表盘统计、报告可视化、WebSocket 推送、CI 模板生成、Webhook 触发、多通道通知、场景编排、性能基线（T40-T60）。
