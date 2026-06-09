#!/usr/bin/env python3
"""Guard a release against version/tag drift.

The Release workflow runs this before building and publishing, so a release
whose git tag, ``pyproject.toml`` version, and ``CHANGELOG.md`` entry disagree
can never reach PyPI.

Usage:
    python .github/scripts/check_release_version.py <release-tag>

The tag may be given with or without a leading ``v`` (tags are ``v0.0.41``).
"""

import sys
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]


def pyproject_version() -> str:
    data = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    return data["project"]["version"]


def changelog_has_version(version: str) -> bool:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for line in changelog.splitlines():
        if line.split()[:2] == ["##", version]:
            return True
    return False


def collect_problems(tag: str) -> list[str]:
    tag_version = tag[1:] if tag.startswith("v") else tag
    project_version = pyproject_version()

    problems: list[str] = []
    if tag_version != project_version:
        problems.append(
            f"Release tag '{tag}' (version '{tag_version}') does not match "
            f"pyproject.toml version '{project_version}'."
        )
    if not changelog_has_version(project_version):
        problems.append(
            f"CHANGELOG.md has no '## {project_version}' entry for the "
            "released version."
        )
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0]:
        print("usage: check_release_version.py <release-tag>", file=sys.stderr)
        return 2

    tag = argv[0]
    problems = collect_problems(tag)
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        return 1

    print(
        f"Release version check passed: tag {tag} matches "
        f"pyproject {pyproject_version()} with a CHANGELOG entry."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
