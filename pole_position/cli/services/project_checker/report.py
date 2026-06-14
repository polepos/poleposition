"""Project check result types and the issue/remediation catalog."""

import re
from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.module_templates import (
    SUPPORTED_MODULE_TEMPLATES,
)


@dataclass(frozen=True)
class ProjectCheckIssue:
    code: str
    message: str
    remediation: str


@dataclass(frozen=True)
class ProjectCheckResult:
    project_root: Path
    package_root: Path
    problems: list[str]

    @property
    def package_name(self) -> str:
        return self.package_root.name

    @property
    def passed(self) -> bool:
        return not self.problems

    @property
    def issues(self) -> tuple[ProjectCheckIssue, ...]:
        return tuple(
            describe_project_check_issue(problem) for problem in self.problems
        )


def describe_project_check_issue(problem: str) -> ProjectCheckIssue:
    return ProjectCheckIssue(
        code=_project_check_issue_code(problem),
        message=problem,
        remediation=_project_check_remediation(problem),
    )


def _project_check_issue_code(problem: str) -> str:
    if problem.startswith("Project identity file is missing"):
        return "PPCHK001"
    if problem.startswith("Project src directory is missing"):
        return "PPCHK002"
    if problem.startswith(
        "Application package is not under project src directory"
    ):
        return "PPCHK003"
    if problem.startswith(
        "Application package name is not a valid Python identifier"
    ):
        return "PPCHK004"
    if problem.startswith("Project manifest package does not match"):
        return "PPCHK005"
    if problem.startswith("Required generated path is missing"):
        return "PPCHK010"
    if problem.startswith("Required Alembic path is missing"):
        return "PPCHK011"
    if problem.startswith(
        "Database-free project contains database-specific content"
    ):
        return "PPCHK012"
    if problem.startswith("Project manifest has unsupported database mode"):
        return "PPCHK013"
    if problem.startswith("Project manifest has unsupported module template"):
        return "PPCHK014"
    if problem.startswith("Project manifest has unsupported integration value"):
        return "PPCHK015"
    if problem.startswith("Could not read project manifest as UTF-8"):
        return "PPCHK016"
    if problem.startswith("Managed file is missing"):
        return "PPCHK020"
    if problem.startswith("Managed marker"):
        return "PPCHK021"
    if problem.startswith("Starter module 'status' is missing"):
        return "PPCHK022"
    if problem.startswith("Could not read generated text file as UTF-8"):
        return "PPCHK023"
    if problem.startswith(
        "Lifecycle module directory is not a valid Python identifier"
    ):
        return "PPCHK030"
    if problem.startswith("Auth workflow requires generated database wiring"):
        return "PPCHK044"
    if problem.startswith("Auth workflow is missing generated file:"):
        return "PPCHK045"
    if problem.startswith("Auth workflow is missing integration test:"):
        return "PPCHK046"
    if problem.startswith("Auth workflow is missing unit test:"):
        return "PPCHK047"
    if problem.startswith("Auth workflow is missing dependency "):
        return "PPCHK048"
    if problem.startswith("Auth workflow is missing router import "):
        return "PPCHK049"
    if problem.startswith("Auth workflow is missing API router include "):
        return "PPCHK050"
    if problem.startswith("Auth workflow is missing model import "):
        return "PPCHK051"
    if " is missing generated path:" in problem:
        return "PPCHK031"
    if " is missing module export " in problem:
        return "PPCHK032"
    if " is missing router import " in problem:
        return "PPCHK033"
    if " is missing API router include " in problem:
        return "PPCHK034"
    if " is missing model import " in problem:
        return "PPCHK035"
    if " is missing integration test:" in problem:
        return "PPCHK036"
    if " is missing unit test:" in problem:
        return "PPCHK037"
    if problem.startswith("Could not parse Python file for lifecycle checks"):
        return "PPCHK038"
    if problem.startswith("Orphan module"):
        return "PPCHK039"
    if (
        problem.startswith("Integration ")
        and " is missing generated file:" in problem
    ):
        return "PPCHK040"
    if (
        problem.startswith("Integration ")
        and " is missing dependency " in problem
    ):
        return "PPCHK041"
    if problem.startswith("Integration ") and " is missing setting " in problem:
        return "PPCHK042"
    if (
        problem.startswith("Integration ")
        and " is missing env value " in problem
    ):
        return "PPCHK043"
    return "PPCHK000"


