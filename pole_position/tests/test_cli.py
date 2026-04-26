import subprocess
import sys


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pole_position.cli.main", *args],
        capture_output=True,
        text=True,
    )


def test_help_command():
    result = run_cli("help")
    assert result.returncode == 0
    assert "Usage" in result.stdout


def test_version_command():
    result = run_cli("version")
    assert result.returncode == 0


def test_unknown_command():
    result = run_cli("unknown")
    assert result.returncode != 0
    assert "Unknown command" in result.stdout