from pathlib import Path

import pytest

from pole_position.cli.services.pyproject_editor import (
    ensure_project_dependency,
    ensure_project_dependency_text,
)


def test_ensure_project_dependency_handles_flexible_multiline_layout(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies   =   [
    "fastapi>=0.115.0",
    "sqlalchemy>=2.0.0",
]

[tool.example]
dependencies = [
    "custom>=1.0.0",
]
""",
        encoding="utf-8",
    )

    ensure_project_dependency(pyproject_path, "aiokafka>=0.12.0")

    content = pyproject_path.read_text(encoding="utf-8")
    assert "dependencies   =   [" in content
    assert '    "aiokafka>=0.12.0",' in content
    assert content.count('"aiokafka>=0.12.0"') == 1
    assert '    "custom>=1.0.0",' in content


def test_ensure_project_dependency_expands_inline_project_dependencies(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies = ["sqlalchemy>=2.0.0", "fastapi>=0.115.0"]
""",
        encoding="utf-8",
    )

    ensure_project_dependency(pyproject_path, "aiokafka>=0.12.0")

    assert pyproject_path.read_text(encoding="utf-8").splitlines() == [
        "[project]",
        'name = "shop-api"',
        "dependencies = [",
        '    "aiokafka>=0.12.0",',
        '    "fastapi>=0.115.0",',
        '    "sqlalchemy>=2.0.0",',
        "]",
    ]


def test_ensure_project_dependency_text_can_preview_without_writing() -> None:
    content = """[project]
name = "shop-api"
dependencies = ["fastapi>=0.115.0"]
"""

    updated = ensure_project_dependency_text(content, "aiokafka>=0.12.0")

    assert updated != content
    assert '"aiokafka>=0.12.0",' in updated
    assert '"fastapi>=0.115.0",' in updated


def test_ensure_project_dependency_noops_for_missing_dependency(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"

    ensure_project_dependency(pyproject_path, None)

    assert not pyproject_path.exists()


def test_ensure_project_dependency_does_not_duplicate_existing_dependency(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies = [
    'aiokafka>=0.12.0',
    "fastapi>=0.115.0",
]
""",
        encoding="utf-8",
    )
    original_content = pyproject_path.read_text(encoding="utf-8")

    ensure_project_dependency(pyproject_path, "aiokafka>=0.12.0")

    assert pyproject_path.read_text(encoding="utf-8") == original_content


def test_ensure_project_dependency_does_not_duplicate_upgraded_dependency(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies = [
    "Aiokafka>=0.13.0",
    "fastapi>=0.115.0",
]
""",
        encoding="utf-8",
    )
    original_content = pyproject_path.read_text(encoding="utf-8")

    ensure_project_dependency(pyproject_path, "aiokafka>=0.12.0")

    assert pyproject_path.read_text(encoding="utf-8") == original_content


def test_ensure_project_dependency_replaces_lower_version_dependency(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies = ["fastapi>=0.115.0", "Aiokafka>=0.11.0"]
""",
        encoding="utf-8",
    )

    ensure_project_dependency(pyproject_path, "aiokafka>=0.12.0")

    content = pyproject_path.read_text(encoding="utf-8")
    assert '"aiokafka>=0.12.0",' in content
    assert "Aiokafka>=0.11.0" not in content
    assert content.count("aiokafka") == 1


def test_ensure_project_dependency_replaces_dependency_missing_required_extra(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies = [
    "pwdlib>=0.2.0",
]
""",
        encoding="utf-8",
    )

    ensure_project_dependency(pyproject_path, "pwdlib[argon2]>=0.2.0")

    content = pyproject_path.read_text(encoding="utf-8")
    assert '"pwdlib[argon2]>=0.2.0",' in content
    assert '"pwdlib>=0.2.0",' not in content


def test_ensure_project_dependency_accepts_dependency_with_required_extra(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"
dependencies = [
    "PwdLib[argon2]>=0.3.0",
]
""",
        encoding="utf-8",
    )
    original_content = pyproject_path.read_text(encoding="utf-8")

    ensure_project_dependency(pyproject_path, "pwdlib[argon2]>=0.2.0")

    assert pyproject_path.read_text(encoding="utf-8") == original_content


def test_ensure_project_dependency_requires_project_dependencies(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """[project]
name = "shop-api"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Unsupported dependency layout"):
        ensure_project_dependency(pyproject_path, "aiokafka>=0.12.0")
