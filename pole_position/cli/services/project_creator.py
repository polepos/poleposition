import shutil
from pathlib import Path

from pole_position.cli.services.template_renderer import (
    build_context,
    render_project_files,
)


def create_project(
    project_name: str,
    package_name: str,
    project_path: Path,
) -> None:
    template_dir = Path(__file__).resolve().parents[2] / "template"

    if not template_dir.exists():
        raise RuntimeError(f"Template directory not found: {template_dir}")

    shutil.copytree(
        template_dir,
        project_path,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    _rename_source_package(
        project_path=project_path,
        package_name=package_name,
    )

    context = build_context(
        project_name=project_name,
        package_name=package_name,
    )
    render_project_files(project_path=project_path, context=context)


def _rename_source_package(project_path: Path, package_name: str) -> None:
    src_root = project_path / "src"
    source_package_dir = src_root / "app"
    target_package_dir = src_root / package_name

    if not source_package_dir.exists():
        raise RuntimeError(f"Template source package not found: {source_package_dir}")

    source_package_dir.rename(target_package_dir)
