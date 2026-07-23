from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.projects.domain.entities import Project, ProjectStatus
from forgeml.modules.projects.infrastructure.sqlalchemy_models import ProjectModel


def _to_domain(model: ProjectModel) -> Project:
    return Project(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        status=ProjectStatus(model.status),
        owner_user_id=model.owner_user_id,
    )


class SqlAlchemyProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: Project) -> Project:
        model = ProjectModel(
            id=project.id,
            organization_id=project.organization_id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            status=project.status.value,
            owner_user_id=project.owner_user_id,
        )
        self._session.add(model)
        self._session.flush()
        return _to_domain(model)

    def get(self, project_id: UUID) -> Project | None:
        model = self._session.get(ProjectModel, project_id)
        return _to_domain(model) if model else None

    def list_for_organization(self, organization_id: UUID) -> list[Project]:
        models = self._session.scalars(
            select(ProjectModel)
            .where(ProjectModel.organization_id == organization_id)
            .order_by(ProjectModel.name)
        ).all()
        return [_to_domain(model) for model in models]

    def slug_exists(self, organization_id: UUID, slug: str) -> bool:
        return (
            self._session.scalar(
                select(ProjectModel.id).where(
                    ProjectModel.organization_id == organization_id,
                    ProjectModel.slug == slug,
                )
            )
            is not None
        )

