"""MwjRunner 命令行入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

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
    run_parser.add_argument("--env", help="环境名称,对应 envs/<name>.yaml。")
    run_parser.add_argument("--tags", help="仅运行指定标签用例,多个标签可用逗号分隔。")
    run_parser.add_argument("--exclude-tags", help="排除指定标签用例,多个标签可用逗号分隔。")
    run_parser.add_argument("--priority", help="仅运行指定优先级用例,多个可用逗号分隔。")
    run_parser.add_argument("--workers", type=int, help="并发执行 worker 数量。")
    run_parser.add_argument("--retry", type=int, help="失败重试次数。")
    run_parser.add_argument("--fail-fast", action="store_true", help="遇到失败后尽快停止执行。")
    run_parser.add_argument("--report", help="报告输出类型,多个类型可用逗号分隔。")
    run_parser.add_argument("--report-dir", help="报告输出目录。")
    run_parser.add_argument("--var", action="append", default=[], metavar="KEY=VALUE", help="设置运行变量,可重复传入。")
    run_parser.add_argument("--base-url", help="HTTP 请求基础地址。")
    run_parser.set_defaults(handler=handle_run)

    # validate 子命令
    validate_parser = subparsers.add_parser(
        "validate",
        help="校验用例文件格式",
        description="校验 YAML 用例文件格式是否正确,不执行请求。",
    )
    validate_parser.add_argument("path", help="用例文件或用例目录路径。")
    validate_parser.set_defaults(handler=handle_validate)

    # init 子命令
    init_parser = subparsers.add_parser(
        "init",
        help="初始化项目目录结构",
        description="在当前目录创建 MwjRunner 推荐的项目结构。",
    )
    init_parser.add_argument("--dir", default=".", help="初始化目标目录,默认当前目录。")
    init_parser.set_defaults(handler=handle_init)

    # import 子命令
    import_parser = subparsers.add_parser(
        "import",
        help="导入外部用例集合",
        description="从 Postman Collection 等格式导入并生成 MwjRunner YAML 用例。",
    )
    import_parser.add_argument("source", help="源文件路径（如 postman_collection.json）。")
    import_parser.add_argument("--format", default="postman", choices=["postman", "openapi"], help="源格式,默认 postman。")
    import_parser.add_argument("--output", "-o", default="cases/imported", help="输出目录,默认 cases/imported。")
    import_parser.set_defaults(handler=handle_import)

    return parser


def handle_run(args: argparse.Namespace) -> int:
    """处理 run 子命令。"""
    return run_from_args(args)


def handle_validate(args: argparse.Namespace) -> int:
    """处理 validate 子命令：校验用例文件格式。"""
    from mwjrunner.cases.discovery import discover_case_files
    from mwjrunner.cases.errors import CaseLoadError
    from mwjrunner.cases.loader import load_yaml_case

    path = Path(args.path)
    case_files = discover_case_files(path)
    if not case_files:
        print(f"未发现用例文件: {path}")
        return 2

    errors: list[str] = []
    for case_file in case_files:
        try:
            load_yaml_case(case_file)
            print(f"  [OK] {case_file}")
        except CaseLoadError as exc:
            print(f"  [FAIL] {case_file}")
            print(f"    {exc}")
            errors.append(str(case_file))

    print()
    total = len(case_files)
    failed = len(errors)
    print(f"校验完成: {total} 个文件, {total - failed} 个通过, {failed} 个失败")
    return 1 if errors else 0


def handle_init(args: argparse.Namespace) -> int:
    """处理 init 子命令：初始化项目目录结构。"""
    target = Path(args.dir)
    dirs_to_create = [
        target / "cases",
        target / "envs",
        target / "reports",
    ]
    files_to_create = {
        target / "mwjrunner.yaml": (
            "# MwjRunner 项目配置\n"
            "# base_url: http://localhost:8000\n"
            "# timeout: 30\n"
            "# timezone: Asia/Shanghai\n"
            "# report_dir: reports\n"
        ),
        target / "envs" / "dev.yaml": (
            "# 开发环境配置\n"
            "base_url: http://localhost:8000\n"
            "variables:\n"
            "  env_name: dev\n"
        ),
        target / "cases" / "example.yaml": (
            "name: 示例用例\n"
            "tags: [smoke]\n"
            "priority: P0\n"
            "steps:\n"
            "  - name: 健康检查\n"
            "    request:\n"
            "      method: GET\n"
            "      url: /health\n"
            "    assertions:\n"
            "      - type: status_code\n"
            "        expected: 200\n"
        ),
    }

    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  目录: {d}")

    for file_path, content in files_to_create.items():
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")
            print(f"  文件: {file_path}")
        else:
            print(f"  跳过: {file_path} (已存在)")

    print()
    print("项目初始化完成。运行 mwjrunner run cases/ --base-url <url> 开始测试。")
    return 0


def handle_import(args: argparse.Namespace) -> int:
    """处理 import 子命令：导入外部用例集合。"""
    from mwjrunner.importers import import_postman_collection
    from mwjrunner.importers.openapi import generate_from_openapi

    source = Path(args.source)
    output = Path(args.output)
    fmt = args.format

    try:
        if fmt == "postman":
            generated = import_postman_collection(source, output)
        elif fmt == "openapi":
            generated = generate_from_openapi(source, output)
        else:
            print(f"不支持的导入格式: {fmt}")
            return 2
    except (FileNotFoundError, ValueError) as exc:
        print(f"导入失败: {exc}")
        return 2

    if not generated:
        print("未发现可导入的请求。")
        return 0

    print(f"导入完成，共生成 {len(generated)} 个用例文件:")
    for file_path in generated:
        print(f"  {file_path}")
    return 0


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
