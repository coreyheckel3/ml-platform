from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from forgeml.platform.database.base import Base


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ReleaseEvidenceReportModel(Base):
    __tablename__ = "release_evidence_reports"
    __table_args__ = (
        Index(
            "ix_release_evidence_reports_organization_created",
            "organization_id",
            "created_at",
        ),
        Index(
            "ix_release_evidence_reports_organization_status",
            "organization_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    repository: Mapped[str | None] = mapped_column(String(256), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workflow: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    run_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manifest_git_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_git_branch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ci_run_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_gate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_artifacts_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    missing_quality_gates_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    comparison_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    manifest_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    report_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
