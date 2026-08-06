"""Add training worker queue hardening fields.

Revision ID: 202607190014
Revises: 202607190013
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607190014"
down_revision: str | None = "202607190013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "training_runs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "training_runs",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column("training_runs", sa.Column("worker_id", sa.String(length=120), nullable=True))
    op.add_column(
        "training_runs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_runs",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_runs",
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_runs",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_training_runs_status", "training_runs", ["status"])
    op.create_index("ix_training_runs_worker_id", "training_runs", ["worker_id"])
    op.create_index(
        "ix_training_runs_lease_expires_at",
        "training_runs",
        ["lease_expires_at"],
    )
    op.create_index("ix_training_runs_next_retry_at", "training_runs", ["next_retry_at"])
    op.create_index(
        "ix_training_runs_queue_polling",
        "training_runs",
        ["organization_id", "status", "next_retry_at"],
    )
    op.create_index(
        "ix_training_runs_running_leases",
        "training_runs",
        ["organization_id", "status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_training_runs_running_leases", table_name="training_runs")
    op.drop_index("ix_training_runs_queue_polling", table_name="training_runs")
    op.drop_index("ix_training_runs_next_retry_at", table_name="training_runs")
    op.drop_index("ix_training_runs_lease_expires_at", table_name="training_runs")
    op.drop_index("ix_training_runs_worker_id", table_name="training_runs")
    op.drop_index("ix_training_runs_status", table_name="training_runs")
    op.drop_column("training_runs", "next_retry_at")
    op.drop_column("training_runs", "completed_at")
    op.drop_column("training_runs", "started_at")
    op.drop_column("training_runs", "queued_at")
    op.drop_column("training_runs", "last_heartbeat_at")
    op.drop_column("training_runs", "lease_expires_at")
    op.drop_column("training_runs", "worker_id")
    op.drop_column("training_runs", "max_attempts")
    op.drop_column("training_runs", "attempt_count")
