from pole_position.cli.services.module_templates.naming import to_class_name
from pole_position.cli.services.module_templates.renderer import render_template
from pole_position.cli.services.module_templates.spec import (
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
)


def build_ai_prompt_template(
    *, package_name: str, module_name: str
) -> ModuleTemplate:
    class_name = to_class_name(module_name)
    context = {
        "package_name": package_name,
        "module_name": module_name,
        "class_name": class_name,
    }

    return ModuleTemplate(
        files={
            "__init__.py": render_template(
                "ai_prompt/__init__.py.tpl", context
            ),
            "schemas.py": render_template("ai_prompt/schemas.py.tpl", context),
            "prompts.py": render_template("ai_prompt/prompts.py.tpl", context),
            "orchestrator.py": render_template(
                "ai_prompt/orchestrator.py.tpl", context
            ),
            "services/__init__.py": render_template(
                "ai_prompt/services/__init__.py.tpl",
                context,
            ),
            f"services/{module_name}_service.py": render_template(
                "ai_prompt/services/module_service.py.tpl",
                context,
            ),
            "router.py": render_template("ai_prompt/router.py.tpl", context),
        },
        integration_test_name=AI_PROMPT_MODULE_TEMPLATE_CONTRACT.integration_test_name(
            module_name
        ),
        integration_test_content=render_template(
            "ai_prompt/tests/integration.py.tpl",
            context,
        ),
        unit_test_name=AI_PROMPT_MODULE_TEMPLATE_CONTRACT.unit_test_name(
            module_name
        ),
        unit_test_content=render_template(
            "ai_prompt/tests/unit.py.tpl",
            context,
        ),
        update_db_models=AI_PROMPT_MODULE_TEMPLATE_CONTRACT.update_db_models,
        ensure_llm_integrations=(
            AI_PROMPT_MODULE_TEMPLATE_CONTRACT.ensure_llm_integrations
        ),
        ensure_llm_settings=AI_PROMPT_MODULE_TEMPLATE_CONTRACT.ensure_llm_settings,
    )
