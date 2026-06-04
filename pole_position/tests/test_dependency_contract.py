from pole_position.cli.services.dependency_contract import (
    dependency_contract_satisfied,
    dependency_names_match,
    parse_dependency_entry,
    quoted_dependency_values,
)


def test_dependency_contract_requires_extras_and_min_version() -> None:
    dependencies = [
        "pwdlib>=0.2.0",
        "redis>=5.0.1",
    ]

    assert not dependency_contract_satisfied(
        dependencies,
        "pwdlib[argon2]>=0.2.0",
    )
    assert dependency_contract_satisfied(
        [*dependencies, "pwdlib[argon2]>=0.2.1"],
        "pwdlib[argon2]>=0.2.0",
    )
    assert not dependency_contract_satisfied(
        dependencies,
        "redis>=5.1.0",
    )


def test_dependency_names_match_normalized_names() -> None:
    assert dependency_names_match(
        "pydantic-settings>=2.0.0", "pydantic_settings"
    )
    assert dependency_names_match("SQLAlchemy ~= 2.0", "sqlalchemy")
    assert not dependency_names_match("sqlalchemy>=2.0.0", "alembic")


def test_parse_dependency_entry_preserves_line_parts() -> None:
    entry = parse_dependency_entry(
        '    "psycopg[binary] == 3.2.1",  # postgres driver'
    )

    assert entry is not None
    assert entry.indent == "    "
    assert entry.quote == '"'
    assert entry.value == "psycopg[binary] == 3.2.1"
    assert entry.trailing == ",  # postgres driver"


def test_quoted_dependency_values_collects_quoted_specs() -> None:
    assert quoted_dependency_values(
        """
        "fastapi[standard]>=0.115.0",
        'sqlalchemy>=2.0.0',
        """
    ) == (
        "fastapi[standard]>=0.115.0",
        "sqlalchemy>=2.0.0",
    )
