from collections.abc import Callable

from pole_position.cli.services.module_templates.ai_prompt import (
    build_ai_prompt_template,
)
from pole_position.cli.services.module_templates.api import build_api_template
from pole_position.cli.services.module_templates.api_only import (
    build_api_only_template,
)
from pole_position.cli.services.module_templates.crud import build_crud_template
from pole_position.cli.services.module_templates.crud_features import (
    CrudFeatureSet,
)
from pole_position.cli.services.module_templates.service import (
    build_service_template,
)
from pole_position.cli.services.module_templates.service_only import (
    build_service_only_template,
)
from pole_position.cli.services.module_templates.spec import (
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
    API_MODULE_TEMPLATE_CONTRACT,
    API_ONLY_MODULE_TEMPLATE_CONTRACT,
    CRUD_MODULE_TEMPLATE_CONTRACT,
    SERVICE_MODULE_TEMPLATE_CONTRACT,
    SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
    ModuleTemplateContract,
)

MODULE_TEMPLATE_CONTRACTS = {
    API_MODULE_TEMPLATE_CONTRACT.name: API_MODULE_TEMPLATE_CONTRACT,
    CRUD_MODULE_TEMPLATE_CONTRACT.name: CRUD_MODULE_TEMPLATE_CONTRACT,
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT.name: AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
    API_ONLY_MODULE_TEMPLATE_CONTRACT.name: API_ONLY_MODULE_TEMPLATE_CONTRACT,
    SERVICE_MODULE_TEMPLATE_CONTRACT.name: SERVICE_MODULE_TEMPLATE_CONTRACT,
    SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT.name: (
        SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT
    ),
}

# Back-compat template names accepted as input; they resolve to a canonical
# name. `standard` predates the api/service naming.
MODULE_TEMPLATE_ALIASES = {
    "standard": API_MODULE_TEMPLATE_CONTRACT.name,
}

# Detection order for manifest-less projects: most-restrictive archetypes first
# so a weaker file heuristic never beats a stronger one. `requires_absent`
# gating on each contract keeps neighbours from matching.
MODULE_TEMPLATE_DETECTION_ORDER = (
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT.name,
    CRUD_MODULE_TEMPLATE_CONTRACT.name,
    SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT.name,
    SERVICE_MODULE_TEMPLATE_CONTRACT.name,
    API_ONLY_MODULE_TEMPLATE_CONTRACT.name,
    API_MODULE_TEMPLATE_CONTRACT.name,
)

DEFAULT_MODULE_TEMPLATE = API_MODULE_TEMPLATE_CONTRACT.name
SUPPORTED_MODULE_TEMPLATES = tuple(MODULE_TEMPLATE_CONTRACTS)

_SIMPLE_BUILDERS: dict[str, Callable[..., ModuleTemplate]] = {
    API_MODULE_TEMPLATE_CONTRACT.name: build_api_template,
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT.name: build_ai_prompt_template,
    API_ONLY_MODULE_TEMPLATE_CONTRACT.name: build_api_only_template,
    SERVICE_MODULE_TEMPLATE_CONTRACT.name: build_service_template,
    SERVICE_ONLY_MODULE_TEMPLATE_CONTRACT.name: build_service_only_template,
}


def resolve_module_template_name(template: str) -> str:
    """Map a back-compat alias to its canonical template name."""
    return MODULE_TEMPLATE_ALIASES.get(template, template)


def get_module_template_contract(template: str) -> ModuleTemplateContract:
    canonical = resolve_module_template_name(template)
    try:
        return MODULE_TEMPLATE_CONTRACTS[canonical]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_MODULE_TEMPLATES)
        raise ValueError(
            f"Unsupported module template '{template}'. Expected one of: "
            f"{supported}."
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
    crud_features: CrudFeatureSet | None = None,
) -> ModuleTemplate:
    canonical = resolve_module_template_name(template)
    # Validate (raises a clear error for an unknown template).
    get_module_template_contract(canonical)

    if canonical == CRUD_MODULE_TEMPLATE_CONTRACT.name:
        return build_crud_template(
            package_name=package_name,
            module_name=module_name,
            features=crud_features,
        )

    return _SIMPLE_BUILDERS[canonical](
        package_name=package_name,
        module_name=module_name,
    )
