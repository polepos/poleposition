from pathlib import Path
import os
import subprocess
import sys
from unittest.mock import patch

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


def test_db_upgrade_defaults_to_head(tmp_path: Path):
    from pole_position.cli.commands.db.upgrade import run

    with patch("pole_position.cli.commands.db.upgrade.run_alembic_command") as mock_run:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run([])

    mock_run.assert_called_once_with("upgrade", ["head"])


def test_db_revision_requires_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    from pole_position.cli.commands.db.revision import run

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        with pytest.raises(SystemExit):
            run([])

    captured = capsys.readouterr()
    assert 'Usage: polepos db revision -m "<message>"' in captured.out


def test_db_revision_invokes_autogenerate(tmp_path: Path):
    from pole_position.cli.commands.db.revision import run

    with patch("pole_position.cli.commands.db.revision.run_alembic_command") as mock_run:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["-m", "create garage table"])

    mock_run.assert_called_once_with(
        "revision",
        ["--autogenerate", "-m", "create garage table"],
    )


def test_db_downgrade_requires_target(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    from pole_position.cli.commands.db.downgrade import run

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp_path)
        with pytest.raises(SystemExit):
            run([])

    captured = capsys.readouterr()
    assert "Usage: polepos db downgrade <target>" in captured.out


def test_db_upgrade_requires_poleposition_project(tmp_path: Path):
    result = run_cli(tmp_path, "db", "upgrade")

    assert result.returncode != 0
    assert "does not look like a PolePosition project" in result.stdout


def test_run_alembic_command_uses_project_root_from_nested_directory(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    nested_dir = tmp_path / "myapp" / "src" / "myapp" / "modules"

    from pole_position.cli.services.db_runner import run_alembic_command

    with patch("pole_position.cli.services.db_runner.shutil.which", return_value="/usr/bin/alembic"):
        with patch("pole_position.cli.services.db_runner.subprocess.run") as mock_run:
            run_alembic_command("upgrade", ["head"], cwd=nested_dir)

    mock_run.assert_called_once_with(
        ["alembic", "upgrade", "head"],
        cwd=tmp_path / "myapp",
        check=True,
    )
