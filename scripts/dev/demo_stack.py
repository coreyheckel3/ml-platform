from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

DEMO_STACK_SCHEMA_VERSION = "forgeml.demo_stack.v1"
DEFAULT_API_URL = "http://127.0.0.1:8001"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:5173"
DEFAULT_ARTIFACT_ROOT = Path(".forgeml/demo/artifacts")
DEFAULT_SUMMARY_OUTPUT = Path(".forgeml/demo/demo-stack-summary.json")
DEFAULT_DATA_REFRESH_OUTPUT = Path(".forgeml/demo/demo-data-refresh.json")


@dataclass(frozen=True)
class DemoCommand:
    code: str
    description: str
    command: tuple[str, ...]
    environment: dict[str, str]


@dataclass(frozen=True)
class DemoStackConfig:
    repo_root: Path
    api_url: str
    frontend_url: str
    artifact_root: Path
    summary_output: Path
    data_refresh_output: Path
    skip_docker: bool
    skip_examples: bool
    no_frontend: bool
    exit_after_bootstrap: bool
    api_timeout_seconds: float
    frontend_timeout_seconds: float


class DemoStackError(RuntimeError):
    pass


def build_demo_plan(config: DemoStackConfig) -> dict[str, Any]:
    commands = [
        *build_bootstrap_commands(config),
        build_api_command(config),
    ]
    if not config.skip_examples:
        commands.append(build_demo_data_refresh_command(config))
    if not config.no_frontend:
        commands.append(build_frontend_command(config))
    return {
        "schema_version": DEMO_STACK_SCHEMA_VERSION,
        "api_url": config.api_url,
        "frontend_url": config.frontend_url,
        "summary_output": config.summary_output.as_posix(),
        "artifact_root": config.artifact_root.as_posix(),
        "commands": [serialize_command(command) for command in commands],
        "credentials": {
            "email": "admin@forgeml.dev",
            "password": "forgeml-local-admin",
        },
        "demo_projects": [
            "movie-recommendation",
            "semantic-search",
            "fraud-detection",
        ],
    }


def build_bootstrap_commands(config: DemoStackConfig) -> list[DemoCommand]:
    commands: list[DemoCommand] = []
    if not config.skip_docker:
        commands.append(
            DemoCommand(
                code="core_services",
                description="Start PostgreSQL, Redis, and MinIO for local demo state.",
                command=(
                    "docker",
                    "compose",
                    "-f",
                    "infra/compose/docker-compose.yml",
                    "--profile",
                    "core",
                    "up",
                    "-d",
                    "postgres",
                    "redis",
                    "minio",
                ),
                environment={},
            )
        )
    commands.extend(
        [
            DemoCommand(
                code="database_migrations",
                description="Apply Alembic migrations to the local control-plane database.",
                command=(".venv/bin/alembic", "-c", "backend/alembic.ini", "upgrade", "head"),
                environment={"PYTHONPATH": "backend/src"},
            ),
            DemoCommand(
                code="admin_seed",
                description="Seed the local admin organization and console account.",
                command=(".venv/bin/python", "scripts/dev/seed_backend.py"),
                environment={"PYTHONPATH": "backend/src"},
            ),
        ]
    )
    return commands


def build_api_command(config: DemoStackConfig) -> DemoCommand:
    parsed = urlparse(config.api_url)
    return DemoCommand(
        code="backend_api",
        description="Run the FastAPI control plane.",
        command=(
            ".venv/bin/uvicorn",
            "forgeml.main:create_app",
            "--factory",
            "--host",
            parsed.hostname or "127.0.0.1",
            "--port",
            str(port_from_url(config.api_url)),
            "--reload",
            "--app-dir",
            "backend/src",
        ),
        environment={"PYTHONPATH": "backend/src:."},
    )


def build_demo_data_refresh_command(config: DemoStackConfig) -> DemoCommand:
    return DemoCommand(
        code="demo_data_refresh",
        description="Refresh example projects through ForgeML public APIs.",
        command=(
            ".venv/bin/python",
            "scripts/dev/refresh_demo_data.py",
            "--base-url",
            config.api_url,
            "--artifact-root",
            config.artifact_root.as_posix(),
            "--output",
            config.data_refresh_output.as_posix(),
        ),
        environment={"PYTHONPATH": "backend/src:."},
    )


def build_frontend_command(config: DemoStackConfig) -> DemoCommand:
    parsed = urlparse(config.frontend_url)
    return DemoCommand(
        code="frontend",
        description="Run the Vite console with the API proxy pointed at the local backend.",
        command=(
            "npm",
            "--prefix",
            "frontend",
            "run",
            "dev",
            "--",
            "--host",
            parsed.hostname or "127.0.0.1",
            "--port",
            str(port_from_url(config.frontend_url)),
            "--strictPort",
        ),
        environment={"VITE_FORGEML_API_PROXY_TARGET": config.api_url},
    )


def serialize_command(command: DemoCommand) -> dict[str, Any]:
    return {
        **asdict(command),
        "command": list(command.command),
    }


def port_from_url(url: str) -> int:
    parsed = urlparse(url)
    if parsed.port is not None:
        return parsed.port
    if parsed.scheme == "https":
        return 443
    return 80


