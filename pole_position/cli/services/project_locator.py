from pathlib import Path


def find_project_root(start_path: Path | None = None) -> Path:
    current = (start_path or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        if _find_package_root_in(candidate) is not None:
            return candidate

    raise RuntimeError("Current directory does not look like a PolePosition project.")


def find_package_root(start_path: Path | None = None) -> Path:
    project_root = find_project_root(start_path)
    package_root = _find_package_root_in(project_root)

    if package_root is None:
        raise RuntimeError("Could not determine the application package under src/.")

    return package_root


def _find_package_root_in(project_root: Path) -> Path | None:
    src_root = project_root / "src"
    if not src_root.exists():
        return None

    candidates = [
        path
        for path in src_root.iterdir()
        if path.is_dir() and (path / "api" / "router.py").exists() and (path / "modules").exists()
    ]

    if len(candidates) != 1:
        return None

    return candidates[0]
