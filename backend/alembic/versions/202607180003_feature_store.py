"""Add feature store schema.

Revision ID: 202607180003
Revises: 202607180002
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607180003"
down_revision: str | None = "202607180002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("entity_key", sa.String(length=120), nullable=False),
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
            name="uq_feature_sets_project_slug",
        ),
    )
    op.create_index("ix_feature_sets_organization_id", "feature_sets", ["organization_id"])
    op.create_index("ix_feature_sets_project_id", "feature_sets", ["project_id"])
    op.create_index("ix_feature_sets_slug", "feature_sets", ["slug"])

    op.create_table(
        "feature_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("feature_set_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("dtype", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("nullable", sa.Boolean(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"]),
        sa.UniqueConstraint(
            "feature_set_id",
            "name",
            name="uq_feature_definitions_feature_set_name",
        ),
    )
    op.create_index(
        "ix_feature_definitions_feature_set_id",
        "feature_definitions",
        ["feature_set_id"],
    )

    op.create_table(
        "feature_pipelines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("feature_set_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_dataset_id", sa.Uuid(), nullable=True),
        sa.Column("code_ref", sa.String(length=512), nullable=False),
        sa.Column("schedule_cron", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"]),
        sa.ForeignKeyConstraint(["source_dataset_id"], ["datasets.id"]),
        sa.UniqueConstraint(
            "feature_set_id",
            "name",
            name="uq_feature_pipelines_feature_set_name",
        ),
    )
    op.create_index("ix_feature_pipelines_feature_set_id", "feature_pipelines", ["feature_set_id"])

    op.create_table(
        "feature_materializations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("feature_set_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("offline_uri", sa.String(length=2048), nullable=False),
        sa.Column("online_ref", sa.String(length=512), nullable=True),
        sa.Column("orchestrator_run_id", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"]),
        sa.ForeignKeyConstraint(["pipeline_id"], ["feature_pipelines.id"]),
        sa.UniqueConstraint(
            "feature_set_id",
            "version",
            name="uq_feature_materializations_feature_set_version",
        ),
    )
    op.create_index(
        "ix_feature_materializations_feature_set_id",
        "feature_materializations",
        ["feature_set_id"],
    )
    op.create_index(
        "ix_feature_materializations_pipeline_id",
        "feature_materializations",
        ["pipeline_id"],
    )

    op.create_table(
        "feature_lineage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("feature_set_id", sa.Uuid(), nullable=False),
        sa.Column("upstream_type", sa.String(length=64), nullable=False),
        sa.Column("upstream_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"]),
    )
    op.create_index("ix_feature_lineage_feature_set_id", "feature_lineage", ["feature_set_id"])


def downgrade() -> None:
    op.drop_index("ix_feature_lineage_feature_set_id", table_name="feature_lineage")
    op.drop_table("feature_lineage")
    op.drop_index(
        "ix_feature_materializations_pipeline_id",
        table_name="feature_materializations",
    )
    op.drop_index(
        "ix_feature_materializations_feature_set_id",
        table_name="feature_materializations",
    )
    op.drop_table("feature_materializations")
    op.drop_index("ix_feature_pipelines_feature_set_id", table_name="feature_pipelines")
    op.drop_table("feature_pipelines")
    op.drop_index("ix_feature_definitions_feature_set_id", table_name="feature_definitions")
    op.drop_table("feature_definitions")
    op.drop_index("ix_feature_sets_slug", table_name="feature_sets")
    op.drop_index("ix_feature_sets_project_id", table_name="feature_sets")
    op.drop_index("ix_feature_sets_organization_id", table_name="feature_sets")
    op.drop_table("feature_sets")

