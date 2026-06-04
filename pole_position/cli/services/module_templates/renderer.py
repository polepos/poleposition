from pathlib import Path

TEMPLATE_ROOT = Path(__file__).parent / "files"


def render_template(relative_path: str, context: dict[str, str]) -> str:
    content = (TEMPLATE_ROOT / relative_path).read_text(encoding="utf-8")

    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", value)

    return content
