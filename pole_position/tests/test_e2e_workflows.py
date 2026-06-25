import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request

import pytest

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


def run_in_project(
    project_root: Path,
    *args: str,
    uv_cache_dir: Path,
    **extra_env: str,
) -> subprocess.CompletedProcess[str]:
    env = build_project_env(uv_cache_dir, **extra_env)

    return subprocess.run(
        list(args),
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
    )


def build_project_env(uv_cache_dir: Path, **extra_env: str) -> dict[str, str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(uv_cache_dir)
    env.update(extra_env)
    return env


def start_in_project(
    project_root: Path,
    *args: str,
    uv_cache_dir: Path,
    **extra_env: str,
) -> subprocess.Popen[str]:
    env = build_project_env(uv_cache_dir, **extra_env)
    return subprocess.Popen(
        list(args),
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def run_compose(
    project_root: Path,
    *args: str,
    uv_cache_dir: Path,
    **extra_env: str,
) -> subprocess.CompletedProcess[str]:
    return run_in_project(
        project_root,
        "docker",
        "compose",
        *args,
        uv_cache_dir=uv_cache_dir,
        **extra_env,
    )


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return sock.getsockname()[1]


def wait_for_status(
    port: int, timeout_seconds: float = 20.0
) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    url = f"http://127.0.0.1:{port}/api/v1/status"
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=1) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except Exception as exc:  # pragma: no cover - exercised in e2e only
            last_error = exc
            time.sleep(0.25)

    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLEPOSITION_RUN_E2E") != "1",
    reason="Set POLEPOSITION_RUN_E2E=1 to run end-to-end workflow tests.",
)
@pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv is required for end-to-end workflow tests.",
)
def test_e2e_start_project_and_run_generated_tests(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")

    assert create_result.returncode == 0, create_result.stderr

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")

    assert add_result.returncode == 0, add_result.stderr

    # Exercise a service-only module too, so its generated database-backed
    # service test runs against the real environment alongside the standard
    # module's HTTP tests.
    service_only_result = run_cli(
        project_root, "add", "module", "notifications", "--service-only"
    )

    assert service_only_result.returncode == 0, service_only_result.stderr

    env_example = project_root / ".env.example"
    env_file = project_root / ".env"
    env_file.write_text(
        env_example.read_text(encoding="utf-8"), encoding="utf-8"
    )

    uv_cache_dir = tmp_path / ".uv-cache"
    sync_result = run_in_project(
        project_root,
        "uv",
        "sync",
        "--extra",
        "dev",
        uv_cache_dir=uv_cache_dir,
    )

    assert sync_result.returncode == 0, (
        f"uv sync --extra dev "
        f"failed\nstdout:\n{sync_result.stdout}\nstderr:\n{sync_result.stderr}"
    )
    assert list(project_root.rglob("*.egg-info")) == []

    pytest_result = run_in_project(
        project_root, "uv", "run", "pytest", uv_cache_dir=uv_cache_dir
    )

    assert pytest_result.returncode == 0, (
        f"Generated project tests failed\nstdout:\n{pytest_result.stdout}\n"
        f"stderr:\n{pytest_result.stderr}"
    )
    assert "passed" in pytest_result.stdout

    check_result = run_cli(project_root, "check")

    assert check_result.returncode == 0, (
        f"Generated project check failed after "
        f"pytest\nstdout:\n{check_result.stdout}\n"
        f"stderr:\n{check_result.stderr}"
    )


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLEPOSITION_RUN_E2E") != "1",
    reason="Set POLEPOSITION_RUN_E2E=1 to run end-to-end workflow tests.",
)
@pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv is required for end-to-end workflow tests.",
)
def test_e2e_start_project_and_run_generated_app(tmp_path: Path) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")

    assert create_result.returncode == 0, create_result.stderr

    project_root = tmp_path / "myapp"
    env_example = project_root / ".env.example"
    port = find_free_port()
    env_file = project_root / ".env"
    env_file.write_text(
        env_example.read_text(encoding="utf-8")
        + f"\nAPP_RELOAD=false\nAPP_PORT={port}\n",
        encoding="utf-8",
    )

    uv_cache_dir = tmp_path / ".uv-cache"
    sync_result = run_in_project(
        project_root,
        "uv",
        "sync",
        "--extra",
        "dev",
        uv_cache_dir=uv_cache_dir,
    )

    assert sync_result.returncode == 0, (
        f"uv sync --extra dev "
        f"failed\nstdout:\n{sync_result.stdout}\nstderr:\n{sync_result.stderr}"
    )

    process = start_in_project(
        project_root,
        "uv",
        "run",
        "python",
        "-m",
        "myapp.run",
        uv_cache_dir=uv_cache_dir,
    )

    try:
        status_payload = wait_for_status(port)
        assert status_payload["status"] == "ok"
        assert status_payload["service"] == "myapp"
    except Exception:
        stdout, stderr = process.communicate(timeout=5)
        raise AssertionError(
            "Generated app failed to start with `uv run python -m myapp.run`\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        ) from None
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


@pytest.mark.e2e
@pytest.mark.docker_e2e
@pytest.mark.skipif(
    os.environ.get("POLEPOSITION_RUN_DOCKER_E2E") != "1",
    reason="Set POLEPOSITION_RUN_DOCKER_E2E=1 to run Docker "
    "end-to-end workflow tests.",
)
@pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="docker is required for Docker end-to-end workflow tests.",
)
def test_e2e_start_project_and_run_generated_app_with_docker(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")

    assert create_result.returncode == 0, create_result.stderr

    project_root = tmp_path / "myapp"
    env_example = project_root / ".env.example"
    app_port = find_free_port()
    postgres_port = find_free_port()
    env_file = project_root / ".env"
    env_file.write_text(
        env_example.read_text(encoding="utf-8")
        + (
            f"\nAPP_PORT={app_port}\n"
            "APP_RELOAD=false\n"
            f"POSTGRES_PORT={postgres_port}\n"
        ),
        encoding="utf-8",
    )

    uv_cache_dir = tmp_path / ".uv-cache"

    try:
        up_result = run_compose(
            project_root, "up", "--build", "-d", uv_cache_dir=uv_cache_dir
        )
        assert up_result.returncode == 0, (
            f"docker compose up "
            f"failed\nstdout:\n{up_result.stdout}\nstderr:\n{up_result.stderr}"
        )

        migrate_result = run_compose(
            project_root,
            "run",
            "--rm",
            "app",
            "uv",
            "run",
            "alembic",
            "upgrade",
            "head",
            uv_cache_dir=uv_cache_dir,
        )
        assert migrate_result.returncode == 0, (
            "docker compose migration failed\n"
            f"stdout:\n{migrate_result.stdout}\n"
            f"stderr:\n{migrate_result.stderr}"
        )

        status_payload = wait_for_status(app_port, timeout_seconds=30.0)
        assert status_payload["status"] == "ok"
        assert status_payload["service"] == "myapp"
    finally:
        down_result = run_compose(
            project_root, "down", "-v", uv_cache_dir=uv_cache_dir
        )
        if down_result.returncode != 0:
            print(
                "docker compose down failed\n"
                f"stdout:\n{down_result.stdout}\n"
                f"stderr:\n{down_result.stderr}"
            )
