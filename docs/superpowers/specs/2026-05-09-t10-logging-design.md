# T10 日志模块设计

## 目标

实现 MwjRunner 自有日志基础能力，为后续完整执行编排、CI 排查和报告关联提供稳定日志入口。

日志模块应支持控制台日志、文件日志、日志级别配置、`run_id` 关联和敏感信息脱敏。它只负责日志初始化、格式化和安全输出，不依赖报告模块，也不读取执行过程中的可变上下文。

## 范围

覆盖：

- 新增独立日志模块，建议路径为 `mwjrunner/logging/`。
- 提供统一初始化函数，由 CLI 或后续 engine 在运行开始时调用。
- 支持控制台日志和文件日志。
- 支持 `run_id` 注入日志记录，方便与后续 `RunResult`、JSON 报告、HTML 报告关联。
- 支持日志级别配置，默认使用 `INFO`。
- 输出前执行敏感信息脱敏，覆盖 `token`、`password`、`cookie`、`secret`、`authorization`、`access_token`、`refresh_token`、`set-cookie` 等字段。
- 新增 `doc/开发问题跟踪.md`，用于沉淀开发过程中发现的 P0-P3 问题。
- 更新 `doc/下一步计划.md`，把 HTML report 模板渲染列为后置任务，并明确最后开发。

不覆盖：

- 不实现完整 `mwjrunner run` 执行编排。
- 不实现 HTML 报告页面。
- 不实现日志轮转、远程日志收集或结构化日志平台接入。
- 不新增三方依赖。

## 设计方案

### 日志模块边界

新增 `mwjrunner/logging/` 包，负责日志相关能力：

- `config.py`：日志配置模型，例如日志级别、日志文件路径、是否启用控制台输出。
- `context.py`：`run_id` 上下文适配，保证日志格式中可以稳定出现 `run_id`。
- `redaction.py`：日志输出前的敏感信息脱敏函数。T10 可以先在日志模块内提供独立实现，后续 T11 再抽成报告和日志共享的统一脱敏策略。
- `setup.py`：日志初始化入口，封装 Python 标准库 `logging` 细节。
- `__init__.py`：导出稳定 API。

日志模块不依赖 `mwjrunner.reports`，也不反向读取 `RunResult`。后续完整运行流程中，engine / CLI 负责同时生成 `run_id`、初始化日志、收集 `RunResult`，日志与报告只通过相同 `run_id` 建立关联。

### 日志初始化

提供统一初始化入口，例如：

```python
configure_logging(config: LogConfig) -> logging.Logger
```

建议配置项：

- `level: str = "INFO"`
- `run_id: str = "-"`
- `log_file: Path | None = None`
- `console: bool = True`

初始化时使用标准库 `logging`：

- 创建项目 logger，例如 `mwjrunner`。
- 清理该 logger 已有 handler，避免重复初始化导致重复输出。
- 根据配置添加 `StreamHandler` 和可选 `FileHandler`。
- 使用统一 formatter，包含时间、级别、run_id、logger 名称和消息。

### run_id 关联

T10 不负责生成 `run_id`，只消费外部传入的 `run_id`。后续 CLI / engine 在一次运行开始时生成 `run_id`，并传给日志配置和 `RunResult`。

日志格式建议：

```text
%(asctime)s %(levelname)s [run_id=%(run_id)s] %(name)s - %(message)s
```

可通过 logging `Filter` 给记录注入 `run_id`。如果调用方没有传入，默认使用 `-`，避免格式化失败。

### 敏感信息脱敏

日志输出前必须脱敏。T10 优先覆盖日志消息和常见 dict/list 参数，不追求复杂模板引擎。

默认敏感字段：

- `authorization`
- `token`
- `access_token`
- `refresh_token`
- `password`
- `secret`
- `cookie`
- `set-cookie`

脱敏值统一使用 `***REDACTED***`。

大小写不敏感匹配字段名。对于嵌套 dict/list 递归处理；对于普通字符串，至少覆盖常见 `key=value`、`key: value` 形式中的敏感值。T11 再统一整理成日志和报告共享脱敏能力。

### 错误处理

- 日志目录不存在时由日志初始化创建父目录。
- 日志级别非法时抛出清晰的 `ValueError`，提示支持的级别。
- 文件日志写入失败不在日志模块内吞掉异常，由调用方决定是否降级为仅控制台输出。

### P0-P3 问题跟踪文档

新增 `doc/开发问题跟踪.md`，用于记录开发过程中发现但不适合在当前任务内修复的问题。

字段建议：

- 编号。
- 优先级：P0 / P1 / P2 / P3。
- 问题描述。
- 影响。
- 发现阶段。
- 建议修复方式。
- 状态。
- 相关文件。

当前任务发现的问题需要写入该文档。已知需要记录：`doc/下一步计划.md` 的后续任务池中仍存在已完成 T9 的旧条目，需要在本轮计划同步时清理。

### HTML report 后置任务

HTML report 不在 T10 实现。计划文档中新增后置任务，明确：

- HTML report 最后开发，先完成日志、脱敏、执行编排、调度等核心能力。
- HTML report 数据源复用 `RunResult.to_dict()` / JSON 报告结构。
- HTML report 通过数据渲染到 HTML 模板，不反向依赖执行上下文。
- HTML 输出必须转义用户可控内容，避免 XSS。
- HTML 输出必须复用统一脱敏策略。

## 测试策略

使用 pytest 作为项目自身开发测试工具，不作为 MwjRunner 核心执行或断言机制。

覆盖测试：

- 日志初始化返回项目 logger。
- 控制台日志包含 `run_id`。
- 文件日志可以写入指定路径并包含 `run_id`。
- 日志级别配置生效。
- 日志消息中的敏感字段被脱敏。
- 嵌套 dict/list 中的敏感字段被脱敏。
- 日志模块不导入、不依赖 `mwjrunner.reports`。

## 文档同步

T10 实现时同步：

- `doc/下一步计划.md`：T10 状态、P0-P3 问题跟踪规则、HTML report 后置任务。
- `doc/开发问题跟踪.md`：开发过程中发现的问题清单。
- 必要时同步 `doc/技术方案.md` 中日志模块和报告后续方向。

## 验收标准

- 每次运行可以通过日志配置写出带 `run_id` 的日志。
- 控制台日志和文件日志不明文输出 token、password、cookie、secret、authorization 等敏感字段。
- 日志模块不依赖报告模块。
- 日志模块只封装日志初始化和安全输出，不包含执行、断言、报告生成逻辑。
- P0-P3 问题跟踪文档已创建。
- HTML report 模板渲染已作为最后开发的后置任务进入计划。
