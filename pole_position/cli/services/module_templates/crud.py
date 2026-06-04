from pole_position.cli.services.module_templates.crud_features import (
    DEFAULT_CRUD_FEATURES,
    CrudFeatureSet,
)
from pole_position.cli.services.module_templates.naming import to_class_name
from pole_position.cli.services.module_templates.renderer import render_template
from pole_position.cli.services.module_templates.spec import (
    CRUD_MODULE_TEMPLATE_CONTRACT,
    ModuleTemplate,
)


def build_crud_template(
    *,
    package_name: str,
    module_name: str,
    features: CrudFeatureSet | None = None,
) -> ModuleTemplate:
    resolved_features = features or DEFAULT_CRUD_FEATURES
    class_name = to_class_name(module_name)
    context = _crud_context(
        package_name=package_name,
        module_name=module_name,
        class_name=class_name,
        features=resolved_features,
    )

    return ModuleTemplate(
        files={
            "__init__.py": render_template("crud/__init__.py.tpl", context),
            "model.py": render_template("crud/model.py.tpl", context),
            "repository.py": render_template("crud/repository.py.tpl", context),
            "schemas.py": render_template("crud/schemas.py.tpl", context),
            "services/__init__.py": render_template(
                "crud/services/__init__.py.tpl",
                context,
            ),
            f"services/{module_name}_crud_service.py": render_template(
                "crud/services/module_crud_service.py.tpl",
                context,
            ),
            "router.py": render_template("crud/router.py.tpl", context),
        },
        integration_test_name=CRUD_MODULE_TEMPLATE_CONTRACT.integration_test_name(
            module_name
        ),
        integration_test_content=render_template(
            "crud/tests/integration.py.tpl",
            context,
        ),
        unit_test_name=CRUD_MODULE_TEMPLATE_CONTRACT.unit_test_name(
            module_name
        ),
        unit_test_content=render_template(
            "crud/tests/unit.py.tpl",
            context,
        ),
        features=resolved_features.enabled_labels,
        update_db_models=CRUD_MODULE_TEMPLATE_CONTRACT.update_db_models,
        ensure_llm_integrations=CRUD_MODULE_TEMPLATE_CONTRACT.ensure_llm_integrations,
        ensure_llm_settings=CRUD_MODULE_TEMPLATE_CONTRACT.ensure_llm_settings,
    )


def _crud_context(
    *,
    package_name: str,
    module_name: str,
    class_name: str,
    features: CrudFeatureSet,
) -> dict[str, str]:
    return {
        "package_name": package_name,
        "module_name": module_name,
        "class_name": class_name,
        **_model_context(features),
        **_repository_context(class_name, features),
        **_schemas_context(class_name, features),
        **_router_context(module_name, class_name, features),
        **_service_context(module_name, class_name, features),
        **_integration_test_context(
            package_name, module_name, class_name, features
        ),
        **_unit_test_context(class_name, features),
    }


def _model_context(features: CrudFeatureSet) -> dict[str, str]:
    sqlalchemy_imports = ["String"]
    if features.timestamps or features.soft_delete:
        sqlalchemy_imports.insert(0, "DateTime")

    datetime_import = ""
    utc_now = ""
    if features.timestamps:
        datetime_import = "from datetime import datetime, timezone\n\n"
        utc_now = (
            "\n\n"
            "def utc_now() -> datetime:\n"
            "    return datetime.now(timezone.utc)\n"
        )
    elif features.soft_delete:
        datetime_import = "from datetime import datetime\n\n"

    return {
        "model_datetime_import": datetime_import,
        "model_sqlalchemy_imports": ", ".join(sqlalchemy_imports),
        "model_utc_now": utc_now,
        "model_tenant_field": _line_if(
            features.tenant_scoped,
            "    tenant_id: Mapped[str] = mapped_column(String(64), "
            "index=True)\n",
        ),
        "model_timestamp_fields": _line_if(
            features.timestamps,
            "    created_at: Mapped[datetime] = mapped_column(\n"
            "        DateTime(timezone=True),\n"
            "        default=utc_now,\n"
            "    )\n"
            "    updated_at: Mapped[datetime] = mapped_column(\n"
            "        DateTime(timezone=True),\n"
            "        default=utc_now,\n"
            "        onupdate=utc_now,\n"
            "    )\n",
        ),
        "model_soft_delete_field": _line_if(
            features.soft_delete,
            "    deleted_at: Mapped[datetime | None] = mapped_column(\n"
            "        DateTime(timezone=True),\n"
            "        default=None,\n"
            "        index=True,\n"
            "    )\n",
        ),
    }


