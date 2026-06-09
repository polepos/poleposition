from itertools import combinations

import pytest

from pole_position.cli.services.module_templates import (
    CRUD_FEATURE_NAMES,
    SUPPORTED_MODULE_TEMPLATES,
    CrudFeatureSet,
    build_module_template,
    get_module_template_contract,
    llm_env_block,
    llm_integration_files,
    llm_settings_block,
)
from pole_position.cli.services.module_templates.naming import to_class_name
from pole_position.cli.services.module_templates.renderer import render_template


def test_supported_module_templates_are_stable() -> None:
    assert SUPPORTED_MODULE_TEMPLATES == (
        "standard",
        "crud",
        "ai-prompt",
        "api-only",
    )


def test_to_class_name_normalizes_module_names() -> None:
    assert to_class_name("garage") == "Garage"
    assert to_class_name("race_results") == "RaceResults"


def test_render_template_replaces_context_values() -> None:
    rendered = render_template(
        "standard/model.py.tpl",
        {
            "package_name": "shop_api",
            "module_name": "customers",
            "class_name": "Customers",
        },
    )

    assert "from shop_api.db.base import Base" in rendered
    assert "class Customers(Base):" in rendered
    assert '__tablename__ = "customers"' in rendered
    assert "{{" not in rendered
    assert "}}" not in rendered


def test_standard_template_contract() -> None:
    contract = get_module_template_contract("standard")
    template = build_module_template(
        template="standard",
        package_name="shop_api",
        module_name="customers",
    )

    assert set(template.files) == set(contract.file_names_for("customers"))
    assert template.integration_test_name == contract.integration_test_name(
        "customers"
    )
    assert template.unit_test_name == contract.unit_test_name("customers")
    assert template.update_db_models is contract.update_db_models
    assert template.ensure_llm_integrations is contract.ensure_llm_integrations
    assert template.ensure_llm_settings is contract.ensure_llm_settings
    assert '"services"' in template.files["__init__.py"]
    assert '"service"' not in template.files["__init__.py"]
    service_content = template.files["services/customers_service.py"]
    assert (
        "from shop_api.bootstrap.logging import get_logger" in service_content
    )
    assert 'extra={"item_name": payload.name}' in service_content
    assert 'extra={"name": payload.name}' not in service_content
    assert (
        'client.post("/api/v1/customers/"' in template.integration_test_content
    )


def test_crud_template_contract() -> None:
    contract = get_module_template_contract("crud")
    template = build_module_template(
        template="crud",
        package_name="shop_api",
        module_name="customers",
    )

    assert set(template.files) == set(contract.file_names_for("customers"))
    assert template.integration_test_name == contract.integration_test_name(
        "customers"
    )
    assert template.unit_test_name == contract.unit_test_name("customers")
    assert template.update_db_models is contract.update_db_models
    assert "services/customers_crud_service.py" in template.files
    assert (
        "def get_customers"
        in template.files["services/customers_crud_service.py"]
    )
    assert "def update(self" in template.files["repository.py"]
    assert "@router.delete" in template.files["router.py"]
    assert "client.patch(" in template.integration_test_content


def test_crud_template_supports_enterprise_feature_options() -> None:
    template = build_module_template(
        template="crud",
        package_name="shop_api",
        module_name="customers",
        crud_features=CrudFeatureSet(
            pagination=True,
            timestamps=True,
            soft_delete=True,
            tenant_scoped=True,
            auth_required=True,
        ),
    )

    model_content = template.files["model.py"]
    router_content = template.files["router.py"]
    repository_content = template.files["repository.py"]
    schemas_content = template.files["schemas.py"]

    assert template.features == (
        "pagination",
        "timestamps",
        "soft-delete",
        "tenant-scoped",
        "auth-required",
    )
    assert "created_at: Mapped[datetime]" in model_content
    assert "deleted_at: Mapped[datetime | None]" in model_content
    assert "tenant_id: Mapped[str]" in model_content
    assert "CustomersPage" in schemas_content
    assert "limit: int = Query(default=100, ge=1, le=500)" in router_content
    assert (
        "APIRouter(dependencies=[Depends(get_current_user)])" in router_content
    )
    assert (
        "statement = statement.offset(offset).limit(limit)"
        in repository_content
    )
    assert "item.deleted_at = utc_now()" in repository_content
    assert "headers=_auth_headers()" in template.integration_test_content


