#!/usr/bin/env python3
"""Fail when public project files contain likely secrets or personal machine data."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".kt",
    ".kts",
    ".md",
    ".mdc",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519", "kubeconfig"}
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}


def candidate_files() -> list[Path]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        paths = []
        for directory, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = sorted(name for name in dirnames if name != ".git")
            paths.extend(Path(directory) / name for name in sorted(filenames))
        return paths
    return [
        ROOT / value.decode("utf-8") for value in result.stdout.split(b"\0") if value
    ]


def patterns() -> list[tuple[str, re.Pattern[str]]]:
    user_root = "/" + "Users" + r"/[A-Za-z0-9._-]+/"
    home_root = "/" + "home" + r"/[A-Za-z0-9._-]+/"
    windows_root = r"[A-Za-z]:\\" + "Users" + r"\\[A-Za-z0-9._-]+\\"
    private_key = "BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY"
    return [
        ("macOS personal path", re.compile(user_root)),
        ("Linux personal path", re.compile(home_root)),
        ("Windows personal path", re.compile(windows_root, re.IGNORECASE)),
        ("private key block", re.compile(private_key)),
        ("GitHub token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
        ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("OpenAI-style secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
        ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
        ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
        ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}\b")),
        ("GCP API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ]


def main() -> int:
    findings: list[str] = []
    checks = patterns()
    for path in sorted(candidate_files()):
        if not path.is_file() or path.is_symlink() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"{relative}: secret-bearing filename is not allowed")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "Makefile",
            "Dockerfile",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in checks:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{relative}:{line}: {label}")
    if findings:
        for finding in findings:
            print(f"ERROR {finding}", file=sys.stderr)
        print(
            f"Public hygiene check failed with {len(findings)} finding(s).",
            file=sys.stderr,
        )
        return 1
    print(
        "Public hygiene check passed: no common secrets or personal filesystem paths found."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
