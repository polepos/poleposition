from pathlib import Path
import os
import subprocess
import sys


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

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "garage").exists()
    assert not (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert not (project_root / "tests" / "unit" / "test_garage_service.py").exists()

    router_content = (package_root / "api" / "router.py").read_text(encoding="utf-8")
    db_models_content = (package_root / "db" / "models.py").read_text(encoding="utf-8")
    modules_init_content = (package_root / "modules" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "garage_router" not in router_content
    assert "modules.garage" not in router_content
    assert "modules.garage" not in db_models_content
    assert '"garage"' not in modules_init_content

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_module_trace_reports_plan_without_changing_files(tmp_path: Path):
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

    package_root = project_root / "src" / "myapp"
    assert (package_root / "modules" / "garage").exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert "garage_router" in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")


def test_remove_module_rejects_custom_module_files_without_force(tmp_path: Path):
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
    assert "garage_router" in (
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
    assert not (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert "garage_router" not in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_api_only_module_does_not_require_model_wiring(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "webhooks", "--api-only")
    assert add_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "webhooks")

    assert result.returncode == 0
    assert "Template: api-only" in result.stdout

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "webhooks").exists()
    assert not (project_root / "tests" / "integration" / "test_webhooks.py").exists()
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


def test_remove_last_ai_prompt_module_cleans_llm_shared_scaffold(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "assistant", "--template", "ai-prompt")
    assert add_result.returncode == 0

    result = run_cli(project_root, "remove", "module", "assistant")

    assert result.returncode == 0
    assert "Template: ai-prompt" in result.stdout

    package_root = project_root / "src" / "myapp"
    assert not (package_root / "modules" / "assistant").exists()
    assert not (package_root / "integrations" / "llm").exists()
    assert "llm_provider" not in (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    assert "LLM_PROVIDER" not in (project_root / ".env.example").read_text(
        encoding="utf-8"
    )

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_remove_last_ai_prompt_module_preserves_custom_llm_scaffold(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "assistant", "--template", "ai-prompt")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    custom_provider = package_root / "integrations" / "llm" / "custom_provider.py"
    custom_provider.write_text("class CustomProvider:\n    pass\n", encoding="utf-8")

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
    add_result = run_cli(project_root, "add", "module", "assistant", "--template", "ai-prompt")
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


def test_remove_ai_prompt_module_keeps_shared_llm_scaffold_when_another_ai_module_exists(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "module", "assistant", "--template", "ai-prompt")
    second_result = run_cli(project_root, "add", "module", "copilot", "--template", "ai-prompt")
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
        'api_router.include_router(garage_router, prefix="/garage", tags=["garage"])',
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
        "from myapp.modules.garage.router import router as custom_garage_router",
    )
    router_path.write_text(router_content, encoding="utf-8")

    result = run_cli(project_root, "remove", "module", "garage")

    assert result.returncode != 0
    assert "project layout is not ready" in result.stdout
    assert "router import" in result.stdout
    assert (package_root / "modules" / "garage").exists()
    assert (project_root / "tests" / "integration" / "test_garage.py").exists()


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
