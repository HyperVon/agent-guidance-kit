#!/usr/bin/env python3
"""Validate the portable skill catalog with local tooling."""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CATALOG_LINK = re.compile(r"\]\(skills/([a-z0-9-]+)/SKILL\.md\)")
MARKDOWN_LINK = re.compile(r"\]\((?:<([^>]+)>|([^\s)]+))\)")
FRONTMATTER_FIELD = re.compile(r"^(.+?)\s*:\s*(.*)$")
ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
MAX_NAME_CHARS = 64
MIN_DESCRIPTION_CHARS = 40
MAX_DESCRIPTION_CHARS = 1024
MAX_COMPATIBILITY_CHARS = 500
YAML_DOUBLE_QUOTE_ESCAPES = {
    "0": "\0",
    "a": "\a",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "v": "\v",
    "f": "\f",
    "r": "\r",
    "e": "\x1b",
    " ": " ",
    '"': '"',
    "/": "/",
    "\\": "\\",
    "N": "\u0085",
    "_": "\u00a0",
    "L": "\u2028",
    "P": "\u2029",
}


def tracked_markdown_files() -> list[Path]:
    """Use tracked files so local experiments do not affect the product gate."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", "*.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)
    return [ROOT / line for line in result.stdout.splitlines() if line]


def _strip_yaml_comment(value: str) -> str:
    """Remove a YAML comment while preserving # characters inside quotes."""
    value = value.lstrip()
    quote = ""
    escaped = False
    index = 0
    while index < len(value):
        character = value[index]
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
        elif quote == "'":
            if character == quote:
                if index + 1 < len(value) and value[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
        elif index == 0 and character in {'"', "'"}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    return value.strip()


def _parse_inline_scalar(value: str) -> str:
    """Parse the scalar forms used by required frontmatter fields."""
    value = _strip_yaml_comment(value)
    if not value:
        return ""
    if value.startswith('"'):
        if len(value) < 2 or not value.endswith('"'):
            raise ValueError("frontmatter quoted scalar is invalid")
        inner = value[1:-1]
        parsed: list[str] = []
        index = 0
        while index < len(inner):
            character = inner[index]
            if character == '"':
                raise ValueError("frontmatter quoted scalar is invalid")
            if character != "\\":
                parsed.append(character)
                index += 1
                continue
            index += 1
            if index >= len(inner):
                raise ValueError("frontmatter quoted scalar is invalid")
            escape = inner[index]
            if escape in YAML_DOUBLE_QUOTE_ESCAPES:
                parsed.append(YAML_DOUBLE_QUOTE_ESCAPES[escape])
                index += 1
                continue
            width = {"x": 2, "u": 4, "U": 8}.get(escape)
            if width is None or index + width >= len(inner):
                raise ValueError("frontmatter quoted scalar is invalid")
            digits = inner[index + 1 : index + width + 1]
            if not re.fullmatch(rf"[0-9A-Fa-f]{{{width}}}", digits):
                raise ValueError("frontmatter quoted scalar is invalid")
            parsed.append(chr(int(digits, 16)))
            index += width + 1
        return "".join(parsed)
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise ValueError("frontmatter quoted scalar is invalid")
        inner = value[1:-1]
        index = 0
        while index < len(inner):
            if inner[index] != "'":
                index += 1
                continue
            if index + 1 >= len(inner) or inner[index + 1] != "'":
                raise ValueError("frontmatter quoted scalar is invalid")
            index += 2
        return inner.replace("''", "'")
    if value in {"-", "?", ":"} or value.startswith(
        ("- ", "? ", ": ", ",", "[", "]", "{", "}", "&", "*", "!", "%", "@", "`")
    ):
        raise ValueError("frontmatter scalar must be a string")
    if re.search(r":\s", value):
        raise ValueError("frontmatter scalar must be a string")
    return value


def _parse_block_header(value: str) -> tuple[str, int | None, str]:
    header = _strip_yaml_comment(value)
    if not header or header[0] not in {">", "|"}:
        raise ValueError("frontmatter block scalar header is invalid")
    style = header[0]
    indicators = header[1:]
    if any(character.isspace() for character in indicators) or not re.fullmatch(
        r"(?:[1-9]?[+-]?|[+-]?[1-9]?)", indicators
    ):
        raise ValueError("frontmatter block scalar header is invalid")
    indentation: int | None = None
    chomping = ""
    for character in indicators:
        if character in {"+", "-"}:
            if chomping:
                raise ValueError("frontmatter block scalar header is invalid")
            chomping = character
        elif character in "123456789":
            if indentation is not None:
                raise ValueError("frontmatter block scalar header is invalid")
            indentation = int(character)
        else:
            raise ValueError("frontmatter block scalar header is invalid")
    return style, indentation, chomping


def _fold_block_lines(lines: list[tuple[str, bool]]) -> str:
    """Apply the relevant folded-scalar line-break semantics."""
    result: list[str] = []
    index = 0
    last_was_content = False
    last_was_more_indented = False
    while index < len(lines):
        if lines[index][0] == "":
            end = index
            while end < len(lines) and lines[end][0] == "":
                end += 1
            next_is_more_indented = end < len(lines) and lines[end][1]
            newline_count = end - index
            if end < len(lines) and last_was_content and (
                last_was_more_indented or next_is_more_indented
            ):
                newline_count += 1
            result.append("\n" * newline_count)
            last_was_content = False
            index = end
            continue
        if last_was_content:
            result.append("\n" if last_was_more_indented or lines[index][1] else " ")
        result.append(lines[index][0])
        last_was_content = True
        last_was_more_indented = lines[index][1]
        index += 1
    return "".join(result)


def _apply_chomping(value: str, chomping: str) -> str:
    if not value:
        return ""
    if chomping == "-":
        return value.rstrip("\n")
    if chomping == "+":
        return value.rstrip("\n") + "\n" * (len(value) - len(value.rstrip("\n")) + 1)
    return value.rstrip("\n") + "\n"


def _parse_block_scalar(
    lines: list[str], start: int, end: int, header: str, parent_indent: int = 0
) -> tuple[str, int]:
    style, explicit_indent, chomping = _parse_block_header(header)
    required_indent = parent_indent + explicit_indent if explicit_indent is not None else None
    raw_lines: list[str] = []
    index = start
    inferred_indent: int | None = None
    while index < end:
        line = lines[index]
        if not line.strip():
            raw_lines.append("")
            index += 1
            continue
        if not line[:1].isspace():
            break
        if line.startswith("\t"):
            raise ValueError("frontmatter block scalar indentation is invalid")
        leading_spaces = len(line) - len(line.lstrip(" "))
        if leading_spaces <= parent_indent:
            break
        if required_indent is not None:
            if leading_spaces < required_indent:
                break
        elif inferred_indent is not None and leading_spaces < inferred_indent:
            break
        elif inferred_indent is None:
            inferred_indent = leading_spaces
        raw_lines.append(line)
        index += 1

    if not raw_lines:
        return "", index
    nonblank_indents = [len(line) - len(line.lstrip(" ")) for line in raw_lines if line.strip()]
    indentation = required_indent or inferred_indent or min(nonblank_indents, default=0)
    values: list[tuple[str, bool]] = []
    for line in raw_lines:
        if not line.strip():
            values.append(("", False))
            continue
        leading_spaces = len(line) - len(line.lstrip(" "))
        if leading_spaces < indentation:
            raise ValueError("frontmatter block scalar indentation is invalid")
        values.append((line[indentation:], leading_spaces > indentation))

    value = "\n".join(line for line, _more_indented in values) if style == "|" else _fold_block_lines(values)
    return _apply_chomping(value, chomping), index


def _quoted_scalar_complete(value: str) -> bool:
    if not value or value[0] not in {'"', "'"}:
        return False
    quote = value[0]
    index = 1
    while index < len(value):
        if value[index] != quote:
            if value[index] == "\\" and quote == '"':
                index += 2
            else:
                index += 1
            continue
        if quote == "'" and index + 1 < len(value) and value[index + 1] == quote:
            index += 2
            continue
        return index == len(value) - 1
    return False


def _parse_multiline_quoted_scalar(
    lines: list[str], start: int, end: int, value: str, parent_indent: int = 0
) -> tuple[str, int]:
    parts = [value]
    index = start
    while not _quoted_scalar_complete(_strip_yaml_comment("".join(parts))):
        if index >= end:
            raise ValueError("frontmatter quoted scalar is invalid")
        line = lines[index]
        if not line.strip():
            parts.append("\n")
            index += 1
            continue
        if line.startswith("\t"):
            raise ValueError("frontmatter quoted scalar indentation is invalid")
        indentation = len(line) - len(line.lstrip(" "))
        if indentation <= parent_indent:
            raise ValueError("frontmatter quoted scalar indentation is invalid")
        parts.append(" " + line.strip())
        index += 1
    return _parse_inline_scalar(_strip_yaml_comment("".join(parts))), index


def _parse_scalar_field(
    lines: list[str], start: int, end: int, value: str, parent_indent: int = 0
) -> tuple[str, int]:
    cleaned = _strip_yaml_comment(value)
    if cleaned.lstrip().startswith((">", "|")):
        return _parse_block_scalar(lines, start, end, cleaned, parent_indent)
    if cleaned.startswith(('"', "'")) and not _quoted_scalar_complete(cleaned):
        return _parse_multiline_quoted_scalar(lines, start, end, cleaned, parent_indent)
    parsed = _parse_inline_scalar(cleaned)
    continuation: list[tuple[str, bool]] = [(parsed, False)]
    index = start
    inferred_indent: int | None = None
    while index < end:
        line = lines[index]
        if not line.strip():
            lookahead = index + 1
            while lookahead < end and not lines[lookahead].strip():
                lookahead += 1
            if lookahead >= end or not lines[lookahead][:1].isspace():
                break
            continuation.append(("", False))
            index += 1
            continue
        if line.lstrip().startswith("#"):
            break
        if not line[:1].isspace():
            break
        if line.startswith("\t"):
            raise ValueError("frontmatter scalar indentation is invalid")
        indentation = len(line) - len(line.lstrip(" "))
        if indentation <= parent_indent:
            break
        if inferred_indent is None:
            inferred_indent = indentation
        elif indentation < inferred_indent:
            raise ValueError("frontmatter scalar indentation is invalid")
        continuation.append((line.strip(), indentation > inferred_indent))
        index += 1
    if len(continuation) == 1:
        return parsed, index
    return _fold_block_lines(continuation), index


def _parse_mapping_line(line: str) -> tuple[str, str] | None:
    if "\t" in line:
        raise ValueError("frontmatter tabs are invalid")
    match = FRONTMATTER_FIELD.match(line)
    if not match:
        return None
    raw_key, value = match.groups()
    key = _parse_inline_scalar(raw_key.strip())
    if not key:
        raise ValueError("frontmatter field name is empty")
    return key, value


def _parse_metadata_map(lines: list[str], start: int, end: int) -> tuple[dict[str, str], int]:
    """Parse the supported string-to-string form of the optional metadata map."""
    metadata: dict[str, str] = {}
    index = start
    expected_indent: int | None = None
    while index < end:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if not line[:1].isspace():
            break
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break
        if expected_indent is None:
            expected_indent = indent
        if indent != expected_indent:
            raise ValueError("frontmatter metadata indentation is invalid")
        parsed_line = _parse_mapping_line(line[indent:])
        if parsed_line is None:
            raise ValueError("frontmatter metadata must be a mapping of scalar values")
        key, value = parsed_line
        if key in metadata:
            raise ValueError(f"frontmatter metadata key {key!r} is duplicated")
        metadata[key], index = _parse_scalar_field(lines, index + 1, end, value, indent)
    return metadata, index


def _validate_skill_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name.strip())
    if not normalized:
        raise ValueError("frontmatter name is missing")
    if len(normalized) > MAX_NAME_CHARS:
        raise ValueError(f"frontmatter name exceeds {MAX_NAME_CHARS} characters")
    if normalized != normalized.lower():
        raise ValueError("frontmatter name must be lowercase")
    if normalized.startswith("-") or normalized.endswith("-"):
        raise ValueError("frontmatter name cannot start or end with a hyphen")
    if "--" in normalized:
        raise ValueError("frontmatter name cannot contain consecutive hyphens")
    if not all(character.isalnum() or character == "-" for character in normalized):
        raise ValueError("frontmatter name may contain only letters, digits, and hyphens")
    return normalized


