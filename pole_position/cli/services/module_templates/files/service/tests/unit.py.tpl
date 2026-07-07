from unittest.mock import Mock

from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


def test_list_{{module_name}}_delegates_to_repository() -> None:
    service = {{class_name}}Service(db=Mock())
    service.repository = Mock()

    service.list_{{module_name}}()

    service.repository.list.assert_called_once_with()


def test_create_{{module_name}}_delegates_to_repository() -> None:
    service = {{class_name}}Service(db=Mock())
    service.repository = Mock()

    service.create_{{module_name}}(name="Main")

    service.repository.create.assert_called_once_with(name="Main")