def _project_check_remediation(problem: str) -> str:
    module_name = _extract_lifecycle_module_name(problem)
    integration_name = _extract_integration_name(problem)

    if problem.startswith("Project identity file is missing"):
        return (
            "Restore pyproject.toml or run the command from the generated "
            "project root."
        )
    if problem.startswith("Project src directory is missing"):
        return (
            "Restore the generated src/ directory or run the command from the "
            "project root."
        )
    if problem.startswith(
        "Application package is not under project src directory"
    ):
        return (
            "Move the application package back under src/ or document the "
            "project "
            "as manually managed."
        )
    if problem.startswith(
        "Application package name is not a valid Python identifier"
    ):
        return "Rename the package directory to a valid Python identifier."
    if problem.startswith("Project manifest package does not match"):
        return (
            "Update .poleposition.toml or move the package back to the "
            "recorded name."
        )
    if problem.startswith("Required generated path is missing"):
        return (
            "Restore the generated path, or intentionally opt out and document "
            "the drift."
        )
    if problem.startswith("Required Alembic path is missing"):
        return (
            "Restore Alembic files or regenerate the migration setup "
            "before using "
            "polepos db commands."
        )
    if problem.startswith(
        "Database-free project contains database-specific content"
    ):
        return (
            "Remove database-specific remnants or add a database layer "
            "intentionally."
        )
    if problem.startswith("Project manifest has unsupported database mode"):
        return 'Use db = "sqlite", "postgres", "none", or "custom".'
    if problem.startswith("Project manifest has unsupported module template"):
        supported = ", ".join((*SUPPORTED_MODULE_TEMPLATES, "starter"))
        return (
            f"Use one of these module template values: {supported}; CRUD "
            f"options "
            "may be recorded as crud[pagination,timestamps,...]."
        )
    if problem.startswith("Project manifest has unsupported integration value"):
        return "Use unquoted true or false for generated integration values."
    if problem.startswith("Could not read project manifest as UTF-8"):
        return (
            "Restore .poleposition.toml as UTF-8 TOML or remove the corrupt "
            "file."
        )
    if problem.startswith("Managed file is missing"):
        return (
            "Restore the managed file before running PolePosition lifecycle "
            "commands."
        )
    if problem.startswith("Managed marker"):
        return (
            "Restore the listed # polepos marker or manage that file manually."
        )
    if problem.startswith("Starter module 'status' is missing"):
        return (
            "Restore the generated status router import/include in "
            "api/router.py."
        )
    if problem.startswith("Could not read generated text file as UTF-8"):
        return (
            "Restore the file as UTF-8 text or replace it with generated "
            "content."
        )
    if problem.startswith(
        "Lifecycle module directory is not a valid Python identifier"
    ):
        return "Rename the module directory to a valid Python identifier."
    if problem.startswith("Auth workflow requires generated database wiring"):
        return (
            "Create the project with database support or fully detach the auth "
            "workflow."
        )
    if problem.startswith("Auth workflow "):
        return (
            "Restore the missing auth workflow piece or fully detach auth from "
            "router wiring, db/models.py, pyproject.toml, tests, and "
            ".poleposition.toml."
        )
    if " is missing generated path:" in problem:
        return _module_fix(
            module_name,
            "Restore the missing generated module file, or detach/remove "
            "the module.",
        )
    if " is missing module export " in problem:
        return _module_fix(
            module_name,
            "Restore the module export, or clean the detached module with "
            "wiring-only removal.",
        )
    if " is missing router import " in problem:
        return _module_fix(
            module_name,
            "Restore the router import, or clean the detached module with "
            "wiring-only removal.",
        )
    if " is missing API router include " in problem:
        return _module_fix(
            module_name,
            "Restore the router include, or clean the detached module with "
            "wiring-only removal.",
        )
    if " is missing model import " in problem:
        return _module_fix(
            module_name,
            "Restore the db/models.py import so Alembic can see the model.",
        )
    if " is missing integration test:" in problem:
        return _module_fix(
            module_name,
            "Restore the generated integration test or clean detached "
            "test remnants.",
        )
    if " is missing unit test:" in problem:
        return _module_fix(
            module_name,
            "Restore the generated unit test or clean detached test remnants.",
        )
    if problem.startswith("Could not parse Python file for lifecycle checks"):
        return "Fix the Python syntax error before rerunning polepos check."
    if problem.startswith("Orphan module"):
        orphan_name = _extract_orphan_module_name(problem)
        if orphan_name is not None:
            return (
                f"Run `polepos remove module {orphan_name}` to clean generated "
                "remnants, or restore the missing module directory."
            )
        return (
            "Clean generated remnants or restore the missing module directory."
        )
    if (
        problem.startswith("Integration ")
        and " is missing generated file:" in problem
    ):
        return _integration_fix(
            integration_name,
            "Restore the generated integration file or remove the integration "
            "completely.",
        )
    if (
        problem.startswith("Integration ")
        and " is missing dependency " in problem
    ):
        return _integration_fix(
            integration_name,
            "Restore the dependency in pyproject.toml or remove the "
            "integration "
            "scaffold.",
        )
    if problem.startswith("Integration ") and " is missing setting " in problem:
        return _integration_fix(
            integration_name,
            "Restore the generated settings.py value or remove the integration "
            "scaffold.",
        )
    if (
        problem.startswith("Integration ")
        and " is missing env value " in problem
    ):
        return _integration_fix(
            integration_name,
            "Restore the .env.example value or remove the integration "
            "scaffold.",
        )

    return (
        "Review the reported drift and restore the PolePosition-managed "
        "contract."
    )


def _extract_lifecycle_module_name(problem: str) -> str | None:
    match = re.search(r"Lifecycle module '([^']+)'", problem)
    return match.group(1) if match else None


def _extract_integration_name(problem: str) -> str | None:
    match = re.search(r"Integration '([^']+)'", problem)
    return match.group(1) if match else None


def _extract_orphan_module_name(problem: str) -> str | None:
    match = re.search(r"missing module '([^']+)'", problem)
    return match.group(1) if match else None


def _module_fix(module_name: str | None, message: str) -> str:
    if module_name is None:
        return message
    return (
        f"{message} If '{module_name}' was intentionally detached, run "
        f"`polepos remove module {module_name} --wiring-only`; if it was "
        f"already "
        "detached, move, delete, or rewire the module directory."
    )


def _integration_fix(integration_name: str | None, message: str) -> str:
    if integration_name is None:
        return message
    return (
        f"{message} Re-run `polepos add integration {integration_name}` only "
        "after cleanup."
    )
