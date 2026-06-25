import os
import subprocess
import sys
from pathlib import Path

import pytest

from pole_position.cli.commands import register_commands
from pole_position.cli.services.completion import (
    SUPPORTED_SHELLS,
    complete,
    completion_script,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(cwd, *args):
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(REPO_ROOT)
    )

    return subprocess.run(
        [sys.executable, "-m", "pole_position.cli.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture(autouse=True)
def _commands_registered() -> None:
    register_commands()


# --- complete() candidate logic -------------------------------------------


def test_top_level_lists_user_commands_and_hides_internal() -> None:
    candidates = complete([])

    for expected in ("start", "add", "remove", "check", "db", "completion"):
        assert expected in candidates
    # The hidden completion backend must never be suggested.
    assert "__complete" not in candidates


def test_add_completes_subcommands() -> None:
    candidates = complete(["add"])

    assert set(candidates) >= {"auth", "integration", "module"}
    assert "__complete" not in candidates


def test_add_module_completes_flags() -> None:
    candidates = complete(["add", "module"])

    assert "--template" in candidates
    assert "--api-only" in candidates
    assert "--help" in candidates


def test_template_flag_completes_template_values() -> None:
    candidates = complete(["add", "module", "--template"])

    assert "standard" in candidates
    assert "crud" in candidates
    # No flags are offered while completing a flag's value.
    assert "--api-only" not in candidates


def test_db_flag_completes_database_values() -> None:
    assert complete(["start", "--db"]) == ["sqlite", "postgres", "none"]


def test_add_integration_completes_integration_names() -> None:
    candidates = complete(["add", "integration"])

    assert "kafka" in candidates
    assert "redis" in candidates


def test_db_completes_subcommands() -> None:
    candidates = complete(["db"])

    assert set(candidates) >= {"status", "upgrade", "revision", "downgrade"}


def test_db_revision_completes_message_flag() -> None:
    candidates = complete(["db", "revision"])

    assert "-m" in candidates
    assert "--message" in candidates


def test_message_flag_value_offers_nothing() -> None:
    assert complete(["db", "revision", "-m"]) == []


def test_completion_completes_supported_shells() -> None:
    candidates = complete(["completion"])

    assert set(SUPPORTED_SHELLS) <= set(candidates)
    assert candidates[: len(SUPPORTED_SHELLS)] == list(SUPPORTED_SHELLS)


def test_remove_module_outside_project_has_no_module_names() -> None:
    candidates = complete(["remove", "module"], cwd=Path(os.devnull).parent)

    # Only flags are offered when there is no project to read modules from.
    assert all(candidate.startswith("-") for candidate in candidates)


def test_unknown_command_yields_no_candidates() -> None:
    assert complete(["nonsense"]) == []


# --- completion_script() ---------------------------------------------------


def test_completion_script_markers() -> None:
    assert "complete -F _poleposition_complete" in completion_script("bash")
    assert "#compdef polepos" in completion_script("zsh")
    assert "complete -c polepos" in completion_script("fish")


def test_completion_script_rejects_unknown_shell() -> None:
    with pytest.raises(ValueError) as exc_info:
        completion_script("powershell")

    assert "Unsupported shell 'powershell'" in str(exc_info.value)
    assert "bash, zsh, fish" in str(exc_info.value)


# --- CLI surface -----------------------------------------------------------


def test_cli_completion_prints_bash_script(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "completion", "bash")

    assert result.returncode == 0
    assert "complete -F _poleposition_complete polepos poleposition" in (
        result.stdout
    )


def test_cli_completion_rejects_unknown_shell(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "completion", "powershell")

    assert result.returncode != 0
    assert "Unsupported shell 'powershell'" in result.stdout


def test_cli_completion_without_shell_prints_help(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "completion")

    assert result.returncode == 0
    assert "completion" in result.stdout


def test_cli_complete_backend_lists_commands(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "__complete", "add")

    assert result.returncode == 0
    lines = result.stdout.split()
    assert "module" in lines


def test_cli_complete_module_names_in_project(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    assert run_cli(project_root, "add", "module", "garage").returncode == 0
    assert run_cli(project_root, "add", "module", "billing").returncode == 0

    result = run_cli(project_root, "__complete", "remove", "module")

    assert result.returncode == 0
    candidates = result.stdout.split()
    assert "garage" in candidates
    assert "billing" in candidates
    # The starter module cannot be removed and must not be suggested.
    assert "status" not in candidates


def test_internal_backend_is_not_listed_in_help(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "help")

    assert result.returncode == 0
    assert "completion" in result.stdout
    assert "__complete" not in result.stdout


@pytest.mark.skipif(
    __import__("shutil").which("bash") is None,
    reason="bash is required to syntax-check the generated bash completion.",
)
def test_generated_bash_script_is_syntactically_valid(tmp_path: Path) -> None:
    script = run_cli(tmp_path, "completion", "bash").stdout
    script_path = tmp_path / "polepos.bash"
    script_path.write_text(script, encoding="utf-8")

    check = subprocess.run(
        ["bash", "-n", str(script_path)],
        capture_output=True,
        text=True,
    )

    assert check.returncode == 0, check.stderr
