#!/usr/bin/env python3
"""Inventory repository facts without interpreting or reading file contents."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".local",
    ".next",
    ".venv",
    ".worktrees",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "vendor",
}

LANGUAGES = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".scala": "Scala",
    ".sh": "Shell",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
}

BUILD_MARKERS = {
    "Cargo.toml",
    "Gemfile",
    "Makefile",
    "Package.swift",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "settings.gradle",
    "settings.gradle.kts",
}

EXACT_GUIDANCE = {
    ".aider.conf.yml",
    ".cursorrules",
    ".kilocoderules",
    ".windsurfrules",
    "AGENT.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "OPERATING.md",
    "SKILL.md",
    "copilot-instructions.md",
}

HARNESS_DIRS = {
    ".agents",
    ".claude",
    ".cline",
    ".clinerules",
    ".codex",
    ".cursor",
    ".gemini",
    ".kilo",
    ".kilocode",
    ".opencode",
    ".pi",
    ".roo",
    ".windsurf",
}

HARNESS_FILES = {
    ".aider.conf.yml",
    ".cursorrules",
    ".github/copilot-instructions.md",
    ".kilocoderules",
    ".windsurfrules",
    "AGENT.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
}


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_guidance(relative: Path) -> bool:
    if relative.name in EXACT_GUIDANCE:
        return True
    parts = set(relative.parts)
    if parts & HARNESS_DIRS and relative.suffix in {".md", ".mdc", ".yaml", ".yml"}:
        return True
    return relative == Path(".github/copilot-instructions.md")


def inventory(root: Path, max_files: int) -> dict[str, object]:
    languages: Counter[str] = Counter()
    build_files: list[str] = []
    ci_files: list[str] = []
    guidance_files: list[str] = []
    harness_markers: set[str] = set()
    test_paths: set[str] = set()
    symlinks: list[str] = []
    file_count = 0
    truncated = False

    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        retained: list[str] = []
        for name in sorted(dirnames):
            path = current / name
            relative = path.relative_to(root)
            if path.is_symlink():
                symlinks.append(relative.as_posix())
            elif name not in SKIP_DIRS:
                retained.append(name)
                if name in HARNESS_DIRS:
                    harness_markers.add(name)
        dirnames[:] = retained

        for filename in sorted(filenames):
            path = current / filename
            relative = path.relative_to(root)
            rel = relative.as_posix()
            if path.is_symlink():
                symlinks.append(rel)
                continue
            if not path.is_file():
                continue
            file_count += 1
            if file_count > max_files:
                truncated = True
                break

            if path.suffix.lower() in LANGUAGES:
                languages[LANGUAGES[path.suffix.lower()]] += 1
            if filename in BUILD_MARKERS:
                build_files.append(rel)
            if is_guidance(relative):
                guidance_files.append(rel)
            if rel in HARNESS_FILES:
                harness_markers.add(rel)
            if any(
                part.lower() in {"test", "tests", "spec", "specs"}
                for part in relative.parts[:-1]
            ):
                test_paths.add(relative.parts[0])
            if relative.parts[:2] == (".github", "workflows") or filename in {
                ".gitlab-ci.yml",
                "azure-pipelines.yml",
                "bitbucket-pipelines.yml",
            }:
                ci_files.append(rel)
        if truncated:
            break

    branch = git_value(root, "branch", "--show-current")
    status = git_value(root, "status", "--short")
    commit = git_value(root, "rev-parse", "--short", "HEAD")

    return {
        "schema_version": 1,
        "root": str(root),
        "files_scanned": min(file_count, max_files),
        "truncated": truncated,
        "languages_by_file_count": dict(
            sorted(languages.items(), key=lambda item: (-item[1], item[0]))
        ),
        "build_files": sorted(build_files),
        "test_roots": sorted(test_paths),
        "ci_files": sorted(ci_files),
        "guidance_files": sorted(guidance_files),
        "harness_markers": sorted(harness_markers),
        "symlinks_not_followed": sorted(symlinks),
        "git": {
            "repository": branch is not None or commit is not None,
            "branch": branch,
            "commit": commit,
            "dirty": bool(status) if status is not None else None,
        },
    }


def markdown(data: dict[str, object]) -> str:
    git = data["git"]
    languages = data["languages_by_file_count"]
    lines = [
        "# Project inventory",
        "",
        f"- Root: `{data['root']}`",
        f"- Files scanned: **{data['files_scanned']}**"
        + (" (limit reached)" if data["truncated"] else ""),
        f"- Git: **{'yes' if git['repository'] else 'no'}**; branch `{git['branch'] or 'unknown'}`; commit `{git['commit'] or 'unknown'}`; dirty `{git['dirty']}`",
        "",
        "## Languages by file count",
        "",
    ]
    if languages:
        lines.extend(f"- {name}: {count}" for name, count in languages.items())
    else:
        lines.append("- None detected from file extensions.")

    for key, title in (
        ("build_files", "Build markers"),
        ("test_roots", "Test roots"),
        ("ci_files", "CI files"),
        ("guidance_files", "Agent guidance"),
        ("harness_markers", "Harness markers"),
        ("symlinks_not_followed", "Symlinks not followed"),
    ):
        lines.extend(["", f"## {title}", ""])
        values = data[key]
        lines.extend(f"- `{value}`" for value in values) if values else lines.append(
            "- None detected."
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to inventory")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--max-files", type=int, default=50_000)
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    if root.is_symlink() or not root.is_dir():
        print(f"error: root must be a real directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    if args.max_files < 1:
        print("error: --max-files must be positive", file=sys.stderr)
        return 2

    data = inventory(root, args.max_files)
    if args.format == "markdown":
        sys.stdout.write(markdown(data))
    else:
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
