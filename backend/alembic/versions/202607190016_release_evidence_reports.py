"""Add release evidence report persistence.

Revision ID: 202607190016
Revises: 202607190015
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190016"
down_revision: str | None = "202607190015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_evidence_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("repository", sa.String(length=256), nullable=True),
        sa.Column("branch", sa.String(length=128), nullable=True),
        sa.Column("workflow", sa.String(length=128), nullable=True),
        sa.Column("artifact_name", sa.String(length=128), nullable=True),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("run_url", sa.String(length=512), nullable=True),
        sa.Column("manifest_git_sha", sa.String(length=64), nullable=True),
        sa.Column("manifest_git_branch", sa.String(length=128), nullable=True),
        sa.Column("ci_run_url", sa.String(length=512), nullable=True),
        sa.Column("artifact_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_gate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "missing_artifacts_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "missing_quality_gates_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "comparison_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "manifest_summary_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "report_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index(
        "ix_release_evidence_reports_organization_id",
        "release_evidence_reports",
        ["organization_id"],
    )
    op.create_index(
        "ix_release_evidence_reports_status",
        "release_evidence_reports",
        ["status"],
    )
    op.create_index(
        "ix_release_evidence_reports_organization_created",
        "release_evidence_reports",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_release_evidence_reports_organization_status",
        "release_evidence_reports",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_release_evidence_reports_organization_status",
        table_name="release_evidence_reports",
    )
    op.drop_index(
        "ix_release_evidence_reports_organization_created",
        table_name="release_evidence_reports",
    )
    op.drop_index("ix_release_evidence_reports_status", table_name="release_evidence_reports")
    op.drop_index(
        "ix_release_evidence_reports_organization_id",
        table_name="release_evidence_reports",
    )
    op.drop_table("release_evidence_reports")
