from pole_position.cli.services.module_templates.simple import (
    build_simple_template,
)
from pole_position.cli.services.module_templates.spec import (
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
)

_FILE_TEMPLATES = {
    "__init__.py": "__init__.py.tpl",
    "schemas.py": "schemas.py.tpl",
    "prompts.py": "prompts.py.tpl",
    "orchestrator.py": "orchestrator.py.tpl",
    "services/__init__.py": "services/__init__.py.tpl",
    "services/{module_name}_service.py": "services/module_service.py.tpl",
    "router.py": "router.py.tpl",
}


def build_ai_prompt_template(
    *, package_name: str, module_name: str
) -> ModuleTemplate:
    return build_simple_template(
        package_name=package_name,
        module_name=module_name,
        contract=AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
        template_dir="ai_prompt",
        file_templates=_FILE_TEMPLATES,
    )
