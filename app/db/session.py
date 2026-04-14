"""
Database engine and session factory.
Uses SQLAlchemy 2.x with a synchronous session for simplicity.
"""
import uuid
from typing import Generator

from sqlalchemy import create_engine, event, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# GUID type for SQLite compatibility
class GUID(TypeDecorator):
    """Platform-independent GUID type for SQLite/PostgreSQL compatibility."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value) if isinstance(value, str) else value


# Database engine
# SQLite doesn't support pool parameters like max_overflow, so conditionally apply them
engine_kwargs = {"echo": settings.DEBUG}
if "sqlite" not in settings.DATABASE_URL.lower():
    engine_kwargs.update({
        "pool_pre_ping": True,    # Verify connections before use (handles DB restarts)
        "pool_size": 10,          # Number of persistent connections
        "max_overflow": 20,       # Additional connections beyond pool_size
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # Prevent lazy-load issues after commit
)


# Declarative base
class Base(DeclarativeBase):
    pass


# FastAPI dependency
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and ensure it is closed after the request.
    Use as a FastAPI dependency: `db: Session = Depends(get_db)`.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
