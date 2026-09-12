"""Database connection manager for AI Interview Orchestrator.

Centralises SQLAlchemy connection and session management. Use SessionLocal()
as a context-manager (or close it manually) and prefer the type-hinted
with SessionLocal() as db: pattern in new code.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_SSLMODE, DATABASE_URL

logger = logging.getLogger(__name__)

db_url = DATABASE_URL
if not db_url or "sqlite" in db_url.lower():
    if not db_url:
        db_url = "sqlite:///./intelliview.db"
    _engine_kwargs = {
        "echo": False,
        "connect_args": {"check_same_thread": False},
    }
else:
    _connect_args = {}
    _engine_kwargs = {
        "echo": False,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    if DATABASE_SSLMODE and DATABASE_SSLMODE != "disable":
        _connect_args["sslmode"] = DATABASE_SSLMODE
        _engine_kwargs["connect_args"] = _connect_args

# Database engine initialization with structured error handling
try:
    engine = create_engine(
        db_url,
        **_engine_kwargs,
    )
    # Test database connectivity
    with engine.connect() as conn:
        pass
    logger.info("Database engine initialized successfully with URL: %s", db_url)

except Exception as exc:
    if "sqlite" in db_url.lower():
        logger.error("SQLite database engine initialization failed (%s).", exc)
    else:
        logger.error(
            "Database connection to PostgreSQL/external server failed (%s). "
            "Failing closed (no SQLite fallback for configured PostgreSQL).",
            exc,
        )
    raise


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session after the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
