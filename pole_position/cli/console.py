"""Terminal output styling for the polepos CLI.

Stdlib-only (no runtime dependencies). Styling is applied only when stdout is
an interactive terminal, so piped output, CI, the test suite, and ``--json``
all receive the exact plain text they did before. Honors the ``NO_COLOR`` and
``FORCE_COLOR`` conventions.
"""

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


def _enable_windows_vt() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11; enable virtual terminal processing.
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


_enable_windows_vt()


def _use_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") is not None:
        return True
    stream = sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


def style(text: str, *codes: str) -> str:
    """Wrap ``text`` in ANSI codes when color is enabled, else return as-is."""
    if not codes or not _use_color():
        return text
    return f"{''.join(codes)}{text}{RESET}"


def _emit(message: str, *codes: str, glyph: str | None = None) -> None:
    if _use_color():
        prefix = f"{glyph} " if glyph else ""
        print(style(f"{prefix}{message}", *codes))
    else:
        print(message)


def success(message: str) -> None:
    """A completed action. Green with a check glyph on a terminal."""
    _emit(message, GREEN, glyph="✓")


def error(message: str) -> None:
    """A failure. Red with a cross glyph on a terminal. Stays on stdout."""
    _emit(message, RED, glyph="✗")


def warn(message: str) -> None:
    """A caution. Yellow with a bang glyph on a terminal."""
    _emit(message, YELLOW, glyph="!")


def info(message: str = "") -> None:
    """A plain line, unchanged whether or not color is enabled."""
    print(message)


def heading(text: str) -> None:
    """A section label such as ``Created`` or ``Next steps``. Bold."""
    print(style(text, BOLD))


def field(label: str, value: str) -> None:
    """A ``label: value`` line with a dim label on a terminal."""
    if _use_color():
        print(f"{style(f'{label}:', DIM)} {value}")
    else:
        print(f"{label}: {value}")


def item(text: str, *, indent: int = 2) -> None:
    """An indented list entry (e.g. a file path). Dim on a terminal."""
    print(style(f"{' ' * indent}{text}", DIM))


def step(text: str, *, indent: int = 2) -> None:
    """A next-step entry. Cyan with an arrow glyph on a terminal."""
    if _use_color():
        print(style(f"{' ' * indent}→ {text}", CYAN))
    else:
        print(f"{' ' * indent}{text}")
