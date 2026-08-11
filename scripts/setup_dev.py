#!/usr/bin/env python3
"""Create the local development environment and install declared requirements."""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV / "Scripts/python.exe"
    return VENV / "bin/python"


def main() -> int:
    venv.EnvBuilder(with_pip=True).create(VENV)
    python = venv_python()
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements-dev.txt")],
        check=True,
        cwd=ROOT,
    )
    print(f"Development environment ready: {VENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
