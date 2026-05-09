# T9 Console 和 JSON 报告设计

## 目标

实现 M1 阶段的基础报告能力：结构化运行结果模型、终端摘要报告、JSON 报告和稳定退出码映射。

本任务只实现报告与退出码基础能力，不在本轮把 `mwjrunner run` 串成完整真实执行入口。完整执行编排应由后续 runner / engine 任务负责。

## 范围

覆盖：

- `RunResult`、`Summary`、`CaseResult`、`StepResult` 等报告结果模型。
- `ConsoleReporter`：输出终端摘要和失败明细。
- `JsonReporter`：输出机器可读 JSON 报告。
- 退出码映射：成功为 0，断言失败为 1，加载或执行错误为 2。
- 单元测试覆盖报告模型、Console 输出、JSON 结构和退出码。
- 同步 `doc/下一步计划.md`，并把日志模块作为后续任务加入计划。

不覆盖：

- 不实现完整 `mwjrunner run` 执行编排。
- 不实现 HTML 报告。
- 不实现 tags、priority、retry、fail-fast、并发等调度能力。
- 不新增三方依赖。

## 设计方案

### 结果模型

新增 `mwjrunner/reports/` 包，报告模型只表达报告需要的数据，不反向依赖执行上下文。

建议模型：

- `Summary`：记录 case、step、assertion、error 统计和总耗时。
- `RunResult`：记录 run_id、started_at、ended_at、summary、cases、errors。
- `CaseResult`：记录 case 名称、来源文件、状态、步骤、错误。
- `StepResult`：记录 step 名称、状态、请求、响应、断言、提取、错误、耗时。

状态建议使用简单字符串：`passed`、`failed`、`error`、`skipped`。M1 只需要覆盖 `passed`、`failed`、`error`。

### ConsoleReporter

`ConsoleReporter` 只消费 `RunResult`，输出适合本地调试和 CI 日志的摘要：

- run_id。
- case / step / assertion 统计。
- passed / failed / error 统计。
- 总耗时。
- 失败或错误明细，包含 case、step 和 message。

Console 报告不读取执行上下文，不主动执行 HTTP 请求，不做调度。

### JsonReporter

`JsonReporter` 只消费 `RunResult`，生成结构化 JSON。JSON 报告必须包含：

- `summary`。
- `cases`。
- `steps`。
- `request`。
- `response`。
- `assertions`。
- `extracts`。
- `errors`。

JSON 写入文件时由调用方指定输出路径。M1 使用标准库 `json`，不新增依赖。

### 退出码映射

新增简单函数根据 `RunResult` 返回退出码：

- 没有失败断言、没有错误：`0`。
- 存在断言失败：`1`。
- 存在加载错误或执行错误：`2`。

如果同时存在断言失败和执行错误，优先返回 `2`，因为执行错误比断言失败更高优先级。

### 脱敏与安全

T9 不新增新的脱敏规则，报告消费的 `HttpRequest` / `HttpResponse` 快照应已经在 HTTP 层完成脱敏。

后续日志模块必须复用统一脱敏策略，避免日志和报告中明文出现 `token`、`password`、`cookie`、`secret`、`authorization` 等敏感字段。

### 日志模块后续任务

当前项目文档已经提到日志系统，但代码中尚未实现日志模块。需要在 `doc/下一步计划.md` 中增加后续任务：

- 初始化项目日志模块。
- 支持控制台和文件日志。
- 支持 run_id 关联日志和报告。
- 日志输出前复用敏感信息脱敏策略。
- 不在 T9 中实现，避免报告任务扩范围。

## 测试策略

- 使用 pytest 作为项目自身开发测试工具。
- 测试 `Summary` 和 `RunResult` 的序列化结果。
- 测试 `ConsoleReporter` 输出摘要和失败明细。
- 测试 `JsonReporter` 输出包含 case、step、request、response、assertions、extracts、errors。
- 测试退出码映射：成功、断言失败、执行错误、错误优先级。

## 文档同步

本任务实现时需要同步：

- `doc/下一步计划.md`：T9 完成情况和日志模块后续任务。
- 必要时同步 `doc/技术方案.md`、`doc/使用手册.md` 中与报告字段或退出码不一致的描述。

## 验收标准

- 可以通过单元测试验证 Console 和 JSON 报告能力。
- JSON 报告包含 case、step、request、response、assertions、extracts、errors。
- 退出码映射符合成功 0、断言失败 1、加载或执行错误 2。
- 报告逻辑与执行逻辑分离。
- 未引入 pytest / Allure 作为核心报告或执行能力。
- 日志模块后续任务已进入计划文档。
