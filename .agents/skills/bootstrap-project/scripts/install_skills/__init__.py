"""Plan and apply receipt-aware skill adoption from Agent Guidance Kit."""

from __future__ import annotations

from pathlib import Path

from .apply import (
    apply_plan,
    build_plan,
    main,
    print_summary,
    validate_installed,
    validate_installed_impl,
)
from .constants import (
    DEPENDENCIES,
    IGNORE_PATTERN,
    MARKDOWN_LINK,
    RECEIPTS,
    ROUTE_END,
    ROUTE_START,
    SCHEMA_VERSION,
    SHA256,
    SKILL_NAME,
    SOURCE_ENVIRONMENT,
    SOURCE_LOCATOR,
    SOURCE_ONLY_DIRS,
    SOURCE_SKILLS,
    TARGET_SKILLS,
    TRANSIENT_DIRS,
    TRANSIENT_FILES,
    TRANSIENT_SUFFIXES,
)
from .dependencies import (
    dependency_closure,
    get_mandatory_skill,
    load_dependencies,
    normalize_skills,
)
from .inspect import inspect_skill
from .manifest import git_revision, manifest_digest, tree_manifest
from .receipts import (
    read_json,
    receipt_for,
    receipt_route_block_digests,
    receipt_skill_digests,
)
from .routing import (
    inspect_routing,
    managed_route_block,
    managed_route_names,
    render_routing,
    restore_routing,
    route_block,
    routing_path,
    write_routing,
)
from .source import (
    configure_source_locator,
    restore_source_locator,
    source_resolution_plan,
)
from .utils import read_text_exact
from .validation import (
    AdoptionError,
    ensure_safe_ancestors,
    validate_relative,
    validate_root,
)

SCRIPT = Path(__file__).parent.parent / "install_skills.py"

__all__ = [
    "DEPENDENCIES",
    "IGNORE_PATTERN",
    "MARKDOWN_LINK",
    "RECEIPTS",
    "ROUTE_END",
    "ROUTE_START",
    "SCHEMA_VERSION",
    "SCRIPT",
    "SHA256",
    "SKILL_NAME",
    "SOURCE_ENVIRONMENT",
    "SOURCE_LOCATOR",
    "SOURCE_ONLY_DIRS",
    "SOURCE_SKILLS",
    "TARGET_SKILLS",
    "TRANSIENT_DIRS",
    "TRANSIENT_FILES",
    "TRANSIENT_SUFFIXES",
    "AdoptionError",
    "apply_plan",
    "build_plan",
    "configure_source_locator",
    "dependency_closure",
    "ensure_safe_ancestors",
    "get_mandatory_skill",
    "git_revision",
    "inspect_routing",
    "inspect_skill",
    "load_dependencies",
    "main",
    "managed_route_block",
    "managed_route_names",
    "manifest_digest",
    "normalize_skills",
    "print_summary",
    "read_json",
    "read_text_exact",
    "receipt_for",
    "receipt_route_block_digests",
    "receipt_skill_digests",
    "render_routing",
    "restore_routing",
    "restore_source_locator",
    "route_block",
    "routing_path",
    "source_resolution_plan",
    "tree_manifest",
    "validate_installed",
    "validate_installed_impl",
    "validate_relative",
    "validate_root",
    "write_routing",
]
