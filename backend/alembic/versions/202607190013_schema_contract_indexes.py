"""Add schema contract foreign key indexes.

Revision ID: 202607190013
Revises: 202607190012
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202607190013"
down_revision: str | None = "202607190012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_auth_refresh_sessions_replaced_by_session_id",
        "auth_refresh_sessions",
        ["replaced_by_session_id"],
    )
    op.create_index(
        "ix_feature_pipelines_source_dataset_id",
        "feature_pipelines",
        ["source_dataset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_feature_pipelines_source_dataset_id",
        table_name="feature_pipelines",
    )
    op.drop_index(
        "ix_auth_refresh_sessions_replaced_by_session_id",
        table_name="auth_refresh_sessions",
    )
