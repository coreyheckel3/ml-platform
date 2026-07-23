from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.projects.infrastructure.sqlalchemy_models import OrganizationModel
from forgeml.platform.config import get_settings
from forgeml.platform.security.passwords import PasswordHasher


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    password_hash = PasswordHasher().hash("forgeml-local-admin")

    with Session(engine) as session:
        organization = session.scalar(
            select(OrganizationModel).where(OrganizationModel.slug == "forgeml-local")
        )
        if organization is None:
            organization = OrganizationModel(
                id=uuid4(),
                name="ForgeML Local",
                slug="forgeml-local",
                status="active",
            )
            session.add(organization)
            session.flush()

        user = session.scalar(select(UserModel).where(UserModel.email == "admin@forgeml.dev"))
        if user is None:
            session.add(
                UserModel(
                    id=uuid4(),
                    organization_id=organization.id,
                    email="admin@forgeml.dev",
                    display_name="Platform Admin",
                    password_hash=password_hash,
                    status="active",
                    permissions_csv="*",
                )
            )
        session.commit()

    print("Seeded admin@forgeml.dev with password forgeml-local-admin")


if __name__ == "__main__":
    main()
