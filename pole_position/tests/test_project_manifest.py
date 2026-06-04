from pathlib import Path

from pole_position.cli.services.project_manifest import (
    ProjectManifest,
    format_manifest_module_template,
    parse_manifest_module_template,
    read_project_manifest,
    record_manifest_integration,
    record_manifest_module,
    write_project_manifest,
)


def test_manifest_keeps_quoted_false_integration_invalid_not_enabled(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / ".poleposition.toml"
    manifest_path.write_text(
        (
            "[poleposition]\n"
            'package = "myapp"\n'
            'db = "sqlite"\n'
            "\n"
            "[modules]\n"
            'status = "starter"\n'
            "\n"
            "[integrations]\n"
            'kafka = "false"\n'
            "rabbitmq = false\n"
            "llm = true\n"
        ),
        encoding="utf-8",
    )

    manifest = read_project_manifest(tmp_path)

    assert manifest.enabled_integrations == {
        "llm": True,
        "rabbitmq": False,
    }
    assert manifest.invalid_integration_values == {"kafka": '"false"'}


def test_manifest_preserves_invalid_integration_values_when_recording_module(
    tmp_path: Path,
) -> None:
    write_project_manifest(
        tmp_path,
        ProjectManifest(
            package_name="myapp",
            database="sqlite",
            modules={"status": "starter"},
            invalid_integrations={"kafka": '"false"'},
            exists=True,
        ),
    )

    record_manifest_module(
        project_root=tmp_path,
        module_name="garage",
        template="standard",
    )

    manifest_content = (tmp_path / ".poleposition.toml").read_text(
        encoding="utf-8"
    )
    assert 'garage = "standard"' in manifest_content
    assert 'kafka = "false"' in manifest_content


def test_record_manifest_integration_replaces_invalid_integration_value(
    tmp_path: Path,
) -> None:
    write_project_manifest(
        tmp_path,
        ProjectManifest(
            package_name="myapp",
            database="sqlite",
            invalid_integrations={"kafka": '"false"'},
            exists=True,
        ),
    )

    record_manifest_integration(project_root=tmp_path, integration_name="kafka")

    manifest = read_project_manifest(tmp_path)
    assert manifest.enabled_integrations == {"kafka": True}
    assert manifest.invalid_integration_values == {}


def test_record_manifest_module_preserves_crud_feature_options(
    tmp_path: Path,
) -> None:
    write_project_manifest(
        tmp_path,
        ProjectManifest(
            package_name="myapp",
            database="sqlite",
            modules={"status": "starter"},
            exists=True,
        ),
    )

    record_manifest_module(
        project_root=tmp_path,
        module_name="customers",
        template="crud",
        features=("tenant-scoped", "pagination", "auth-required"),
    )

    manifest = read_project_manifest(tmp_path)
    assert manifest.module_templates == {
        "customers": "crud[pagination,tenant-scoped,auth-required]",
        "status": "starter",
    }


def test_unreadable_manifest_is_reported_and_left_untouched(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / ".poleposition.toml"
    manifest_path.write_bytes(b"\xff\xfe\x00")

    manifest = read_project_manifest(tmp_path)

    assert manifest.exists is True
    assert manifest.read_error is not None
    assert "Could not read project manifest as UTF-8" in manifest.read_error

    record_manifest_module(
        project_root=tmp_path,
        module_name="garage",
        template="standard",
    )
    record_manifest_integration(project_root=tmp_path, integration_name="kafka")

    assert manifest_path.read_bytes() == b"\xff\xfe\x00"


def test_manifest_module_template_parser_reads_crud_features() -> None:
    parsed = parse_manifest_module_template(
        "crud[pagination,timestamps,soft-delete,tenant-scoped,auth-required]"
    )

    assert parsed.name == "crud"
    assert parsed.crud_features.enabled_labels == (
        "pagination",
        "timestamps",
        "soft-delete",
        "tenant-scoped",
        "auth-required",
    )


def test_manifest_module_template_formatter_skips_non_crud_features() -> None:
    assert (
        format_manifest_module_template(
            "crud",
            features=("timestamps", "soft-delete"),
        )
        == "crud[timestamps,soft-delete]"
    )
    assert format_manifest_module_template("standard") == "standard"
