"""CLI run 最小执行编排。"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from mwjrunner.assertions.builtin import create_default_registry
from mwjrunner.cases.errors import CaseLoadError
from mwjrunner.cases.loader import load_yaml_case
from mwjrunner.cases.model import RequestSpec, TestCase, TestStep
from mwjrunner.http.executor import HttpExecutor
from mwjrunner.http.model import HttpResult
from mwjrunner.logging.config import LogConfig
from mwjrunner.logging.setup import configure_logging
from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.exit_code import ERROR_EXIT_CODE, INTERNAL_ERROR_EXIT_CODE, resolve_exit_code
from mwjrunner.reports.html import HtmlReporter
from mwjrunner.reports.json import JsonReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary
from mwjrunner.variables.engine import VariableEngine, VariableError

DEFAULT_REPORT_DIR = "reports"
DEFAULT_REPORT_TYPES = ("console",)


class RunConfigError(Exception):
    """run 命令配置错误。"""


class RunExecutor:
    """执行单个 YAML 用例文件并生成报告。"""

    def __init__(
        self,
        *,
        path: str | Path,
        base_url: str | None = None,
        report: str | None = None,
        report_dir: str | Path | None = None,
        cli_variables: dict[str, Any] | None = None,
    ) -> None:
        self.path = Path(path)
        self.base_url = base_url
        self.report_types = _parse_report_types(report)
        self.report_dir = Path(report_dir or DEFAULT_REPORT_DIR)
        self.cli_variables = dict(cli_variables or {})

    def run(self) -> int:
        """执行用例、输出报告并返回退出码。"""
        result = self.execute()
        self.write_reports(result)
        if any(error.startswith("执行引擎内部错误") for error in result.errors):
            return INTERNAL_ERROR_EXIT_CODE
        return resolve_exit_code(result)

    def execute(self) -> RunResult:
        """执行用例并返回结构化运行结果。"""
        run_id = _new_run_id()
        started_at = datetime.now(UTC)
        start_time = time.perf_counter()
        log_file = self.report_dir / run_id / "run.log"
        logger = configure_logging(LogConfig(run_id=run_id, log_file=log_file, console=True))
        logger.info("开始执行用例: %s", self.path)

        try:
            case = load_yaml_case(self.path)
            case_result = self._execute_case(case, logger)
            ended_at = datetime.now(UTC)
            summary = _build_summary([case_result], [], start_time)
            result = RunResult(
                run_id=run_id,
                started_at=started_at,
                ended_at=ended_at,
                summary=summary,
                cases=[case_result],
            )
            logger.info("用例执行完成: %s", case.name)
            return result
        except (CaseLoadError, RunConfigError) as exc:
            logger.error("运行错误: %s", exc)
            errors = [str(exc)]
            return _error_run_result(run_id, started_at, start_time, errors)
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

    def _execute_case(self, case: TestCase, logger: logging.Logger) -> CaseResult:
        variable_engine = VariableEngine({**case.variables, **self.cli_variables})
        http_executor = HttpExecutor(base_url=self.base_url)
        registry = create_default_registry()
        steps: list[StepResult] = []
        errors: list[str] = []

        for step in case.steps:
            step_result = self._execute_step(step, variable_engine, http_executor, registry, logger)
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
    ) -> StepResult:
        start_time = time.perf_counter()
        logger.info("开始执行步骤: %s", step.name)
        try:
            rendered_request = _render_request(step.request, variable_engine)
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
        executor = RunExecutor(
            path=getattr(args, "path", None) or _raise_config_error("缺少用例文件路径"),
            base_url=getattr(args, "base_url", None),
            report=getattr(args, "report", None),
            report_dir=getattr(args, "report_dir", None),
            cli_variables=cli_variables,
        )
        return executor.run()
    except RunConfigError as exc:
        run_id = _new_run_id()
        started_at = datetime.now(UTC)
        result = RunResult(
            run_id=run_id,
            started_at=started_at,
            ended_at=datetime.now(UTC),
            summary=Summary(total_errors=1),
            errors=[str(exc)],
        )
        ConsoleReporter().write(result)
        return ERROR_EXIT_CODE


def _render_request(request: RequestSpec, variable_engine: VariableEngine) -> RequestSpec:
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
    )


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
    ended_at = datetime.now(UTC)
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


def _collect_unsupported_options(args: Any) -> list[str]:
    unsupported: list[str] = []
    option_names = {
        "env": "--env",
        "tags": "--tags",
        "exclude_tags": "--exclude-tags",
        "priority": "--priority",
        "workers": "--workers",
        "retry": "--retry",
        "fail_fast": "--fail-fast",
    }
    for attr_name, option_name in option_names.items():
        value = getattr(args, attr_name, None)
        if value not in (None, False):
            unsupported.append(option_name)
    return unsupported


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
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _elapsed_ms(start_time: float) -> float:
    return round((time.perf_counter() - start_time) * 1000, 3)
