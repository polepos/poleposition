import os
import subprocess
import sys
from pathlib import Path

import pytest

from pole_position.cli.command import Command
from pole_position.cli.registry import CommandRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args, cwd: Path | None = None):
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


def test_help_command():
    result = run_cli("help")
    assert result.returncode == 0
    assert "project lifecycle CLI" in result.stdout
    assert "Usage" in result.stdout
    assert "Usage and Commands" in result.stdout
    assert "check" in result.stdout
    assert "remove" in result.stdout
    assert "upgrade" in result.stdout


def test_help_command_accepts_command_topic():
    result = run_cli("help", "add", "module")

    assert result.returncode == 0
    assert "Usage: polepos add module <module_name>" in result.stdout
    assert "--template <template_name>" in result.stdout
    assert "polepos add module assistant --template ai-prompt" in result.stdout


def test_help_command_rejects_unknown_topic():
    result = run_cli("help", "missing")

    assert result.returncode != 0
    assert "Unknown help topic: missing" in result.stdout
    assert "Run `polepos help` for available commands." in result.stdout


def test_version_command():
    result = run_cli("version")
    assert result.returncode == 0


def test_version_help_shows_usage():
    result = run_cli("version", "--help")
    assert result.returncode == 0
    assert "Usage: polepos version" in result.stdout


def test_version_rejects_extra_argument():
    result = run_cli("version", "extra")
    assert result.returncode != 0
    assert "Unexpected argument: extra" in result.stdout
    assert "Usage: polepos version" in result.stdout


def test_upgrade_help_shows_usage():
    result = run_cli("upgrade", "--help")

    assert result.returncode == 0
    assert "Usage: polepos upgrade" in result.stdout


def test_upgrade_requires_poleposition_project(tmp_path: Path):
    result = run_cli("upgrade", cwd=tmp_path)

    assert result.returncode != 0
    assert "does not look like a PolePosition project" in result.stdout


def test_upgrade_reports_project_readiness(tmp_path: Path):
    create_result = run_cli("start", "myapp", cwd=tmp_path)
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        "add",
        "module",
        "customers",
        "--template",
        "crud",
        cwd=project_root,
    )
    integration_result = run_cli("add", "integration", "rq", cwd=project_root)
    assert add_result.returncode == 0
    assert integration_result.returncode == 0

    result = run_cli("upgrade", cwd=project_root)

    assert result.returncode == 0
    assert "PolePosition upgrade report" in result.stdout
    assert "CLI version:" in result.stdout
    assert f"Project root: {project_root}" in result.stdout
    assert "Package: myapp" in result.stdout
    assert "Project check: passed" in result.stdout
    assert "customers: crud" in result.stdout
    assert "rq" in result.stdout
    assert "polepos check --fix" in result.stdout


def test_unknown_command():
    result = run_cli("unknown")
    assert result.returncode != 0
    assert "Unknown command" in result.stdout


def test_command_registry_allows_idempotent_registration():
    registry = CommandRegistry()
    command = Command(
        name="example",
        aliases=("sample",),
        handler=lambda args: None,
        description="Example command",
    )

    registry.register(command)
    registry.register(command)

    assert registry.get("example") is command
    assert registry.get("sample") is command
    assert registry.all() == [command]


def test_command_registry_rejects_conflicting_registration():
    registry = CommandRegistry()
    command = Command(
        name="example",
        handler=lambda args: None,
        description="Example command",
    )
    conflicting_command = Command(
        name="example",
        handler=lambda args: None,
        description="Conflicting command",
    )

    registry.register(command)

    with pytest.raises(
        RuntimeError, match="Command already registered: example"
    ):
        registry.register(conflicting_command)
