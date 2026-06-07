import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(cwd, *args):
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


def test_remove_command_shows_usage(tmp_path: Path):
    result = run_cli(tmp_path, "remove")

    assert result.returncode == 0
    assert "Usage: polepos remove <subcommand>" in result.stdout
    assert "module" in result.stdout


def test_remove_module_shows_usage_without_name(tmp_path: Path):
    result = run_cli(tmp_path, "remove", "module")

    assert result.returncode != 0
    assert "Usage: polepos remove module <module_name>" in result.stdout
    assert "--force" in result.stdout
    assert "--trace" in result.stdout
    assert "--wiring-only" in result.stdout


def test_remove_standard_module_cleans_generated_wiring(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode == 0
    assert "Removed module: garage" in result.stdout
    assert "Template: standard" in result.stdout
    assert (
        "Create a migration if removing the module also removes database tables"
        in (result.stdout)
    )

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_garage_service.py"
    ).exists()

    router_content = (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )
    db_models_content = (package_root / "db" / "models.py").read_text(
        encoding="utf-8"
    )
    modules_init_content = (package_root / "modules" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "garage_router" not in router_content
    assert "modules.garage" not in router_content
    assert "modules.garage" not in db_models_content
    assert '"garage"' not in modules_init_content
    assert "garage =" not in (project_root / ".poleposition.toml").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_featured_crud_module_cleans_generated_wiring(tmp_path: Path):
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

    result = run_cli(project_root, "remove", "module", "customers")

    assert result.returncode == 0
    assert "Removed module: customers" in result.stdout
    assert "Template: crud" in result.stdout
    assert "custom changes" not in result.stdout

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "customers").exists()
    assert not (
        project_root / "tests" / "integration" / "test_customers_crud.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_customers_crud_service.py"
    ).exists()

    assert "customers_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert "modules.customers" not in (
        package_root / "db" / "models.py"
    ).read_text(encoding="utf-8")
    assert "customers =" not in (project_root / ".poleposition.toml").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_standard_module_cleans_remnants_when_dir_missing(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    shutil.rmtree(package_root / "modules" / "garage")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode == 0
    assert "Module does not exist" not in result.stdout
    assert "Removed module: garage" in result.stdout
    assert "tests/integration/test_garage.py" in result.stdout
    assert "tests/unit/test_garage_service.py" in result.stdout

    router_content = (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )
    db_models_content = (package_root / "db" / "models.py").read_text(
        encoding="utf-8"
    )
    modules_init_content = (package_root / "modules" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "garage_router" not in router_content
    assert "modules.garage" not in router_content
    assert "modules.garage" not in db_models_content
    assert '"garage"' not in modules_init_content
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_garage_service.py"
    ).exists()

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_force_cleans_non_generated_orphan_reference(
    tmp_path: Path,
):
    # Regression for #37: `polepos check` recommends `remove module X` for an
    # orphan reference, but `remove` used to dead-end with "Module does not
    # exist" when the reference was not in the exact generated shape (for
    # example hand-edited, or left by a mis-detected template).
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    models_path = package_root / "db" / "models.py"

    models_path.write_text(
        models_path.read_text(encoding="utf-8").replace(
            "# polepos:model-imports",
            "from myapp.modules.ghost import GhostModel  # custom\n"
            "    # polepos:model-imports",
        ),
        encoding="utf-8",
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode != 0
    assert "missing module 'ghost'" in check_result.stdout
    assert "remove module ghost" in check_result.stdout

    result = run_cli(project_root, "remove", "module", "ghost", "--force")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Module does not exist" not in result.stdout
    assert "modules.ghost" not in models_path.read_text(encoding="utf-8")

    recheck = run_cli(project_root, "check")
    assert recheck.returncode == 0


def test_remove_module_force_cleans_orphan_router_references(tmp_path: Path):
    # Regression: `remove --force` reported success but left a custom router
    # include for a missing module, so `check` kept looping.
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    router_path = project_root / "src" / "myapp" / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8")
        .replace(
            "# polepos:router-imports",
            "from myapp.modules.ghostr.router import router as "
            "ghostr_router\n# polepos:router-imports",
        )
        .replace(
            "# polepos:router-includes",
            'api_router.include_router(ghostr_router, prefix="/ghostr")\n'
            "# polepos:router-includes",
        ),
        encoding="utf-8",
    )

    assert run_cli(project_root, "check").returncode != 0

    result = run_cli(project_root, "remove", "module", "ghostr", "--force")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ghostr" not in router_path.read_text(encoding="utf-8")
    assert run_cli(project_root, "check").returncode == 0


def test_remove_module_does_not_touch_prefix_sharing_module(tmp_path: Path):
    # Regression: removing `user` must not scrub `users` references.
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    assert run_cli(project_root, "add", "module", "user").returncode == 0
    assert run_cli(project_root, "add", "module", "users").returncode == 0

    shutil.rmtree(package_root / "modules" / "user")

    result = run_cli(project_root, "remove", "module", "user", "--force")

    assert result.returncode == 0, result.stdout + result.stderr

    models = (package_root / "db" / "models.py").read_text(encoding="utf-8")
    router = (package_root / "api" / "router.py").read_text(encoding="utf-8")
    init = (package_root / "modules" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "modules.users" in models
    assert "users_router" in router
    assert '"users"' in init
    assert (package_root / "modules" / "users").is_dir()
    assert run_cli(project_root, "check").returncode == 0


def test_remove_api_only_module_cleans_remnants_when_dir_missing(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root, "add", "module", "webhooks", "--api-only"
    )
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    shutil.rmtree(package_root / "modules" / "webhooks")

    result = run_cli(project_root, "remove", "module", "webhooks")

    assert result.returncode == 0
    assert "Module does not exist" not in result.stdout
    assert "Template: api-only" in result.stdout
    assert "Create a migration" not in result.stdout
    assert "webhooks_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert '"webhooks"' not in (
        package_root / "modules" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert not (
        project_root / "tests" / "integration" / "test_webhooks.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_webhooks_api_service.py"
    ).exists()

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_trace_reports_plan_without_changing_files(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "garage", "--trace")

    assert result.returncode == 0
    assert "Removal trace: garage" in result.stdout
    assert "Template: standard" in result.stdout
    assert "Would remove:" in result.stdout
    assert "src/myapp/modules/garage" in result.stdout
    assert "tests/integration/test_garage.py" in result.stdout
    assert "Would update:" in result.stdout
    assert "src/myapp/api/router.py" in result.stdout
    assert ".poleposition.toml" in result.stdout

    package_root = project_root / "src" / "myapp"
    assert (package_root / "modules" / "garage").exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert "garage_router" in (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )


def test_remove_module_cleans_manifest_only_remnant(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            "\n[integrations]",
            '\nghost = "api-only"\n\n[integrations]',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "remove", "module", "ghost")

    assert result.returncode == 0
    assert "Removed module: ghost" in result.stdout
    assert "Template: api-only" in result.stdout
    assert "Module does not exist" not in result.stdout
    assert ".poleposition.toml" in result.stdout
    assert 'ghost = "api-only"' not in manifest_path.read_text(encoding="utf-8")

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_rejects_custom_module_files_without_force(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    custom_file = package_root / "modules" / "garage" / "custom_logic.py"
    custom_file.write_text("CUSTOM_VALUE = 1\n", encoding="utf-8")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "custom changes" in result.stdout
    assert "Unexpected module file" in result.stdout
    assert "custom_logic.py" in result.stdout
    assert "polepos remove module garage --force" in result.stdout
    assert custom_file.exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert "garage_router" in (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )


def test_remove_module_wiring_only_preserves_custom_module_files(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    custom_file = package_root / "modules" / "garage" / "custom_logic.py"
    custom_file.write_text("CUSTOM_VALUE = 1\n", encoding="utf-8")

    result = run_cli(
        project_root, "remove", "module", "garage", "--wiring-only"
    )

    assert result.returncode == 0
    assert "Cleaned module wiring: garage" in result.stdout
    assert (
        "Move, delete, or rewire the preserved module directory"
        in result.stdout
    )
    assert (package_root / "modules" / "garage").exists()
    assert custom_file.exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_garage_service.py"
    ).exists()

    assert "garage_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert "modules.garage" not in (
        package_root / "db" / "models.py"
    ).read_text(encoding="utf-8")
    assert '"garage"' not in (
        package_root / "modules" / "__init__.py"
    ).read_text(encoding="utf-8")


def test_remove_module_wiring_only_rejects_custom_tests_without_force(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    unit_test = project_root / "tests" / "unit" / "test_garage_service.py"
    unit_test.write_text(
        "def test_customized():\n    assert True\n", encoding="utf-8"
    )

    result = run_cli(
        project_root, "remove", "module", "garage", "--wiring-only"
    )

    assert result.returncode != 0
    assert "Cannot clean module wiring" in result.stdout
    assert "Modified generated test file" in result.stdout
    assert "--wiring-only --force" in result.stdout
    assert unit_test.exists()
    assert "garage_router" in (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )

    force_result = run_cli(
        project_root,
        "remove",
        "module",
        "garage",
        "--wiring-only",
        "--force",
    )

    assert force_result.returncode == 0
    assert not unit_test.exists()
    assert (package_root / "modules" / "garage").exists()
    assert "garage_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")


def test_remove_module_force_removes_custom_module_files(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    custom_file = package_root / "modules" / "garage" / "custom_logic.py"
    custom_file.write_text("CUSTOM_VALUE = 1\n", encoding="utf-8")

    result = run_cli(project_root, "remove", "module", "garage", "--force")

    assert result.returncode == 0
    assert "Removed module: garage" in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()
    assert "garage_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_force_removes_non_utf8_generated_module_file(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    router_path = package_root / "modules" / "garage" / "router.py"
    router_path.write_bytes(b"\xff\xfe\x00")

    blocked_result = run_cli(project_root, "remove", "module", "garage")

    assert blocked_result.returncode != 0
    assert "Modified generated module file" in blocked_result.stdout
    assert "UnicodeDecodeError" not in blocked_result.stdout
    assert router_path.exists()

    force_result = run_cli(
        project_root, "remove", "module", "garage", "--force"
    )

    assert force_result.returncode == 0
    assert "Removed module: garage" in force_result.stdout
    assert not (package_root / "modules" / "garage").exists()

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_ignores_python_cache_artifacts(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    cache_root = package_root / "modules" / "garage" / "__pycache__"
    cache_root.mkdir()
    (cache_root / "router.cpython-311.pyc").write_bytes(b"cache")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode == 0
    assert "custom changes" not in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_api_only_module_does_not_require_model_wiring(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root, "add", "module", "webhooks", "--api-only"
    )
    assert add_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "webhooks")

    assert result.returncode == 0
    assert "Template: api-only" in result.stdout
    assert "Create a migration" not in result.stdout

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "webhooks").exists()
    assert not (
        project_root / "tests" / "integration" / "test_webhooks.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_webhooks_api_service.py"
    ).exists()
    assert "webhooks_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert "modules.webhooks" not in (
        package_root / "db" / "models.py"
    ).read_text(encoding="utf-8")

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_races_module_also_removes_legacy_unit_test_name(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "races")
    assert add_result.returncode == 0

    legacy_unit_test = project_root / "tests" / "unit" / "test_race_service.py"
    legacy_unit_test.write_text("", encoding="utf-8")

    result = run_cli(project_root, "remove", "module", "races")

    assert result.returncode == 0
    assert not legacy_unit_test.exists()


def test_remove_last_ai_prompt_module_cleans_llm_shared_scaffold(
    tmp_path: Path,
):
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

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0
    assert "Template: ai-prompt" in result.stdout
    assert "Create a migration" not in result.stdout

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "assistant").exists()
    assert not (package_root / "integrations" / "llm").exists()
    assert "llm_provider" not in (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    assert "LLM_PROVIDER" not in (project_root / ".env.example").read_text(
        encoding="utf-8"
    )
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")
    assert "assistant =" not in manifest
    assert "llm = true" not in manifest

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_ai_prompt_module_cleans_remnants_when_dir_missing(
    tmp_path: Path,
):
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
    shutil.rmtree(package_root / "modules" / "assistant")

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0
    assert "Module does not exist" not in result.stdout
    assert "Template: ai-prompt" in result.stdout
    assert "assistant_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert '"assistant"' not in (
        package_root / "modules" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert not (package_root / "integrations" / "llm").exists()
    assert not (
        project_root / "tests" / "integration" / "test_assistant.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_assistant_orchestrator.py"
    ).exists()
    assert "LLM_PROVIDER" not in (project_root / ".env.example").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_last_ai_prompt_module_cleans_llm_scaffold_with_others(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    kafka_result = run_cli(project_root, "add", "integration", "kafka")
    add_result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
    )
    assert kafka_result.returncode == 0
    assert add_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "assistant").exists()
    assert not (package_root / "integrations" / "llm").exists()
    assert (package_root / "integrations" / "kafka").exists()
    assert "llm_provider" not in (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    assert "LLM_PROVIDER" not in (project_root / ".env.example").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_last_ai_prompt_module_preserves_custom_llm_scaffold(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    custom_provider = (
        package_root / "integrations" / "llm" / "custom_provider.py"
    )
    custom_provider.write_text(
        "class CustomProvider:\n    pass\n", encoding="utf-8"
    )

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0
    assert not (package_root / "modules" / "assistant").exists()
    assert custom_provider.exists()
    assert "llm_provider" in (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    assert "LLM_PROVIDER" in (project_root / ".env.example").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_ai_prompt_module_does_not_crash_when_llm_settings_are_missing(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_path.write_text(
        settings_path.read_text(encoding="utf-8").replace(
            '    llm_provider: str = "openai"\n',
            "",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0
    assert not (package_root / "modules" / "assistant").exists()
    assert (package_root / "integrations" / "llm").exists()


def test_remove_ai_prompt_module_keeps_shared_llm_scaffold_when_other_ai_exists(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )
    second_result = run_cli(
        project_root, "add", "module", "copilot", "--template", "ai-prompt"
    )
    assert first_result.returncode == 0
    assert second_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "assistant").exists()
    assert (package_root / "modules" / "copilot").exists()
    assert (package_root / "integrations" / "llm" / "factory.py").exists()
    assert "llm_provider" in (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    assert "LLM_PROVIDER" in (project_root / ".env.example").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_rejects_starter_module(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "remove", "module", "status")

    assert result.returncode != 0
    assert "Starter module cannot be removed: status" in result.stdout
    assert (project_root / "src" / "myapp" / "modules" / "status").exists()


def test_remove_module_accepts_multiline_router_wiring(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
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

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode == 0
    assert not (package_root / "modules" / "garage").exists()
    assert "garage_router" not in router_path.read_text(encoding="utf-8")


def test_remove_module_fails_before_deleting_when_router_alias_drifted(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
        "from myapp.modules.garage.router import router as garage_router",
        "from myapp.modules.garage.router import router as "
        "custom_garage_router",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "project layout is not ready" in result.stdout
    assert "router import" in result.stdout
    assert (package_root / "modules" / "garage").exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()


def test_remove_module_fails_before_deleting_when_manifest_is_non_utf8(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "project layout is not ready" in result.stdout
    assert "Could not read project manifest as UTF-8" in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr
    assert (package_root / "modules" / "garage").exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert manifest_path.read_bytes() == b"\xff\xfe\x00"


def test_remove_module_fails_before_deleting_when_router_is_non_utf8(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "project layout is not ready" in result.stdout
    assert "Could not read managed text file for removal" in result.stdout
    assert "api/router.py" in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr
    assert (package_root / "modules" / "garage").exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()


def test_remove_module_fails_before_delete_when_custom_router_ref_exists(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8")
        + "\n"
        + "from myapp.modules.garage.router import router as "
        "garage_custom_router\n"
        + "api_router.include_router(garage_custom_router, "
        'prefix="/garage-custom", tags=["garage_custom"])\n',
        encoding="utf-8",
    )

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "project layout is not ready" in result.stdout
    assert "router import" in result.stdout
    assert "router include" in result.stdout
    assert (package_root / "modules" / "garage").exists()
    assert "garage_custom_router" in router_path.read_text(encoding="utf-8")


def test_remove_module_fails_before_deleting_when_custom_model_reference_exists(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    models_path = package_root / "db" / "models.py"
    models_path.write_text(
        models_path.read_text(encoding="utf-8")
        + "\nfrom myapp.modules.garage import model as garage_model\n",
        encoding="utf-8",
    )

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "project layout is not ready" in result.stdout
    assert "model import" in result.stdout
    assert (package_root / "modules" / "garage").exists()
    assert "garage_model" in models_path.read_text(encoding="utf-8")


def test_remove_module_ignores_comments_when_router_import_is_already_missing(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8").replace(
        "from myapp.modules.garage.router import router as garage_router\n",
        "# removed import: myapp.modules.garage.router\n",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode == 0
    assert not (package_root / "modules" / "garage").exists()
    assert "garage_router" not in router_path.read_text(encoding="utf-8")


def test_remove_module_works_from_nested_directory(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    nested_dir = project_root / "src" / "myapp" / "modules" / "garage"
    result = run_cli(nested_dir, "remove", "module", "garage")

    assert result.returncode == 0
    assert not nested_dir.exists()
