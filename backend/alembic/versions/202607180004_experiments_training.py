"""Add experiments and training run schema.

Revision ID: 202607180004
Revises: 202607180003
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607180004"
down_revision: str | None = "202607180003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
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
            name="uq_experiments_project_slug",
        ),
    )
    op.create_index("ix_experiments_organization_id", "experiments", ["organization_id"])
    op.create_index("ix_experiments_project_id", "experiments", ["project_id"])
    op.create_index("ix_experiments_slug", "experiments", ["slug"])

    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("run_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_type", sa.String(length=64), nullable=False),
        sa.Column("started_by", sa.Uuid(), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=True),
        sa.Column("feature_set_id", sa.Uuid(), nullable=True),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("artifact_uri", sa.String(length=2048), nullable=False),
        sa.Column("evaluation_report_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
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
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_experiment_runs_experiment_id", "experiment_runs", ["experiment_id"])
    op.create_index("ix_experiment_runs_project_id", "experiment_runs", ["project_id"])
    op.create_index(
        "ix_experiment_runs_dataset_version_id",
        "experiment_runs",
        ["dataset_version_id"],
    )
    op.create_index("ix_experiment_runs_feature_set_id", "experiment_runs", ["feature_set_id"])

    op.create_table(
        "experiment_artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("experiment_run_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("uri", sa.String(length=2048), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["experiment_run_id"], ["experiment_runs.id"]),
    )
    op.create_index(
        "ix_experiment_artifacts_experiment_run_id",
        "experiment_artifacts",
        ["experiment_run_id"],
    )

    op.create_table(
        "training_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_run_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=True),
        sa.Column("feature_set_id", sa.Uuid(), nullable=True),
        sa.Column("algorithm", sa.String(length=120), nullable=False),
        sa.Column("model_type", sa.String(length=64), nullable=False),
        sa.Column("objective_metric_name", sa.String(length=120), nullable=False),
        sa.Column("hyperparameters_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("artifact_uri", sa.String(length=2048), nullable=False),
        sa.Column("orchestrator_run_id", sa.String(length=512), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
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
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["experiment_run_id"], ["experiment_runs.id"]),
        sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_training_runs_organization_id", "training_runs", ["organization_id"])
    op.create_index("ix_training_runs_project_id", "training_runs", ["project_id"])
    op.create_index("ix_training_runs_experiment_id", "training_runs", ["experiment_id"])
    op.create_index("ix_training_runs_experiment_run_id", "training_runs", ["experiment_run_id"])
    op.create_index(
        "ix_training_runs_dataset_version_id",
        "training_runs",
        ["dataset_version_id"],
    )
    op.create_index("ix_training_runs_feature_set_id", "training_runs", ["feature_set_id"])

    op.create_table(
        "training_run_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("training_run_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["training_run_id"], ["training_runs.id"]),
    )
    op.create_index(
        "ix_training_run_events_training_run_id",
        "training_run_events",
        ["training_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_training_run_events_training_run_id", table_name="training_run_events")
    op.drop_table("training_run_events")
    op.drop_index("ix_training_runs_feature_set_id", table_name="training_runs")
    op.drop_index("ix_training_runs_dataset_version_id", table_name="training_runs")
    op.drop_index("ix_training_runs_experiment_run_id", table_name="training_runs")
    op.drop_index("ix_training_runs_experiment_id", table_name="training_runs")
    op.drop_index("ix_training_runs_project_id", table_name="training_runs")
    op.drop_index("ix_training_runs_organization_id", table_name="training_runs")
    op.drop_table("training_runs")
    op.drop_index(
        "ix_experiment_artifacts_experiment_run_id",
        table_name="experiment_artifacts",
    )
    op.drop_table("experiment_artifacts")
    op.drop_index("ix_experiment_runs_feature_set_id", table_name="experiment_runs")
    op.drop_index("ix_experiment_runs_dataset_version_id", table_name="experiment_runs")
    op.drop_index("ix_experiment_runs_project_id", table_name="experiment_runs")
    op.drop_index("ix_experiment_runs_experiment_id", table_name="experiment_runs")
    op.drop_table("experiment_runs")
    op.drop_index("ix_experiments_slug", table_name="experiments")
    op.drop_index("ix_experiments_project_id", table_name="experiments")
    op.drop_index("ix_experiments_organization_id", table_name="experiments")
    op.drop_table("experiments")
