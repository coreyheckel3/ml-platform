from collections.abc import Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forgeml.main import create_app
from forgeml.modules.administration.infrastructure.sqlalchemy_models import AuditLogModel
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.projects.infrastructure.sqlalchemy_models import OrganizationModel
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.database.base import Base
from forgeml.platform.security.passwords import PasswordHasher
from forgeml.platform.security.rbac import Principal


def test_auth_and_project_routes_persist_audit_events_with_real_dependencies() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    Base.metadata.create_all(engine)
    organization_id = uuid4()
    user_id = uuid4()
    email = "ml.engineer@example.com"
    credential_phrase = "correct horse battery staple"

    with session_factory() as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        session.add(
            UserModel(
                id=user_id,
                organization_id=organization_id,
                email=email,
                display_name="ML Engineer",
                password_hash=PasswordHasher().hash(credential_phrase),
                status="active",
                permissions_csv="projects:create,projects:read,admin:audit_log:read",
            )
        )
        session.commit()

    settings = Settings(
        jwt_secret="api-audit-instrumentation-secret",
        rate_limit_enabled=False,
    )
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = _session_override(session_factory)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email=email,
        organization_id=str(organization_id),
        permissions=frozenset({"projects:create", "projects:read", "admin:audit_log:read"}),
    )
    client = TestClient(app)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": credential_phrase},
    )
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Fraud Detection", "description": "Payment risk scoring."},
    )

    assert login_response.status_code == 200
    assert project_response.status_code == 201

    with session_factory() as session:
        events = session.scalars(select(AuditLogModel)).all()

    events_by_action = {event.action: event for event in events}
    assert set(events_by_action) == {"auth.login", "projects.create"}
    assert events_by_action["auth.login"].actor_id == str(user_id)
    assert events_by_action["auth.login"].metadata_json == {"email": email}
    assert events_by_action["projects.create"].organization_id == organization_id
    assert events_by_action["projects.create"].resource_type == "project"
    assert events_by_action["projects.create"].metadata_json == {
        "slug": "fraud-detection",
        "name": "Fraud Detection",
    }


def _session_override(
    session_factory: sessionmaker[Session],
) -> object:
    def override() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return override
