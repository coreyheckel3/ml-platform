from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeml.platform.database.base import Base


class TrainingRunModel(Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        Index("ix_training_runs_queue_polling", "organization_id", "status", "next_retry_at"),
        Index(
            "ix_training_runs_running_leases",
            "organization_id",
            "status",
            "lease_expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("experiments.id"),
        nullable=False,
        index=True,
    )
    experiment_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("experiment_runs.id"),
        nullable=False,
        index=True,
    )
    dataset_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("dataset_versions.id"),
        nullable=True,
        index=True,
    )
    feature_set_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("feature_sets.id"),
        nullable=True,
        index=True,
    )
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    objective_metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hyperparameters_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    orchestrator_run_id: Mapped[str] = mapped_column(String(512), nullable=False)
    metrics_json: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    worker_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TrainingRunEventModel(Base):
    __tablename__ = "training_run_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("training_runs.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TrainingRunLogModel(Base):
    __tablename__ = "training_run_logs"
    __table_args__ = (UniqueConstraint("training_run_id", "sequence"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("training_runs.id"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    logger: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(String(4000), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
