"""Synchronize Claude project assets to Codex project assets.

Source of truth:
- CLAUDE.md -> AGENTS.md
- .claude/skills/* -> .agents/skills/*

The generated Codex files keep the same project rules while translating
tool-specific names, paths, and plugin identifiers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".csv",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

TEXT_REPLACEMENTS = (
    ("CLAUDE.md", "AGENTS.md"),
    ("Claude Code", "Codex"),
    ("claude-plugins-official", "Codex-plugins-official"),
    ("claude plugin", "Codex plugin"),
    (".claude/skills/py-code-review", ".agents/skills/code-review"),
    (".claude/skills/ui-ux-pro-max-new", ".agents/skills/ui-ux-pro-max"),
    (".claude/skills", ".agents/skills"),
    ("py-code-review", "code-review"),
    ("ui-ux-pro-max-new", "ui-ux-pro-max"),
)

CODEX_POST_REPLACEMENTS = (
    (
        "`AGENTS.md` 和 `.agents/skills/` 是项目级智能体指南与技能的源内容。",
        "`CLAUDE.md` 和 `.claude/skills/` 是项目级智能体指南与技能的源内容。",
    ),
)

SKILL_MAPPINGS = (
    (Path(".claude/skills/py-code-review"), Path(".agents/skills/code-review")),
    (Path(".claude/skills/req-doc-generator"), Path(".agents/skills/req-doc-generator")),
    (Path(".claude/skills/ui-ux-pro-max-new"), Path(".agents/skills/ui-ux-pro-max")),
)

IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def render_codex_text(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in CODEX_POST_REPLACEMENTS:
        text = text.replace(old, new)
    return "\n".join(line.rstrip() for line in text.splitlines()) + ("\n" if text.endswith("\n") else "")


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def read_rendered_source(source: Path) -> bytes:
    if is_text_file(source):
        text = source.read_text(encoding="utf-8")
        return render_codex_text(text).encode("utf-8")
    return source.read_bytes()


def assert_under_root(path: Path) -> None:
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise RuntimeError(f"Refusing to write outside workspace: {resolved_path}")


def sync_file(source: Path, target: Path, write: bool) -> list[str]:
    expected = read_rendered_source(source)
    if target.exists() and target.read_bytes() == expected:
        return []

    if write:
        assert_under_root(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(expected)
        return [f"updated {target.relative_to(ROOT)}"]
    return [f"outdated {target.relative_to(ROOT)}"]


def iter_source_files(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.rglob("*") if path.is_file() and not is_ignored(path))


def expected_targets(source_dir: Path, target_dir: Path) -> set[Path]:
    return {target_dir / path.relative_to(source_dir) for path in iter_source_files(source_dir)}


def sync_dir(source_dir: Path, target_dir: Path, write: bool) -> list[str]:
    changes: list[str] = []
    for source in iter_source_files(source_dir):
        target = target_dir / source.relative_to(source_dir)
        changes.extend(sync_file(source, target, write))

    if target_dir.exists():
        expected = expected_targets(source_dir, target_dir)
        for target in sorted(path for path in target_dir.rglob("*") if path.is_file() and not is_ignored(path)):
            if target not in expected:
                message = f"extra {target.relative_to(ROOT)}"
                if write:
                    assert_under_root(target)
                    target.unlink()
                    changes.append(f"removed {target.relative_to(ROOT)}")
                else:
                    changes.append(message)

    return changes


def sync(write: bool) -> list[str]:
    changes: list[str] = []
    changes.extend(sync_file(ROOT / "CLAUDE.md", ROOT / "AGENTS.md", write))
    for source_rel, target_rel in SKILL_MAPPINGS:
        changes.extend(sync_dir(ROOT / source_rel, ROOT / target_rel, write))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Claude assets to Codex assets.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write generated Codex assets")
    mode.add_argument("--check", action="store_true", help="check whether Codex assets are up to date")
    args = parser.parse_args()

    changes = sync(write=args.write)
    if changes:
        for change in changes:
            print(change)
        return 0 if args.write else 1

    print("Codex agent assets are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
