import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import run_cli

from pole_position.cli.commands import register_commands
from pole_position.cli.services.completion import (
    SUPPORTED_SHELLS,
    complete,
    completion_script,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


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

    assert "api" in candidates
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


# --- Regression tests for the 0.0.47 completion review fixes ---------------


def test_alias_completes_canonical_command_flags() -> None:
    # #5: `startproject` is an alias for `start`; COMMAND_HELP is keyed by the
    # canonical name, so the alias must resolve to it and keep its flags.
    assert complete(["startproject"]) == complete(["start"])
    assert "--db" in complete(["startproject"])


def test_value_flag_offered_only_when_declared_for_the_command() -> None:
    # #6: --template is not a flag of `check`, so its value must not complete.
    assert complete(["check", "--template"]) == []
    # ...but it still completes where it is valid.
    assert "api" in complete(["add", "module", "--template"])
    assert complete(["start", "--db"]) == ["sqlite", "postgres", "none"]


def test_filled_positional_slot_is_not_reoffered() -> None:
    # #7: after the single positional is supplied, do not re-offer it.
    assert complete(["completion"])[: len(SUPPORTED_SHELLS)] == list(
        SUPPORTED_SHELLS
    )
    filled = complete(["completion", "bash"])
    assert "bash" not in filled
    assert "zsh" not in filled


def test_add_integration_positional_not_reoffered_when_filled() -> None:
    # #7: same for `add integration <name>`.
    assert "redis" in complete(["add", "integration"])
    assert "redis" not in complete(["add", "integration", "redis"])


def test_zsh_script_runs_completer_for_fpath_autoload() -> None:
    # #4: when autoloaded from $fpath the script must invoke the completer so
    # the first Tab completes, not just register it via compdef.
    script = completion_script("zsh")
    assert 'if [ "$funcstack[1]" = "_polepos" ]; then' in script
    assert '_polepos "$@"' in script
    assert "compdef _polepos polepos poleposition" in script


def test_bash_script_guards_empty_array_under_set_u() -> None:
    # #8: an empty prior array must expand safely under `set -u`.
    script = completion_script("bash")
    assert '${prior[@]+"${prior[@]}"}' in script


@pytest.mark.skipif(
    __import__("shutil").which("bash") is None,
    reason="bash is required to exercise the completion under set -u.",
)
def test_bash_first_arg_completion_survives_set_u(tmp_path: Path) -> None:
    # #8: drive the generated function under `set -u` for the first argument
    # (empty prior array) and confirm it does not abort with 'unbound variable'.
    script_path = tmp_path / "polepos.bash"
    script_path.write_text(completion_script("bash"), encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "polepos"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'exec "{sys.executable}" -m pole_position.cli.main "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)

    driver = (
        "set -u\n"
        f'export PATH="{bin_dir}:$PATH"\n'
        f'export PYTHONPATH="{REPO_ROOT}"\n'
        f'source "{script_path}"\n'
        "COMP_WORDS=(polepos ''); COMP_CWORD=1; COMPREPLY=()\n"
        "_poleposition_complete\n"
        'printf "%s\\n" "${COMPREPLY[@]}"\n'
    )
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", driver],
        capture_output=True,
        text=True,
    )

    assert "unbound variable" not in result.stderr
    assert result.returncode == 0
    assert "start" in result.stdout
