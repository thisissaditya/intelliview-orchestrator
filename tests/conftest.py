import os
import pathlib
import sys
from types import SimpleNamespace

import pytest

# ---------------------------------------------------------------------------
# Test environment defaults
# ---------------------------------------------------------------------------

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "ai_interview_db")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("API_TOKEN", "ci-test-token")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "10000")

os.environ["OTEL_SDK_DISABLED"] = "true"

# ---------------------------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# PostgreSQL Testcontainer
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container():
    """
    Provide PostgreSQL for integration tests.

    GitHub Actions / act:
        Use the PostgreSQL service defined in ci.yml.

    Local development:
        Start PostgreSQL using Testcontainers.
    """

    if os.getenv("GITHUB_ACTIONS") == "true":
        database_url = (
            "postgresql+psycopg2://postgres:postgres"
            "@localhost:5432/ai_interview_test"
        )

        postgres = SimpleNamespace(get_connection_url=lambda: database_url)

        yield postgres
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as postgres:
        database_url = postgres.get_connection_url()

        os.environ["DATABASE_URL"] = database_url
        os.environ["POSTGRES_HOST"] = postgres.get_container_host_ip()
        os.environ["POSTGRES_PORT"] = str(postgres.get_exposed_port(5432))
        os.environ["POSTGRES_DB"] = postgres.dbname
        os.environ["POSTGRES_USER"] = postgres.username
        os.environ["POSTGRES_PASSWORD"] = postgres.password

        yield postgres


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session(postgres_container):
    """Provide a SQLAlchemy session connected to the test database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base

    engine = create_engine(
        postgres_container.get_connection_url(),
        future=True,
    )

    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.getenv(
        "API_BASE_URL",
        "http://localhost:8000",
    )


@pytest.fixture(scope="session")
def api_token() -> str:
    return os.getenv("API_TOKEN", "ci-test-token")


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": os.environ["REDIS_URL"],
        "result_backend": os.environ["REDIS_URL"],
    }


@pytest.fixture(scope="session")
def celery_app_fixture():
    from workers.celery_app import celery_app

    return celery_app


# ---------------------------------------------------------------------------
# Unit-test fixtures — pure mocks, no live Postgres/Redis required.
# Use these in tests that shouldn't depend on docker-compose being up.
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_session(mocker):
    """Fake SQLAlchemy session factory — patches database.db.SessionLocal."""
    session = mocker.MagicMock()
    mocker.patch("database.db.SessionLocal", return_value=session)
    return session


@pytest.fixture
def mock_state_sync(mocker):
    """Fake Redis-backed StateSynchronizer for session state caching."""
    mock_cls = mocker.patch("orchestrator.state_sync.StateSynchronizer", autospec=True)
    return mock_cls.return_value


@pytest.fixture
def mock_circuit_closed(mocker):
    """Defaults the Redis circuit breaker to closed (Redis 'available')."""
    return mocker.patch("orchestrator.redis_client.is_circuit_open", return_value=False)
