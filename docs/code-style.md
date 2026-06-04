# Code Style

PolePosition's Python code follows the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).
The conventions in that guide — naming, imports, layout, and exception
handling — are the source of truth for how code in this repository is written.

The style is **enforced automatically** with [Ruff](https://docs.astral.sh/ruff/)
(linter and formatter), so contributors do not need to apply it by hand. The
configuration lives in [`pyproject.toml`](https://github.com/erenertemden/poleposition/blob/main/pyproject.toml)
under `[tool.ruff]`.

## What is enforced

| Area | Setting | Google guide reference |
|---|---|---|
| Line length | 80 columns | [§3.2 Line length](https://google.github.io/styleguide/pyguide.html#32-line-length) |
| Indentation / layout | `ruff format` (4-space, no tabs) | [§3.4 Indentation](https://google.github.io/styleguide/pyguide.html#34-indentation) |
| Imports | sorted, grouped stdlib / third-party / first-party (`I`) | [§3.1 Imports formatting](https://google.github.io/styleguide/pyguide.html#313-imports-formatting) |
| Naming | `pep8-naming` (`N`) | [§3.16 Naming](https://google.github.io/styleguide/pyguide.html#316-naming) |
| Exception chaining | `raise ... from err` / `from None` (`B904`) | [§2.4 Exceptions](https://google.github.io/styleguide/pyguide.html#24-exceptions) |
| Modern idioms | `pyupgrade` (`UP`), comprehensions (`C4`) | — |
| Correctness | `pyflakes` (`F`), `pycodestyle` (`E`, `W`) | — |

The selected Ruff lint rule sets are `E`, `W`, `F`, `I`, `N`, `UP`, `B`, and
`C4`. Type annotations are used throughout the codebase (every function carries
a return annotation).

## Running it locally

```bash
# Report any style or lint violations
ruff check pole_position polepos

# Apply formatting (80-column layout, import sorting)
ruff format pole_position polepos

# Auto-fix the safe lint findings (imports, modern idioms, ...)
ruff check pole_position polepos --fix
```

## Continuous integration

The `CI` workflow runs a dedicated **Lint (Ruff / Google Python Style Guide)**
job that fails the build on any violation:

```bash
ruff check pole_position polepos
ruff format --check pole_position polepos
```

A pull request must pass this job to merge.

## Scope and exceptions

- **Generated project templates** under `pole_position/template/` are excluded
  from linting. They embed `{{placeholder}}` tokens and are not valid Python on
  disk; their style is validated through the end-to-end tests that generate and
  run real projects instead.
- A few inherently unsplittable lines (long URLs, long string content) may use a
  scoped `# noqa: E501`. These are the exception, not the rule.
- Docstrings are not yet required by the linter. Type hints already cover the
  public surface; adding Google-style docstrings (summary, `Args:`, `Returns:`,
  `Raises:`) to public APIs is a planned follow-up.
