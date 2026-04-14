"""
Pytest configuration and shared fixtures.

Strategy:
  - Each test function gets a fresh database transaction that is rolled back
    after the test, keeping tests isolated without recreating the schema.
  - A separate in-memory SQLite engine is used so tests don't require PostgreSQL.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Point to SQLite in-memory DB before importing anything that touches the engine
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")

from app.db.session import Base, get_db   # noqa: E402
from app.main import app                  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.core.security import hash_password  # noqa: E402

# SQLite engine
TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db() -> Session:
    """
    Provide a transactional DB session that rolls back after each test.
    This keeps tests fully isolated.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    """
    Return a FastAPI TestClient that uses the test database session.
    Overrides the `get_db` dependency for the duration of each test.
    """
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# Test factories
@pytest.fixture()
def regular_user(db: Session) -> User:
    """A standard (non-admin) user."""
    user = User(
        email="user@example.com",
        hashed_password=hash_password("Password123"),
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def admin_user(db: Session) -> User:
    """An admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Helper to log in and return Authorization headers."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
