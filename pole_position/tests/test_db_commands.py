import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import call, patch

import pytest

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


def test_db_command_shows_usage(tmp_path: Path):
    result = run_cli(tmp_path, "db")

    assert result.returncode == 0
    assert "Usage: polepos db <subcommand>" in result.stdout
    assert "upgrade" in result.stdout
    assert "revision" in result.stdout
    assert "downgrade" in result.stdout
    assert "status" in result.stdout


def test_db_help_shows_namespace_usage(tmp_path: Path):
    result = run_cli(tmp_path, "db", "--help")

    assert result.returncode == 0
    assert "Usage: polepos db <subcommand>" in result.stdout
    assert "Unknown command" not in result.stdout
    assert "upgrade" in result.stdout
    assert "revision" in result.stdout
    assert "downgrade" in result.stdout
    assert "status" in result.stdout


def test_db_upgrade_defaults_to_head(tmp_path: Path):
    from pole_position.cli.commands.db.upgrade import run

    with patch(
        "pole_position.cli.commands.db.upgrade.run_alembic_command"
    ) as mock_run:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run([])

    mock_run.assert_called_once_with("upgrade", ["head"])


def test_db_upgrade_help_shows_usage_without_project(tmp_path: Path):
    result = run_cli(tmp_path, "db", "upgrade", "--help")

    assert result.returncode == 0
    assert "Usage: polepos db upgrade [target]" in result.stdout


def test_db_upgrade_help_rejects_extra_argument(tmp_path: Path):
    result = run_cli(tmp_path, "db", "upgrade", "--help", "head")

    assert result.returncode != 0
    assert "Unexpected argument: head" in result.stdout
    assert "Usage: polepos db upgrade [target]" in result.stdout


def test_db_revision_requires_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    from pole_position.cli.commands.db.revision import run

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        with pytest.raises(SystemExit):
            run([])

    captured = capsys.readouterr()
    assert 'Usage: polepos db revision -m "<message>"' in captured.out


def test_db_revision_rejects_message_flag_without_value(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    from pole_position.cli.commands.db.revision import run

    with patch(
        "pole_position.cli.commands.db.revision.run_alembic_command"
    ) as mock_run:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            with pytest.raises(SystemExit):
                run(["--message", "--empty"])

    captured = capsys.readouterr()
    assert 'Usage: polepos db revision -m "<message>"' in captured.out
    mock_run.assert_not_called()


def test_db_revision_help_shows_usage_without_project(tmp_path: Path):
    result = run_cli(tmp_path, "db", "revision", "--help")

    assert result.returncode == 0
    assert 'Usage: polepos db revision -m "<message>"' in result.stdout


def test_db_revision_help_rejects_extra_argument(tmp_path: Path):
    result = run_cli(tmp_path, "db", "revision", "--help", "-m")

    assert result.returncode != 0
    assert "Unexpected argument: -m" in result.stdout
    assert 'Usage: polepos db revision -m "<message>"' in result.stdout


def test_db_revision_invokes_autogenerate(tmp_path: Path):
    from pole_position.cli.commands.db.revision import run

    with patch(
        "pole_position.cli.commands.db.revision.run_alembic_command"
    ) as mock_run:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["-m", "create garage table"])

    mock_run.assert_called_once_with(
        "revision",
        ["--autogenerate", "-m", "create garage table"],
    )


def test_db_downgrade_requires_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    from pole_position.cli.commands.db.downgrade import run

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        with pytest.raises(SystemExit):
            run([])

    captured = capsys.readouterr()
    assert "Usage: polepos db downgrade <target>" in captured.out


def test_db_downgrade_help_shows_usage_without_project(tmp_path: Path):
    result = run_cli(tmp_path, "db", "downgrade", "--help")

    assert result.returncode == 0
    assert "Usage: polepos db downgrade <target>" in result.stdout


def test_db_downgrade_help_rejects_extra_argument(tmp_path: Path):
    result = run_cli(tmp_path, "db", "downgrade", "--help", "-1")

    assert result.returncode != 0
    assert "Unexpected argument: -1" in result.stdout
    assert "Usage: polepos db downgrade <target>" in result.stdout


