"""Constants for install_skills."""

from __future__ import annotations

import re
from pathlib import Path

SCHEMA_VERSION = 2
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SOURCE_SKILLS = Path(".agents/skills")
TARGET_SKILLS = Path(".agents/skills")
DEPENDENCIES = Path(".agents/skill-dependencies.json")
RECEIPTS = Path(".agents/.agent-guidance-kit/receipts")
SOURCE_LOCATOR = Path(".agents/.agent-guidance-kit/source.json")
IGNORE_PATTERN = "/.agents/.agent-guidance-kit/source.json"
SOURCE_ENVIRONMENT = "AGENT_GUIDANCE_KIT_ROOT"
ROUTE_START = "<!-- agent-guidance-kit:routes:start -->"
ROUTE_END = "<!-- agent-guidance-kit:routes:end -->"
TRANSIENT_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
TRANSIENT_FILES = {".DS_Store"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo", ".swp"}
# Evaluation cases validate the kit and are not runtime guidance for targets.
SOURCE_ONLY_DIRS = {"evals"}