def run_demo_stack(config: DemoStackConfig) -> dict[str, Any]:
    for command in build_bootstrap_commands(config):
        run_command(command, config.repo_root)

    api_process = start_process(build_api_command(config), config.repo_root)
    managed_processes = [api_process]
    try:
        wait_for_http(f"{config.api_url.rstrip('/')}/health/ready", config.api_timeout_seconds)
        if not config.skip_examples:
            run_command(build_demo_data_refresh_command(config), config.repo_root)

        frontend_ready = False
        if not config.no_frontend:
            frontend_process = start_process(build_frontend_command(config), config.repo_root)
            managed_processes.append(frontend_process)
            wait_for_http(config.frontend_url, config.frontend_timeout_seconds)
            frontend_ready = True

        summary = build_demo_summary(
            config,
            api_ready=True,
            frontend_ready=frontend_ready,
        )
        write_summary(summary, config.summary_output)
        if config.exit_after_bootstrap:
            return summary
        print_summary(summary)
        wait_forever(managed_processes)
        return summary
    finally:
        terminate_processes(managed_processes)


def run_command(command: DemoCommand, repo_root: Path) -> None:
    print(f"[demo] {command.description}")
    result = subprocess.run(  # noqa: S603
        list(command.command),
        cwd=repo_root,
        env=merged_environment(command.environment),
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise DemoStackError(
            f"Demo command failed with exit code {result.returncode}: {' '.join(command.command)}"
        )


def start_process(command: DemoCommand, repo_root: Path) -> subprocess.Popen[str]:
    print(f"[demo] {command.description}")
    return subprocess.Popen(  # noqa: S603
        list(command.command),
        cwd=repo_root,
        env=merged_environment(command.environment),
        text=True,
    )


def merged_environment(overrides: dict[str, str]) -> dict[str, str]:
    environment = os.environ.copy()
    for key, value in overrides.items():
        if key == "PYTHONPATH" and environment.get("PYTHONPATH"):
            environment[key] = f"{value}{os.pathsep}{environment[key]}"
        else:
            environment[key] = value
    return environment


def wait_for_http(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with request.urlopen(url, timeout=2.0) as response:  # noqa: S310
                if response.status < 500:
                    return
                last_error = f"HTTP {response.status}"
        except error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
        except OSError as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise DemoStackError(f"Timed out waiting for {url}: {last_error}")


def build_demo_summary(
    config: DemoStackConfig,
    *,
    api_ready: bool,
    frontend_ready: bool,
) -> dict[str, Any]:
    return {
        "schema_version": DEMO_STACK_SCHEMA_VERSION,
        "api_url": config.api_url,
        "frontend_url": config.frontend_url,
        "api_ready": api_ready,
        "frontend_ready": frontend_ready,
        "data_refresh_output": config.data_refresh_output.as_posix(),
        "artifact_root": config.artifact_root.as_posix(),
        "credentials": {
            "email": "admin@forgeml.dev",
            "password": "forgeml-local-admin",
        },
        "manual_review_paths": [
            "/projects",
            "/datasets",
            "/training-runs",
            "/models",
            "/deployments",
            "/inference",
            "/monitoring",
            "/alerts",
            "/drift",
            "/retraining",
        ],
    }


def write_summary(summary: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_summary(summary: dict[str, Any]) -> None:
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("[demo] ForgeML demo stack is running. Press Ctrl+C to stop the managed processes.")


def wait_forever(processes: list[subprocess.Popen[str]]) -> None:
    while True:
        for process in processes:
            return_code = process.poll()
            if return_code is not None:
                raise DemoStackError(f"Managed demo process exited with code {return_code}.")
        time.sleep(2.0)


def terminate_processes(processes: list[subprocess.Popen[str]]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
    deadline = time.monotonic() + 10
    for process in reversed(processes):
        if process.poll() is not None:
            continue
        remaining = max(0.1, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ForgeML local demo stack.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--data-refresh-output", type=Path, default=DEFAULT_DATA_REFRESH_OUTPUT)
    parser.add_argument("--skip-docker", action="store_true")
    parser.add_argument("--skip-examples", action="store_true")
    parser.add_argument("--no-frontend", action="store_true")
    parser.add_argument("--exit-after-bootstrap", action="store_true")
    parser.add_argument("--api-timeout-seconds", type=float, default=90.0)
    parser.add_argument("--frontend-timeout-seconds", type=float, default=60.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command plan without starting services.",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> DemoStackConfig:
    return DemoStackConfig(
        repo_root=args.repo_root.resolve(),
        api_url=args.api_url,
        frontend_url=args.frontend_url,
        artifact_root=args.artifact_root,
        summary_output=args.summary_output,
        data_refresh_output=args.data_refresh_output,
        skip_docker=args.skip_docker,
        skip_examples=args.skip_examples,
        no_frontend=args.no_frontend,
        exit_after_bootstrap=args.exit_after_bootstrap,
        api_timeout_seconds=args.api_timeout_seconds,
        frontend_timeout_seconds=args.frontend_timeout_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = config_from_args(args)
    if args.dry_run:
        print(json.dumps(build_demo_plan(config), indent=2, sort_keys=True))
        return 0
    try:
        run_demo_stack(config)
    except KeyboardInterrupt:
        print("[demo] Stopped ForgeML demo stack.")
    except DemoStackError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