def _repository_context(
    class_name: str, features: CrudFeatureSet
) -> dict[str, str]:
    sqlalchemy_imports = ["select"]
    if features.pagination:
        sqlalchemy_imports.insert(0, "func")

    return {
        "repository_datetime_import": _line_if(
            features.soft_delete,
            "from datetime import datetime, timezone\n\n",
        ),
        "repository_sqlalchemy_imports": ", ".join(sqlalchemy_imports),
        "repository_utc_now": _line_if(
            features.soft_delete,
            "\n\n"
            "def utc_now() -> datetime:\n"
            "    return datetime.now(timezone.utc)\n",
        ),
        "repository_list_parameters": _keyword_parameters(
            [
                ("tenant_id: str", features.tenant_scoped),
                ("limit: int", features.pagination),
                ("offset: int", features.pagination),
            ]
        ),
        "repository_list_filters": _repository_filters(class_name, features),
        "repository_pagination_clause": _line_if(
            features.pagination,
            "        statement = statement.offset(offset).limit(limit)\n",
        ),
        "repository_count_method": _repository_count_method(
            class_name, features
        ),
        "repository_get_parameters": _keyword_parameters(
            [("tenant_id: str", features.tenant_scoped)]
        ),
        "repository_get_filters": _repository_filters(class_name, features),
        "repository_create_parameters": _keyword_parameters(
            [
                ("tenant_id: str", features.tenant_scoped),
                ("name: str", True),
            ]
        ),
        "repository_create_fields": _repository_create_fields(features),
        "repository_delete_body": _repository_delete_body(features),
    }


