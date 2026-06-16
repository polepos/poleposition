from pole_position.cli.services.module_templates import ModuleTemplate


def _module_next_steps(
    *,
    package_name: str,
    module_name: str,
    template_spec: ModuleTemplate,
) -> tuple[str, ...]:
    steps = [
        f"Review src/{package_name}/modules/{module_name}/",
        "Run `polepos check`",
    ]

    if template_spec.features:
        features = ", ".join(template_spec.features)
        steps.append(f"Review generated CRUD options: {features}")

    if template_spec.update_db_models:
        steps.append(
            f'After model changes, run `polepos db revision -m "add '
            f'{module_name} table"`'
        )

    if template_spec.ensure_llm_settings:
        steps.append(
            "Set LLM_API_KEY in .env before calling the generated endpoint"
        )

    return tuple(steps)
