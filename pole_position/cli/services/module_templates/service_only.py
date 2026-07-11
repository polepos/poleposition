from pole_position.cli.services.module_templates.simple import (
    build_simple_template,
)
from pole_position.cli.services.module_templates.spec import (
    SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
)

_FILE_TEMPLATES = {
    "__init__.py": "__init__.py.tpl",
    "services/__init__.py": "services/__init__.py.tpl",
    "services/{module_name}_service.py": "services/module_service.py.tpl",
}


def build_service_only_template(
    *, package_name: str, module_name: str
) -> ModuleTemplate:
    return build_simple_template(
        package_name=package_name,
        module_name=module_name,
        contract=SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT,
        template_dir="service_only",
        file_templates=_FILE_TEMPLATES,
    )
