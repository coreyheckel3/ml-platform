from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.examples.bootstrap_examples import (  # noqa: E402
    build_bootstrap_summary_payload,
    run_bootstrap,
)

DEMO_DATA_REFRESH_SCHEMA_VERSION = "forgeml.demo_data_refresh.v1"
DEFAULT_BASE_URL = "http://127.0.0.1:8001"
DEFAULT_EMAIL = "admin@forgeml.dev"
DEFAULT_PASSWORD = "forgeml-local-admin"  # noqa: S105 - local demo account only.
DEFAULT_CATALOG_PATH = Path("examples/catalog.json")
DEFAULT_ARTIFACT_ROOT = Path(".forgeml/demo/artifacts")
DEFAULT_OUTPUT_PATH = Path(".forgeml/demo/demo-data-refresh.json")


def refresh_demo_data(
    *,
    base_url: str = DEFAULT_BASE_URL,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    selected_projects: list[str] | None = None,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
) -> dict[str, Any]:
    summaries = run_bootstrap(
        base_url=base_url,
        email=email,
        password=password,
        catalog_path=catalog_path,
        selected_projects=selected_projects,
        artifact_root=artifact_root,
    )
    bootstrap_summary = build_bootstrap_summary_payload(
        summaries,
        base_url=base_url,
        catalog_path=catalog_path,
        selected_projects=selected_projects,
        artifact_root=artifact_root,
    )
    project_slugs = [summary.slug for summary in summaries]
    return {
        "schema_version": DEMO_DATA_REFRESH_SCHEMA_VERSION,
        "base_url": base_url,
        "admin_email": email,
        "catalog_path": catalog_path.as_posix(),
        "artifact_root": artifact_root.as_posix(),
        "summary": {
            "project_count": len(project_slugs),
            "project_slugs": project_slugs,
            "seeded_surfaces": [
                "projects",
                "datasets",
                "feature_store",
                "experiments",
                "training_runs",
                "model_registry",
                "deployments",
                "inference",
                "monitoring",
                "alerts",
                "drift_detection",
                "retraining",
            ],
        },
        "bootstrap": bootstrap_summary,
    }


def serialize_refresh_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def write_refresh_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_refresh_report(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh ForgeML demo seed data against a running local API."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="Example project slug to seed. Repeat to seed multiple projects.",
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    report = refresh_demo_data(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        catalog_path=args.catalog,
        selected_projects=args.project,
        artifact_root=args.artifact_root,
    )
    write_refresh_report(report, args.output)
    print(serialize_refresh_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