def test_db_status_invokes_current_and_heads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    from pole_position.cli.commands.db.status import run

    with patch(
        "pole_position.cli.commands.db.status.run_alembic_command"
    ) as mock_run:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run([])

    captured = capsys.readouterr()
    assert "Alembic current revision:" in captured.out
    assert "Alembic heads:" in captured.out
    assert mock_run.call_args_list == [call("current", []), call("heads", [])]


def test_db_status_help_shows_usage_without_project(tmp_path: Path):
    result = run_cli(tmp_path, "db", "status", "--help")

    assert result.returncode == 0
    assert "Usage: polepos db status" in result.stdout


def test_db_status_rejects_extra_argument(tmp_path: Path):
    result = run_cli(tmp_path, "db", "status", "head")

    assert result.returncode != 0
    assert "Unexpected argument: head" in result.stdout
    assert "Usage: polepos db status" in result.stdout


def test_db_upgrade_requires_poleposition_project(tmp_path: Path):
    result = run_cli(tmp_path, "db", "upgrade")

    assert result.returncode != 0
    assert "does not look like a PolePosition project" in result.stdout


def test_run_alembic_command_uses_project_root_from_nested_directory(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    nested_dir = tmp_path / "myapp" / "src" / "myapp" / "modules"

    from pole_position.cli.services.db_runner import run_alembic_command

    with patch(
        "pole_position.cli.services.db_runner.shutil.which",
        return_value="/usr/bin/uv",
    ):
        with patch(
            "pole_position.cli.services.db_runner.subprocess.run"
        ) as mock_run:
            run_alembic_command("upgrade", ["head"], cwd=nested_dir)

    mock_run.assert_called_once_with(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=tmp_path / "myapp",
        check=True,
    )


def test_run_alembic_command_falls_back_to_active_virtualenv_python(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    active_venv = tmp_path / ".active-venv"
    active_python = active_venv / "bin" / "python"
    active_python.parent.mkdir(parents=True)
    active_python.write_text("", encoding="utf-8")

    from pole_position.cli.services.db_runner import run_alembic_command

    with patch(
        "pole_position.cli.services.db_runner.shutil.which", return_value=None
    ):
        with patch.dict(os.environ, {"VIRTUAL_ENV": str(active_venv)}):
            with patch(
                "pole_position.cli.services.db_runner.subprocess.run"
            ) as mock_run:
                run_alembic_command("upgrade", ["head"], cwd=tmp_path / "myapp")

    mock_run.assert_called_once_with(
        [str(active_python), "-m", "alembic", "upgrade", "head"],
        cwd=tmp_path / "myapp",
        check=True,
    )


def test_run_alembic_command_falls_back_to_project_venv_python(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    project_python = project_root / ".venv" / "bin" / "python"
    project_python.parent.mkdir(parents=True)
    project_python.write_text("", encoding="utf-8")

    from pole_position.cli.services.db_runner import run_alembic_command

    with patch(
        "pole_position.cli.services.db_runner.shutil.which", return_value=None
    ):
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "pole_position.cli.services.db_runner.subprocess.run"
            ) as mock_run:
                run_alembic_command(
                    "revision",
                    ["--autogenerate", "-m", "add cars"],
                    cwd=project_root,
                )

    mock_run.assert_called_once_with(
        [
            str(project_python),
            "-m",
            "alembic",
            "revision",
            "--autogenerate",
            "-m",
            "add cars",
        ],
        cwd=project_root,
        check=True,
    )


def test_run_alembic_command_falls_back_to_path_python(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    from pole_position.cli.services.db_runner import run_alembic_command

    def fake_which(command: str) -> str | None:
        if command == "python":
            return "/usr/bin/python"
        return None

    with patch(
        "pole_position.cli.services.db_runner.shutil.which",
        side_effect=fake_which,
    ):
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "pole_position.cli.services.db_runner.subprocess.run"
            ) as mock_run:
                run_alembic_command("downgrade", ["-1"], cwd=tmp_path / "myapp")

    mock_run.assert_called_once_with(
        ["/usr/bin/python", "-m", "alembic", "downgrade", "-1"],
        cwd=tmp_path / "myapp",
        check=True,
    )
