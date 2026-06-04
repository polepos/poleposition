import re
from collections.abc import Iterable
from dataclasses import dataclass

try:
    from packaging.version import InvalidVersion, Version
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    InvalidVersion = ValueError  # type: ignore[assignment]
    Version = None  # type: ignore[assignment]


DEPENDENCY_NAME_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
)
DEPENDENCY_EXTRAS_PATTERN = re.compile(
    r"^\s*[A-Za-z0-9][A-Za-z0-9._-]*(?:\[(?P<extras>[^\]]*)\])?"
)
DEPENDENCY_SPECIFIER_PATTERN = re.compile(
    r"(?P<operator>~=|===|==|!=|<=|>=|<|>)\s*(?P<version>[^,;\s]+)"
)
DEPENDENCY_ENTRY_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?P<quote>[\"'])(?P<value>.+?)(?P=quote)"
    r"(?P<trailing>\s*,?\s*(?:#.*)?)$"
)
QUOTED_DEPENDENCY_PATTERN = re.compile(
    r"""(?P<quote>["'])(?P<dependency>.+?)(?P=quote)"""
)


@dataclass(frozen=True)
class DependencyEntry:
    indent: str
    quote: str
    value: str
    trailing: str


def dependency_contract_satisfied(
    dependencies: Iterable[str],
    required_dependency: str,
) -> bool:
    required_name = _dependency_name(required_dependency)
    required_extras = _dependency_extras(required_dependency)
    required_min_version = _dependency_min_version(required_dependency)
    if required_name is None:
        return False

    for dependency in dependencies:
        if _dependency_name(dependency) != required_name:
            continue
        if not required_extras.issubset(_dependency_extras(dependency)):
            continue
        if required_min_version is None:
            return True

        dependency_min_version = _dependency_min_version(dependency)
        if dependency_min_version is None:
            continue
        if _version_at_least(dependency_min_version, required_min_version):
            return True

    return False


def dependency_names_match(dependency: str, other_dependency: str) -> bool:
    dependency_name = _dependency_name(dependency)
    return dependency_name is not None and dependency_name == _dependency_name(
        other_dependency
    )


def parse_dependency_entry(line: str) -> DependencyEntry | None:
    match = DEPENDENCY_ENTRY_PATTERN.match(line)
    if match is None:
        return None

    return DependencyEntry(
        indent=match.group("indent"),
        quote=match.group("quote"),
        value=match.group("value"),
        trailing=match.group("trailing"),
    )


def quoted_dependency_values(text: str) -> tuple[str, ...]:
    return tuple(
        match.group("dependency")
        for match in QUOTED_DEPENDENCY_PATTERN.finditer(text)
    )


def _dependency_name(dependency: str) -> str | None:
    match = DEPENDENCY_NAME_PATTERN.match(dependency.split(";", 1)[0])
    if match is None:
        return None
    return _normalize_dependency_name(match.group("name"))


def _dependency_extras(dependency: str) -> frozenset[str]:
    match = DEPENDENCY_EXTRAS_PATTERN.match(dependency.split(";", 1)[0])
    if match is None:
        return frozenset()

    extras = match.group("extras")
    if not extras:
        return frozenset()

    return frozenset(
        _normalize_dependency_name(extra.strip())
        for extra in extras.split(",")
        if extra.strip()
    )


def _normalize_dependency_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _dependency_min_version(dependency: str) -> str | None:
    lower_bounds: list[str] = []
    dependency_spec = dependency.split(";", 1)[0]
    for match in DEPENDENCY_SPECIFIER_PATTERN.finditer(dependency_spec):
        operator = match.group("operator")
        if operator not in {">=", ">", "==", "===", "~="}:
            continue
        lower_bounds.append(match.group("version"))

    if not lower_bounds:
        return None

    return max(lower_bounds, key=_version_sort_key)


def _version_at_least(version: str, required_version: str) -> bool:
    if Version is not None:
        try:
            return Version(version) >= Version(required_version)
        except InvalidVersion:
            pass

    return _version_sort_key(version) >= _version_sort_key(required_version)


def _version_sort_key(version: str) -> tuple[int, ...]:
    parts = [int(part) for part in re.findall(r"\d+", version)]
    return tuple(parts)
