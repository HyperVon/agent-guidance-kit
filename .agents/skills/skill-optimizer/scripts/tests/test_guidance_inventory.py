"""Tests for guidance_inventory.py.

These cover the measurement-critical paths the optimizer relies on: a normal
repo root, a missing root (non-directory exit), symlink escape refusal, and the
`possible_saved_characters` math.
"""

import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import guidance_inventory as gi  # noqa: E402


def _make_skill(root: Path, name: str, body: str) -> Path:
    skill_dir = root / ".agents" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / "SKILL.md"
    path.write_text(
        f"---\nname: {name}\ndescription: example\n---\n# {name}\n\n{body}\n"
    )
    return path


def test_normal_repo_root(tmp_path):
    _make_skill(tmp_path, "foo", "# Foo\n\nSome normal content.\n")
    root = Path(str(tmp_path))
    records, repeated = gi.read_records(root, "active")
    paths = [record["path"] for record in records]
    assert any(path.endswith("SKILL.md") for path in paths)
    assert repeated == []


def test_missing_root_returns_exit_code(tmp_path):
    missing = tmp_path / "does-not-exist"
    code = gi.main(["--root", str(missing)])
    assert code == 2


def test_symlink_file_escape_refused(tmp_path):
    outside = Path(tempfile.mkdtemp())
    (outside / "SKILL.md").write_text("# outside secret\n")

    skill_dir = tmp_path / ".agents" / "skills" / "x"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").symlink_to(outside / "SKILL.md")
    (skill_dir / "real.md").write_text("# real inside content\n")

    symlink_path = skill_dir / "SKILL.md"
    yielded = list(gi.iter_files(Path(str(tmp_path))))
    assert not any(path.is_symlink() for path in yielded)
    assert symlink_path not in yielded
    assert any(str(path).endswith("real.md") for path in yielded)


def test_symlink_directory_escape_refused(tmp_path):
    outside = Path(tempfile.mkdtemp())
    (outside / "SKILL.md").write_text("# outside secret via dir\n")

    skills = tmp_path / ".agents" / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    link = skills / "y"
    link.symlink_to(outside, target_is_directory=True)
    _make_skill(tmp_path, "z", "# real inside content\n")

    yielded = list(gi.iter_files(Path(str(tmp_path))))
    assert not any(path.is_symlink() for path in yielded)
    assert not any(str(path).startswith(str(link)) for path in yielded)
    assert any(str(path).endswith("z/SKILL.md") for path in yielded)


def test_possible_saved_characters_math(tmp_path):
    paragraph = (
        "This is a deliberately long repeated paragraph that exceeds the "
        "one hundred character threshold used by the inventory helper so "
        "it qualifies as a normalized prose block candidate for dedup. "
    )
    assert len(paragraph) >= 100

    for name in ("a", "b", "c"):
        _make_skill(tmp_path, name, paragraph)

    records, repeated = gi.read_records(Path(str(tmp_path)), "active")
    assert records
    matches = [item for item in repeated if paragraph.strip() in item["text"]]
    assert matches, "expected repeated block not found"
    item = matches[0]
    assert len(item["paths"]) == 3
    assert item["possible_saved_characters"] == item["characters"] * (
        len(item["paths"]) - 1
    )
