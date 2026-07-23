from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeml.platform.database.base import Base


class DriftProfileModel(Base):
    __tablename__ = "drift_profiles"
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
    model_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("model_versions.id"),
        nullable=True,
        index=True,
    )
    dataset_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("dataset_versions.id"),
        nullable=True,
        index=True,
    )
    baseline_profile_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
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


class DriftReportModel(Base):
    __tablename__ = "drift_reports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    drift_profile_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("drift_profiles.id"),
        nullable=False,
        index=True,
    )
    endpoint_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("inference_endpoints.id"),
        nullable=False,
        index=True,
    )
    deployment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("deployments.id"),
        nullable=False,
        index=True,
    )
    deployment_revision_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("deployment_revisions.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    drift_score: Mapped[float] = mapped_column(Float, nullable=False)
    drifted_feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    drift_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    report_uri: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class DriftFeatureResultModel(Base):
    __tablename__ = "drift_feature_results"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    drift_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("drift_reports.id"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    feature_type: Mapped[str] = mapped_column(String(32), nullable=False)
    drift_score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    drift_detected: Mapped[bool] = mapped_column(nullable=False)
    statistics_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