def _repository_filters(class_name: str, features: CrudFeatureSet) -> str:
    lines: list[str] = []
    if features.tenant_scoped:
        lines.append(
            f"        statement = statement.where({class_name}.tenant_id "
            f"== tenant_id)"
        )
    if features.soft_delete:
        lines.append(
            f"        statement = "
            f"statement.where({class_name}.deleted_at.is_(None))"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def _repository_count_method(class_name: str, features: CrudFeatureSet) -> str:
    if not features.pagination:
        return ""

    parameters = _keyword_parameters(
        [("tenant_id: str", features.tenant_scoped)]
    )
    filters = _repository_filters(class_name, features)
    return (
        "\n"
        f"    def count(self{parameters}) -> int:\n"
        f"        statement = select(func.count()).select_from({class_name})\n"
        f"{filters}"
        "        return self.db.scalar(statement) or 0\n"
    )


def _repository_create_fields(features: CrudFeatureSet) -> str:
    fields = []
    if features.tenant_scoped:
        fields.append("tenant_id=tenant_id")
    fields.append("name=name")
    return "".join(f"            {field},\n" for field in fields)


def _repository_delete_body(features: CrudFeatureSet) -> str:
    if features.soft_delete:
        return (
            "        item.deleted_at = utc_now()\n"
            "        self.db.commit()\n"
            "        self.db.refresh(item)\n"
        )

    return "        self.db.delete(item)\n        self.db.commit()\n"


def _schemas_context(
    class_name: str, features: CrudFeatureSet
) -> dict[str, str]:
    read_fields = ["    id: int"]
    create_fields = []
    if features.tenant_scoped:
        create_fields.append(
            "    tenant_id: str = Field(min_length=1, max_length=64)"
        )
        read_fields.append("    tenant_id: str")
    create_fields.append("    name: str = Field(min_length=3, max_length=120)")
    read_fields.append("    name: str")
    if features.timestamps:
        read_fields.extend(
            ["    created_at: datetime", "    updated_at: datetime"]
        )
    if features.soft_delete:
        read_fields.append("    deleted_at: datetime | None = None")

    return {
        "schemas_datetime_import": _line_if(
            features.timestamps or features.soft_delete,
            "from datetime import datetime\n\n",
        ),
        "schemas_create_fields": "\n".join(create_fields),
        "schemas_read_fields": "\n".join(read_fields),
        "schemas_page_class": _schemas_page_class(class_name, features),
    }


def _schemas_page_class(class_name: str, features: CrudFeatureSet) -> str:
    if not features.pagination:
        return ""

    return (
        "\n\n"
        f"class {class_name}Page(BaseModel):\n"
        f"    items: list[{class_name}Read]\n"
        "    total: int\n"
        "    limit: int\n"
        "    offset: int\n"
    )


def _router_context(
    module_name: str,
    class_name: str,
    features: CrudFeatureSet,
) -> dict[str, str]:
    list_response_model = (
        f"{class_name}Page"
        if features.pagination
        else f"list[{class_name}Read]"
    )
    schema_imports = [
        f"{class_name}Create",
        f"{class_name}Read",
        f"{class_name}Update",
    ]
    if features.pagination:
        schema_imports.insert(1, f"{class_name}Page")

    return {
        "router_query_import": _line_if(
            features.pagination or features.tenant_scoped,
            ", Query",
        ),
        "router_api_deps_imports": (
            "db_session, get_current_user"
            if features.auth_required
            else "db_session"
        ),
        "router_schema_imports": _multiline_import_names(schema_imports),
        "router_dependencies": (
            "dependencies=[Depends(get_current_user)]"
            if features.auth_required
            else ""
        ),
        "router_list_response_model": list_response_model,
        "router_list_parameters": _router_list_parameters(features),
        "router_list_call_args": _call_arguments(
            [
                ("tenant_id=tenant_id", features.tenant_scoped),
                ("limit=limit", features.pagination),
                ("offset=offset", features.pagination),
            ]
        ),
        "router_create_parameters": _router_create_parameters(class_name),
        "router_get_parameters": _router_item_parameters(features),
        "router_get_call_args": _call_arguments(
            [
                ("item_id", True),
                ("tenant_id=tenant_id", features.tenant_scoped),
            ]
        ),
        "router_update_parameters": _router_update_parameters(
            class_name, features
        ),
        "router_update_call_args": _call_arguments(
            [
                ("item_id", True),
                ("payload", True),
                ("tenant_id=tenant_id", features.tenant_scoped),
            ]
        ),
        "router_delete_parameters": _router_item_parameters(features),
        "router_delete_call_args": _call_arguments(
            [
                ("item_id", True),
                ("tenant_id=tenant_id", features.tenant_scoped),
            ]
        ),
    }


def _router_list_parameters(features: CrudFeatureSet) -> str:
    parameters = []
    if features.tenant_scoped:
        parameters.append("tenant_id: str = Query(..., min_length=1)")
    if features.pagination:
        parameters.extend(
            [
                "limit: int = Query(default=100, ge=1, le=500)",
                "offset: int = Query(default=0, ge=0)",
            ]
        )
    parameters.append("db: Session = Depends(db_session)")
    return _parameter_block(parameters)


def _router_create_parameters(class_name: str) -> str:
    return _parameter_block(
        [
            f"payload: {class_name}Create",
            "db: Session = Depends(db_session)",
        ]
    )


def _router_item_parameters(features: CrudFeatureSet) -> str:
    parameters = ["item_id: int"]
    if features.tenant_scoped:
        parameters.append("tenant_id: str = Query(..., min_length=1)")
    parameters.append("db: Session = Depends(db_session)")
    return _parameter_block(parameters)


def _router_update_parameters(class_name: str, features: CrudFeatureSet) -> str:
    parameters = ["item_id: int", f"payload: {class_name}Update"]
    if features.tenant_scoped:
        parameters.append("tenant_id: str = Query(..., min_length=1)")
    parameters.append("db: Session = Depends(db_session)")
    return _parameter_block(parameters)


def _service_context(
    module_name: str,
    class_name: str,
    features: CrudFeatureSet,
) -> dict[str, str]:
    schema_imports = [f"{class_name}Create", f"{class_name}Update"]
    if features.pagination:
        schema_imports.insert(1, f"{class_name}Page")

    list_return_type = (
        f"{class_name}Page" if features.pagination else f"list[{class_name}]"
    )
    return {
        "service_schema_imports": _multiline_import_names(schema_imports),
        "service_list_parameters": _keyword_parameters(
            [
                ("tenant_id: str", features.tenant_scoped),
                ("limit: int", features.pagination),
                ("offset: int", features.pagination),
            ]
        ),
        "service_list_return_type": list_return_type,
        "service_list_body": _service_list_body(
            module_name, class_name, features
        ),
        "service_get_parameters": _keyword_parameters(
            [("tenant_id: str", features.tenant_scoped)]
        ),
        "service_get_call_args": _call_arguments(
            [
                ("item_id", True),
                ("tenant_id=tenant_id", features.tenant_scoped),
            ]
        ),
        "service_create_call_args": _call_arguments(
            [
                ("tenant_id=payload.tenant_id", features.tenant_scoped),
                ("name=payload.name", True),
            ]
        ),
        "service_update_parameters": _line_if(
            features.tenant_scoped,
            "        *,\n        tenant_id: str,\n",
        ),
        "service_update_get_args": _call_arguments(
            [
                ("item_id", True),
                ("tenant_id=tenant_id", features.tenant_scoped),
            ]
        ),
        "service_delete_parameters": _keyword_parameters(
            [("tenant_id: str", features.tenant_scoped)]
        ),
        "service_delete_get_args": _call_arguments(
            [
                ("item_id", True),
                ("tenant_id=tenant_id", features.tenant_scoped),
            ]
        ),
    }


def _service_list_body(
    module_name: str,
    class_name: str,
    features: CrudFeatureSet,
) -> str:
    if not features.pagination:
        return (
            f'        logger.info("Listing {module_name}")\n'
            f"        return "
            f"self.repository.list({_inline_call_arguments(_list_args(features))})"
        )

    list_args = _inline_call_arguments(
        _list_args(features) + ["limit=limit", "offset=offset"]
    )
    count_args = _inline_call_arguments(_list_args(features))
    return (
        f'        logger.info("Listing {module_name}", extra={{"limit": '
        f'limit, "offset": offset}})\n'
        f"        items = self.repository.list({list_args})\n"
        f"        total = self.repository.count({count_args})\n"
        f"        return {class_name}Page(\n"
        "            items=items,\n"
        "            total=total,\n"
        "            limit=limit,\n"
        "            offset=offset,\n"
        "        )"
    )


def _integration_test_context(
    package_name: str,
    module_name: str,
    class_name: str,
    features: CrudFeatureSet,
) -> dict[str, str]:
    create_payload = (
        {
            "tenant_id": "tenant-a",
            "name": f"Main {class_name}",
        }
        if features.tenant_scoped
        else {"name": f"Main {class_name}"}
    )
    update_payload = {"name": f"Updated {class_name}"}

    return {
        "integration_auth_import": _line_if(
            features.auth_required,
            f"\nfrom {package_name}.auth.token import create_access_token\n",
        ),
        "integration_auth_helpers": _line_if(
            features.auth_required,
            "\n\n"
            "def _auth_headers() -> dict[str, str]:\n"
            '    token = create_access_token(subject="test-user", '
            'roles=["user"])\n'
            '    return {"Authorization": f"Bearer {token}"}\n',
        ),
        "integration_headers_argument": _line_if(
            features.auth_required,
            "        headers=_auth_headers(),\n",
        ),
        "integration_create_payload": repr(create_payload),
        "integration_update_payload": repr(update_payload),
        "integration_item_query_suffix": (
            "?tenant_id=tenant-a" if features.tenant_scoped else ""
        ),
        "integration_list_query_suffix": _integration_list_query_suffix(
            features
        ),
        "integration_list_assertions": _integration_list_assertions(
            class_name,
            features,
        ),
        "integration_timestamp_assertions": _integration_timestamp_assertions(
            features
        ),
        "integration_soft_delete_assertions": (
            _integration_soft_delete_assertions(module_name, features)
        ),
        "integration_auth_required_test": _integration_auth_required_test(
            module_name,
            features,
        ),
    }


def _integration_list_query_suffix(features: CrudFeatureSet) -> str:
    query_params = []
    if features.tenant_scoped:
        query_params.append("tenant_id=tenant-a")
    if features.pagination:
        query_params.extend(["limit=10", "offset=0"])
    return f"?{'&'.join(query_params)}" if query_params else ""


def _integration_list_assertions(
    class_name: str, features: CrudFeatureSet
) -> str:
    if features.pagination:
        return (
            "    list_payload = list_response.json()\n"
            '    assert list_payload["total"] == 1\n'
            '    assert list_payload["limit"] == 10\n'
            '    assert list_payload["offset"] == 0\n'
            f'    assert list_payload["items"][0]["name"] == "Updated '
            f'{class_name}"\n'
        )

    return (
        "    list_payload = list_response.json()\n"
        f'    assert list_payload[0]["name"] == "Updated {class_name}"\n'
    )


def _integration_timestamp_assertions(features: CrudFeatureSet) -> str:
    assertions = []
    if features.timestamps:
        assertions.extend(
            [
                '    assert created["created_at"] is not None',
                '    assert created["updated_at"] is not None',
            ]
        )
    if features.soft_delete:
        assertions.append('    assert created["deleted_at"] is None')
    return "\n".join(assertions) + ("\n" if assertions else "")


def _integration_soft_delete_assertions(
    module_name: str,
    features: CrudFeatureSet,
) -> str:
    if not features.soft_delete:
        return ""

    headers_argument = _line_if(
        features.auth_required,
        "        headers=_auth_headers(),\n",
    )
    list_url = (
        f"/api/v1/{module_name}/{_integration_list_query_suffix(features)}"
    )
    if features.pagination:
        return (
            "\n"
            "    list_after_delete_response = client.get(\n"
            f'        "{list_url}",\n'
            f"{headers_argument}"
            "    )\n"
            "    assert list_after_delete_response.status_code == 200\n"
            '    assert list_after_delete_response.json()["total"] == 0\n'
        )

    return (
        "\n"
        "    list_after_delete_response = client.get(\n"
        f'        "{list_url}",\n'
        f"{headers_argument}"
        "    )\n"
        "    assert list_after_delete_response.status_code == 200\n"
        "    assert list_after_delete_response.json() == []\n"
    )


def _integration_auth_required_test(
    module_name: str,
    features: CrudFeatureSet,
) -> str:
    if not features.auth_required:
        return ""

    return (
        "\n\n"
        f"def test_{module_name}_requires_auth(client: TestClient) -> None:\n"
        "    response = client.get(\n"
        f"        "
        f'"/api/v1/{module_name}/{_integration_list_query_suffix(features)}",\n'
        "    )\n"
        "    assert response.status_code == 401\n"
    )


def _unit_test_context(
    class_name: str, features: CrudFeatureSet
) -> dict[str, str]:
    tenant_update_argument = _line_if(
        features.tenant_scoped,
        '        tenant_id="tenant-a",\n',
    )
    get_assertion = (
        "    service.repository.get.assert_called_once_with(123, "
        'tenant_id="tenant-a")'
        if features.tenant_scoped
        else "    service.repository.get.assert_called_once_with(123)"
    )
    return {
        "unit_get_missing_call_args": _call_arguments(
            [
                ("123", True),
                ('tenant_id="tenant-a"', features.tenant_scoped),
            ]
        ),
        "unit_update_tenant_argument": tenant_update_argument,
        "unit_get_assertion": get_assertion,
    }


def _keyword_parameters(parameters: list[tuple[str, bool]]) -> str:
    enabled = [parameter for parameter, include in parameters if include]
    if not enabled:
        return ""

    return ", *, " + ", ".join(enabled)


def _parameter_block(parameters: list[str]) -> str:
    return "".join(f"    {parameter},\n" for parameter in parameters)


def _call_arguments(arguments: list[tuple[str, bool]]) -> str:
    enabled = [argument for argument, include in arguments if include]
    return _inline_call_arguments(enabled)


def _inline_call_arguments(arguments: list[str]) -> str:
    return ", ".join(arguments)


def _list_args(features: CrudFeatureSet) -> list[str]:
    return ["tenant_id=tenant_id"] if features.tenant_scoped else []


def _multiline_import_names(names: list[str]) -> str:
    return "\n".join(f"    {name}," for name in names)


def _line_if(condition: bool, content: str) -> str:
    return content if condition else ""
