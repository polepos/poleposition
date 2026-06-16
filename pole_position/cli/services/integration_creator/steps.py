def _integration_next_steps(
    *,
    package_name: str,
    integration_name: str,
) -> tuple[str, ...]:
    return (
        "Run `uv sync --extra dev`",
        (
            "Copy new integration env values from `.env.example` into `.env` "
            "if `.env` already exists"
        ),
        f"Review src/{package_name}/integrations/{integration_name}/",
        "Run `polepos check`",
    )