def parse_frontmatter(path: Path) -> tuple[str, str]:
    """Parse and validate the supported Agent Skills YAML frontmatter subset.

    Unsupported or malformed YAML is rejected rather than silently ignored so
    the catalog gate cannot accept a file that the reference validator rejects.
    """
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or not lines[0].startswith("---"):
        raise ValueError("frontmatter must start with ---")
    opening_suffix = lines[0][3:]
    if "\t" in opening_suffix or (opening_suffix.strip() and not opening_suffix.lstrip().startswith("#")):
        raise ValueError("frontmatter opening marker is invalid")

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("frontmatter closing --- is missing") from exc

    raw_lines = content.splitlines(keepends=True)
    for line in raw_lines[1:end]:
        if any(ord(character) < 0x20 and character not in "\t\r\n" for character in line):
            raise ValueError("frontmatter control character is invalid")
        if any(ord(character) == 0x7F for character in line):
            raise ValueError("frontmatter control character is invalid")

    fields: dict[str, object] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[:1].isspace():
            raise ValueError("frontmatter indentation is invalid")
        parsed_line = _parse_mapping_line(line)
        if parsed_line is None:
            raise ValueError("frontmatter line is not a valid YAML field")
        field, value = parsed_line
        if field not in ALLOWED_FRONTMATTER_FIELDS:
            raise ValueError(f"frontmatter field {field!r} is not supported")
        if field in fields:
            raise ValueError(f"frontmatter field {field!r} is duplicated")
        if field == "metadata":
            cleaned_metadata = _strip_yaml_comment(value)
            if cleaned_metadata in {"{}", "{ }"}:
                raise ValueError("frontmatter metadata must be an indented mapping")
            if cleaned_metadata:
                raise ValueError("frontmatter metadata must be an indented mapping")
            fields[field], index = _parse_metadata_map(lines, index + 1, end)
        elif value.lstrip().startswith((">", "|")):
            if field == "name":
                raise ValueError("frontmatter name must be an inline scalar")
            fields[field], index = _parse_scalar_field(lines, index + 1, end, value)
        else:
            fields[field], index = _parse_scalar_field(lines, index + 1, end, value)

    if "name" not in fields:
        raise ValueError("frontmatter name is missing")
    if not isinstance(fields["name"], str):
        raise ValueError("frontmatter name must be a string")
    name = _validate_skill_name(fields["name"])
    if "description" not in fields:
        raise ValueError("frontmatter description is empty")
    description = fields["description"]
    if not isinstance(description, str) or not description.strip():
        raise ValueError("frontmatter description is empty")
    if "compatibility" in fields:
        compatibility = fields["compatibility"]
        if not isinstance(compatibility, str):
            raise ValueError("frontmatter compatibility must be a string")
        if len(compatibility) > MAX_COMPATIBILITY_CHARS:
            raise ValueError(f"frontmatter compatibility exceeds {MAX_COMPATIBILITY_CHARS} characters")
    for field in ("license", "allowed-tools"):
        if field in fields and not isinstance(fields[field], str):
            raise ValueError(f"frontmatter {field} must be a string")
    if "metadata" in fields and not isinstance(fields["metadata"], dict):
        raise ValueError("frontmatter metadata must be a mapping")

    if not MIN_DESCRIPTION_CHARS <= len(description) <= MAX_DESCRIPTION_CHARS:
        raise ValueError(
            "frontmatter description length "
            f"{len(description)} is outside "
            f"{MIN_DESCRIPTION_CHARS}-{MAX_DESCRIPTION_CHARS} characters"
        )

    if not any(line.strip() for line in lines[end + 1 :]):
        raise ValueError("skill body is empty")

    return name, description


