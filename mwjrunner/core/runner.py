"""CLI run 执行编排。"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from mwjrunner.assertions.builtin import create_default_registry
from mwjrunner.cases.data_driver import expand_data_driven
from mwjrunner.cases.discovery import discover_case_files
from mwjrunner.cases.errors import CaseLoadError
from mwjrunner.cases.filter import filter_cases
from mwjrunner.cases.loader import load_yaml_case
from mwjrunner.cases.model import RequestSpec, TestCase, TestStep
from mwjrunner.config.loader import ConfigLoadError, load_config
from mwjrunner.config.model import AuthConfig
from mwjrunner.core.quality_gate import (
    QualityGateConfig,
    evaluate_quality_gate,
    parse_quality_gate_config,
)
from mwjrunner.hooks.executor import run_hooks
from mwjrunner.http.executor import HttpExecutor
from mwjrunner.http.model import HttpResult
from mwjrunner.logging.config import LogConfig
from mwjrunner.logging.setup import configure_logging
from mwjrunner.notifications import parse_notify_configs, send_notification
from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.exit_code import (
    ASSERTION_FAILED_EXIT_CODE,
    ERROR_EXIT_CODE,
    INTERNAL_ERROR_EXIT_CODE,
    QUALITY_GATE_EXIT_CODE,
    SUCCESS_EXIT_CODE,
    resolve_exit_code,
)
from mwjrunner.reports.html import HtmlReporter
from mwjrunner.reports.json import JsonReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary
from mwjrunner.variables.engine import VariableEngine, VariableError

_DEFAULT_TZ = ZoneInfo("Asia/Shanghai")

DEFAULT_REPORT_DIR = "reports"
DEFAULT_REPORT_TYPES = ("console",)


class RunConfigError(Exception):
    """run 命令配置错误。"""


class RunExecutor:
    """执行 YAML 用例文件或目录并生成报告。"""

    def __init__(
        self,
        *,
        path: str | Path,
        base_url: str | None = None,
        report: str | None = None,
        report_dir: str | Path | None = None,
        cli_variables: dict[str, Any] | None = None,
        retry: int = 2,
        fail_fast: bool = False,
        tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        priority: list[str] | None = None,
        workers: int = 1,
        timezone_name: str | None = None,
        auth: AuthConfig | None = None,
        quality_gate: QualityGateConfig | None = None,
        notify_configs: list[Any] | None = None,
    ) -> None:
        self.path = Path(path)
        self.base_url = base_url
        self.report_types = _parse_report_types(report)
        self.report_dir = Path(report_dir or DEFAULT_REPORT_DIR)
        self.cli_variables = dict(cli_variables or {})
        self.retry = retry
        self.fail_fast = fail_fast
        self.tags = tags
        self.exclude_tags = exclude_tags
        self.priority = priority
        self.workers = workers
        self.tz = ZoneInfo(timezone_name) if timezone_name else ZoneInfo("Asia/Shanghai")
        self.auth = auth
        self.quality_gate = quality_gate
        self.notify_configs = notify_configs or []

    def run(self) -> int:
        """执行用例、输出报告并返回退出码。"""
        result = self.execute()
        self.write_reports(result)

        # 发送通知
        self._send_notifications(result)

        if any(error.startswith("执行引擎内部错误") for error in result.errors):
            return INTERNAL_ERROR_EXIT_CODE

        exit_code = resolve_exit_code(result)

        # 质量门禁检查（仅在执行成功或断言失败时评估）
        if self.quality_gate and exit_code in (SUCCESS_EXIT_CODE, ASSERTION_FAILED_EXIT_CODE):
            gate_result = evaluate_quality_gate(result, self.quality_gate)
            if not gate_result.passed:
                for violation in gate_result.violations:
                    print(f"  [质量门禁] {violation}")
                return QUALITY_GATE_EXIT_CODE

        return exit_code

    def _send_notifications(self, result: RunResult) -> None:
        """发送通知（如果配置了通知渠道）。"""
        if not self.notify_configs:
            return
        for config in self.notify_configs:
            notify_result = send_notification(result, config)
            if not notify_result.success:
                print(f"  [通知] 发送失败: {notify_result.message}")

    def execute(self) -> RunResult:
        """执行用例并返回结构化运行结果。"""
        run_id = _new_run_id()
        started_at = datetime.now(self.tz)
        start_time = time.perf_counter()
        log_file = self.report_dir / run_id / "run.log"
        logger = configure_logging(LogConfig(run_id=run_id, log_file=log_file, console=True))
        logger.info("开始执行用例: %s", self.path)

        try:
            case_files = discover_case_files(self.path)
            if not case_files:
                message = f"未发现用例文件: {self.path}"
                logger.error(message)
                return _error_run_result(run_id, started_at, start_time, [message])

            # 加载并展开所有用例
            all_cases: list[TestCase] = []
            load_errors: list[CaseResult] = []
            for case_file in case_files:
                try:
                    case = load_yaml_case(case_file)
                    all_cases.extend(expand_data_driven(case))
                except CaseLoadError as exc:
                    logger.error("用例加载失败: %s - %s", case_file, exc)
                    load_errors.append(
                        CaseResult(
                            name=str(case_file),
                            status="error",
                            source_file=str(case_file),
                            errors=[str(exc)],
                        )
                    )

            # 过滤
            filtered_cases = filter_cases(
                all_cases,
                tags=self.tags,
                exclude_tags=self.exclude_tags,
                priority=self.priority,
            )

            if not filtered_cases and not load_errors:
                logger.info("过滤后无可执行用例")
                ended_at = datetime.now(self.tz)
                return RunResult(
                    run_id=run_id,
                    started_at=started_at,
                    ended_at=ended_at,
                    summary=_build_summary([], [], start_time),
                )

            # 执行
            case_results: list[CaseResult] = list(load_errors)

            if self.workers > 1 and len(filtered_cases) > 1:
                case_results.extend(self._run_concurrent(filtered_cases, logger))
            else:
                case_results.extend(self._run_serial(filtered_cases, logger))

            ended_at = datetime.now(self.tz)
            summary = _build_summary(case_results, [], start_time)
            result = RunResult(
                run_id=run_id,
                started_at=started_at,
                ended_at=ended_at,
                summary=summary,
                cases=case_results,
            )
            logger.info("执行完成, 共 %d 个用例", len(case_results))
            return result
        except RunConfigError as exc:
            logger.error("运行错误: %s", exc)
            return _error_run_result(run_id, started_at, start_time, [str(exc)])
        except Exception as exc:
            logger.exception("执行引擎内部错误")
            errors = [f"执行引擎内部错误: {exc}"]
            return _error_run_result(run_id, started_at, start_time, errors)

    def write_reports(self, result: RunResult) -> None:
        """按配置输出报告。"""
        if "console" in self.report_types:
            ConsoleReporter().write(result)
        if "json" in self.report_types:
            JsonReporter().write(result, self.report_dir / result.run_id / "result.json")
        if "html" in self.report_types:
            HtmlReporter().write(result, self.report_dir / result.run_id / "report.html")

    def _run_serial(self, cases: list[TestCase], logger: logging.Logger) -> list[CaseResult]:
        """串行执行用例。"""
        results: list[CaseResult] = []
        stopped = False
        for case_to_run in cases:
            if stopped:
                results.append(
                    CaseResult(
                        name=case_to_run.name,
                        status="skipped",
                        source_file=case_to_run.source_file,
                    )
                )
                continue
            case_result = self._execute_case_with_retry(case_to_run, logger)
            results.append(case_result)
            if self.fail_fast and case_result.status in ("failed", "error"):
                logger.info("fail-fast 触发, 停止后续用例执行")
                stopped = True
        return results

    def _run_concurrent(self, cases: list[TestCase], logger: logging.Logger) -> list[CaseResult]:
        """并发执行用例，结果按原始顺序返回。"""
        stop_event = Event()
        results: dict[int, CaseResult] = {}

        def run_one(index: int, case: TestCase) -> tuple[int, CaseResult]:
            if stop_event.is_set():
                return index, CaseResult(name=case.name, status="skipped", source_file=case.source_file)
            result = self._execute_case_with_retry(case, logger)
            if self.fail_fast and result.status in ("failed", "error"):
                stop_event.set()
            return index, result

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(run_one, i, case): i for i, case in enumerate(cases)}
            for future in as_completed(futures):
                index, case_result = future.result()
                results[index] = case_result

        return [results[i] for i in range(len(cases))]

    def _execute_case_with_retry(self, case: TestCase, logger: logging.Logger) -> CaseResult:
        """执行用例，支持失败重试。"""
        max_retry = case.retry if case.retry is not None else self.retry
        max_attempts = 1 + max_retry

        last_result: CaseResult | None = None
        for attempt in range(max_attempts):
            if attempt > 0:
                logger.info("重试用例: %s (attempt %d/%d)", case.name, attempt + 1, max_attempts)
            last_result = self._execute_case(case, logger)
            if last_result.status == "passed":
                return last_result
        return last_result  # type: ignore[return-value]

    def _execute_case(self, case: TestCase, logger: logging.Logger) -> CaseResult:
        variable_engine = VariableEngine({**case.variables, **self.cli_variables})
        context = variable_engine.variables

        # before_case hook
        before_hooks = _get_hook_paths(case.hooks, "before_case")
        if before_hooks:
            hook_result = run_hooks(before_hooks, context)
            if not hook_result.success:
                return CaseResult(
                    name=case.name,
                    status="error",
                    source_file=case.source_file,
                    errors=[hook_result.error or "before_case hook 失败"],
                )

        # 解析认证配置：case 级覆盖全局
        effective_auth = _resolve_auth(case.auth, self.auth, variable_engine)

        # 用例文件所在目录，用于解析相对路径
        case_dir = Path(case.source_file).parent if case.source_file else None

        http_executor = HttpExecutor(base_url=self.base_url)
        registry = create_default_registry()
        steps: list[StepResult] = []
        errors: list[str] = []

        for step in case.steps:
            step_result = self._execute_step(
                step,
                variable_engine,
                http_executor,
                registry,
                logger,
                effective_auth,
                case_dir,
            )
            steps.append(step_result)
            if step_result.status == "error":
                errors.extend(step_result.errors)
                break

        if errors:
            status = "error"
        elif any(step.status == "failed" for step in steps):
            status = "failed"
        else:
            status = "passed"

        # after_case hook
        after_hooks = _get_hook_paths(case.hooks, "after_case")
        if after_hooks:
            hook_result = run_hooks(after_hooks, context)
            if not hook_result.success:
                errors.append(hook_result.error or "after_case hook 失败")
                status = "error"

        return CaseResult(
            name=case.name,
            status=status,
            source_file=case.source_file,
            steps=steps,
            errors=errors,
        )

    def _execute_step(
        self,
        step: TestStep,
        variable_engine: VariableEngine,
        http_executor: HttpExecutor,
        registry: Any,
        logger: logging.Logger,
        auth_header: str | None = None,
        case_dir: Path | None = None,
    ) -> StepResult:
        start_time = time.perf_counter()
        logger.info("开始执行步骤: %s", step.name)
        try:
            rendered_request = _render_request(step.request, variable_engine, case_dir)
            # 注入认证 header（不覆盖用户显式声明的 Authorization）
            if auth_header and "authorization" not in {k.lower() for k in rendered_request.headers}:
                rendered_request = replace(
                    rendered_request,
                    headers={**rendered_request.headers, "Authorization": auth_header},
                )
            http_result = http_executor.execute(rendered_request)
            if http_result.error is not None:
                message = f"HTTP 请求失败: {http_result.error.error_type}: {http_result.error.message}"
                logger.error("步骤执行错误: %s", message)
                return _step_result(step.name, "error", http_result, [], [], [message], start_time)

            extracts = variable_engine.extract_all(step.extract, http_result)
            assertions = registry.execute_all(step.assertions, http_result)
            status = "failed" if any(not assertion.passed for assertion in assertions) else "passed"
            logger.info("步骤执行完成: %s, status=%s", step.name, status)
            return _step_result(step.name, status, http_result, assertions, extracts, [], start_time)
        except VariableError as exc:
            message = f"变量处理失败: {exc}"
            logger.error("步骤执行错误: %s", message)
            return StepResult(
                name=step.name,
                status="error",
                errors=[message],
                elapsed_ms=_elapsed_ms(start_time),
            )


def run_from_args(args: Any) -> int:
    """从 argparse 参数执行 run 子命令。"""
    try:
        unsupported_options = _collect_unsupported_options(args)
        if unsupported_options:
            joined_options = ", ".join(unsupported_options)
            _raise_config_error(f"当前 run 暂不支持参数: {joined_options}")

        cli_variables = _parse_cli_variables(getattr(args, "var", []) or [])
        path = getattr(args, "path", None) or _raise_config_error("缺少用例文件路径")

        # 加载配置（项目配置 + 环境配置）
        env_name = getattr(args, "env", None)
        project_dir = Path(path).parent if Path(path).is_file() else Path(path)
        try:
            config = load_config(env=env_name, project_dir=project_dir)
        except ConfigLoadError as exc:
            _raise_config_error(str(exc))
            return ERROR_EXIT_CODE  # unreachable, for type checker

        # CLI 参数覆盖配置
        base_url = getattr(args, "base_url", None) or config.base_url
        report = getattr(args, "report", None)
        report_dir = getattr(args, "report_dir", None) or config.report_dir
        retry = getattr(args, "retry", None) or config.retry
        fail_fast = getattr(args, "fail_fast", False) or config.fail_fast
        workers = getattr(args, "workers", None) or config.workers

        # 解析过滤参数
        tags = _parse_comma_list(getattr(args, "tags", None))
        exclude_tags = _parse_comma_list(getattr(args, "exclude_tags", None))
        priority = _parse_comma_list(getattr(args, "priority", None))

        # 合并变量：config.variables < cli_variables
        merged_variables = {**config.variables, **cli_variables}

        executor = RunExecutor(
            path=path,
            base_url=base_url,
            report=report,
            report_dir=report_dir,
            cli_variables=merged_variables,
            retry=retry,
            fail_fast=fail_fast,
            tags=tags,
            exclude_tags=exclude_tags,
            priority=priority,
            workers=workers,
            timezone_name=config.timezone,
            auth=config.auth,
            quality_gate=parse_quality_gate_config(config.quality_gate),
            notify_configs=_parse_notify_configs(config.notifications),
        )
        return executor.run()
    except RunConfigError as exc:
        run_id = _new_run_id()
        started_at = datetime.now(_DEFAULT_TZ)
        result = RunResult(
            run_id=run_id,
            started_at=started_at,
            ended_at=datetime.now(_DEFAULT_TZ),
            summary=Summary(total_errors=1),
            errors=[str(exc)],
        )
        ConsoleReporter().write(result)
        return ERROR_EXIT_CODE


def _render_request(request: RequestSpec, variable_engine: VariableEngine, case_dir: Path | None = None) -> RequestSpec:
    rendered_files = None
    if request.files:
        rendered_files = []
        for file_spec in request.files:
            rendered_spec = {k: variable_engine.render(v) for k, v in file_spec.items()}
            # 解析相对路径
            if case_dir and "path" in rendered_spec:
                file_path = Path(rendered_spec["path"])
                if not file_path.is_absolute():
                    rendered_spec["path"] = str(case_dir / file_path)
            rendered_files.append(rendered_spec)

    return replace(
        request,
        method=variable_engine.render(request.method),
        url=variable_engine.render(request.url),
        headers=variable_engine.render(request.headers),
        query=variable_engine.render(request.query),
        cookies=variable_engine.render(request.cookies),
        json=variable_engine.render(request.json),
        data=variable_engine.render(request.data),
        body=variable_engine.render(request.body),
        files=rendered_files,
    )


def _resolve_auth(
    case_auth: dict[str, Any] | None,
    global_auth: AuthConfig | None,
    variable_engine: VariableEngine,
) -> str | None:
    """解析认证配置，返回 Authorization header 值。case 级优先于全局。"""
    auth_dict = case_auth
    if auth_dict is not None:
        # case 级 auth，先渲染变量
        rendered = variable_engine.render(auth_dict)
        auth_config = AuthConfig(
            type=rendered.get("type", "bearer"),
            token=rendered.get("token"),
            username=rendered.get("username"),
            password=rendered.get("password"),
        )
        return auth_config.to_header_value()
    if global_auth is not None:
        # 全局 auth 中的 token 等字段也可能包含变量引用
        rendered_token = variable_engine.render(global_auth.token) if global_auth.token else global_auth.token
        rendered_username = (
            variable_engine.render(global_auth.username) if global_auth.username else global_auth.username
        )
        rendered_password = (
            variable_engine.render(global_auth.password) if global_auth.password else global_auth.password
        )
        resolved = AuthConfig(
            type=global_auth.type,
            token=rendered_token,
            username=rendered_username,
            password=rendered_password,
        )
        return resolved.to_header_value()
    return None


def _step_result(
    name: str,
    status: str,
    http_result: HttpResult,
    assertions: list[Any],
    extracts: list[Any],
    errors: list[str],
    start_time: float,
) -> StepResult:
    return StepResult(
        name=name,
        status=status,
        request=http_result.request,
        response=http_result.response,
        assertions=assertions,
        extracts=extracts,
        errors=errors,
        elapsed_ms=_elapsed_ms(start_time),
    )


def _build_summary(case_results: list[CaseResult], errors: list[str], start_time: float) -> Summary:
    total_steps = sum(len(case.steps) for case in case_results)
    passed_steps = sum(1 for case in case_results for step in case.steps if step.status == "passed")
    failed_steps = sum(1 for case in case_results for step in case.steps if step.status == "failed")
    error_steps = sum(1 for case in case_results for step in case.steps if step.status == "error")
    total_assertions = sum(len(step.assertions) for case in case_results for step in case.steps)
    failed_assertions = sum(
        1 for case in case_results for step in case.steps for assertion in step.assertions if not assertion.passed
    )
    step_errors = sum(len(step.errors) for case in case_results for step in case.steps)
    return Summary(
        total_cases=len(case_results),
        passed_cases=sum(1 for case in case_results if case.status == "passed"),
        failed_cases=sum(1 for case in case_results if case.status == "failed"),
        error_cases=sum(1 for case in case_results if case.status == "error"),
        skipped_cases=sum(1 for case in case_results if case.status == "skipped"),
        total_steps=total_steps,
        passed_steps=passed_steps,
        failed_steps=failed_steps,
        error_steps=error_steps,
        total_assertions=total_assertions,
        failed_assertions=failed_assertions,
        total_errors=len(errors) + step_errors,
        elapsed_ms=_elapsed_ms(start_time),
    )


def _error_run_result(run_id: str, started_at: datetime, start_time: float, errors: list[str]) -> RunResult:
    ended_at = datetime.now(_DEFAULT_TZ)
    return RunResult(
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        summary=_build_summary([], errors, start_time),
        errors=errors,
    )


def _parse_report_types(report: str | None) -> tuple[str, ...]:
    if report is None:
        return DEFAULT_REPORT_TYPES
    report_types = tuple(item.strip().lower() for item in report.split(",") if item.strip())
    if not report_types:
        return DEFAULT_REPORT_TYPES
    supported = {"console", "json", "html"}
    unsupported = [item for item in report_types if item not in supported]
    if unsupported:
        raise RunConfigError(f"不支持的报告类型: {', '.join(unsupported)}")
    return report_types


def _collect_unsupported_options(_args: Any) -> list[str]:
    return []


def _parse_comma_list(value: str | None) -> list[str] | None:
    """解析逗号分隔的字符串为列表，None 输入返回 None。"""
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items if items else None


def _get_hook_paths(hooks: dict[str, str | list[str]], key: str) -> list[str]:
    """从 hooks dict 中获取指定 key 的 hook 路径列表。"""
    value = hooks.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return value


def _parse_cli_variables(raw_variables: list[str]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for raw_variable in raw_variables:
        if "=" not in raw_variable:
            raise RunConfigError(f"运行变量格式错误: {raw_variable}, 应使用 KEY=VALUE")
        key, value = raw_variable.split("=", 1)
        if not key:
            raise RunConfigError(f"运行变量名称不能为空: {raw_variable}")
        variables[key] = value
    return variables


def _raise_config_error(message: str) -> None:
    raise RunConfigError(message)


def _new_run_id() -> str:
    timestamp = datetime.now(_DEFAULT_TZ).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _elapsed_ms(start_time: float) -> float:
    return round((time.perf_counter() - start_time) * 1000, 3)


def _parse_notify_configs(raw: list[dict[str, Any]] | None) -> list[Any]:
    """解析通知配置列表。"""
    if not raw:
        return []
    return parse_notify_configs(raw)
