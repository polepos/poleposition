"""Shared pyproject dependency-spec parsing for project checks."""

import re

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from pole_position.cli.services.dependency_contract import (
    dependency_contract_satisfied,
    quoted_dependency_values,
)


def _pyproject_has_dependency(
    pyproject_content: str, required_dependency: str
) -> bool:
    return dependency_contract_satisfied(
        _project_dependency_specs(pyproject_content),
        required_dependency,
    )


def _project_dependency_specs(pyproject_content: str) -> tuple[str, ...]:
    if tomllib is not None:
        try:
            pyproject = tomllib.loads(pyproject_content)
        except tomllib.TOMLDecodeError:
            return ()

        project = pyproject.get("project")
        if not isinstance(project, dict):
            return ()

        dependencies = project.get("dependencies")
        if not isinstance(dependencies, list):
            return ()

        return tuple(
            dependency
            for dependency in dependencies
            if isinstance(dependency, str)
        )

    return _fallback_project_dependency_specs(pyproject_content)


def _fallback_project_dependency_specs(
    pyproject_content: str,
) -> tuple[str, ...]:
    project_match = re.search(
        r"(?ms)^\s*\[project\]\s*$"
        r"(?P<section>.*?)"
        r"^\s*\[[^\]]+\]\s*$",
        f"{pyproject_content}\n[__poleposition_end__]\n",
    )
    if project_match is None:
        return ()

    dependencies_match = re.search(
        r"(?ms)^\s*dependencies\s*=\s*\[(?P<dependencies>.*?)\]\s*(?:#.*)?$",
        project_match.group("section"),
    )
    if dependencies_match is None:
        return ()

    return quoted_dependency_values(dependencies_match.group("dependencies"))
