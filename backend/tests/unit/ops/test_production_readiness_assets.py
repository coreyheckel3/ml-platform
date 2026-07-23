import json
from pathlib import Path

from scripts.ci.production_readiness import run_checks


def test_production_readiness_checks_pass() -> None:
    checks = run_checks(Path("."))

    failed = [check for check in checks if not check.passed]

    assert failed == []


def test_grafana_dashboard_has_prometheus_panels() -> None:
    dashboard = json.loads(
        Path("infra/observability/grafana/dashboards/forgeml-platform.json").read_text(
            encoding="utf-8"
        )
    )

    panel_titles = {panel["title"] for panel in dashboard["panels"]}

    assert dashboard["uid"] == "forgeml-platform-health"
    assert {
        "API Request Rate",
        "API Latency P95",
        "API Error Rate",
        "Rate Limited Requests",
    }.issubset(panel_titles)


def test_compose_file_mounts_observability_configuration() -> None:
    compose = Path("infra/compose/docker-compose.yml").read_text(encoding="utf-8")

    assert "../observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" in compose
    assert "../observability/grafana/provisioning:/etc/grafana/provisioning:ro" in compose
    assert "../observability/grafana/dashboards:/var/lib/grafana/dashboards:ro" in compose
    assert "grafana-data:" in compose
