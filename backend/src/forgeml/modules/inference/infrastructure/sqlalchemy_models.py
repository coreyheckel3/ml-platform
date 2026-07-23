from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from forgeml.platform.database.base import Base


class InferenceEndpointModel(Base):
    __tablename__ = "inference_endpoints"
    __table_args__ = (UniqueConstraint("organization_id", "project_id", "route_path"),)

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
    deployment_revision_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("deployment_revisions.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    route_path: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
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


class InferenceRequestLogModel(Base):
    __tablename__ = "inference_request_logs"
    __table_args__ = (UniqueConstraint("endpoint_id", "request_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("inference_endpoints.id"),
        nullable=False,
        index=True,
    )
    deployment_revision_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("deployment_revisions.id"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[float] = mapped_column(nullable=False)
    input_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    output_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InferenceMetricSnapshotModel(Base):
    __tablename__ = "inference_metric_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("inference_endpoints.id"),
        nullable=False,
        index=True,
    )
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    prediction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False)
    p50_latency_ms: Mapped[float] = mapped_column(nullable=False)
    p95_latency_ms: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
