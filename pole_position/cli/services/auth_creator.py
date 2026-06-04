from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.module_creator import (
    MODEL_IMPORTS_MARKER,
    ROUTER_IMPORTS_MARKER,
    ROUTER_INCLUDES_MARKER,
)
from pole_position.cli.services.module_templates.renderer import render_template
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    read_project_manifest,
    record_manifest_integration,
)
from pole_position.cli.services.pyproject_editor import (
    ensure_project_dependency,
    ensure_project_dependency_text,
)

AUTH_DEPENDENCY = "pwdlib[argon2]>=0.2.0"


@dataclass(frozen=True)
class AddedAuthResult:
    project_root: Path
    package_root: Path
    auth_files: tuple[Path, ...]
    test_files: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]

    @property
    def package_name(self) -> str:
        return self.package_root.name


def add_auth(cwd: Path | None = None) -> AddedAuthResult:
    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    auth_root = package_root / "auth"

    auth_files = _auth_files(package_name)
    test_files = _auth_test_files(package_name)

    _validate_add_auth_preflight(
        project_root=project_root,
        package_root=package_root,
        auth_root=auth_root,
        auth_files=auth_files,
        test_files=test_files,
    )

    written_auth_files = _write_files(auth_root, auth_files)
    written_test_files = _write_test_files(project_root / "tests", test_files)
    updated_files: list[Path] = []

    router_path = package_root / "api" / "router.py"
    if _update_api_router(router_path, package_name):
        updated_files.append(router_path)

    models_path = package_root / "db" / "models.py"
    if _update_db_models(models_path, package_name):
        updated_files.append(models_path)

    pyproject_path = project_root / "pyproject.toml"
    ensure_project_dependency(pyproject_path, AUTH_DEPENDENCY)
    updated_files.append(pyproject_path)

    record_manifest_integration(
        project_root=project_root, integration_name="auth"
    )
    project_manifest_path = manifest_path(project_root)
    if project_manifest_path.is_file():
        updated_files.append(project_manifest_path)

    return AddedAuthResult(
        project_root=project_root,
        package_root=package_root,
        auth_files=tuple(written_auth_files),
        test_files=tuple(written_test_files),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=(
            "Run `uv sync --extra dev`",
            'Run `polepos db revision -m "add auth users table"`',
            "Run `polepos db upgrade`",
            "Run `polepos check`",
        ),
    )


def _validate_add_auth_preflight(
    *,
    project_root: Path,
    package_root: Path,
    auth_root: Path,
    auth_files: dict[str, str],
    test_files: dict[str, str],
) -> None:
    problems: list[str] = []

    _collect_manifest_read_error(problems, project_root)

    if not (package_root / "db" / "models.py").is_file():
        problems.append(
            "Auth workflow requires generated db/ wiring. "
            "Projects created with `--db none` need an explicit database "
            "layer first."
        )

    for relative_path in auth_files:
        path = auth_root / relative_path
        if path.exists():
            problems.append(f"Generated auth file already exists: {path}")

    tests_root = project_root / "tests"
    for relative_path in test_files:
        path = tests_root / relative_path
        if path.exists():
            problems.append(f"Generated auth test already exists: {path}")

    _collect_missing_marker(
        problems,
        package_root / "api" / "router.py",
        ROUTER_IMPORTS_MARKER,
    )
    _collect_missing_marker(
        problems,
        package_root / "api" / "router.py",
        ROUTER_INCLUDES_MARKER,
    )
    _collect_missing_marker(
        problems,
        package_root / "db" / "models.py",
        MODEL_IMPORTS_MARKER,
    )
    _collect_patchable_project_dependency(
        problems,
        project_root / "pyproject.toml",
    )

    if problems:
        formatted_problems = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(
            "Cannot add auth because the project layout is not ready:\n"
            f"{formatted_problems}"
        )


def _collect_missing_marker(
    problems: list[str], path: Path, marker: str
) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for auth add: {path}: "
            f"{exc.reason}"
        )
        return

    if marker not in lines:
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _collect_manifest_read_error(
    problems: list[str], project_root: Path
) -> None:
    manifest = read_project_manifest(project_root)
    if manifest.read_error is not None:
        problems.append(manifest.read_error)


def _collect_patchable_project_dependency(
    problems: list[str], path: Path
) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    try:
        ensure_project_dependency_text(
            path.read_text(encoding="utf-8"),
            AUTH_DEPENDENCY,
            path_label=str(path),
        )
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for auth add: {path}: "
            f"{exc.reason}"
        )
    except RuntimeError as exc:
        problems.append(str(exc))


def _auth_files(package_name: str) -> dict[str, str]:
    context = {"package_name": package_name}
    return {
        "model.py": _render_auth_template("model.py", context),
        "password.py": _render_auth_template("password.py", context),
        "repository.py": _render_auth_template("repository.py", context),
        "router.py": _render_auth_template("router.py", context),
        "user_schemas.py": _render_auth_template("user_schemas.py", context),
        "user_service.py": _render_auth_template("user_service.py", context),
    }


def _auth_test_files(package_name: str) -> dict[str, str]:
    context = {"package_name": package_name}
    return {
        "integration/test_auth.py": _render_auth_template(
            "tests/integration.py",
            context,
        ),
        "unit/test_auth_service.py": _render_auth_template(
            "tests/unit.py", context
        ),
    }


def _render_auth_template(relative_path: str, context: dict[str, str]) -> str:
    return render_template(f"auth/{relative_path}.tpl", context)


def _write_files(root: Path, files: dict[str, str]) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def _write_test_files(tests_root: Path, files: dict[str, str]) -> list[Path]:
    return _write_files(tests_root, files)


def _update_api_router(path: Path, package_name: str) -> bool:
    import_line = (
        f"from {package_name}.auth.router import router as auth_router"
    )
    include_line = (
        'api_router.include_router(auth_router, prefix="/auth", tags=["auth"])'
    )

    changed = _insert_line_before_marker(
        path=path,
        line=import_line,
        marker=ROUTER_IMPORTS_MARKER,
    )
    return (
        _insert_line_before_marker(
            path=path,
            line=include_line,
            marker=ROUTER_INCLUDES_MARKER,
        )
        or changed
    )


def _update_db_models(path: Path, package_name: str) -> bool:
    import_line = (
        f"    from {package_name}.auth import model as auth_model  # noqa: F401"
    )
    return _insert_line_before_marker(
        path=path,
        line=import_line,
        marker=MODEL_IMPORTS_MARKER,
    )


def _insert_line_before_marker(*, path: Path, line: str, marker: str) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if line in lines:
        return False

    try:
        marker_index = lines.index(marker)
    except ValueError as exc:
        raise RuntimeError(f"Unsupported managed block layout: {path}") from exc

    lines.insert(marker_index, line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True
