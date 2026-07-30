"""Add training run execution logs.

Revision ID: 202607190012
Revises: 202607190011
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190012"
down_revision: str | None = "202607190011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_run_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("training_run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("logger", sa.String(length=120), nullable=False),
        sa.Column("message", sa.String(length=4000), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["training_run_id"], ["training_runs.id"]),
        sa.UniqueConstraint(
            "training_run_id",
            "sequence",
            name="uq_training_run_logs_run_sequence",
        ),
    )
    op.create_index(
        "ix_training_run_logs_training_run_id",
        "training_run_logs",
        ["training_run_id"],
    )
    op.create_index("ix_training_run_logs_level", "training_run_logs", ["level"])


def downgrade() -> None:
    op.drop_index("ix_training_run_logs_level", table_name="training_run_logs")
    op.drop_index("ix_training_run_logs_training_run_id", table_name="training_run_logs")
    op.drop_table("training_run_logs")
