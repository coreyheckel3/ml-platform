"""Add automatic retraining policies and runs schema.

Revision ID: 202607190010
Revises: 202607190009
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190010"
down_revision: str | None = "202607190009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retraining_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_config_json", sa.JSON(), nullable=False),
        sa.Column("training_template_json", sa.JSON(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("max_runs_per_day", sa.Integer(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "slug",
            name="uq_retraining_policies_project_slug",
        ),
    )
    op.create_index(
        "ix_retraining_policies_organization_id",
        "retraining_policies",
        ["organization_id"],
    )
    op.create_index("ix_retraining_policies_project_id", "retraining_policies", ["project_id"])
    op.create_index(
        "ix_retraining_policies_deployment_id",
        "retraining_policies",
        ["deployment_id"],
    )
    op.create_index("ix_retraining_policies_slug", "retraining_policies", ["slug"])
    op.create_index(
        "ix_retraining_policies_trigger_type",
        "retraining_policies",
        ["trigger_type"],
    )
    op.create_index("ix_retraining_policies_status", "retraining_policies", ["status"])

    op.create_table(
        "retraining_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("drift_report_id", sa.Uuid(), nullable=True),
        sa.Column("alert_event_id", sa.Uuid(), nullable=True),
        sa.Column("training_run_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=2000), nullable=False),
        sa.Column("training_config_json", sa.JSON(), nullable=False),
        sa.Column("decision_metadata_json", sa.JSON(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("rejected_by", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["policy_id"], ["retraining_policies.id"]),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"]),
        sa.ForeignKeyConstraint(["drift_report_id"], ["drift_reports.id"]),
        sa.ForeignKeyConstraint(["alert_event_id"], ["alert_events.id"]),
        sa.ForeignKeyConstraint(["training_run_id"], ["training_runs.id"]),
    )
    op.create_index("ix_retraining_runs_organization_id", "retraining_runs", ["organization_id"])
    op.create_index("ix_retraining_runs_project_id", "retraining_runs", ["project_id"])
    op.create_index("ix_retraining_runs_policy_id", "retraining_runs", ["policy_id"])
    op.create_index("ix_retraining_runs_deployment_id", "retraining_runs", ["deployment_id"])
    op.create_index("ix_retraining_runs_trigger_type", "retraining_runs", ["trigger_type"])
    op.create_index("ix_retraining_runs_drift_report_id", "retraining_runs", ["drift_report_id"])
    op.create_index("ix_retraining_runs_alert_event_id", "retraining_runs", ["alert_event_id"])
    op.create_index("ix_retraining_runs_training_run_id", "retraining_runs", ["training_run_id"])
    op.create_index("ix_retraining_runs_status", "retraining_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_retraining_runs_status", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_training_run_id", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_alert_event_id", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_drift_report_id", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_trigger_type", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_deployment_id", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_policy_id", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_project_id", table_name="retraining_runs")
    op.drop_index("ix_retraining_runs_organization_id", table_name="retraining_runs")
    op.drop_table("retraining_runs")
    op.drop_index("ix_retraining_policies_status", table_name="retraining_policies")
    op.drop_index("ix_retraining_policies_trigger_type", table_name="retraining_policies")
    op.drop_index("ix_retraining_policies_slug", table_name="retraining_policies")
    op.drop_index("ix_retraining_policies_deployment_id", table_name="retraining_policies")
    op.drop_index("ix_retraining_policies_project_id", table_name="retraining_policies")
    op.drop_index("ix_retraining_policies_organization_id", table_name="retraining_policies")
    op.drop_table("retraining_policies")
