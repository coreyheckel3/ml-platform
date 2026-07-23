from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from forgeml.platform.database.base import Base


class RegisteredModelModel(Base):
    __tablename__ = "registered_models"
    __table_args__ = (UniqueConstraint("organization_id", "project_id", "slug"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
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


class ModelVersionModel(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("registered_model_id", "version"),
        UniqueConstraint("registered_model_id", "training_run_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    registered_model_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("registered_models.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    training_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("training_runs.id"),
        nullable=False,
        index=True,
    )
    experiment_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("experiment_runs.id"),
        nullable=False,
        index=True,
    )
    artifact_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    model_format: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metrics_json: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
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


class ModelApprovalModel(Base):
    __tablename__ = "model_approvals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("model_versions.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reviewer_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    comment: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    policy_snapshot_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ModelLineageModel(Base):
    __tablename__ = "model_lineage"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("model_versions.id"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
