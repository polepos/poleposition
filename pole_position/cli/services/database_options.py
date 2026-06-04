from dataclasses import dataclass

DEFAULT_DATABASE = "sqlite"
SUPPORTED_DATABASES = ("sqlite", "postgres", "none")


@dataclass(frozen=True)
class DatabaseOption:
    name: str
    default_url: str
    postgres_db_name: str
    uses_database: bool


def get_database_option(name: str, *, package_name: str) -> DatabaseOption:
    normalized = name.strip().lower()

    if normalized == "sqlite":
        return DatabaseOption(
            name="sqlite",
            default_url="sqlite:///./poleposition.db",
            postgres_db_name="app",
            uses_database=True,
        )

    if normalized == "postgres":
        return DatabaseOption(
            name="postgres",
            default_url=(
                f"postgresql+psycopg://postgres:postgres@localhost:5432/{package_name}"
            ),
            postgres_db_name=package_name,
            uses_database=True,
        )

    if normalized == "none":
        return DatabaseOption(
            name="none",
            default_url="",
            postgres_db_name="app",
            uses_database=False,
        )

    supported = ", ".join(SUPPORTED_DATABASES)
    raise ValueError(
        f"Unsupported database option '{name}'. Expected one of: {supported}."
    )
