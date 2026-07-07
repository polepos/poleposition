from {{package_name}}.db.base import Base
from {{package_name}}.db.models import import_models
from {{package_name}}.db.session import get_engine, get_session_factory
from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


def test_{{module_name}}_service_persists_and_lists() -> None:
    import_models()
    Base.metadata.create_all(bind=get_engine())

    session = get_session_factory()()
    try:
        service = {{class_name}}Service(session)
        created = service.create_{{module_name}}(name="Main {{class_name}}")
        assert created.id is not None

        names = [item.name for item in service.list_{{module_name}}()]
        assert names == ["Main {{class_name}}"]
    finally:
        session.close()
