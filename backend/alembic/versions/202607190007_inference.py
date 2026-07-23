"""Add inference serving control plane schema.

Revision ID: 202607190007
Revises: 202607190006
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190007"
down_revision: str | None = "202607190006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inference_endpoints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_revision_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("route_path", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"]),
        sa.ForeignKeyConstraint(["deployment_revision_id"], ["deployment_revisions.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "route_path",
            name="uq_inference_endpoints_project_route_path",
        ),
    )
    op.create_index(
        "ix_inference_endpoints_organization_id",
        "inference_endpoints",
        ["organization_id"],
    )
    op.create_index("ix_inference_endpoints_project_id", "inference_endpoints", ["project_id"])
    op.create_index(
        "ix_inference_endpoints_deployment_id",
        "inference_endpoints",
        ["deployment_id"],
    )
    op.create_index(
        "ix_inference_endpoints_deployment_revision_id",
        "inference_endpoints",
        ["deployment_revision_id"],
    )
    op.create_index("ix_inference_endpoints_slug", "inference_endpoints", ["slug"])
    op.create_index("ix_inference_endpoints_route_path", "inference_endpoints", ["route_path"])

    op.create_table(
        "inference_request_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_revision_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("input_payload_json", sa.JSON(), nullable=False),
        sa.Column("output_payload_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["inference_endpoints.id"]),
        sa.ForeignKeyConstraint(["deployment_revision_id"], ["deployment_revisions.id"]),
        sa.UniqueConstraint(
            "endpoint_id",
            "request_id",
            name="uq_inference_request_logs_endpoint_request_id",
        ),
    )
    op.create_index(
        "ix_inference_request_logs_endpoint_id",
        "inference_request_logs",
        ["endpoint_id"],
    )
    op.create_index(
        "ix_inference_request_logs_deployment_revision_id",
        "inference_request_logs",
        ["deployment_revision_id"],
    )
    op.create_index(
        "ix_inference_request_logs_request_id",
        "inference_request_logs",
        ["request_id"],
    )

    op.create_table(
        "inference_metric_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("prediction_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("p50_latency_ms", sa.Float(), nullable=False),
        sa.Column("p95_latency_ms", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["inference_endpoints.id"]),
    )
    op.create_index(
        "ix_inference_metric_snapshots_endpoint_id",
        "inference_metric_snapshots",
        ["endpoint_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inference_metric_snapshots_endpoint_id",
        table_name="inference_metric_snapshots",
    )
    op.drop_table("inference_metric_snapshots")
    op.drop_index("ix_inference_request_logs_request_id", table_name="inference_request_logs")
    op.drop_index(
        "ix_inference_request_logs_deployment_revision_id",
        table_name="inference_request_logs",
    )
    op.drop_index("ix_inference_request_logs_endpoint_id", table_name="inference_request_logs")
    op.drop_table("inference_request_logs")
    op.drop_index("ix_inference_endpoints_route_path", table_name="inference_endpoints")
    op.drop_index("ix_inference_endpoints_slug", table_name="inference_endpoints")
    op.drop_index(
        "ix_inference_endpoints_deployment_revision_id",
        table_name="inference_endpoints",
    )
    op.drop_index("ix_inference_endpoints_deployment_id", table_name="inference_endpoints")
    op.drop_index("ix_inference_endpoints_project_id", table_name="inference_endpoints")
    op.drop_index("ix_inference_endpoints_organization_id", table_name="inference_endpoints")
    op.drop_table("inference_endpoints")
