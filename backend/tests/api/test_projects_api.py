from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.projects.api.routes import get_project_service
from forgeml.modules.projects.application.services import CreateProjectCommand
from forgeml.modules.projects.domain.entities import Project, ProjectStatus
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


class FakeProjectService:
    def __init__(self) -> None:
        self.organization_id = uuid4()
        self.owner_user_id = uuid4()
        self.project_id = uuid4()

    def create_project(self, command: CreateProjectCommand, principal: Principal) -> Project:
        assert command.name == "Fraud Detection"
        return self._project()

    def list_projects(self, principal: Principal) -> list[Project]:
        return [self._project()]

    def get_project(self, project_id: UUID, principal: Principal) -> Project:
        assert project_id == self.project_id
        return self._project()

    def _project(self) -> Project:
        return Project(
            id=self.project_id,
            organization_id=self.organization_id,
            name="Fraud Detection",
            slug="fraud-detection",
            description="Payment risk scoring.",
            status=ProjectStatus.ACTIVE,
            owner_user_id=self.owner_user_id,
        )


def test_project_routes_use_application_service_contract() -> None:
    fake_service = FakeProjectService()
    app = create_app()
    app.dependency_overrides[get_project_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(fake_service.owner_user_id),
        email="owner@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"projects:create", "projects:read"}),
    )
    client = TestClient(app)

    created = client.post(
        "/api/v1/projects",
        json={"name": "Fraud Detection", "description": "Payment risk scoring."},
    )
    listed = client.get("/api/v1/projects")
    fetched = client.get(f"/api/v1/projects/{fake_service.project_id}")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-detection"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(fake_service.project_id)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Fraud Detection"

