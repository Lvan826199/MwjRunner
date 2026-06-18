"""Run the local release readiness gate for MwjRunner."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]


def build_checks(include_httpbin: bool) -> list[Check]:
    """Build the release gate command list."""
    checks = [
        Check("Ruff 全仓检查", ("uv", "run", "ruff", "check", ".")),
        Check(
            "单元测试与集成测试",
            ("uv", "run", "pytest", "tests/unit", "tests/integration", "-q", "-p", "no:cacheprovider"),
        ),
        Check(
            "Quick Start 用例格式校验",
            ("uv", "run", "mwjrunner", "validate", "examples/cases/quickstart_httpbin.yaml"),
        ),
    ]
    if include_httpbin:
        checks.append(
            Check(
                "外部 httpbin smoke",
                (
                    "uv",
                    "run",
                    "mwjrunner",
                    "run",
                    "examples/cases/quickstart_httpbin.yaml",
                    "--base-url",
                    "https://httpbin.org",
                    "--report",
                    "console,json",
                    "--report-dir",
                    "reports/release-smoke",
                ),
            )
        )
    return checks


def run_check(check: Check, env: dict[str, str]) -> int:
    """Run one check and return its exit code."""
    print(f"\n==> {check.name}")
    print(" ".join(check.command))
    completed = subprocess.run(check.command, cwd=ROOT, env=env, check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MwjRunner release readiness checks.")
    parser.add_argument(
        "--include-httpbin",
        action="store_true",
        help="also run the external httpbin smoke test; this requires network access",
    )
    args = parser.parse_args(argv)

    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(ROOT / ".uv-cache"))

    failed: list[str] = []
    for check in build_checks(include_httpbin=args.include_httpbin):
        exit_code = run_check(check, env)
        if exit_code != 0:
            failed.append(f"{check.name} (exit={exit_code})")

    if failed:
        print("\n发布门禁失败:")
        for item in failed:
            print(f"- {item}")
        return 1

    print("\n发布门禁通过。")
    if not args.include_httpbin:
        print("提示：发布前如需覆盖外部网络 smoke，可追加 --include-httpbin。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
