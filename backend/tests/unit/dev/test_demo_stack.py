from pathlib import Path

from scripts.dev.demo_stack import (
    DEFAULT_API_URL,
    DEFAULT_FRONTEND_URL,
    DemoStackConfig,
    build_api_command,
    build_bootstrap_commands,
    build_demo_plan,
    build_demo_reset_command,
    build_demo_summary,
    build_frontend_command,
    build_release_evidence_refresh_command,
    build_release_manifest_command,
    port_from_url,
)


def test_demo_plan_includes_full_reviewer_stack(tmp_path: Path) -> None:
    config = demo_config(tmp_path)

    plan = build_demo_plan(config)
    command_codes = [command["code"] for command in plan["commands"]]

    assert plan["schema_version"] == "forgeml.demo_stack.v1"
    assert plan["credentials"]["email"] == "admin@forgeml.dev"
    assert plan["demo_projects"] == [
        "movie-recommendation",
        "semantic-search",
        "fraud-detection",
    ]
    assert command_codes == [
        "core_services",
        "database_migrations",
        "admin_seed",
        "release_manifest",
        "backend_api",
        "demo_data_refresh",
        "release_evidence_refresh",
        "frontend",
    ]
    assert plan["release_evidence_output"].endswith("release-evidence-refresh.json")


def test_demo_plan_respects_skip_flags(tmp_path: Path) -> None:
    config = demo_config(
        tmp_path,
        skip_docker=True,
        skip_examples=True,
        skip_release_evidence=True,
        no_frontend=True,
    )

    plan = build_demo_plan(config)

    assert [command["code"] for command in plan["commands"]] == [
        "database_migrations",
        "admin_seed",
        "backend_api",
    ]


def test_demo_plan_supports_fresh_reset(tmp_path: Path) -> None:
    config = demo_config(tmp_path, fresh=True, no_frontend=True)

    plan = build_demo_plan(config)
    reset_command = build_demo_reset_command(config)

    assert plan["fresh"] is True
    assert [command["code"] for command in plan["commands"]][:2] == [
        "demo_reset",
        "core_services",
    ]
    assert reset_command.command[:2] == (".venv/bin/python", "scripts/dev/demo_reset.py")
    assert "--release-manifest-output" in reset_command.command


def test_demo_commands_wire_ports_and_proxy_target(tmp_path: Path) -> None:
    config = demo_config(
        tmp_path,
        api_url="http://127.0.0.1:8100",
        frontend_url="http://127.0.0.1:5200",
    )

    api_command = build_api_command(config)
    frontend_command = build_frontend_command(config)
    manifest_command = build_release_manifest_command(config)
    evidence_command = build_release_evidence_refresh_command(config)
    bootstrap_commands = build_bootstrap_commands(config)

    assert api_command.command[api_command.command.index("--port") + 1] == "8100"
    assert api_command.environment["PYTHONPATH"] == "backend/src:."
    assert frontend_command.command[frontend_command.command.index("--port") + 1] == "5200"
    assert frontend_command.environment["VITE_FORGEML_API_PROXY_TARGET"] == (
        "http://127.0.0.1:8100"
    )
    assert manifest_command.command[-1].endswith("forgeml-release-manifest.json")
    assert evidence_command.command[evidence_command.command.index("--base-url") + 1] == (
        "http://127.0.0.1:8100"
    )
    assert "--force" in evidence_command.command
    assert bootstrap_commands[1].environment["PYTHONPATH"] == "backend/src"


def test_demo_summary_records_manual_review_paths(tmp_path: Path) -> None:
    config = demo_config(tmp_path)

    summary = build_demo_summary(config, api_ready=True, frontend_ready=True)

    assert summary["schema_version"] == "forgeml.demo_stack.v1"
    assert summary["api_ready"] is True
    assert summary["frontend_ready"] is True
    assert summary["seeded_evidence_ready"] is True
    assert "/portfolio" in summary["manual_review_paths"]
    assert "/training-runs" in summary["manual_review_paths"]
    assert "/monitoring" in summary["manual_review_paths"]
    assert "/release-evidence" in summary["manual_review_paths"]
    assert "/operational-audit" in summary["manual_review_paths"]
    assert "/admin" in summary["manual_review_paths"]


def test_port_from_url_uses_explicit_or_scheme_default() -> None:
    assert port_from_url(DEFAULT_API_URL) == 8001
    assert port_from_url(DEFAULT_FRONTEND_URL) == 5173
    assert port_from_url("https://forgeml.example") == 443
    assert port_from_url("http://forgeml.example") == 80


def demo_config(
    tmp_path: Path,
    *,
    api_url: str = DEFAULT_API_URL,
    frontend_url: str = DEFAULT_FRONTEND_URL,
    skip_docker: bool = False,
    skip_examples: bool = False,
    skip_release_evidence: bool = False,
    no_frontend: bool = False,
    fresh: bool = False,
) -> DemoStackConfig:
    return DemoStackConfig(
        repo_root=Path("."),
        api_url=api_url,
        frontend_url=frontend_url,
        artifact_root=tmp_path / "artifacts",
        summary_output=tmp_path / "demo-stack-summary.json",
        data_refresh_output=tmp_path / "demo-data-refresh.json",
        demo_reset_output=tmp_path / "demo-reset-report.json",
        release_manifest_output=tmp_path / "dist/release/forgeml-release-manifest.json",
        release_evidence_output=tmp_path / "release-evidence-refresh.json",
        fresh=fresh,
        skip_docker=skip_docker,
        skip_examples=skip_examples,
        skip_release_evidence=skip_release_evidence,
        no_frontend=no_frontend,
        exit_after_bootstrap=True,
        api_timeout_seconds=1.0,
        frontend_timeout_seconds=1.0,
    )
