# Contributing to PolePosition

Contributions are welcome — open an
[issue](https://github.com/erenertemden/poleposition/issues) or a
[pull request](https://github.com/erenertemden/poleposition/pulls).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -e .           # installs the polepos / poleposition CLIs
python -m pip install pytest ruff    # test runner + linter/formatter
```

Before opening a pull request:

```bash
python -m pytest                     # tests pass
ruff check pole_position polepos     # lint clean
ruff format pole_position polepos    # format clean
```

- **Code style:** [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html),
  enforced with Ruff (the `CI` workflow gates every PR).
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/),
  e.g. `fix(add): require integration managed markers before patching`.

## Full guide

The complete contributor guide — dev setup, opt-in end-to-end tests, project
layout, common tasks, and the pull-request checklist — lives in the docs:

**https://erenertemden.github.io/poleposition/contributing**
(source: [`docs/contributing.md`](docs/contributing.md))

For maintainer-level conventions, see
[`AGENTS.md`](AGENTS.md) and [`docs/architecture.md`](docs/architecture.md).
