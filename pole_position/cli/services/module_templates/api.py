from pole_position.cli.services.module_templates.naming import to_class_name
from pole_position.cli.services.module_templates.renderer import render_template
from pole_position.cli.services.module_templates.spec import (
    API_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
)


def build_api_template(
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
            "__init__.py": render_template("api/__init__.py.tpl", context),
            "model.py": render_template("api/model.py.tpl", context),
            "repository.py": render_template("api/repository.py.tpl", context),
            "schemas.py": render_template("api/schemas.py.tpl", context),
            "services/__init__.py": render_template(
                "api/services/__init__.py.tpl",
                context,
            ),
            f"services/{module_name}_service.py": render_template(
                "api/services/module_service.py.tpl",
                context,
            ),
            "router.py": render_template("api/router.py.tpl", context),
        },
        integration_test_name=API_MODULE_TEMPLATE_CONTRACT.integration_test_name(
            module_name
        ),
        integration_test_content=render_template(
            "api/tests/integration.py.tpl",
            context,
        ),
        unit_test_name=API_MODULE_TEMPLATE_CONTRACT.unit_test_name(module_name),
        unit_test_content=render_template(
            "api/tests/unit.py.tpl",
            context,
        ),
        contract=API_MODULE_TEMPLATE_CONTRACT,
    )
