from pathlib import Path

from pole_position.cli.services.project_checker import (
    ProjectCheckResult,
    _check_alembic_config,
    _check_database_free_remnants,
    _check_generated_structure,
    _check_lifecycle_wiring,
    _check_managed_markers,
    _check_project_identity,
    describe_project_check_issue,
)


def test_project_check_result_properties(tmp_path: Path) -> None:
    result = ProjectCheckResult(
        project_root=tmp_path,
        package_root=tmp_path / "src" / "shop_api",
        problems=[],
    )
    failed_result = ProjectCheckResult(
        project_root=tmp_path,
        package_root=tmp_path / "src" / "shop_api",
        problems=["broken"],
    )

    assert result.package_name == "shop_api"
    assert result.passed is True
    assert failed_result.passed is False
    assert failed_result.issues[0].code == "PPCHK000"
    assert failed_result.issues[0].message == "broken"


def test_project_check_issue_describes_managed_marker_remediation() -> None:
    issue = describe_project_check_issue(
        "Managed marker '# polepos:router-imports' is missing in api/router.py"
    )

    assert issue.code == "PPCHK021"
    assert issue.message.startswith("Managed marker")
    assert "Restore the listed # polepos marker" in issue.remediation


def test_project_identity_check_reports_missing_identity_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    package_root.mkdir(parents=True)
    problems: list[str] = []

    _check_project_identity(problems, project_root, package_root)

    assert any(
        "Project identity file is missing" in problem for problem in problems
    )
    assert any("pyproject.toml" in problem for problem in problems)


def test_generated_structure_check_reports_missing_paths(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    problems: list[str] = []

    _check_generated_structure(problems, project_root, package_root)

    assert any(".env.example" in problem for problem in problems)
    assert any("AGENTS.md" in problem for problem in problems)
    assert any("tests/conftest.py" in problem for problem in problems)
    assert any("src/shop_api/app.py" in problem for problem in problems)
    assert any(
        "src/shop_api/modules/status/router.py" in problem
        for problem in problems
    )


def test_alembic_config_check_reports_missing_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "shop-api"
    problems: list[str] = []

    _check_alembic_config(problems, project_root)

    assert any("alembic.ini" in problem for problem in problems)
    assert any("migrations/env.py" in problem for problem in problems)
    assert any("migrations/versions" in problem for problem in problems)


def test_database_free_remnant_check_reports_database_content(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    _write_text(
        project_root / "Dockerfile",
        "COPY pyproject.toml README.md alembic.ini ./\nCOPY migrations "
        "./migrations\n",
    )
    _write_text(
        project_root / "README.md",
        "## Project "
        "Layout\n\n```text\nalembic.ini\nmigrations/\nsrc/shop_api/\n  "
        "db/\n```\n",
    )
    _write_text(
        package_root / "api" / "deps.py",
        (
            "from sqlalchemy.orm import Session\n"
            "from shop_api.db.session import get_db\n"
            "def db_session():\n"
            "    yield from get_db()\n"
        ),
    )
    problems: list[str] = []

    _check_database_free_remnants(problems, project_root, package_root)

    assert any("Dockerfile" in problem for problem in problems)
    assert any("README.md" in problem for problem in problems)
    assert any("api/deps.py" in problem for problem in problems)
    assert any("sqlalchemy" in problem for problem in problems)
    assert any("COPY migrations" in problem for problem in problems)


def test_managed_marker_check_reports_missing_files(tmp_path: Path) -> None:
    package_root = tmp_path / "shop-api" / "src" / "shop_api"
    problems: list[str] = []

    _check_managed_markers(problems, package_root)

    assert any("api/router.py" in problem for problem in problems)
    assert any("db/models.py" in problem for problem in problems)
    assert any(".env.example" in problem for problem in problems)


def test_managed_marker_check_reports_missing_markers(tmp_path: Path) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    _write_marker_files_without_all_markers(project_root, package_root)
    problems: list[str] = []

    _check_managed_markers(problems, package_root)

    assert any("# polepos:router-includes" in problem for problem in problems)
    assert any(
        "# polepos:integration-settings" in problem for problem in problems
    )
    assert any("# polepos:llm-settings" in problem for problem in problems)
    assert any("# polepos:integration-env" in problem for problem in problems)
    assert any("# polepos:llm-env" in problem for problem in problems)


def test_managed_marker_check_passes_with_all_markers(tmp_path: Path) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    _write_marker_files_with_all_markers(project_root, package_root)
    problems: list[str] = []

    _check_managed_markers(problems, package_root)

    assert problems == []


def test_lifecycle_check_ignores_legacy_starter_samples(tmp_path: Path) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    _write_text(package_root / "modules" / "profile" / "__init__.py", "")
    _write_text(package_root / "modules" / "profile" / "router.py", "")
    _write_text(package_root / "modules" / "profile" / "schemas.py", "")
    _write_text(package_root / "modules" / "races" / "__init__.py", "")
    _write_text(package_root / "modules" / "races" / "model.py", "")
    _write_text(package_root / "modules" / "races" / "repository.py", "")
    _write_text(package_root / "modules" / "races" / "router.py", "")
    _write_text(package_root / "modules" / "races" / "schemas.py", "")
    _write_text(package_root / "modules" / "races" / "service.py", "")
    _write_text(project_root / "tests" / "unit" / "test_race_service.py", "")
    problems: list[str] = []

    _check_lifecycle_wiring(problems, project_root, package_root)

    assert problems == []


def test_lifecycle_check_ignores_python_cache_directories(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    (package_root / "modules" / "__pycache__").mkdir(parents=True)
    problems: list[str] = []

    _check_lifecycle_wiring(problems, project_root, package_root)

    assert problems == []


def _write_marker_files_without_all_markers(
    project_root: Path, package_root: Path
) -> None:
    _write_text(
        package_root / "api" / "router.py",
        "# polepos:router-imports\n",
    )
    _write_text(
        package_root / "db" / "models.py",
        "    # polepos:model-imports\n",
    )
    _write_text(
        package_root / "modules" / "__init__.py",
        "    # polepos:module-exports\n",
    )
    _write_text(
        package_root / "settings.py",
        "    # polepos:auth-settings\n",
    )
    _write_text(
        project_root / ".env.example",
        "# polepos:auth-env\n",
    )


def _write_marker_files_with_all_markers(
    project_root: Path, package_root: Path
) -> None:
    _write_text(
        package_root / "api" / "router.py",
        "# polepos:router-imports\n# polepos:router-includes\n",
    )
    _write_text(
        package_root / "db" / "models.py",
        "    # polepos:model-imports\n",
    )
    _write_text(
        package_root / "modules" / "__init__.py",
        "    # polepos:module-exports\n",
    )
    _write_text(
        package_root / "settings.py",
        (
            "    # polepos:auth-settings\n"
            "    # polepos:integration-settings\n"
            "    # polepos:llm-settings\n"
        ),
    )
    _write_text(
        project_root / ".env.example",
        "# polepos:auth-env\n# polepos:integration-env\n# polepos:llm-env\n",
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
