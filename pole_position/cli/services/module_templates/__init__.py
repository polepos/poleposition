from pole_position.cli.services.module_templates.crud_features import (
    CRUD_FEATURE_FLAGS,
    CRUD_FEATURE_LABELS,
    CRUD_FEATURE_NAMES,
    CRUD_FEATURE_NAMES_BY_LABEL,
    DEFAULT_CRUD_FEATURES,
    CrudFeatureSet,
)
from pole_position.cli.services.module_templates.llm import (
    llm_env_block,
    llm_integration_files,
    llm_settings_block,
)
from pole_position.cli.services.module_templates.registry import (
    DEFAULT_MODULE_TEMPLATE,
    MODULE_TEMPLATE_CONTRACTS,
    MODULE_TEMPLATE_DETECTION_ORDER,
    SUPPORTED_MODULE_TEMPLATES,
    build_module_template,
    get_module_template_contract,
    module_template_detection_contracts,
)
from pole_position.cli.services.module_templates.spec import (
    AI_PROMPT_MODULE_TEMPLATE_CONTRACT,
    API_ONLY_MODULE_TEMPLATE_CONTRACT,
    CRUD_MODULE_TEMPLATE_CONTRACT,
    STANDARD_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
    ModuleTemplateContract,
)

__all__ = [
    "ModuleTemplate",
    "ModuleTemplateContract",
    "API_ONLY_MODULE_TEMPLATE_CONTRACT",
    "AI_PROMPT_MODULE_TEMPLATE_CONTRACT",
    "CRUD_FEATURE_FLAGS",
    "CRUD_FEATURE_LABELS",
    "CRUD_FEATURE_NAMES",
    "CRUD_FEATURE_NAMES_BY_LABEL",
    "CRUD_MODULE_TEMPLATE_CONTRACT",
    "CrudFeatureSet",
    "DEFAULT_CRUD_FEATURES",
    "DEFAULT_MODULE_TEMPLATE",
    "MODULE_TEMPLATE_CONTRACTS",
    "MODULE_TEMPLATE_DETECTION_ORDER",
    "STANDARD_MODULE_TEMPLATE_CONTRACT",
    "SUPPORTED_MODULE_TEMPLATES",
    "build_module_template",
    "get_module_template_contract",
    "llm_env_block",
    "llm_integration_files",
    "llm_settings_block",
    "module_template_detection_contracts",
]
