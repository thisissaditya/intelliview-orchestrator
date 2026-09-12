import importlib
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

import database.db
from database.db import get_db


def test_get_db_closes_session():
    """Database session should always be closed after successful use."""
    mock_db = MagicMock()

    with patch("database.db.SessionLocal", return_value=mock_db):
        dependency = get_db()

        session = next(dependency)
        assert session is mock_db

        with pytest.raises(StopIteration):
            next(dependency)

    mock_db.close.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_get_db_rolls_back_and_closes_on_exception():
    """Failed database operations should rollback and close the session."""
    mock_db = MagicMock()

    with patch("database.db.SessionLocal", return_value=mock_db):
        dependency = get_db()

        session = next(dependency)
        assert session is mock_db

        with pytest.raises(RuntimeError, match="database failure"):
            dependency.throw(RuntimeError("database failure"))

    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()


def test_postgres_connection_failure_fails_closed():
    """PostgreSQL connection failure should fail closed without SQLite fallback."""

    def mock_create_engine(url, **kwargs):
        mock_eng = MagicMock()
        mock_eng.connect.side_effect = OperationalError(
            "SSL connection error", None, Exception("SSL connection error")
        )
        return mock_eng

    with patch("sqlalchemy.create_engine", side_effect=mock_create_engine):
        with patch(
            "config.DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb"
        ):
            with patch("config.DATABASE_SSLMODE", "disable"):
                with pytest.raises(OperationalError):
                    importlib.reload(database.db)


def test_postgres_sslmode_require_passed_to_engine():
    """DATABASE_SSLMODE=require must pass sslmode in connect_args to create_engine."""

    captured_kwargs = {}

    def mock_create_engine(url, **kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        mock_eng = MagicMock()
        mock_eng.connect.return_value.__enter__.return_value = MagicMock()
        return mock_eng

    with patch("sqlalchemy.create_engine", side_effect=mock_create_engine):
        with patch(
            "config.DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb"
        ):
            with patch("config.DATABASE_SSLMODE", "require"):
                importlib.reload(database.db)

    assert captured_kwargs.get("connect_args", {}).get("sslmode") == "require"
