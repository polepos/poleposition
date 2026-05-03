from pole_position.cli.services.module_templates.api_only import build_api_only_template
from pole_position.cli.services.module_templates.ai_prompt import build_ai_prompt_template
from pole_position.cli.services.module_templates.spec import API_ONLY_MODULE_TEMPLATE_CONTRACT
from pole_position.cli.services.module_templates.spec import AI_PROMPT_MODULE_TEMPLATE_CONTRACT
from pole_position.cli.services.module_templates.spec import ModuleTemplate
from pole_position.cli.services.module_templates.spec import ModuleTemplateContract
from pole_position.cli.services.module_templates.spec import STANDARD_MODULE_TEMPLATE_CONTRACT
from pole_position.cli.services.module_templates.standard import build_standard_template


MODULE_TEMPLATE_CONTRACTS = {
    STANDARD_MODULE_TEMPLATE_CONTRACT.name: STANDARD_MODULE_TEMPLATE_CONTRACT,
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT.name: AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
    API_ONLY_MODULE_TEMPLATE_CONTRACT.name: API_ONLY_MODULE_TEMPLATE_CONTRACT,
}

MODULE_TEMPLATE_DETECTION_ORDER = (
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT.name,
    STANDARD_MODULE_TEMPLATE_CONTRACT.name,
    API_ONLY_MODULE_TEMPLATE_CONTRACT.name,
)

DEFAULT_MODULE_TEMPLATE = STANDARD_MODULE_TEMPLATE_CONTRACT.name
SUPPORTED_MODULE_TEMPLATES = tuple(MODULE_TEMPLATE_CONTRACTS)


def get_module_template_contract(template: str) -> ModuleTemplateContract:
    try:
        return MODULE_TEMPLATE_CONTRACTS[template]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_MODULE_TEMPLATES)
        raise ValueError(
            f"Unsupported module template '{template}'. Expected one of: {supported}."
        ) from exc


def module_template_detection_contracts() -> tuple[ModuleTemplateContract, ...]:
    return tuple(
        get_module_template_contract(template)
        for template in MODULE_TEMPLATE_DETECTION_ORDER
    )


def build_module_template(
    *,
    template: str,
    package_name: str,
    module_name: str,
) -> ModuleTemplate:
    if template == "standard":
        return build_standard_template(
            package_name=package_name,
            module_name=module_name,
        )

    if template == "ai-prompt":
        return build_ai_prompt_template(
            package_name=package_name,
            module_name=module_name,
        )

    if template == "api-only":
        return build_api_only_template(
            package_name=package_name,
            module_name=module_name,
        )

    get_module_template_contract(template)
    raise AssertionError(f"Unhandled module template: {template}")
