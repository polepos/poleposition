import shutil
from dataclasses import dataclass
from pathlib import Path

MANIFEST_FILE_NAME = ".poleposition.toml"


@dataclass(frozen=True)
class DeletedProjectResult:
    name: str
    project_root: Path
    removed_paths: tuple[Path, ...]
    trace: bool = False


def resolve_project_to_delete(name: str, cwd: Path | None = None) -> Path:
    """Resolve and validate the project directory targeted for deletion.

    The target is the given name or path, relative to ``cwd`` when not
    absolute. Validation refuses anything that is missing, is not a directory,
    does not carry a PolePosition manifest, or is the current directory or one
    of its parents. Raises ``RuntimeError`` with a user-facing message when the
    target cannot be safely deleted.
    """
    base = (cwd or Path.cwd()).resolve()
    candidate = Path(name)
    target = candidate if candidate.is_absolute() else base / candidate
    target = target.resolve()

    if not target.exists():
        raise RuntimeError(f"No project directory found to delete: {target}")

    if not target.is_dir():
        raise RuntimeError(f"Refusing to delete a non-directory path: {target}")

    if not (target / MANIFEST_FILE_NAME).is_file():
        raise RuntimeError(
            f"{target} does not look like a PolePosition project "
            f"(no {MANIFEST_FILE_NAME}). Refusing to delete it. Remove the "
            "directory manually if you really intend to."
        )

    if base == target or base.is_relative_to(target):
        raise RuntimeError(
            f"Refusing to delete {target} because it is the current directory "
            "or a parent of it. Run `polepos delete` from outside the project "
            "directory."
        )

    return target


def delete_project(
    name: str,
    cwd: Path | None = None,
    *,
    trace: bool = False,
) -> DeletedProjectResult:
    """Delete a generated project directory after validating the target.

    With ``trace=True`` the target is validated and reported but nothing is
    removed.
    """
    target = resolve_project_to_delete(name, cwd)

    if not trace:
        shutil.rmtree(target)

    return DeletedProjectResult(
        name=name,
        project_root=target,
        removed_paths=(target,),
        trace=trace,
    )
