import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(REPO_ROOT)
    )

    return subprocess.run(
        [sys.executable, "-m", "pole_position.cli.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def test_check_help_shows_usage_without_project(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "check", "--help")

    assert result.returncode == 0
    assert "Usage: polepos check [--json] [--fix]" in result.stdout
    assert "--json" in result.stdout
    assert "--fix" in result.stdout
    assert "Unexpected argument" not in result.stdout


def test_check_passes_for_generated_project(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout
    assert f"Project root: {project_root}" in result.stdout
    assert "Package: myapp" in result.stdout


def test_check_json_passes_for_generated_project(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "check", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "passed": True,
        "project_root": str(project_root),
        "package_name": "myapp",
        "issues": [],
    }


def test_check_reports_missing_status_integration_test(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    (project_root / "tests" / "integration" / "test_status.py").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Required generated path is missing" in result.stdout
    assert "tests/integration/test_status.py" in result.stdout


def test_check_json_reports_issues(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    (project_root / "tests" / "integration" / "test_status.py").unlink()

    result = run_cli(project_root, "check", "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert payload["project_root"] == str(project_root)
    assert payload["package_name"] == "myapp"
    assert payload["issues"] == [
        {
            "code": "PPCHK010",
            "message": (
                "Required generated path is missing: "
                f"{project_root / 'tests' / 'integration' / 'test_status.py'}"
            ),
            "remediation": (
                "Restore the generated path, or intentionally opt out and "
                "document "
                "the drift."
            ),
        }
    ]


def test_check_reports_non_utf8_managed_file(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    settings_path = project_root / "src" / "myapp" / "settings.py"
    settings_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "check", "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["issues"] == [
        {
            "code": "PPCHK023",
            "message": (
                "Could not read generated text file as UTF-8: "
                f"{settings_path}: invalid start byte"
            ),
            "remediation": (
                "Restore the file as UTF-8 text or replace it with "
                "generated content."
            ),
        }
    ]
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr


def test_check_reports_non_utf8_legacy_database_free_settings(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    settings_path = project_root / "src" / "myapp" / "settings.py"
    (project_root / ".poleposition.toml").unlink()
    settings_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "check", "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["issues"][0]["code"] == "PPCHK023"
    assert (
        "Could not read generated text file as UTF-8"
        in payload["issues"][0]["message"]
    )
    assert str(settings_path) in payload["issues"][0]["message"]
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr


def test_check_reports_non_utf8_manifest(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "check", "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["issues"][0] == {
        "code": "PPCHK016",
        "message": (
            "Could not read project manifest as UTF-8: "
            f"{manifest_path}: invalid start byte"
        ),
        "remediation": (
            "Restore .poleposition.toml as UTF-8 TOML or remove the "
            "corrupt file."
        ),
    }
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr


def test_check_fix_skips_non_utf8_managed_file_and_reports_issue(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "check", "--fix")

    assert result.returncode != 0
    assert "No automatic fixes were applied." in result.stdout
    assert (
        "[PPCHK023] Could not read generated text file as UTF-8"
        in result.stdout
    )
    assert str(router_path) in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr


def test_check_works_from_nested_directory(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    nested_dir = tmp_path / "myapp" / "src" / "myapp" / "modules"
    result = run_cli(nested_dir, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_passes_after_added_standard_crud_and_ai_prompt_modules(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    standard_result = run_cli(project_root, "add", "module", "garage")
    crud_result = run_cli(
        project_root,
        "add",
        "module",
        "customers",
        "--template",
        "crud",
    )
    ai_prompt_result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
    )

    assert standard_result.returncode == 0
    assert crud_result.returncode == 0
    assert ai_prompt_result.returncode == 0

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_passes_after_added_featured_crud_module(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root,
        "add",
        "module",
        "customers",
        "--template",
        "crud",
        "--pagination",
        "--timestamps",
        "--soft-delete",
        "--tenant-scoped",
        "--auth-required",
    )

    assert add_result.returncode == 0

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_passes_after_added_api_only_module(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root, "add", "module", "webhooks", "--api-only"
    )

    assert add_result.returncode == 0

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_passes_after_added_auth_workflow(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "auth")
    assert add_result.returncode == 0

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_reports_missing_auth_workflow_file(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "auth")
    assert add_result.returncode == 0

    (project_root / "src" / "myapp" / "auth" / "router.py").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK045]" in result.stdout
    assert "Auth workflow is missing generated file" in result.stdout
    assert "auth/router.py" in result.stdout


def test_check_reports_missing_auth_dependency_and_router_wiring(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "auth")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '    "pwdlib[argon2]>=0.2.0",\n',
            "",
        ),
        encoding="utf-8",
    )
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8").replace(
            'api_router.include_router(auth_router, prefix="/auth", '
            'tags=["auth"])\n',
            "",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK048]" in result.stdout
    assert "Auth workflow is missing dependency" in result.stdout
    assert "pwdlib[argon2]>=0.2.0" in result.stdout
    assert "[PPCHK050]" in result.stdout
    assert "Auth workflow is missing API router include" in result.stdout


def test_check_reports_auth_dependency_without_required_extra(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "auth")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '    "pwdlib[argon2]>=0.2.0",\n',
            '    "pwdlib>=0.2.0",\n',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK048]" in result.stdout
    assert "Auth workflow is missing dependency" in result.stdout
    assert "pwdlib[argon2]>=0.2.0" in result.stdout


def test_check_reports_auth_workflow_on_database_free_project(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8") + "auth = true\n",
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK044]" in result.stdout
    assert "Auth workflow requires generated database wiring" in result.stdout


def test_check_reports_database_free_database_remnants(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    (package_root / "api" / "deps.py").write_text(
        (
            "from sqlalchemy.orm import Session\n"
            "from myapp.db.session import get_db\n"
            "def db_session():\n"
            "    yield from get_db()\n"
        ),
        encoding="utf-8",
    )
    (project_root / "Dockerfile").write_text(
        (
            "COPY pyproject.toml README.md alembic.ini ./\n"
            "COPY migrations ./migrations\n"
        ),
        encoding="utf-8",
    )
    (project_root / "README.md").write_text(
        (
            "## Project Layout\n\n"
            "```text\n"
            "alembic.ini\n"
            "migrations/\n"
            "src/myapp/\n"
            "  db/\n"
            "```\n"
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "PolePosition project check failed." in result.stdout
    assert (
        "Database-free project contains database-specific content"
        in result.stdout
    )
    assert "api/deps.py" in result.stdout
    assert "Dockerfile" in result.stdout
    assert "README.md" in result.stdout


def test_check_passes_after_added_messaging_integrations(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    kafka_result = run_cli(project_root, "add", "integration", "kafka")
    rabbitmq_result = run_cli(project_root, "add", "integration", "rabbitmq")
    redis_result = run_cli(project_root, "add", "integration", "redis")
    rq_result = run_cli(project_root, "add", "integration", "rq")

    assert kafka_result.returncode == 0
    assert rabbitmq_result.returncode == 0
    assert redis_result.returncode == 0
    assert rq_result.returncode == 0

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_fails_outside_project(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "check")

    assert result.returncode != 0
    assert "does not look like a PolePosition project" in result.stdout


def test_check_json_fails_outside_project(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "check", "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert payload["project_root"] is None
    assert payload["package_name"] is None
    assert payload["issues"] == [
        {
            "code": "PPCHK000",
            "message": "Current directory does not look like a "
            "PolePosition project.",
            "remediation": (
                "Run the command from a PolePosition project root or a nested "
                "directory inside one."
            ),
        }
    ]


def test_check_reports_missing_managed_marker(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
        "# polepos:router-imports",
        "# router imports are managed manually",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "PolePosition project check failed." in result.stdout
    assert "[PPCHK021]" in result.stdout
    assert (
        "Managed marker '# polepos:router-imports' is missing" in result.stdout
    )
    assert "Fix: Restore the listed # polepos marker" in result.stdout
    assert "api/router.py" in result.stdout


def test_check_reports_issue_codes_and_remediation_for_lifecycle_drift(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
        'api_router.include_router(garage_router, prefix="/garage", '
        'tags=["garage"])',
        "# garage router is wired manually",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK034]" in result.stdout
    assert (
        "Lifecycle module 'garage' is missing API router include"
        in result.stdout
    )
    assert "Fix: Restore the router include" in result.stdout
    assert "polepos remove module garage --wiring-only" in result.stdout


def test_check_reports_missing_core_path_after_loose_project_detection(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "PolePosition project check failed." in result.stdout
    assert "Required generated path is missing" in result.stdout
    assert "api/router.py" in result.stdout


def test_check_accepts_multiline_added_module_router_wiring(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8")
    router_content = router_content.replace(
        "from myapp.modules.garage.router import router as garage_router",
        (
            "from myapp.modules.garage.router import (\n"
            "    router as garage_router,\n"
            ")"
        ),
    ).replace(
        'api_router.include_router(garage_router, prefix="/garage", '
        'tags=["garage"])',
        (
            "api_router.include_router(\n"
            "    garage_router,\n"
            '    prefix="/garage",\n'
            '    tags=["garage"],\n'
            ")"
        ),
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_reports_missing_added_module_router_wiring(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
        'api_router.include_router(garage_router, prefix="/garage", '
        'tags=["garage"])',
        "# garage router is wired manually",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert (
        "Lifecycle module 'garage' is missing API router include"
        in result.stdout
    )
    assert "api/router.py" in result.stdout


def test_check_reports_orphan_module_wiring_after_manual_directory_delete(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    module_root = project_root / "src" / "myapp" / "modules" / "garage"
    shutil.rmtree(module_root)

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK039]" in result.stdout
    assert "Orphan module reference to missing module 'garage'" in result.stdout
    assert "router include" in result.stdout
    assert "module export" in result.stdout
    assert "generated test" in result.stdout
    assert "polepos remove module garage" in result.stdout


def test_check_reports_orphan_custom_module_references_after_marker(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    shutil.rmtree(package_root / "modules" / "garage")
    (project_root / "tests" / "integration" / "test_garage.py").unlink()
    (project_root / "tests" / "unit" / "test_garage_service.py").unlink()

    router_path = package_root / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8")
        .replace(
            "from myapp.modules.garage.router import router as garage_router\n",
            "",
        )
        .replace(
            'api_router.include_router(garage_router, prefix="/garage", '
            'tags=["garage"])\n',
            "",
        )
        + "\n"
        + "from myapp.modules.garage.router import router as "
        "garage_custom_router\n"
        + "api_router.include_router(garage_custom_router, "
        'prefix="/garage-custom", tags=["garage_custom"])\n',
        encoding="utf-8",
    )

    models_path = package_root / "db" / "models.py"
    models_path.write_text(
        models_path.read_text(encoding="utf-8").replace(
            "    from myapp.modules.garage import model  # noqa: F401\n",
            "",
        )
        + "\nfrom myapp.modules.garage import model as garage_model\n",
        encoding="utf-8",
    )

    modules_init_path = package_root / "modules" / "__init__.py"
    modules_init_path.write_text(
        modules_init_path.read_text(encoding="utf-8")
        .replace('    "garage",\n', "")
        .replace(
            "    # polepos:module-exports\n",
            "    # polepos:module-exports\n    'garage',\n",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Orphan module reference to missing module 'garage'" in result.stdout
    assert "router import" in result.stdout
    assert "router include" in result.stdout
    assert "model import" in result.stdout
    assert "module export" in result.stdout


def test_check_reports_missing_status_router_wiring(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
        'api_router.include_router(status_router, tags=["status"])\n',
        "",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK022]" in result.stdout
    assert (
        "Starter module 'status' is missing API router include" in result.stdout
    )


def test_check_reports_missing_added_module_model_wiring(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    models_path = project_root / "src" / "myapp" / "db" / "models.py"
    models_content = models_path.read_text(encoding="utf-8").replace(
        "    from myapp.modules.garage import model  # noqa: F401\n",
        "",
    )
    models_path.write_text(models_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Lifecycle module 'garage' is missing model import" in result.stdout
    assert "db/models.py" in result.stdout


def test_check_reports_parse_error_in_db_models(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    models_path = project_root / "src" / "myapp" / "db" / "models.py"
    models_path.write_text(
        (
            "def import_models() -> None:\n"
            "    from myapp.modules.garage import model  # noqa: F401\n"
            "        broken\n"
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Could not parse Python file for lifecycle checks" in result.stdout
    assert "db/models.py" in result.stdout


def test_check_reports_missing_added_module_test_wiring(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    (project_root / "tests" / "unit" / "test_garage_service.py").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Lifecycle module 'garage' is missing unit test" in result.stdout
    assert "test_garage_service.py" in result.stdout


def test_check_reports_missing_ai_prompt_module_files(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
    )
    assert add_result.returncode == 0

    module_root = project_root / "src" / "myapp" / "modules" / "assistant"
    (module_root / "orchestrator.py").unlink()
    (module_root / "prompts.py").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert (
        "Lifecycle module 'assistant' is missing generated path"
        in result.stdout
    )
    assert "orchestrator.py" in result.stdout
    assert "prompts.py" in result.stdout
    assert "missing model import" not in result.stdout


def test_check_reports_missing_api_only_module_files_without_model_requirement(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root, "add", "module", "webhooks", "--api-only"
    )
    assert add_result.returncode == 0

    module_root = project_root / "src" / "myapp" / "modules" / "webhooks"
    (module_root / "services" / "webhooks_service.py").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert (
        "Lifecycle module 'webhooks' is missing generated path" in result.stdout
    )
    assert "services/webhooks_service.py" in result.stdout
    assert "missing model import" not in result.stdout


def test_check_reports_missing_crud_module_files(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root,
        "add",
        "module",
        "customers",
        "--template",
        "crud",
    )
    assert add_result.returncode == 0

    module_root = project_root / "src" / "myapp" / "modules" / "customers"
    (module_root / "services" / "customers_crud_service.py").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert (
        "Lifecycle module 'customers' is missing generated path"
        in result.stdout
    )
    assert "services/customers_crud_service.py" in result.stdout


def test_check_reports_missing_kafka_integration_file(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "kafka")
    assert add_result.returncode == 0

    (
        project_root
        / "src"
        / "myapp"
        / "integrations"
        / "kafka"
        / "producer.py"
    ).unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'kafka' is missing generated file" in result.stdout
    assert "producer.py" in result.stdout


def test_check_reports_missing_kafka_dependency(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "kafka")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8").replace(
        '    "aiokafka>=0.12.0",\n',
        "",
    )
    pyproject_path.write_text(pyproject_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'kafka' is missing dependency" in result.stdout
    assert "aiokafka>=0.12.0" in result.stdout


def test_check_reports_kafka_directory_signal_without_manifest_entry(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    kafka_root = project_root / "src" / "myapp" / "integrations" / "kafka"
    kafka_root.mkdir(parents=True)
    (kafka_root / "__init__.py").write_text("", encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'kafka' is missing generated file" in result.stdout
    assert "producer.py" in result.stdout
    assert "Integration 'kafka' is missing dependency" in result.stdout
    assert "Integration 'kafka' is missing setting" in result.stdout
    assert "Integration 'kafka' is missing env value" in result.stdout


def test_check_accepts_upgraded_kafka_dependency(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "kafka")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '"aiokafka>=0.12.0"',
            '"aiokafka>=0.13.0"',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_reports_kafka_dependency_below_required_version(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "kafka")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '"aiokafka>=0.12.0"',
            '"aiokafka>=0.11.0"',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'kafka' is missing dependency" in result.stdout
    assert "aiokafka>=0.12.0" in result.stdout


def test_check_accepts_normalized_rabbitmq_dependency_name(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "rabbitmq")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '"aio-pika>=9.0.0"',
            '"aio_pika>=9.1.0"',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_reports_missing_rabbitmq_settings_and_env(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "rabbitmq")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_content = settings_path.read_text(encoding="utf-8").replace(
        '    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"\n',
        "",
    )
    settings_path.write_text(settings_content, encoding="utf-8")

    env_path = project_root / ".env.example"
    env_content = env_path.read_text(encoding="utf-8").replace(
        "RABBITMQ_URL=amqp://guest:guest@localhost:5672/\n",
        "",
    )
    env_path.write_text(env_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'rabbitmq' is missing setting" in result.stdout
    assert "rabbitmq_url" in result.stdout
    assert "Integration 'rabbitmq' is missing env value" in result.stdout
    assert "RABBITMQ_URL" in result.stdout


def test_check_reports_missing_redis_integration_file(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "redis")
    assert add_result.returncode == 0

    (
        project_root / "src" / "myapp" / "integrations" / "redis" / "cache.py"
    ).unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'redis' is missing generated file" in result.stdout
    assert "cache.py" in result.stdout


def test_check_reports_missing_redis_dependency(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "redis")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8").replace(
        '    "redis>=5.0.0",\n',
        "",
    )
    pyproject_path.write_text(pyproject_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'redis' is missing dependency" in result.stdout
    assert "redis>=5.0.0" in result.stdout


def test_check_reports_missing_redis_settings_and_env(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "redis")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_content = settings_path.read_text(encoding="utf-8").replace(
        '    redis_url: str = "redis://localhost:6379/0"\n',
        "",
    )
    settings_path.write_text(settings_content, encoding="utf-8")

    env_path = project_root / ".env.example"
    env_content = env_path.read_text(encoding="utf-8").replace(
        "REDIS_URL=redis://localhost:6379/0\n",
        "",
    )
    env_path.write_text(env_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'redis' is missing setting" in result.stdout
    assert "redis_url" in result.stdout
    assert "Integration 'redis' is missing env value" in result.stdout
    assert "REDIS_URL" in result.stdout


def test_check_reports_missing_rq_integration_file(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "rq")
    assert add_result.returncode == 0

    (
        project_root / "src" / "myapp" / "integrations" / "rq" / "jobs.py"
    ).unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'rq' is missing generated file" in result.stdout
    assert "jobs.py" in result.stdout


def test_check_reports_missing_rq_dependency(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "rq")
    assert add_result.returncode == 0

    pyproject_path = project_root / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8").replace(
        '    "rq>=1.16.0",\n',
        "",
    )
    pyproject_path.write_text(pyproject_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'rq' is missing dependency" in result.stdout
    assert "rq>=1.16.0" in result.stdout


def test_check_reports_missing_rq_settings_and_env(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "rq")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_content = settings_path.read_text(encoding="utf-8").replace(
        '    rq_redis_url: str = "redis://localhost:6379/0"\n',
        "",
    )
    settings_path.write_text(settings_content, encoding="utf-8")

    env_path = project_root / ".env.example"
    env_content = env_path.read_text(encoding="utf-8").replace(
        "RQ_REDIS_URL=redis://localhost:6379/0\n",
        "",
    )
    env_path.write_text(env_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'rq' is missing setting" in result.stdout
    assert "rq_redis_url" in result.stdout
    assert "Integration 'rq' is missing env value" in result.stdout
    assert "RQ_REDIS_URL" in result.stdout


def test_check_reports_commented_required_integration_settings_and_env(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "integration", "kafka")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_path.write_text(
        settings_path.read_text(encoding="utf-8").replace(
            '    kafka_bootstrap_servers: str = "localhost:9092"\n',
            '    # kafka_bootstrap_servers: str = "localhost:9092"\n',
        ),
        encoding="utf-8",
    )

    env_path = project_root / ".env.example"
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "KAFKA_BOOTSTRAP_SERVERS=localhost:9092\n",
            "# KAFKA_BOOTSTRAP_SERVERS=localhost:9092\n",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'kafka' is missing setting" in result.stdout
    assert "kafka_bootstrap_servers" in result.stdout
    assert "Integration 'kafka' is missing env value" in result.stdout
    assert "KAFKA_BOOTSTRAP_SERVERS" in result.stdout
    assert "KAFKA_COMPRESSION_TYPE" not in result.stdout


def test_check_reports_missing_llm_integration_file_and_env(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
    )
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    (package_root / "integrations" / "llm" / "factory.py").unlink()

    env_path = project_root / ".env.example"
    env_content = env_path.read_text(encoding="utf-8").replace(
        "LLM_PROVIDER=openai\n",
        "",
    )
    env_path.write_text(env_content, encoding="utf-8")

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'llm' is missing generated file" in result.stdout
    assert "factory.py" in result.stdout
    assert "Integration 'llm' is missing env value" in result.stdout
    assert "LLM_PROVIDER" in result.stdout


def test_check_reports_missing_alembic_config(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    (project_root / "alembic.ini").unlink()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "PolePosition project check failed." in result.stdout
    assert "Required Alembic path is missing" in result.stdout
    assert "alembic.ini" in result.stdout


def test_check_fix_restores_missing_managed_marker(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8").replace(
            "# polepos:router-imports\n",
            "",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check", "--fix")

    assert result.returncode == 0
    assert "Applied fixes:" in result.stdout
    assert "src/myapp/api/router.py" in result.stdout
    assert "PolePosition project check passed." in result.stdout
    assert "# polepos:router-imports" in router_path.read_text(encoding="utf-8")


def test_check_fix_restores_router_include_marker_after_multiline_include(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8").replace(
            (
                'api_router.include_router(status_router, tags=["status"])\n'
                "# polepos:router-includes\n"
            ),
            (
                "api_router.include_router(\n"
                "    status_router,\n"
                '    tags=["status"],\n'
                ")\n"
            ),
        ),
        encoding="utf-8",
    )

    fix_result = run_cli(project_root, "check", "--fix")

    assert fix_result.returncode == 0
    assert "PolePosition project check passed." in fix_result.stdout
    fixed_lines = router_path.read_text(encoding="utf-8").splitlines()
    include_end_index = fixed_lines.index(
        ")", fixed_lines.index("api_router.include_router(")
    )
    assert (
        fixed_lines.index("# polepos:router-includes") == include_end_index + 1
    )

    add_result = run_cli(project_root, "add", "module", "garage")

    assert add_result.returncode == 0, add_result.stdout
    ast.parse(router_path.read_text(encoding="utf-8"))
    assert "garage_router" in router_path.read_text(encoding="utf-8")


def test_check_fix_json_reports_fixed_paths(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    modules_init_path = (
        project_root / "src" / "myapp" / "modules" / "__init__.py"
    )
    modules_init_path.write_text(
        modules_init_path.read_text(encoding="utf-8").replace(
            "    # polepos:module-exports\n",
            "",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check", "--fix", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["fixed"] == ["src/myapp/modules/__init__.py"]
    assert payload["issues"] == []


def test_check_rejects_unexpected_arguments(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "check", "--bogus")

    assert result.returncode != 0
    assert "Unexpected argument: --bogus" in result.stdout
    assert "Usage: polepos check" in result.stdout


def test_check_database_free_project_ignores_sqlalchemy_named_dependencies(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '    "pydantic>=2.0.0",\n',
            ('    "pydantic>=2.0.0",\n    "sqlalchemy-utils>=0.41.0",\n'),
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_manifest_custom_db_allows_user_managed_database_content(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            'db = "none"',
            'db = "custom"',
        ),
        encoding="utf-8",
    )
    (project_root / ".env.example").write_text(
        (project_root / ".env.example").read_text(encoding="utf-8")
        + "DATABASE_URL=clickhouse://localhost/default\n",
        encoding="utf-8",
    )
    (package_root / "api" / "deps.py").write_text(
        "def custom_database_client():\n    return None\n",
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_reports_invalid_manifest_module_template_without_traceback(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            'status = "starter"',
            'status = "starter"\ngarage = "bogus"',
        ),
        encoding="utf-8",
    )
    (package_root / "modules" / "garage").mkdir()

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK014]" in result.stdout
    assert "Project manifest has unsupported module template" in result.stdout
    assert "garage = bogus" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_check_reports_invalid_manifest_crud_feature_without_traceback(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            'status = "starter"',
            'status = "starter"\ncustomers = "crud[unknown]"',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK014]" in result.stdout
    assert "Project manifest has unsupported module template" in result.stdout
    assert "customers = crud[unknown]" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_check_reports_invalid_manifest_integration_value_without_wiring_noise(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8") + 'kafka = "false"\n',
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "[PPCHK015]" in result.stdout
    assert "Project manifest has unsupported integration value" in result.stdout
    assert 'kafka = "false"' in result.stdout
    assert "Fix: Use unquoted true or false" in result.stdout
    assert "Integration 'kafka'" not in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_check_reports_status_router_include_with_added_prefix(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8").replace(
            'api_router.include_router(status_router, tags=["status"])',
            (
                "api_router.include_router("
                'status_router, prefix="/status", tags=["status"])'
            ),
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert (
        "Starter module 'status' is missing API router include" in result.stdout
    )


def test_check_normalizes_manifest_database_mode_case(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            'db = "sqlite"',
            'db = "SQLite"',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode == 0
    assert "PolePosition project check passed." in result.stdout


def test_check_manifest_reports_manual_kafka_dependency_without_integration(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '    "pydantic>=2.0.0",\n',
            '    "pydantic>=2.0.0",\n    "aiokafka>=0.12.0",\n',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "check")

    assert result.returncode != 0
    assert "Integration 'kafka' is missing generated file" in result.stdout
    assert "Integration 'kafka' is missing setting" in result.stdout
    assert "Integration 'kafka' is missing env value" in result.stdout
