"""Add dataset registry schema.

Revision ID: 202607180002
Revises: 202607180001
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607180002"
down_revision: str | None = "202607180001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=32), nullable=False),
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
        sa.UniqueConstraint("organization_id", "project_id", "slug", name="uq_datasets_project_slug"),
    )
    op.create_index("ix_datasets_organization_id", "datasets", ["organization_id"])
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"])
    op.create_index("ix_datasets_slug", "datasets", ["slug"])

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_uri", sa.String(length=2048), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.UniqueConstraint("dataset_id", "version", name="uq_dataset_versions_dataset_version"),
    )
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"])

    op.create_table(
        "dataset_schemas",
        sa.Column("dataset_version_id", sa.Uuid(), primary_key=True),
        sa.Column("fields_json", sa.JSON(), nullable=False),
        sa.Column("inferred", sa.Boolean(), nullable=False),
        sa.Column("schema_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
    )
    op.create_index("ix_dataset_schemas_schema_hash", "dataset_schemas", ["schema_hash"])

    op.create_table(
        "dataset_validation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
    )
    op.create_index(
        "ix_dataset_validation_runs_dataset_version_id",
        "dataset_validation_runs",
        ["dataset_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_validation_runs_dataset_version_id",
        table_name="dataset_validation_runs",
    )
    op.drop_table("dataset_validation_runs")
    op.drop_index("ix_dataset_schemas_schema_hash", table_name="dataset_schemas")
    op.drop_table("dataset_schemas")
    op.drop_index("ix_dataset_versions_dataset_id", table_name="dataset_versions")
    op.drop_table("dataset_versions")
    op.drop_index("ix_datasets_slug", table_name="datasets")
    op.drop_index("ix_datasets_project_id", table_name="datasets")
    op.drop_index("ix_datasets_organization_id", table_name="datasets")
    op.drop_table("datasets")

