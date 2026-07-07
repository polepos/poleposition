from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


def test_{{module_name}}_service_processes_a_message() -> None:
    service = {{class_name}}Service()

    result = service.process("Main {{class_name}}")

    assert result == "Main {{class_name}}"
