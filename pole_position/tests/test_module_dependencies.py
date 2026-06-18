from pathlib import Path

from pole_position.cli.services.project_checker import (
    _check_module_dependencies,
    describe_project_check_issue,
)

PACKAGE = "app"


def _make_module(
    modules_root: Path, name: str, imports: tuple[str, ...] = ()
) -> None:
    module_root = modules_root / name
    module_root.mkdir(parents=True)
    (module_root / "__init__.py").write_text("", encoding="utf-8")
    lines = [
        f"from {PACKAGE}.modules.{target} import service" for target in imports
    ]
    (module_root / "service.py").write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )


def _package_root(tmp_path: Path) -> Path:
    return tmp_path / PACKAGE


def _check(tmp_path: Path) -> list[str]:
    problems: list[str] = []
    _check_module_dependencies(problems, _package_root(tmp_path))
    return problems


def test_three_node_cycle_is_reported(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "a", ("b",))
    _make_module(modules, "b", ("c",))
    _make_module(modules, "c", ("a",))

    assert _check(tmp_path) == [
        "Circular module dependency detected: a -> b -> c -> a"
    ]


def test_acyclic_chain_is_clean(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "a", ("b",))
    _make_module(modules, "b", ("c",))
    _make_module(modules, "c", ())

    assert _check(tmp_path) == []


def test_two_node_cycle_is_reported(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "billing", ("customers",))
    _make_module(modules, "customers", ("billing",))

    assert _check(tmp_path) == [
        "Circular module dependency detected: billing -> customers -> billing"
    ]


def test_self_import_is_not_a_cycle(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "a", ("a",))
    _make_module(modules, "b", ())

    assert _check(tmp_path) == []


def test_imports_to_non_modules_are_ignored(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "a", ())
    _make_module(modules, "b", ())
    # Reference shared infrastructure and a third-party package, not modules.
    (modules / "a" / "service.py").write_text(
        f"from {PACKAGE}.db import session\nimport os\n",
        encoding="utf-8",
    )

    assert _check(tmp_path) == []


def test_independent_cycles_are_each_reported_and_deduped(
    tmp_path: Path,
) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "a", ("b",))
    _make_module(modules, "b", ("a",))
    _make_module(modules, "x", ("y",))
    _make_module(modules, "y", ("x",))

    assert _check(tmp_path) == [
        "Circular module dependency detected: a -> b -> a",
        "Circular module dependency detected: x -> y -> x",
    ]


def test_fewer_than_two_modules_is_a_noop(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "only", ())

    assert _check(tmp_path) == []


def test_missing_modules_dir_is_a_noop(tmp_path: Path) -> None:
    # package root exists but has no modules/ directory.
    _package_root(tmp_path).mkdir()
    assert _check(tmp_path) == []


def test_submodule_dotted_import_resolves_to_module(tmp_path: Path) -> None:
    modules = _package_root(tmp_path) / "modules"
    _make_module(modules, "a", ())
    _make_module(modules, "b", ())
    # a deep import path still maps to the top-level module name.
    (modules / "a" / "service.py").write_text(
        f"from {PACKAGE}.modules.b.repository.queries import run\n",
        encoding="utf-8",
    )
    (modules / "b" / "service.py").write_text(
        f"from {PACKAGE}.modules.a import service\n",
        encoding="utf-8",
    )

    assert _check(tmp_path) == [
        "Circular module dependency detected: a -> b -> a"
    ]


def test_cycle_problem_maps_to_ppchk060() -> None:
    issue = describe_project_check_issue(
        "Circular module dependency detected: a -> b -> a"
    )
    assert issue.code == "PPCHK060"
    assert "DAG" in issue.remediation
