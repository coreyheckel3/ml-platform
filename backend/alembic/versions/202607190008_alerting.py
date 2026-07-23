"""Add alerting rules and events schema.

Revision ID: 202607190008
Revises: 202607190007
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190008"
down_revision: str | None = "202607190007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=16), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            name="uq_alert_rules_project_slug",
        ),
    )
    op.create_index("ix_alert_rules_organization_id", "alert_rules", ["organization_id"])
    op.create_index("ix_alert_rules_project_id", "alert_rules", ["project_id"])
    op.create_index("ix_alert_rules_slug", "alert_rules", ["slug"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("alert_rule_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "triggered_at",
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
        sa.ForeignKeyConstraint(["alert_rule_id"], ["alert_rules.id"]),
        sa.ForeignKeyConstraint(["endpoint_id"], ["inference_endpoints.id"]),
    )
    op.create_index("ix_alert_events_organization_id", "alert_events", ["organization_id"])
    op.create_index("ix_alert_events_project_id", "alert_events", ["project_id"])
    op.create_index("ix_alert_events_alert_rule_id", "alert_events", ["alert_rule_id"])
    op.create_index("ix_alert_events_endpoint_id", "alert_events", ["endpoint_id"])
    op.create_index("ix_alert_events_status", "alert_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_status", table_name="alert_events")
    op.drop_index("ix_alert_events_endpoint_id", table_name="alert_events")
    op.drop_index("ix_alert_events_alert_rule_id", table_name="alert_events")
    op.drop_index("ix_alert_events_project_id", table_name="alert_events")
    op.drop_index("ix_alert_events_organization_id", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_alert_rules_slug", table_name="alert_rules")
    op.drop_index("ix_alert_rules_project_id", table_name="alert_rules")
    op.drop_index("ix_alert_rules_organization_id", table_name="alert_rules")
    op.drop_table("alert_rules")
