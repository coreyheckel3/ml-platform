from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
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


class FeatureSetModel(Base):
    __tablename__ = "feature_sets"
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
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False)
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


class FeatureDefinitionModel(Base):
    __tablename__ = "feature_definitions"
    __table_args__ = (UniqueConstraint("feature_set_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    feature_set_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feature_sets.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    dtype: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    nullable: Mapped[bool] = mapped_column(nullable=False)
    constraints_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class FeaturePipelineModel(Base):
    __tablename__ = "feature_pipelines"
    __table_args__ = (UniqueConstraint("feature_set_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    feature_set_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feature_sets.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_dataset_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("datasets.id"),
        nullable=True,
    )
    code_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
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


class FeatureMaterializationModel(Base):
    __tablename__ = "feature_materializations"
    __table_args__ = (UniqueConstraint("feature_set_id", "version"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    feature_set_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feature_sets.id"),
        nullable=False,
        index=True,
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feature_pipelines.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    offline_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    online_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    orchestrator_run_id: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
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


class FeatureLineageModel(Base):
    __tablename__ = "feature_lineage"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    feature_set_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feature_sets.id"),
        nullable=False,
        index=True,
    )
    upstream_type: Mapped[str] = mapped_column(String(64), nullable=False)
    upstream_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
