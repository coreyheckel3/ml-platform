from uuid import UUID, uuid4

import pytest

from forgeml.modules.projects.application.services import CreateProjectCommand, ProjectService
from forgeml.modules.projects.domain.entities import Project
from forgeml.platform.domain.errors import (
    ConflictError,
    DomainValidationError,
    PermissionDeniedError,
)
from forgeml.platform.security.rbac import Principal


class FakeProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[UUID, Project] = {}
        self.slugs: set[tuple[UUID, str]] = set()

    def add(self, project: Project) -> Project:
        self.projects[project.id] = project
        self.slugs.add((project.organization_id, project.slug))
        return project

    def get(self, project_id: UUID) -> Project | None:
        return self.projects.get(project_id)

    def list_for_organization(self, organization_id: UUID) -> list[Project]:
        return [
            project
            for project in self.projects.values()
            if project.organization_id == organization_id
        ]

    def slug_exists(self, organization_id: UUID, slug: str) -> bool:
        return (organization_id, slug) in self.slugs


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_project_service_creates_project_with_stable_slug() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    service = ProjectService(projects=FakeProjectRepository())

    project = service.create_project(
        CreateProjectCommand(
            organization_id=organization_id,
            owner_user_id=user_id,
            name="Fraud Detection Platform",
            description="Card transaction risk scoring.",
        ),
        principal(organization_id, user_id, {"projects:create"}),
    )

    assert project.slug == "fraud-detection-platform"
    assert project.owner_user_id == user_id
    assert project.is_active()


def test_project_service_rejects_missing_create_permission() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    service = ProjectService(projects=FakeProjectRepository())

    with pytest.raises(PermissionDeniedError):
        service.create_project(
            CreateProjectCommand(
                organization_id=organization_id,
                owner_user_id=user_id,
                name="Search",
            ),
            principal(organization_id, user_id, {"projects:read"}),
        )


def test_project_service_rejects_duplicate_slug() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    repository = FakeProjectRepository()
    service = ProjectService(projects=repository)
    actor = principal(organization_id, user_id, {"projects:create"})

    service.create_project(
        CreateProjectCommand(
            organization_id=organization_id,
            owner_user_id=user_id,
            name="Movie Rec",
        ),
        actor,
    )

    with pytest.raises(ConflictError):
        service.create_project(
            CreateProjectCommand(
                organization_id=organization_id,
                owner_user_id=user_id,
                name="Movie Rec",
            ),
            actor,
        )


def test_project_service_rejects_invalid_name() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    service = ProjectService(projects=FakeProjectRepository())

    with pytest.raises(DomainValidationError):
        service.create_project(
            CreateProjectCommand(organization_id=organization_id, owner_user_id=user_id, name="  "),
            principal(organization_id, user_id, {"projects:create"}),
        )
