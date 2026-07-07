from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


def test_process_strips_whitespace() -> None:
    service = {{class_name}}Service()

    assert service.process("  hello  ") == "hello"
