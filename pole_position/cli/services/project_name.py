import keyword
import re


def normalize_package_name(project_name: str) -> str:
    normalized = project_name.strip().lower()
    normalized = normalized.replace("-", "_")
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized


def validate_project_name(project_name: str) -> None:
    raw_name = project_name.strip()

    if not raw_name:
        raise ValueError("Project name cannot be empty.")

    if any(char.isspace() for char in raw_name):
        raise ValueError("Project name cannot contain whitespace.")

    package_name = normalize_package_name(raw_name)

    if not package_name:
        raise ValueError(
            "Project name must contain at least one valid character."
        )

    if not package_name.isidentifier():
        raise ValueError(
            f"Invalid project name '{project_name}'. "
            f"Derived package name '{package_name}' is not a valid Python identifier."
        )

    if keyword.iskeyword(package_name):
        raise ValueError(
            f"Invalid project name '{project_name}'. "
            f"Derived package name '{package_name}' is a reserved Python keyword."
        )
