#!/usr/bin/env python3
"""Validate the guidance hierarchy, skills, links, metadata, and Python syntax."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents/skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_FRONTMATTER_KEYS = frozenset({"name", "description"})
OPTIONAL_FRONTMATTER_KEYS = frozenset(
    {"license", "compatibility", "metadata", "allowed-tools"}
)
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
INDEX_RE = re.compile(r"\]\(skills/([^/]+)/SKILL\.md\)")
IMPORT_RE = re.compile(r"(?m)^@(?P<path>\S+)\s*$")
DEPENDENCIES_PATH = ROOT / ".agents/skill-dependencies.json"
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".local",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        ".kilo",
        ".idea",
        ".cursor",
        ".vscode",
        ".clinerules",
    }
)


def is_project_path(path: Path, root: Path = ROOT) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return EXCLUDED_DIRECTORIES.isdisjoint(relative.parts)


def simple_frontmatter(text: str) -> tuple[dict[str, object], str | None]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, "missing or malformed YAML frontmatter"
    try:
        values = yaml.safe_load(match.group("body"))
    except yaml.YAMLError as error:
        return {}, f"invalid YAML frontmatter: {error}"
    if not isinstance(values, dict):
        return {}, "frontmatter must be a YAML mapping"
    for key, value in values.items():
        if not isinstance(key, str):
            return {}, "frontmatter keys must be strings"
        if key == "metadata":
            if not isinstance(value, Mapping) or any(
                not isinstance(metadata_key, str) or not isinstance(metadata_value, str)
                for metadata_key, metadata_value in value.items()
            ):
                return {}, "frontmatter metadata must map strings to strings"
        elif not isinstance(value, str):
            return {}, f"frontmatter {key!r} must be a string value"
    return values, None


def without_fenced_code(text: str) -> str:
    output: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            current = stripped[:3]
            if not in_fence:
                in_fence = True
                marker = current
            elif current == marker:
                in_fence = False
                marker = ""
            continue
        if not in_fence:
            output.append(line)
    return "\n".join(output)


def validate_links(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.suffix not in {".md", ".mdc"}
        ):
            continue
        if not is_project_path(path):
            continue
        text = without_fenced_code(path.read_text(encoding="utf-8"))
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            split = urlsplit(target)
            if split.scheme or target.startswith("#"):
                continue
            relative = unquote(split.path)
            if not relative:
                continue
            if Path(relative).is_absolute():
                errors.append(
                    f"{path.relative_to(ROOT)}: absolute local link is not portable: {target}"
                )
                continue
            resolved = (path.parent / relative).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"{path.relative_to(ROOT)}: link escapes repository: {target}"
                )
                continue
            if not resolved.exists():
                errors.append(
                    f"{path.relative_to(ROOT)}: broken relative link: {target}"
                )


def validate_harness_imports(errors: list[str]) -> None:
    for relative_path in (Path("CLAUDE.md"), Path("GEMINI.md")):
        path = ROOT / relative_path
        if not path.is_file() or path.is_symlink():
            errors.append(f"{relative_path}: missing real harness entrypoint")
            continue
        imports = IMPORT_RE.findall(
            without_fenced_code(path.read_text(encoding="utf-8"))
        )
        if not imports:
            errors.append(
                f"{relative_path}: expected at least one canonical-file import"
            )
            continue
        for raw_target in imports:
            target = Path(raw_target)
            if target.is_absolute():
                errors.append(
                    f"{relative_path}: absolute import is not portable: {raw_target}"
                )
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"{relative_path}: import escapes repository: {raw_target}"
                )
                continue
            if not resolved.is_file() or resolved.is_symlink():
                errors.append(f"{relative_path}: broken or unsafe import: {raw_target}")

    copilot = ROOT / ".github/copilot-instructions.md"
    if not copilot.is_file() or copilot.is_symlink():
        errors.append(
            ".github/copilot-instructions.md: missing real harness entrypoint"
        )
    else:
        text = without_fenced_code(copilot.read_text(encoding="utf-8"))
        has_canonical = any(
            canonical in text
            for canonical in ("AGENTS.md", ".agents/AGENTS.md", ".agents/OPERATING.md")
        )
        if not has_canonical:
            errors.append(
                ".github/copilot-instructions.md: expected at least one canonical-file reference"
            )


def validate_skills(errors: list[str]) -> tuple[set[str], set[str]]:
    names: set[str] = set()
    eval_definitions: set[str] = set()
    for directory in sorted(SKILLS_ROOT.iterdir()):
        if directory.name.startswith("."):
            continue
        if directory.is_symlink() or not directory.is_dir():
            errors.append(
                f".agents/skills/{directory.name}: skill entry must be a real directory"
            )
            continue
        skill_md = directory / "SKILL.md"
        if skill_md.is_symlink() or not skill_md.is_file():
            errors.append(f".agents/skills/{directory.name}: missing real SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        values, error = simple_frontmatter(text)
        if error:
            errors.append(f"{skill_md.relative_to(ROOT)}: {error}")
            continue
        keys = set(values)
        missing_keys = REQUIRED_FRONTMATTER_KEYS - keys
        unknown_keys = keys - REQUIRED_FRONTMATTER_KEYS - OPTIONAL_FRONTMATTER_KEYS
        if missing_keys:
            errors.append(
                f"{skill_md.relative_to(ROOT)}: missing frontmatter keys: "
                f"{', '.join(sorted(missing_keys))}"
            )
        if unknown_keys:
            errors.append(
                f"{skill_md.relative_to(ROOT)}: unknown frontmatter keys: "
                f"{', '.join(sorted(unknown_keys))}"
            )
        name_value = values.get("name", "")
        description_value = values.get("description", "")
        name = name_value if isinstance(name_value, str) else ""
        description = description_value if isinstance(description_value, str) else ""
        if not NAME_RE.fullmatch(name) or len(name) > 64:
            errors.append(f"{skill_md.relative_to(ROOT)}: invalid skill name {name!r}")
        if name != directory.name:
            errors.append(
                f"{skill_md.relative_to(ROOT)}: name must match directory {directory.name!r}"
            )
        if not (40 <= len(description) <= 1024):
            errors.append(
                f"{skill_md.relative_to(ROOT)}: description must be 40-1024 characters"
            )
        license_value = values.get("license")
        if license_value is not None and not license_value.strip():
            errors.append(f"{skill_md.relative_to(ROOT)}: license must not be empty")
        compatibility = values.get("compatibility")
        if compatibility is not None and not (1 <= len(compatibility) <= 500):
            errors.append(
                f"{skill_md.relative_to(ROOT)}: compatibility must be 1-500 characters"
            )
        allowed_tools = values.get("allowed-tools")
        if allowed_tools is not None and not allowed_tools.strip():
            errors.append(
                f"{skill_md.relative_to(ROOT)}: allowed-tools must not be empty"
            )
        if "[TODO" in text or "TODO:" in text:
            errors.append(f"{skill_md.relative_to(ROOT)}: unfinished TODO marker")
        names.add(name)

        metadata = directory / "agents/openai.yaml"
        if metadata.is_symlink() or not metadata.is_file():
            errors.append(f"{metadata.relative_to(ROOT)}: missing real metadata file")
            continue
        metadata_text = metadata.read_text(encoding="utf-8")
        try:
            metadata_value = yaml.safe_load(metadata_text)
        except yaml.YAMLError as error:
            errors.append(f"{metadata.relative_to(ROOT)}: invalid YAML: {error}")
            continue
        interface = (
            metadata_value.get("interface", {})
            if isinstance(metadata_value, dict)
            else {}
        )
        display = interface.get("display_name") if isinstance(interface, dict) else None
        short = (
            interface.get("short_description") if isinstance(interface, dict) else None
        )
        prompt = (
            interface.get("default_prompt") if isinstance(interface, dict) else None
        )
        if not display:
            errors.append(f"{metadata.relative_to(ROOT)}: missing quoted display_name")
        if not short or not (25 <= len(short) <= 64):
            errors.append(
                f"{metadata.relative_to(ROOT)}: short_description must be 25-64 characters"
            )
        if not prompt or f"${name}" not in prompt:
            errors.append(
                f"{metadata.relative_to(ROOT)}: default_prompt must mention ${name}"
            )
        if validate_evals(directory, name, errors):
            eval_definitions.add(name)
    return names, eval_definitions


def validate_evals(directory: Path, name: str, errors: list[str]) -> bool:
    path = directory / "evals/evals.json"
    if path.is_symlink():
        errors.append(f"{path}: evaluation definition must not be a symlink")
        return False
    if not path.is_file():
        return False
    path_label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        errors.append(f"{path_label}: invalid evaluation JSON: {error}")
        return True
    if not isinstance(value, dict) or value.get("skill_name") != name:
        errors.append(f"{path_label}: skill_name must match {name!r}")
        return True
    cases = value.get("evals")
    if not isinstance(cases, list) or len(cases) < 3:
        errors.append(f"{path_label}: evals must contain at least three cases")
        return True
    ids: set[int] = set()
    kinds: set[str] = set()
    for index, case in enumerate(cases, start=1):
        prefix = f"{path_label} case {index}"
        if not isinstance(case, dict):
            errors.append(f"{prefix}: case must be an object")
            continue
        case_id = case.get("id")
        if isinstance(case_id, bool) or not isinstance(case_id, int) or case_id in ids:
            errors.append(f"{prefix}: id must be a unique integer")
        else:
            ids.add(case_id)
        kind = case.get("kind")
        if kind not in {"matching", "neighboring", "ambiguous", "edge"}:
            errors.append(
                f"{prefix}: kind must be matching, neighboring, ambiguous, or edge"
            )
        else:
            kinds.add(kind)
        for key in ("prompt", "expected_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                errors.append(f"{prefix}: {key} must be a non-empty string")
        assertions = case.get("assertions", [])
        if not isinstance(assertions, list) or any(
            not isinstance(assertion, str) or not assertion.strip()
            for assertion in assertions
        ):
            errors.append(f"{prefix}: assertions must contain non-empty strings")
        files = case.get("files", [])
        if not isinstance(files, list) or any(
            not isinstance(file_name, str) or not file_name.strip()
            for file_name in files
        ):
            errors.append(f"{prefix}: files must contain non-empty strings")
        else:
            for file_name in files:
                file_path = Path(file_name)
                if file_path.is_absolute():
                    errors.append(
                        f"{prefix}: fixture path must be relative: {file_name}"
                    )
                    continue
                candidate = directory / file_path
                current = directory
                has_symlink = False
                for part in file_path.parts:
                    current = current / part
                    if current.is_symlink():
                        has_symlink = True
                        break
                resolved = candidate.resolve()
                try:
                    resolved.relative_to(directory.resolve())
                except ValueError:
                    errors.append(f"{prefix}: fixture path escapes skill: {file_name}")
                    continue
                if has_symlink or not resolved.is_file():
                    errors.append(
                        f"{prefix}: fixture must be a real file inside the skill: {file_name}"
                    )
    if not {"matching", "neighboring", "ambiguous"}.issubset(kinds):
        errors.append(
            f"{path_label}: evals must cover matching, neighboring, and ambiguous cases"
        )
    return True


def validate_index(skill_names: set[str], errors: list[str]) -> None:
    index_path = ROOT / ".agents/AGENTS.md"
    indexed = set(INDEX_RE.findall(index_path.read_text(encoding="utf-8")))
    missing = sorted(skill_names - indexed)
    extra = sorted(indexed - skill_names)
    if missing:
        errors.append(
            f".agents/AGENTS.md: missing skills from index: {', '.join(missing)}"
        )
    if extra:
        errors.append(
            f".agents/AGENTS.md: index references unknown skills: {', '.join(extra)}"
        )


def validate_skill_dependencies(skill_names: set[str], errors: list[str]) -> None:
    if DEPENDENCIES_PATH.is_symlink() or not DEPENDENCIES_PATH.is_file():
        errors.append(
            ".agents/skill-dependencies.json: missing real dependency catalog"
        )
        return
    try:
        value = json.loads(DEPENDENCIES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        errors.append(f".agents/skill-dependencies.json: invalid JSON: {error}")
        return
    entries = value.get("skills") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or not isinstance(entries, dict)
    ):
        errors.append(".agents/skill-dependencies.json: invalid catalog shape")
        return
    missing = sorted(skill_names - set(entries))
    extra = sorted(set(entries) - skill_names)
    if missing:
        errors.append(
            ".agents/skill-dependencies.json: missing skills: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            ".agents/skill-dependencies.json: unknown skills: " + ", ".join(extra)
        )
    for name in sorted(skill_names & set(entries)):
        entry = entries[name]
        prefix = f".agents/skill-dependencies.json skill {name}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: entry must be an object")
            continue
        requires = entry.get("requires")
        related = entry.get("related")
        route = entry.get("route")
        if not isinstance(requires, list) or not isinstance(related, list):
            errors.append(f"{prefix}: requires and related must be lists")
            continue
        if any(
            not isinstance(item, str) or item not in skill_names
            for item in requires + related
        ):
            errors.append(f"{prefix}: dependencies must name catalog skills")
            continue
        if name in requires or name in related or set(requires) & set(related):
            errors.append(f"{prefix}: dependencies overlap or reference themselves")
        if (
            not isinstance(route, str)
            or not route.strip()
            or "|" in route
            or "\n" in route
        ):
            errors.append(f"{prefix}: route must be one non-empty table-safe line")
        linked: set[str] = set()
        skill_directory = SKILLS_ROOT / name
        skill_root = skill_directory.resolve()
        catalog_root = SKILLS_ROOT.resolve()
        for markdown in sorted(skill_directory.rglob("*.md")):
            if markdown.is_symlink():
                continue
            for raw_target in LINK_RE.findall(markdown.read_text(encoding="utf-8")):
                target = raw_target.strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                split = urlsplit(target)
                if split.scheme or target.startswith("#") or not split.path:
                    continue
                candidate = (markdown.parent / unquote(split.path)).resolve()
                try:
                    candidate.relative_to(skill_root)
                    continue
                except ValueError:
                    pass
                try:
                    relative_to_catalog = candidate.relative_to(catalog_root)
                except ValueError:
                    continue
                dependency = relative_to_catalog.parts[0]
                if dependency != name:
                    linked.add(dependency)
        undeclared = sorted(linked - set(requires))
        if undeclared:
            errors.append(
                f"{prefix}: relative links must be required dependencies: "
                f"{', '.join(undeclared)}"
            )


def validate_evaluation_results(skill_names: set[str], errors: list[str]) -> None:
    results_root = ROOT / "docs/evaluations/results"
    if not results_root.exists():
        return
    if results_root.is_symlink() or not results_root.is_dir():
        errors.append("docs/evaluations/results: must be a real directory")
        return
    # Build committed eval case index for cross-checking
    eval_index: dict[str, dict[int, str]] = {}
    for name in skill_names:
        path = SKILLS_ROOT / name / "evals/evals.json"
        if not path.is_file() or path.is_symlink():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            cases = value.get("evals") if isinstance(value, dict) else None
            if isinstance(cases, list):
                eval_index[name] = {
                    case["id"]: case["kind"]
                    for case in cases
                    if isinstance(case, dict)
                    and isinstance(case.get("id"), int)
                    and isinstance(case.get("kind"), str)
                    and isinstance(case.get("assertions"), list)
                }
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
    allowed_decisions = {
        "KEEP",
        "KEEP_PROVISIONAL",
        "REVISE",
        "MERGE",
        "DEFER",
        "REJECT",
    }
    for path in sorted(results_root.glob("*.json")):
        if path.is_symlink():
            errors.append(f"{path.relative_to(ROOT)}: result must not be a symlink")
            continue
        label = str(path.relative_to(ROOT))
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            errors.append(f"{label}: invalid JSON: {error}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{label}: result must be a JSON object")
            continue
        if value.get("schema_version") != 1:
            errors.append(f"{label}: schema_version must be 1")
        for key in ("run_id", "timestamp", "baseline"):
            if not isinstance(value.get(key), str) or not value[key].strip():
                errors.append(f"{label}: {key} must be a non-empty string")
        harness = value.get("harness")
        if (
            not isinstance(harness, dict)
            or not isinstance(harness.get("name"), str)
            or not harness["name"].strip()
        ):
            errors.append(f"{label}: harness.name must be a non-empty string")
        model = value.get("model")
        if (
            not isinstance(model, dict)
            or not isinstance(model.get("name"), str)
            or not model["name"].strip()
        ):
            errors.append(f"{label}: model.name must be a non-empty string")
        # reasoning_effort dramatically changes results; require it when provider is meta
        if isinstance(model, dict):
            effort = model.get("reasoning_effort")
            if effort is not None and (
                not isinstance(effort, str) or not effort.strip()
            ):
                errors.append(
                    f"{label}: model.reasoning_effort must be a non-empty string when present"
                )
        skills = value.get("skills")
        if not isinstance(skills, list) or not skills:
            errors.append(f"{label}: skills must be a non-empty list")
            continue
        seen_skills: set[str] = set()
        for idx, entry in enumerate(skills, start=1):
            prefix = f"{label} skills[{idx}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix}: must be an object")
                continue
            skill_name = entry.get("skill_name")
            if not isinstance(skill_name, str) or skill_name not in skill_names:
                errors.append(f"{prefix}: skill_name must name a catalog skill")
                continue
            if skill_name in seen_skills:
                errors.append(f"{prefix}: duplicate skill_name {skill_name!r}")
            seen_skills.add(skill_name)
            cases = entry.get("cases")
            if not isinstance(cases, list) or not cases:
                errors.append(f"{prefix}: cases must be a non-empty list")
                continue
            committed = eval_index.get(skill_name, {})
            for cidx, case in enumerate(cases, start=1):
                cprefix = f"{prefix} cases[{cidx}]"
                if not isinstance(case, dict):
                    errors.append(f"{cprefix}: must be an object")
                    continue
                cid = case.get("id")
                kind = case.get("kind")
                total = case.get("assertions_total")
                spass = case.get("skill_pass")
                bpass = case.get("baseline_pass")
                better = case.get("better")
                if not isinstance(cid, int) or cid not in committed:
                    errors.append(f"{cprefix}: id must match committed eval case")
                elif committed.get(cid) != kind:
                    errors.append(
                        f"{cprefix}: kind must match committed eval case "
                        f"({committed.get(cid)!r} != {kind!r})"
                    )
                if not isinstance(total, int) or total <= 0:
                    errors.append(f"{cprefix}: assertions_total must be a positive int")
                for key, val in (
                    ("skill_pass", spass),
                    ("baseline_pass", bpass),
                ):
                    if not isinstance(val, int) or not (0 <= val <= (total or 0)):
                        errors.append(
                            f"{cprefix}: {key} must be in [0, assertions_total]"
                        )
                if not isinstance(better, bool):
                    errors.append(f"{cprefix}: better must be a boolean")
                elif isinstance(spass, int) and isinstance(bpass, int):
                    expected_better = spass > bpass
                    if better != expected_better:
                        errors.append(
                            f"{cprefix}: better must be (skill_pass > baseline_pass)"
                        )
                if isinstance(total, int) and isinstance(spass, int):
                    committed_total = None
                    try:
                        eval_path = SKILLS_ROOT / skill_name / "evals/evals.json"
                        eval_value = json.loads(eval_path.read_text(encoding="utf-8"))
                        for ec in eval_value.get("evals", []):
                            if ec.get("id") == cid:
                                committed_total = len(ec.get("assertions", []))
                                break
                    except (OSError, json.JSONDecodeError):
                        pass
                    if committed_total is not None and total != committed_total:
                        errors.append(
                            f"{cprefix}: assertions_total {total} != committed "
                            f"assertions length {committed_total}"
                        )
            decision = entry.get("decision")
            if decision not in allowed_decisions:
                errors.append(
                    f"{prefix}: decision must be one of {', '.join(sorted(allowed_decisions))}"
                )
            overall = entry.get("overall_better")
            if not isinstance(overall, bool):
                errors.append(f"{prefix}: overall_better must be a boolean")
            elif isinstance(cases, list):
                any_better = any(
                    isinstance(c.get("better"), bool) and c["better"]
                    for c in cases
                    if isinstance(c, dict)
                )
                if overall != any_better:
                    errors.append(
                        f"{prefix}: overall_better must be any(cases[].better)"
                    )
    # Validate matrix links resolve to existing result files
    matrix = ROOT / "docs/evaluations/validation-matrix.md"
    if matrix.is_file() and not matrix.is_symlink():
        text = matrix.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = raw.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            split = urlsplit(target)
            if split.scheme or target.startswith("#") or not split.path:
                continue
            candidate = (matrix.parent / unquote(split.path)).resolve()
            try:
                candidate.relative_to(ROOT)
            except ValueError:
                continue
            # Only check links that point inside results/
            try:
                candidate.relative_to((ROOT / "docs/evaluations/results").resolve())
            except ValueError:
                continue
            if not candidate.is_file() or candidate.is_symlink():
                errors.append(
                    f"docs/evaluations/validation-matrix.md: broken results link: {target}"
                )


def validate_python(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.py")):
        if path.is_symlink() or not is_project_path(path):
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, UnicodeDecodeError) as error:
            errors.append(f"{path.relative_to(ROOT)}: Python syntax error: {error}")


def validate_related_links(skill_names: set[str], errors: list[str]) -> None:
    """Ensure related skills are not linked via relative file paths.

    Related skills are suggestions that do not require installation; a direct
    file link like `](skills/other/SKILL.md)` would break selective installs.
    They should be referenced by plain name or non-file link, not a relative
    path to the sibling skill directory.
    """
    if DEPENDENCIES_PATH.is_symlink() or not DEPENDENCIES_PATH.is_file():
        return
    try:
        value = json.loads(DEPENDENCIES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    entries = value.get("skills") if isinstance(value, dict) else None
    if not isinstance(entries, dict):
        return
    catalog_root = SKILLS_ROOT.resolve()
    for name in sorted(skill_names & set(entries)):
        entry = entries.get(name)
        if not isinstance(entry, dict):
            continue
        related = entry.get("related")
        if not isinstance(related, list) or not related:
            continue
        related_set = {str(item) for item in related if isinstance(item, str)}
        if not related_set:
            continue
        skill_directory = SKILLS_ROOT / name
        skill_root = skill_directory.resolve()
        for markdown in sorted(skill_directory.rglob("*.md")):
            if markdown.is_symlink():
                continue
            if not is_project_path(markdown):
                continue
            text = markdown.read_text(encoding="utf-8")
            # Check file links that resolve to a sibling skill
            for raw_target in LINK_RE.findall(text):
                target = raw_target.strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                split = urlsplit(target)
                if split.scheme or target.startswith("#") or not split.path:
                    continue
                candidate = (markdown.parent / unquote(split.path)).resolve()
                try:
                    candidate.relative_to(skill_root)
                    continue
                except ValueError:
                    pass
                try:
                    relative_to_catalog = candidate.relative_to(catalog_root)
                except ValueError:
                    continue
                dependency = relative_to_catalog.parts[0]
                if dependency in related_set:
                    errors.append(
                        f"{markdown.relative_to(ROOT)}: related skill {dependency!r} must not be linked via relative path; "
                        f"use plain reference instead (skill {name} related={dependency!r})"
                    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate the guidance hierarchy, skills, links, metadata, and Python syntax."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON instead of text"
    )
    args = parser.parse_args()

    errors: list[str] = []
    if not SKILLS_ROOT.is_dir() or SKILLS_ROOT.is_symlink():
        msg = "error: .agents/skills must be a real directory"
        if args.json:
            print(json.dumps({"errors": [msg], "valid": False}, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2
    skills, eval_definitions = validate_skills(errors)
    validate_index(skills, errors)
    validate_skill_dependencies(skills, errors)
    validate_related_links(skills, errors)
    validate_links(errors)
    validate_harness_imports(errors)
    validate_evaluation_results(skills, errors)
    validate_python(errors)
    if args.json:
        results_root = ROOT / "docs/evaluations/results"
        results_count = (
            len(list(results_root.glob("*.json"))) if results_root.is_dir() else 0
        )
        payload = {
            "errors": errors,
            "valid": not errors,
            "skills_validated": len(skills),
            "evaluation_definitions": len(eval_definitions),
            "evaluation_results": results_count,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if errors else 0
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    results_root = ROOT / "docs/evaluations/results"
    results_count = (
        len(list(results_root.glob("*.json"))) if results_root.is_dir() else 0
    )
    print(
        f"Validated {len(skills)} skills, relative links, metadata, and Python syntax; "
        f"evaluation definitions: {len(eval_definitions)} present, "
        f"{len(skills - eval_definitions)} absent; "
        f"evaluation results: {results_count} file(s) validated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
