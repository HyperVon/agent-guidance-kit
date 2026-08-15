#!/usr/bin/env python3
"""Create the local development environment and install declared requirements."""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"


def venv_python(venv_dir: Path = VENV, platform: str = sys.platform) -> Path:
    if platform == "win32":
        return venv_dir / "Scripts/python.exe"
    return venv_dir / "bin/python"


def ensure_venv(venv_dir: Path = VENV) -> Path:
    if venv_dir.is_symlink():
        raise RuntimeError(f"{venv_dir} is a symlink; remove it and run setup again")
    python = venv_python(venv_dir)
    if python.is_file():
        return python
    if venv_dir.exists():
        if venv_dir.is_file():
            raise RuntimeError(
                f"{venv_dir} exists as a file, not a directory; "
                "move or remove it, then run setup again"
            )
        raise RuntimeError(
            f"{venv_dir} exists but is not a complete virtual environment; "
            "move or remove it, then run setup again"
        )
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    return venv_python(venv_dir)


def node_toolchain() -> tuple[str, str] | None:
    node = shutil.which("node")
    npm = shutil.which("npm")
    if node is None or npm is None:
        return None
    result = subprocess.run(
        [node, "--version"], check=False, capture_output=True, text=True
    )
    try:
        major = int(result.stdout.strip().lstrip("v").split(".", 1)[0])
    except (ValueError, IndexError):
        return None
    if result.returncode != 0 or major < 22:
        return None
    if major > 26:
        print(
            f"WARNING Node.js {major} is newer than CI-validated 26; proceeding.",
            file=sys.stderr,
        )
    return node, npm


def main() -> int:
    tools = node_toolchain()
    if tools is None:
        print(
            "ERROR Node.js 22 or newer and npm are required for Markdown lint.",
            file=sys.stderr,
        )
        return 2
    try:
        python = ensure_venv()
    except RuntimeError as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 2
    requirements_file = ROOT / "requirements-dev.txt"
    pip_install = [str(python), "-m", "pip", "install", "-r", str(requirements_file)]
    # Use --require-hashes when the requirements file contains hashes for supply-chain hardening.
    try:
        text = requirements_file.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if "--hash=" in text:
        pip_install.append("--require-hashes")
    subprocess.run(
        pip_install,
        check=True,
        cwd=ROOT,
    )
    subprocess.run([tools[1], "ci", "--ignore-scripts"], check=True, cwd=ROOT)
    print(f"Development environment ready: {VENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
