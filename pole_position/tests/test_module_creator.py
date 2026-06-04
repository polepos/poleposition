from pathlib import Path

import pytest

from pole_position.cli.services.module_creator import (
    _insert_block_before_marker_or_anchor,
    _insert_line_before_marker,
    _insert_sorted_line_before_marker,
    _validate_add_module_preflight,
)
from pole_position.cli.services.module_templates import (
    ModuleTemplate,
    llm_env_block,
    llm_settings_block,
)


def test_insert_line_before_marker_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "router.py"
    path.write_text("# marker\n", encoding="utf-8")

    _insert_line_before_marker(
        path, "api_router.include_router(example_router)", "# marker"
    )
    _insert_line_before_marker(
        path, "api_router.include_router(example_router)", "# marker"
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "api_router.include_router(example_router)",
        "# marker",
    ]


def test_insert_sorted_line_before_marker_preserves_custom_prefix(
    tmp_path: Path,
) -> None:
    path = tmp_path / "router.py"
    path.write_text(
        "\n".join(
            [
                "from shop.modules.zebra.router import router as zebra_router",
                "# custom note",
                "from shop.modules.alpha.router import router as alpha_router",
                "# polepos:router-imports",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _insert_sorted_line_before_marker(
        path=path,
        line="from shop.modules.garage.router import router as garage_router",
        marker="# polepos:router-imports",
        match_prefix="from ",
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "# custom note",
        "from shop.modules.alpha.router import router as alpha_router",
        "from shop.modules.garage.router import router as garage_router",
        "from shop.modules.zebra.router import router as zebra_router",
        "# polepos:router-imports",
    ]


def test_insert_block_uses_marker_before_anchor(tmp_path: Path) -> None:
    path = tmp_path / "settings.py"
    path.write_text(
        "\n".join(
            [
                "class Settings:",
                "    # polepos:llm-settings",
                "    model_config = SettingsConfigDict(",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _insert_block_before_marker_or_anchor(
        path=path,
        block=['    llm_provider: str = "openai"'],
        marker="    # polepos:llm-settings",
        anchor="    model_config = SettingsConfigDict(",
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "class Settings:",
        '    llm_provider: str = "openai"',
        "",
        "    # polepos:llm-settings",
        "    model_config = SettingsConfigDict(",
    ]


def test_preflight_reports_existing_generated_test_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    module_root = package_root / "modules" / "garage"
    _write_required_preflight_files(project_root, package_root)
    existing_test = project_root / "tests" / "integration" / "test_garage.py"
    existing_test.parent.mkdir(parents=True, exist_ok=True)
    existing_test.write_text("# custom test\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        _validate_add_module_preflight(
            project_root=project_root,
            package_root=package_root,
            modules_root=package_root / "modules",
            module_root=module_root,
            module_name="garage",
            template_spec=ModuleTemplate(
                files={},
                integration_test_name="test_garage.py",
                integration_test_content="",
                unit_test_name="test_garage_service.py",
                unit_test_content="",
            ),
        )

    assert "Generated file already exists" in str(exc_info.value)
    assert "test_garage.py" in str(exc_info.value)


def test_ai_preflight_allows_existing_llm_settings_without_markers(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    _write_required_preflight_files(project_root, package_root)
    (package_root / "settings.py").write_text(
        "\n".join(["class Settings:", *llm_settings_block()]) + "\n",
        encoding="utf-8",
    )
    (project_root / ".env.example").write_text(
        "\n".join(llm_env_block()) + "\n",
        encoding="utf-8",
    )

    _validate_add_module_preflight(
        project_root=project_root,
        package_root=package_root,
        modules_root=package_root / "modules",
        module_root=package_root / "modules" / "assistant",
        module_name="assistant",
        template_spec=ModuleTemplate(
            files={},
            integration_test_name="test_assistant.py",
            integration_test_content="",
            unit_test_name="test_assistant_orchestrator.py",
            unit_test_content="",
            update_db_models=False,
            ensure_llm_integrations=True,
            ensure_llm_settings=True,
        ),
    )


def test_ai_preflight_reports_partial_llm_settings_without_markers(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "shop-api"
    package_root = project_root / "src" / "shop_api"
    _write_required_preflight_files(project_root, package_root)
    (package_root / "settings.py").write_text(
        'class Settings:\n    llm_provider: str = "openai"\n',
        encoding="utf-8",
    )
    (project_root / ".env.example").write_text(
        "LLM_PROVIDER=openai\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        _validate_add_module_preflight(
            project_root=project_root,
            package_root=package_root,
            modules_root=package_root / "modules",
            module_root=package_root / "modules" / "assistant",
            module_name="assistant",
            template_spec=ModuleTemplate(
                files={},
                integration_test_name="test_assistant.py",
                integration_test_content="",
                unit_test_name="test_assistant_orchestrator.py",
                unit_test_content="",
                update_db_models=False,
                ensure_llm_integrations=True,
                ensure_llm_settings=True,
            ),
        )

    assert "Required managed marker" in str(exc_info.value)
    assert "polepos:llm-settings" in str(exc_info.value)
    assert "polepos:llm-env" in str(exc_info.value)


def _write_required_preflight_files(
    project_root: Path, package_root: Path
) -> None:
    _write_text(
        package_root / "modules" / "__init__.py",
        "    # polepos:module-exports\n",
    )
    _write_text(
        package_root / "api" / "router.py",
        "# polepos:router-imports\n# polepos:router-includes\n",
    )
    _write_text(
        package_root / "db" / "models.py",
        "    # polepos:model-imports\n",
    )
    _write_text(
        package_root / "settings.py",
        "    # polepos:llm-settings\n",
    )
    _write_text(
        project_root / ".env.example",
        "# polepos:llm-env\n",
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
