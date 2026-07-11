from pole_position.cli.services.module_templates.naming import to_class_name
from pole_position.cli.services.module_templates.renderer import render_template
from pole_position.cli.services.module_templates.spec import (
    ModuleTemplate,
    ModuleTemplateContract,
)


def build_simple_template(
    *,
    package_name: str,
    module_name: str,
    contract: ModuleTemplateContract,
    template_dir: str,
    file_templates: dict[str, str],
) -> ModuleTemplate:
    """Build a module template that only renders static files (no options).

    ``file_templates`` maps each generated file path (relative to the module
    directory, optionally containing a ``{module_name}`` placeholder) to the
    template that renders it, relative to ``template_dir``. The integration and
    unit tests always render from ``<template_dir>/tests/``. This is the shared
    shape behind the option-less builders (api, api-only, ai-prompt, service,
    service-only); the crud builder renders feature-driven context and keeps
    its own builder.
    """
    context = {
        "package_name": package_name,
        "module_name": module_name,
        "class_name": to_class_name(module_name),
    }

    files = {
        output_path.format(module_name=module_name): render_template(
            f"{template_dir}/{template_path}", context
        )
        for output_path, template_path in file_templates.items()
    }

    return ModuleTemplate(
        files=files,
        integration_test_name=contract.integration_test_name(module_name),
        integration_test_content=render_template(
            f"{template_dir}/tests/integration.py.tpl", context
        ),
        unit_test_name=contract.unit_test_name(module_name),
        unit_test_content=render_template(
            f"{template_dir}/tests/unit.py.tpl", context
        ),
        contract=contract,
    )
