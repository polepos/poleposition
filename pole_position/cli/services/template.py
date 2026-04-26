import shutil
from pathlib import Path


def copy_template(project_name: str, target_path: Path) -> None:
    template_dir = Path(__file__).resolve().parents[2] / "template"
    shutil.copytree(
        template_dir,
        target_path,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