def local_link_errors(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for match in MARKDOWN_LINK.finditer(text):
        target = (match.group(1) or match.group(2) or "").strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:", "//")):
            continue
        target = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not target:
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
            continue
        if not candidate.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing link target: {target}")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    if not SKILLS_ROOT.is_dir():
        return ["skills/ directory is missing"]

    skills = sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
    names: dict[str, Path] = {}
    for skill_dir in skills:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{skill_dir.relative_to(ROOT)}: SKILL.md is missing")
            continue
        try:
            name, _description = parse_frontmatter(skill_file)
        except ValueError as exc:
            errors.append(f"{skill_file.relative_to(ROOT)}: {exc}")
            continue
        if name != skill_dir.name:
            errors.append(
                f"{skill_file.relative_to(ROOT)}: frontmatter name {name!r} does not match directory {skill_dir.name!r}"
            )
        if name in names:
            errors.append(f"duplicate skill name {name!r}: {names[name]} and {skill_file}")
        names[name] = skill_file

    readme = ROOT / "README.md"
    catalog_names = CATALOG_LINK.findall(readme.read_text(encoding="utf-8"))
    for name in sorted(names):
        count = catalog_names.count(name)
        if count != 1:
            errors.append(f"README.md: skill {name!r} appears {count} times; expected exactly once")
    for name in sorted(set(catalog_names) - set(names)):
        errors.append(f"README.md: catalog lists removed or unknown skill {name!r}")

    for markdown in tracked_markdown_files():
        if markdown.exists():
            errors.extend(local_link_errors(markdown))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Catalog validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    count = sum(1 for path in SKILLS_ROOT.iterdir() if path.is_dir())
    print(f"Catalog validation passed: {count} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
