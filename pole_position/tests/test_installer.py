from pathlib import Path
from unittest.mock import Mock, patch

from pole_position.cli.services.installer import install_project_dependencies


def test_install_project_dependencies_prefers_uv(tmp_path: Path) -> None:
    with patch(
        "pole_position.cli.services.installer.shutil.which",
        return_value="/usr/bin/uv",
    ):
        with patch(
            "pole_position.cli.services.installer.subprocess.run"
        ) as mock_run:
            installer = install_project_dependencies(tmp_path)

    assert installer == "uv"
    mock_run.assert_called_once_with(
        ["uv", "sync", "--extra", "dev"],
        cwd=tmp_path,
        check=True,
    )


def test_install_project_dependencies_falls_back_to_pip_venv(
    tmp_path: Path,
) -> None:
    builder = Mock()

    def create_venv(venv_path: Path) -> None:
        python = venv_path / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text("", encoding="utf-8")

    builder.create.side_effect = create_venv

    with patch(
        "pole_position.cli.services.installer.shutil.which", return_value=None
    ):
        with patch(
            "pole_position.cli.services.installer.venv.EnvBuilder",
            return_value=builder,
        ):
            with patch(
                "pole_position.cli.services.installer.subprocess.run"
            ) as mock_run:
                installer = install_project_dependencies(tmp_path)

    python = tmp_path / ".venv" / "bin" / "python"
    assert installer == "pip"
    builder.create.assert_called_once_with(tmp_path / ".venv")
    mock_run.assert_called_once_with(
        [str(python), "-m", "pip", "install", "-e", ".[dev]"],
        cwd=tmp_path,
        check=True,
    )
