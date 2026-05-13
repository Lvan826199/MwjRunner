"""MwjRunner 命令行入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mwjrunner.core.runner import run_from_args


def build_parser() -> argparse.ArgumentParser:
    """构建 MwjRunner 命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="mwjrunner",
        description="MwjRunner 接口自动化测试执行引擎。",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        help="可用子命令",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="运行接口自动化测试用例",
        description="运行接口自动化测试用例。支持单个 YAML 用例文件或目录批量执行。",
    )
    run_parser.add_argument(
        "path",
        nargs="?",
        help="用例文件或用例目录路径。",
    )
    run_parser.add_argument(
        "--env",
        help="环境配置文件路径。",
    )
    run_parser.add_argument(
        "--tags",
        help="仅运行指定标签用例,多个标签可用逗号分隔。",
    )
    run_parser.add_argument(
        "--exclude-tags",
        help="排除指定标签用例,多个标签可用逗号分隔。",
    )
    run_parser.add_argument(
        "--priority",
        help="仅运行指定优先级用例。",
    )
    run_parser.add_argument(
        "--workers",
        type=int,
        help="并发执行 worker 数量。",
    )
    run_parser.add_argument(
        "--retry",
        type=int,
        help="失败重试次数。",
    )
    run_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="遇到失败后尽快停止执行。",
    )
    run_parser.add_argument(
        "--report",
        help="报告输出类型,多个类型可用逗号分隔。",
    )
    run_parser.add_argument(
        "--report-dir",
        help="报告输出目录。",
    )
    run_parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="设置运行变量,可重复传入。",
    )
    run_parser.add_argument(
        "--base-url",
        help="HTTP 请求基础地址。",
    )
    run_parser.set_defaults(handler=handle_run)

    return parser


def handle_run(args: argparse.Namespace) -> int:
    """处理 run 子命令。"""
    return run_from_args(args)


def main(argv: Sequence[str] | None = None) -> int:
    """执行命令行入口并返回进程退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
