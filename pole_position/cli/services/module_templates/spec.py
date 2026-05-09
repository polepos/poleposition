from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleTemplateContract:
    name: str
    file_names: tuple[str, ...]
    integration_test_name_template: str
    unit_test_name_template: str
    update_db_models: bool = True
    ensure_llm_integrations: bool = False
    ensure_llm_settings: bool = False
    detection_file_names: tuple[str, ...] = ()

    def integration_test_name(self, module_name: str) -> str:
        return self.integration_test_name_template.format(module_name=module_name)

    def unit_test_name(self, module_name: str) -> str:
        return self.unit_test_name_template.format(module_name=module_name)

    def file_names_for(self, module_name: str) -> tuple[str, ...]:
        return tuple(
            file_name.format(module_name=module_name)
            for file_name in self.file_names
        )

    def detection_file_names_for(self, module_name: str) -> tuple[str, ...]:
        return tuple(
            file_name.format(module_name=module_name)
            for file_name in self.detection_file_names
        )


@dataclass(frozen=True)
class ModuleTemplate:
    files: dict[str, str]
    integration_test_name: str
    integration_test_content: str
    unit_test_name: str
    unit_test_content: str
    update_db_models: bool = True
    ensure_llm_integrations: bool = False
    ensure_llm_settings: bool = False


STANDARD_MODULE_TEMPLATE_CONTRACT = ModuleTemplateContract(
    name="standard",
    file_names=(
        "__init__.py",
        "model.py",
        "repository.py",
        "router.py",
        "schemas.py",
        "services/__init__.py",
        "services/{module_name}_service.py",
    ),
    integration_test_name_template="test_{module_name}.py",
    unit_test_name_template="test_{module_name}_service.py",
    detection_file_names=("model.py", "repository.py"),
)

AI_PROMPT_MODULE_TEMPLATE_CONTRACT = ModuleTemplateContract(
    name="ai-prompt",
    file_names=(
        "__init__.py",
        "orchestrator.py",
        "prompts.py",
        "router.py",
        "schemas.py",
        "services/__init__.py",
        "services/{module_name}_service.py",
    ),
    integration_test_name_template="test_{module_name}.py",
    unit_test_name_template="test_{module_name}_orchestrator.py",
    update_db_models=False,
    ensure_llm_integrations=True,
    ensure_llm_settings=True,
    detection_file_names=("orchestrator.py", "prompts.py"),
)

API_ONLY_MODULE_TEMPLATE_CONTRACT = ModuleTemplateContract(
    name="api-only",
    file_names=(
        "__init__.py",
        "router.py",
        "schemas.py",
        "services/__init__.py",
        "services/{module_name}_service.py",
    ),
    integration_test_name_template="test_{module_name}.py",
    unit_test_name_template="test_{module_name}_api_service.py",
    update_db_models=False,
    detection_file_names=(
        "router.py",
        "service.py",
        "services/{module_name}_service.py",
    ),
)
