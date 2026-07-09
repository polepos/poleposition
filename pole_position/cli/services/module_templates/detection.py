"""Shared module-template detection for `check` and `remove module`.

Detection is used when the manifest does not record a module's template (legacy
or hand-edited projects). It runs in two passes ordered by evidence strength:

1. A generated unit test whose name is unique per template is strong evidence,
   so every contract's unit test is checked first.
2. Only if no unit test matches do we fall back to the file heuristic
   (`detection_file_names` gated by `requires_absent_file_names`), which is
   weaker and order-dependent.

Checking the strong signal across all contracts before the weak one prevents a
lower-precedence contract's file heuristic from beating a higher-precedence
contract's unit test. Both `check` and `remove module` call this so they can
never disagree about a module's template.
"""

from pathlib import Path

from pole_position.cli.services.module_templates.registry import (
    DEFAULT_MODULE_TEMPLATE,
    SUPPORTED_MODULE_TEMPLATES,
    get_module_template_contract,
    module_template_detection_contracts,
)
from pole_position.cli.services.module_templates.spec import (
    ModuleTemplateContract,
)


def detect_module_template_name(
    *,
    tests_root: Path,
    module_root: Path,
    module_name: str,
    manifest_template_name: str | None = None,
) -> str:
    """Return the template name for a module.

    ``manifest_template_name`` is the template already resolved from the
    manifest (a supported name, or ``None`` when the manifest has no usable
    entry). When present it is authoritative; otherwise detection falls back to
    the two-pass file/test heuristic.
    """
    if (
        manifest_template_name
        and manifest_template_name != "starter"
        and manifest_template_name in SUPPORTED_MODULE_TEMPLATES
    ):
        contract = get_module_template_contract(manifest_template_name)
        # Trust the manifest only when the module's files are consistent with
        # the recorded template. A template name can denote a different shape
        # across releases (0.0.46 `service-only` was database-backed; 0.0.48
        # `service-only` is not), so a manifest written by an older release can
        # name a template whose forbidden files are present on disk. Falling
        # through to the file heuristic reclassifies such a module correctly.
        if _requires_absent_satisfied(contract, module_root, module_name):
            return manifest_template_name

    contracts = module_template_detection_contracts()

    for contract in contracts:
        unit_test = tests_root / "unit" / contract.unit_test_name(module_name)
        # The unit-test filename is strong evidence, but a name reused across
        # releases (`test_<m>_service_only.py`) is only trustworthy when the
        # module's shape matches the template it now denotes.
        if unit_test.exists() and _requires_absent_satisfied(
            contract, module_root, module_name
        ):
            return contract.name

    for contract in contracts:
        if _detection_files_match(contract, module_root, module_name):
            return contract.name

    return DEFAULT_MODULE_TEMPLATE


def _requires_absent_satisfied(
    contract: ModuleTemplateContract,
    module_root: Path,
    module_name: str,
) -> bool:
    blocking = contract.requires_absent_file_names_for(module_name)
    return not any((module_root / file_name).exists() for file_name in blocking)


def _detection_files_match(
    contract: ModuleTemplateContract,
    module_root: Path,
    module_name: str,
) -> bool:
    if not _requires_absent_satisfied(contract, module_root, module_name):
        return False

    return any(
        (module_root / file_name).exists()
        for file_name in contract.detection_file_names_for(module_name)
    )
