"""Add deployment control plane schema.

Revision ID: 202607190006
Revises: 202607180005
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190006"
down_revision: str | None = "202607180005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deployments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("environment", sa.String(length=32), nullable=False),
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
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "slug",
            name="uq_deployments_project_slug",
        ),
    )
    op.create_index("ix_deployments_organization_id", "deployments", ["organization_id"])
    op.create_index("ix_deployments_project_id", "deployments", ["project_id"])
    op.create_index("ix_deployments_slug", "deployments", ["slug"])

    op.create_table(
        "deployment_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("serving_image", sa.String(length=512), nullable=False),
        sa.Column("runtime_config_json", sa.JSON(), nullable=False),
        sa.Column("traffic_percentage", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("orchestrator_deployment_id", sa.String(length=512), nullable=False),
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
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
    )
    op.create_index("ix_deployment_revisions_deployment_id", "deployment_revisions", ["deployment_id"])
    op.create_index(
        "ix_deployment_revisions_model_version_id",
        "deployment_revisions",
        ["model_version_id"],
    )

    op.create_table(
        "deployment_health_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deployment_revision_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["deployment_revision_id"], ["deployment_revisions.id"]),
    )
    op.create_index(
        "ix_deployment_health_checks_deployment_revision_id",
        "deployment_health_checks",
        ["deployment_revision_id"],
    )

    op.create_table(
        "deployment_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_revision_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"]),
        sa.ForeignKeyConstraint(["deployment_revision_id"], ["deployment_revisions.id"]),
    )
    op.create_index("ix_deployment_events_deployment_id", "deployment_events", ["deployment_id"])
    op.create_index(
        "ix_deployment_events_deployment_revision_id",
        "deployment_events",
        ["deployment_revision_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_deployment_events_deployment_revision_id", table_name="deployment_events")
    op.drop_index("ix_deployment_events_deployment_id", table_name="deployment_events")
    op.drop_table("deployment_events")
    op.drop_index(
        "ix_deployment_health_checks_deployment_revision_id",
        table_name="deployment_health_checks",
    )
    op.drop_table("deployment_health_checks")
    op.drop_index(
        "ix_deployment_revisions_model_version_id",
        table_name="deployment_revisions",
    )
    op.drop_index("ix_deployment_revisions_deployment_id", table_name="deployment_revisions")
    op.drop_table("deployment_revisions")
    op.drop_index("ix_deployments_slug", table_name="deployments")
    op.drop_index("ix_deployments_project_id", table_name="deployments")
    op.drop_index("ix_deployments_organization_id", table_name="deployments")
    op.drop_table("deployments")
