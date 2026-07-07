from pathlib import Path

from pole_position.cli.services.module_templates.detection import (
    detect_module_template_name,
)


def _make(module_root: Path, files: tuple[str, ...]) -> None:
    for relative in files:
        path = module_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


def _unit_test(tests_root: Path, name: str) -> None:
    path = tests_root / "unit" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_manifest_template_is_authoritative(tmp_path: Path) -> None:
    module_root = tmp_path / "src" / "app" / "modules" / "billing"
    _make(module_root, ("model.py", "repository.py"))

    name = detect_module_template_name(
        tests_root=tmp_path / "tests",
        module_root=module_root,
        module_name="billing",
        manifest_template_name="crud",
    )

    assert name == "crud"


def test_unit_test_beats_file_heuristic(tmp_path: Path) -> None:
    # Regression for the misdetection bug: an api module whose router.py
    # was deleted (so by files alone it looks like the db-backed `service`
    # template) must still be detected as api from its distinctive unit test,
    # not service.
    module_root = tmp_path / "src" / "app" / "modules" / "billing"
    _make(module_root, ("model.py", "repository.py"))  # no router.py
    _unit_test(tmp_path / "tests", "test_billing_service.py")

    name = detect_module_template_name(
        tests_root=tmp_path / "tests",
        module_root=module_root,
        module_name="billing",
    )

    assert name == "api"


def test_service_only_detected_from_its_unit_test(tmp_path: Path) -> None:
    module_root = tmp_path / "src" / "app" / "modules" / "notify"
    _make(module_root, ("model.py", "repository.py"))
    _unit_test(tmp_path / "tests", "test_notify_service_only.py")

    name = detect_module_template_name(
        tests_root=tmp_path / "tests",
        module_root=module_root,
        module_name="notify",
    )

    assert name == "service-only"


def test_router_absent_service_fallback_when_no_unit_test(
    tmp_path: Path,
) -> None:
    # With no unit test at all, the file heuristic applies: a db-backed module
    # (model + repository) with the router absent is the internal `service`
    # template.
    module_root = tmp_path / "src" / "app" / "modules" / "notify"
    _make(module_root, ("model.py", "repository.py"))  # no router.py, no test

    name = detect_module_template_name(
        tests_root=tmp_path / "tests",
        module_root=module_root,
        module_name="notify",
    )

    assert name == "service"


def test_api_router_present_fallback_when_no_unit_test(
    tmp_path: Path,
) -> None:
    module_root = tmp_path / "src" / "app" / "modules" / "billing"
    _make(module_root, ("model.py", "repository.py", "router.py"))

    name = detect_module_template_name(
        tests_root=tmp_path / "tests",
        module_root=module_root,
        module_name="billing",
    )

    assert name == "api"
