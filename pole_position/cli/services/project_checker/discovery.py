"""Project discovery and database-mode detection."""

from pathlib import Path

from pole_position.cli.services.project_checker.constants import (
    PACKAGE_IDENTITY_PATHS,
    PROJECT_IDENTITY_PATHS,
)
from pole_position.cli.services.project_manifest import (
    ProjectManifest,
    read_project_manifest,
)


def _discover_core_project(cwd: Path | None = None) -> tuple[Path, Path]:
    current = (cwd or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        package_root = _find_core_package_root_in(candidate)
        if package_root is not None:
            return candidate, package_root

    raise RuntimeError(
        "Current directory does not look like a PolePosition project."
    )


def _find_core_package_root_in(project_root: Path) -> Path | None:
    src_root = project_root / "src"
    if not src_root.is_dir():
        return None

    manifest = read_project_manifest(project_root)
    if manifest.exists and manifest.package_name:
        package_root = src_root / manifest.package_name
        if (
            package_root.is_dir()
            and package_root.name.isidentifier()
            and _has_core_project_signals(project_root, package_root)
        ):
            return package_root

    candidates = [
        path
        for path in src_root.iterdir()
        if (
            path.is_dir()
            and path.name.isidentifier()
            and _has_core_project_signals(project_root, path)
        )
    ]

    if len(candidates) != 1:
        return None

    return candidates[0]


def _has_core_project_signals(project_root: Path, package_root: Path) -> bool:
    project_signal_count = sum(
        1
        for relative_path in PROJECT_IDENTITY_PATHS
        if (project_root / relative_path).exists()
    )
    package_signal_count = sum(
        1
        for relative_path in PACKAGE_IDENTITY_PATHS
        if (package_root / relative_path).exists()
    )

    return project_signal_count >= 1 and package_signal_count >= 2


def _project_uses_database(project_root: Path, package_root: Path) -> bool:
    if (project_root / "alembic.ini").exists():
        return True
    if (project_root / "migrations").exists():
        return True
    if (package_root / "db").exists():
        return True

    settings_path = package_root / "settings.py"
    if _file_contains_text(settings_path, "database_url:"):
        return True

    env_path = project_root / ".env.example"
    if _file_contains_text(env_path, "DATABASE_URL="):
        return True

    return False


def _file_contains_text(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False

    try:
        return needle in path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False


def _project_database_mode(
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
) -> str:
    if manifest.exists and manifest.database:
        database_mode = manifest.database.strip().lower()
        if database_mode in {"sqlite", "postgres", "none", "custom"}:
            return database_mode
        return "unsupported"

    return (
        "managed"
        if _project_uses_database(project_root, package_root)
        else "none"
    )
