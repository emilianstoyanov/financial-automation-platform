"""SQLAlchemy engine, session factory, and declarative base."""

from collections.abc import Generator
from contextlib import contextmanager
from app.core.config import get_settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

settings = get_settings()


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def _create_engine():
    connect_args = {}
    if settings.sqlalchemy_database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.sqlalchemy_database_url,
        connect_args=connect_args,
        echo=settings.debug and settings.is_development,
        pool_pre_ping=True,
    )


engine = _create_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Enable foreign keys for SQLite connections."""
    if settings.sqlalchemy_database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for scripts and background tasks."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create database tables from registered models."""
    from app.core.data_dirs import DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Import models here when they exist so metadata is populated
    Base.metadata.create_all(bind=engine)
