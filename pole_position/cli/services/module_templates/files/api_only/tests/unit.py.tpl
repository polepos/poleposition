from {{package_name}}.modules.{{module_name}}.schemas import {{class_name}}Request
from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


def test_describe_returns_api_readiness() -> None:
    result = {{class_name}}Service().describe()

    assert result.name == "{{module_name}}"
    assert result.message == "{{class_name}} API is ready."


def test_handle_returns_response_for_payload() -> None:
    result = {{class_name}}Service().handle({{class_name}}Request(name="Ada"))

    assert result.name == "Ada"
    assert result.message == "Ada was handled by {{module_name}}."
