from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from forgeml.platform.config import Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure_database(settings: Settings | None = None) -> None:
    global _engine, _session_factory
    resolved = settings or get_settings()
    if _engine is None:
        _engine = create_engine(resolved.database_url, pool_pre_ping=True, future=True)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        configure_database()
    if _session_factory is None:
        raise RuntimeError("Database session factory was not configured.")

    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

