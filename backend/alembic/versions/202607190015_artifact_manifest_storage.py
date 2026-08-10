"""Add artifact manifest metadata to dataset and model versions.

Revision ID: 202607190015
Revises: 202607190014
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190015"
down_revision: str | None = "202607190014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dataset_versions",
        sa.Column(
            "artifact_manifest_uri",
            sa.String(length=2048),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "dataset_versions",
        sa.Column(
            "artifact_manifest_hash",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "model_versions",
        sa.Column(
            "artifact_manifest_uri",
            sa.String(length=2048),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "model_versions",
        sa.Column(
            "artifact_manifest_hash",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
    )
    op.create_index(
        "ix_dataset_versions_artifact_manifest_hash",
        "dataset_versions",
        ["artifact_manifest_hash"],
    )
    op.create_index(
        "ix_model_versions_artifact_manifest_hash",
        "model_versions",
        ["artifact_manifest_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_versions_artifact_manifest_hash", table_name="model_versions")
    op.drop_index(
        "ix_dataset_versions_artifact_manifest_hash",
        table_name="dataset_versions",
    )
    op.drop_column("model_versions", "artifact_manifest_hash")
    op.drop_column("model_versions", "artifact_manifest_uri")
    op.drop_column("dataset_versions", "artifact_manifest_hash")
    op.drop_column("dataset_versions", "artifact_manifest_uri")
