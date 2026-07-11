from pole_position.cli.services.module_templates.simple import (
    build_simple_template,
)
from pole_position.cli.services.module_templates.spec import (
    API_ONLY_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
)

_FILE_TEMPLATES = {
    "__init__.py": "__init__.py.tpl",
    "schemas.py": "schemas.py.tpl",
    "services/__init__.py": "services/__init__.py.tpl",
    "services/{module_name}_service.py": "services/module_service.py.tpl",
    "router.py": "router.py.tpl",
}


def build_api_only_template(
    *, package_name: str, module_name: str
) -> ModuleTemplate:
    return build_simple_template(
        package_name=package_name,
        module_name=module_name,
        contract=API_ONLY_MODULE_TEMPLATE_CONTRACT,
        template_dir="api_only",
        file_templates=_FILE_TEMPLATES,
    )
