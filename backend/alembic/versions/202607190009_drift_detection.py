"""Add drift detection profiles and reports schema.

Revision ID: 202607190009
Revises: 202607190008
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190009"
down_revision: str | None = "202607190008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drift_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("model_version_id", sa.Uuid(), nullable=True),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=True),
        sa.Column("baseline_profile_json", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "slug",
            name="uq_drift_profiles_project_slug",
        ),
    )
    op.create_index("ix_drift_profiles_organization_id", "drift_profiles", ["organization_id"])
    op.create_index("ix_drift_profiles_project_id", "drift_profiles", ["project_id"])
    op.create_index("ix_drift_profiles_slug", "drift_profiles", ["slug"])
    op.create_index("ix_drift_profiles_model_version_id", "drift_profiles", ["model_version_id"])
    op.create_index(
        "ix_drift_profiles_dataset_version_id",
        "drift_profiles",
        ["dataset_version_id"],
    )

    op.create_table(
        "drift_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("drift_profile_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("deployment_revision_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("drifted_feature_count", sa.Integer(), nullable=False),
        sa.Column("evaluated_feature_count", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("drift_threshold", sa.Float(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("report_uri", sa.String(length=2048), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["drift_profile_id"], ["drift_profiles.id"]),
        sa.ForeignKeyConstraint(["endpoint_id"], ["inference_endpoints.id"]),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"]),
        sa.ForeignKeyConstraint(["deployment_revision_id"], ["deployment_revisions.id"]),
    )
    op.create_index("ix_drift_reports_organization_id", "drift_reports", ["organization_id"])
    op.create_index("ix_drift_reports_project_id", "drift_reports", ["project_id"])
    op.create_index("ix_drift_reports_drift_profile_id", "drift_reports", ["drift_profile_id"])
    op.create_index("ix_drift_reports_endpoint_id", "drift_reports", ["endpoint_id"])
    op.create_index("ix_drift_reports_deployment_id", "drift_reports", ["deployment_id"])
    op.create_index(
        "ix_drift_reports_deployment_revision_id",
        "drift_reports",
        ["deployment_revision_id"],
    )

    op.create_table(
        "drift_feature_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("drift_report_id", sa.Uuid(), nullable=False),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("feature_type", sa.String(length=32), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("drift_detected", sa.Boolean(), nullable=False),
        sa.Column("statistics_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["drift_report_id"], ["drift_reports.id"]),
    )
    op.create_index(
        "ix_drift_feature_results_drift_report_id",
        "drift_feature_results",
        ["drift_report_id"],
    )
    op.create_index(
        "ix_drift_feature_results_feature_name",
        "drift_feature_results",
        ["feature_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_drift_feature_results_feature_name", table_name="drift_feature_results")
    op.drop_index(
        "ix_drift_feature_results_drift_report_id",
        table_name="drift_feature_results",
    )
    op.drop_table("drift_feature_results")
    op.drop_index("ix_drift_reports_deployment_revision_id", table_name="drift_reports")
    op.drop_index("ix_drift_reports_deployment_id", table_name="drift_reports")
    op.drop_index("ix_drift_reports_endpoint_id", table_name="drift_reports")
    op.drop_index("ix_drift_reports_drift_profile_id", table_name="drift_reports")
    op.drop_index("ix_drift_reports_project_id", table_name="drift_reports")
    op.drop_index("ix_drift_reports_organization_id", table_name="drift_reports")
    op.drop_table("drift_reports")
    op.drop_index("ix_drift_profiles_dataset_version_id", table_name="drift_profiles")
    op.drop_index("ix_drift_profiles_model_version_id", table_name="drift_profiles")
    op.drop_index("ix_drift_profiles_slug", table_name="drift_profiles")
    op.drop_index("ix_drift_profiles_project_id", table_name="drift_profiles")
    op.drop_index("ix_drift_profiles_organization_id", table_name="drift_profiles")
    op.drop_table("drift_profiles")
