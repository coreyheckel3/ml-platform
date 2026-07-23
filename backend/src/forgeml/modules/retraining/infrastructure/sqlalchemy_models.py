from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeml.platform.database.base import Base


class RetrainingPolicyModel(Base):
    __tablename__ = "retraining_policies"
    __table_args__ = (UniqueConstraint("organization_id", "project_id", "slug"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    deployment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("deployments.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trigger_config_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    training_template_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_runs_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
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


class RetrainingRunModel(Base):
    __tablename__ = "retraining_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("retraining_policies.id"),
        nullable=False,
        index=True,
    )
    deployment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("deployments.id"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    drift_report_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("drift_reports.id"),
        nullable=True,
        index=True,
    )
    alert_event_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("alert_events.id"),
        nullable=True,
        index=True,
    )
    training_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("training_runs.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    training_config_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    decision_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    rejected_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
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
