"""Add model registry schema.

Revision ID: 202607180005
Revises: 202607180004
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607180005"
down_revision: str | None = "202607180004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registered_models",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
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
            name="uq_registered_models_project_slug",
        ),
    )
    op.create_index("ix_registered_models_organization_id", "registered_models", ["organization_id"])
    op.create_index("ix_registered_models_project_id", "registered_models", ["project_id"])
    op.create_index("ix_registered_models_slug", "registered_models", ["slug"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("registered_model_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("training_run_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_run_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_uri", sa.String(length=2048), nullable=False),
        sa.Column("model_format", sa.String(length=64), nullable=False),
        sa.Column("signature_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["experiment_run_id"], ["experiment_runs.id"]),
        sa.ForeignKeyConstraint(["registered_model_id"], ["registered_models.id"]),
        sa.ForeignKeyConstraint(["training_run_id"], ["training_runs.id"]),
        sa.UniqueConstraint(
            "registered_model_id",
            "version",
            name="uq_model_versions_registered_model_version",
        ),
        sa.UniqueConstraint(
            "registered_model_id",
            "training_run_id",
            name="uq_model_versions_registered_model_training_run",
        ),
    )
    op.create_index("ix_model_versions_registered_model_id", "model_versions", ["registered_model_id"])
    op.create_index("ix_model_versions_training_run_id", "model_versions", ["training_run_id"])
    op.create_index("ix_model_versions_experiment_run_id", "model_versions", ["experiment_run_id"])

    op.create_table(
        "model_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("comment", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("policy_snapshot_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
    )
    op.create_index("ix_model_approvals_model_version_id", "model_approvals", ["model_version_id"])

    op.create_table(
        "model_lineage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
    )
    op.create_index("ix_model_lineage_model_version_id", "model_lineage", ["model_version_id"])


def downgrade() -> None:
    op.drop_index("ix_model_lineage_model_version_id", table_name="model_lineage")
    op.drop_table("model_lineage")
    op.drop_index("ix_model_approvals_model_version_id", table_name="model_approvals")
    op.drop_table("model_approvals")
    op.drop_index("ix_model_versions_experiment_run_id", table_name="model_versions")
    op.drop_index("ix_model_versions_training_run_id", table_name="model_versions")
    op.drop_index("ix_model_versions_registered_model_id", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index("ix_registered_models_slug", table_name="registered_models")
    op.drop_index("ix_registered_models_project_id", table_name="registered_models")
    op.drop_index("ix_registered_models_organization_id", table_name="registered_models")
    op.drop_table("registered_models")
