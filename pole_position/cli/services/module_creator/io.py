from pathlib import Path


def _read_managed_lines(path: Path) -> list[str]:
    """Read a managed file's lines, raising a clear error on non-UTF-8 bytes.

    Used by the insert helpers that mutate managed files during `add module`.
    """
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        ) from exc
