# Changelog

本文件记录 MwjRunner 各版本的主要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [未发布]

### 修复（T70 全仓隐藏 bug 排查）

#### 脱敏体系
- `redact_text` 支持 JSON 引号键（`"token": "abc"`），修复文本兜底脱敏对 JSON 片段完全失效的问题
- `redact_url` 补充 URL userinfo 密码脱敏（`https://user:pass@host`）
- 断言 message 在 path/target 敏感时同步清除内嵌的 expected/actual 原始值
- body 类断言的 actual（完整响应体）在序列化层按 JSON 解析脱敏
- 敏感字段清单补充 `api_key`/`apikey`

#### HTTP 执行
- 响应快照保留原始 headers/cookies，脱敏统一移至报告序列化层——修复 cookie 断言恒为失败、cookie/敏感 header 提取得到 `***REDACTED***` 占位符的功能性缺陷
- URL 拼接保留 base_url 路径前缀（`http://h/api/v1` + `/users` → `http://h/api/v1/users`）
- `timeout: 0` 不再被静默回退为默认 30 秒
- 响应耗时计时窗口收紧到请求本身，不再包含 client 构建/关闭
- dict/list 类型 body 自动补 `Content-Type: application/json`
- 多文件上传中途失败时正确关闭已打开的文件句柄
- 响应文本按响应声明的 charset 解码（回退 UTF-8）
- 环境配置的 `timeout`/`headers`/`verify_ssl`/`proxy` 真正接入执行链路

#### 变量与断言
- 无法解析的变量表达式（如 `${user.name}`）报错而非静默原样发出
- 内置函数参数支持引号包裹（含逗号文本）、空位走默认值；`__random_int`/`__random_str` 参数错误给出清晰提示
- regex 提取/断言对非法正则返回结构化错误，不再炸穿整次运行
- `json_path` 断言修复 `False == 0`/`True == 1` 跨类型误判
- `status_code` 兼容字符串期望值；header/cookie 断言期望值归一为字符串
- `response_time` 对非数字 expected 返回失败结果而非 TypeError
- 断言 handler 异常转为失败结果；重复注册断言类型记录告警

#### 执行编排
- 单步骤未预期异常不再使整次运行坍缩为"执行引擎内部错误"（已执行用例结果不再丢失）
- `mwjrunner.yaml` 与 `envs/` 改为从当前工作目录查找，修复文档化的 `--env` 用法必报错、质量门禁配置静默失效的问题
- 步骤级 `variables` 真正生效（覆盖用例级，步骤结束后还原）
- `--retry 0` 可正确禁用重试；负数 retry 不再导致崩溃
- 步骤 error 后剩余步骤补录为 skipped
- 质量门禁分母排除 skipped 用例；错误场景（退出码 2）也参与门禁评估，`max_error_rate` 不再形同虚设
- 执行历史 `reports/history.json` 接入 run 链路（原子写入）
- OAuth2 认证接入配置链路（`auth.type: oauth2` 自动获取 token 并注入，支持 `${VAR}` 引用）
- 非法时区/配置类型错误转为清晰的配置错误提示（退出码 2）
- hooks 支持 `module:function` 冒号格式；after_case 多个清理 hook 全部执行并聚合错误；正式安装场景自动注入项目目录到导入路径
- 目录批量执行排除 `mwjrunner.yaml` 与 `envs/`、`reports/` 目录；数据驱动配置为空时明确报错

#### 报告与通知
- JSON/HTML 报告序列化对非基础类型兜底（YAML 日期等不再导致报告写入崩溃）
- HTML 报告 JSON 注入统一转义 `<`，status 拼接增加白名单
- 钉钉/企微通知校验响应 `errcode`，业务失败不再误报成功；钉钉支持加签（`secret`）；SMTP 587 端口走 STARTTLS
- Postman 导入转换 `{{var}}` → `${var}` 并保留集合变量；URL host/path 字符串形式正确解析；同名文件不再互相覆盖
- OpenAPI 导入修复 int 状态码键匹配与 `$ref` 前缀剥离
- WebSocket 适配器透传握手 headers；gRPC 反射收集全部依赖文件描述；`ProtocolResult.is_success` 正确判定协议级错误

#### 平台
- 修复执行触发与场景编排的跨团队用例引用（IDOR）
- WebSocket 推送 admin 使用专属分组，无团队用户不再收到其他团队事件
- 前端路由守卫校验 `meta.roles` 角色
- 生产环境（`MWJ_ENV=production`）禁止默认 JWT 密钥启动，开发环境输出告警

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
