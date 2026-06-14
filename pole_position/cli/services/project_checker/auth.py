"""Auth workflow checks: files, tests, dependency, router and model wiring."""

from pathlib import Path

from pole_position.cli.services.auth_creator import AUTH_DEPENDENCY
from pole_position.cli.services.project_checker.constants import (
    AUTH_WORKFLOW_PACKAGE_PATHS,
    AUTH_WORKFLOW_TEST_PATHS,
)
from pole_position.cli.services.project_checker.deps import (
    _pyproject_has_dependency,
)
from pole_position.cli.services.project_checker.io import (
    _parse_python_source,
    _read_file_text,
)
from pole_position.cli.services.project_checker.lifecycle import (
    _has_reported_parse_error,
)
from pole_position.cli.services.project_manifest import ProjectManifest
from pole_position.cli.services.project_wiring import (
    has_router_import,
    has_router_include,
)


def _check_auth_workflow(
    *,
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    uses_database: bool,
) -> None:
    pyproject_content = _read_file_text(
        project_root / "pyproject.toml", problems
    )
    if not _should_check_auth_workflow(
        project_root=project_root,
        package_root=package_root,
        manifest=manifest,
        pyproject_content=pyproject_content,
    ):
        return

    if not uses_database:
        problems.append(
            "Auth workflow requires generated database wiring but the "
            "project is "
            "configured without a database."
        )
        return

    _check_auth_files(problems, package_root)
    _check_auth_tests(problems, project_root)
    _check_auth_dependency(
        problems=problems,
        project_root=project_root,
        pyproject_content=pyproject_content,
    )
    _check_auth_router_wiring(problems, package_root)
    _check_auth_model_wiring(problems, package_root)


def _should_check_auth_workflow(
    *,
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    pyproject_content: str | None,
) -> bool:
    if manifest.exists and manifest.enabled_integrations.get("auth"):
        return True

    if any(
        (package_root / relative_path).exists()
        for relative_path in AUTH_WORKFLOW_PACKAGE_PATHS
    ):
        return True

    if any(
        (project_root / relative_path).exists()
        for relative_path in AUTH_WORKFLOW_TEST_PATHS
    ):
        return True

    router_content = _read_file_text(package_root / "api" / "router.py") or ""
    if (
        f"{package_root.name}.auth.router" in router_content
        or "/auth" in router_content
    ):
        return True

    models_content = _read_file_text(package_root / "db" / "models.py") or ""
    if f"{package_root.name}.auth import model" in models_content:
        return True

    return pyproject_content is not None and _pyproject_has_dependency(
        pyproject_content, AUTH_DEPENDENCY
    )


def _check_auth_files(problems: list[str], package_root: Path) -> None:
    for relative_path in AUTH_WORKFLOW_PACKAGE_PATHS:
        path = package_root / relative_path
        if not path.exists():
            problems.append(f"Auth workflow is missing generated file: {path}")


def _check_auth_tests(problems: list[str], project_root: Path) -> None:
    integration_test = project_root / "tests" / "integration" / "test_auth.py"
    unit_test = project_root / "tests" / "unit" / "test_auth_service.py"

    if not integration_test.exists():
        problems.append(
            f"Auth workflow is missing integration test: {integration_test}"
        )

    if not unit_test.exists():
        problems.append(f"Auth workflow is missing unit test: {unit_test}")


def _check_auth_dependency(
    *,
    problems: list[str],
    project_root: Path,
    pyproject_content: str | None,
) -> None:
    if pyproject_content is None:
        return

    if not _pyproject_has_dependency(pyproject_content, AUTH_DEPENDENCY):
        problems.append(
            f"Auth workflow is missing dependency in "
            f"{project_root / 'pyproject.toml'}: {AUTH_DEPENDENCY}"
        )


def _check_auth_router_wiring(problems: list[str], package_root: Path) -> None:
    router_path = package_root / "api" / "router.py"
    content = _read_file_text(router_path, problems)
    if content is None:
        return

    tree = _parse_python_source(content, router_path, problems)
    if tree is None:
        return

    package_name = package_root.name
    router_module = f"{package_name}.auth.router"
    import_line = (
        f"from {package_name}.auth.router import router as auth_router"
    )
    include_line = (
        'api_router.include_router(auth_router, prefix="/auth", tags=["auth"])'
    )

    if not has_router_import(tree, router_module, "auth_router"):
        problems.append(
            f"Auth workflow is missing router import in {router_path}: "
            f"{import_line}"
        )

    if not has_router_include(tree, "auth_router", "auth"):
        problems.append(
            f"Auth workflow is missing API router include in "
            f"{router_path}: {include_line}"
        )


def _check_auth_model_wiring(problems: list[str], package_root: Path) -> None:
    models_path = package_root / "db" / "models.py"
    content = _read_file_text(models_path, problems)
    if content is None:
        return

    if _has_reported_parse_error(problems, models_path):
        return

    tree = _parse_python_source(content, models_path, problems)
    if tree is None:
        return

    import_line = (
        f"    from {package_root.name}.auth import model as auth_model  # "
        f"noqa: F401"
    )
    if import_line not in content.splitlines():
        problems.append(
            f"Auth workflow is missing model import in {models_path}: "
            f"{import_line}"
        )