def test_crud_feature_combinations_render_compileable_python() -> None:
    feature_names = list(CRUD_FEATURE_NAMES)
    feature_sets = [
        set(combination)
        for size in range(len(feature_names) + 1)
        for combination in combinations(feature_names, size)
    ]

    for feature_set in feature_sets:
        template = build_module_template(
            template="crud",
            package_name="shop_api",
            module_name="customers",
            crud_features=CrudFeatureSet.from_names(feature_set),
        )
        rendered_content = [
            *template.files.values(),
            template.integration_test_content,
            template.unit_test_content,
        ]

        assert all("{{" not in content for content in rendered_content)
        assert all("}}" not in content for content in rendered_content)
        for file_name, content in template.files.items():
            compile(content, file_name, "exec")
        compile(
            template.integration_test_content,
            template.integration_test_name,
            "exec",
        )
        compile(template.unit_test_content, template.unit_test_name, "exec")


def test_ai_prompt_template_contract() -> None:
    contract = get_module_template_contract("ai-prompt")
    template = build_module_template(
        template="ai-prompt",
        package_name="shop_api",
        module_name="assistant",
    )

    assert set(template.files) == set(contract.file_names_for("assistant"))
    assert template.integration_test_name == contract.integration_test_name(
        "assistant"
    )
    assert template.unit_test_name == contract.unit_test_name("assistant")
    assert template.update_db_models is contract.update_db_models
    assert template.ensure_llm_integrations is contract.ensure_llm_integrations
    assert template.ensure_llm_settings is contract.ensure_llm_settings
    assert '"services"' in template.files["__init__.py"]
    assert '"service"' not in template.files["__init__.py"]
    assert "get_llm_provider" in template.files["orchestrator.py"]
    assert '"/api/v1/assistant/respond"' in template.integration_test_content


def test_api_only_template_contract() -> None:
    contract = get_module_template_contract("api-only")
    template = build_module_template(
        template="api-only",
        package_name="shop_api",
        module_name="webhooks",
    )

    assert set(template.files) == set(contract.file_names_for("webhooks"))
    assert template.integration_test_name == contract.integration_test_name(
        "webhooks"
    )
    assert template.unit_test_name == contract.unit_test_name("webhooks")
    assert template.update_db_models is False
    assert "model.py" not in template.files
    assert "repository.py" not in template.files
    assert '"services"' in template.files["__init__.py"]
    assert '"service"' not in template.files["__init__.py"]
    assert "Depends(db_session)" not in template.files["router.py"]
    service_content = template.files["services/webhooks_service.py"]
    assert 'extra={"payload_name": payload.name}' in service_content
    assert 'extra={"name": payload.name}' not in service_content
    assert (
        'client.post("/api/v1/webhooks/"' in template.integration_test_content
    )


def test_unknown_module_template_raises_clear_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        build_module_template(
            template="unknown",
            package_name="shop_api",
            module_name="assistant",
        )

    assert "Unsupported module template 'unknown'" in str(exc_info.value)
    assert "standard, crud, ai-prompt, api-only" in str(exc_info.value)


def test_llm_integration_files_contract() -> None:
    files = llm_integration_files("shop_api")

    assert set(files) == {
        "integrations/__init__.py",
        "integrations/llm/__init__.py",
        "integrations/llm/anthropic_client.py",
        "integrations/llm/factory.py",
        "integrations/llm/openai_client.py",
        "integrations/llm/provider.py",
        "integrations/llm/schemas.py",
    }
    assert (
        "from shop_api.settings import get_settings"
        in files["integrations/llm/factory.py"]
    )
    assert "{{" not in "\n".join(files.values())
    assert "}}" not in "\n".join(files.values())


def test_llm_settings_and_env_blocks() -> None:
    settings_block = llm_settings_block()
    env_block = llm_env_block()

    assert '    llm_provider: str = ""' in settings_block
    assert "    llm_max_tokens: int | None = None" in settings_block
    assert "LLM_PROVIDER=" in env_block
    assert "# LLM_MAX_TOKENS=" in env_block
