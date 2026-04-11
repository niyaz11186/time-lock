import sqlite3
import tempfile
import os
import pytest

from app.db import init_db, get_connection


def test_init_db_runs_without_error():
    """init_db() should complete without raising any exception."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)  # should not raise
    finally:
        os.unlink(db_path)


def test_secrets_table_exists_after_init_db():
    """After init_db(), the secrets table should be present in the database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='secrets'"
            ).fetchone()
        assert row is not None, "secrets table was not created"
        assert row["name"] == "secrets"
    finally:
        os.unlink(db_path)


def test_secrets_table_has_expected_columns():
    """The secrets table should have the correct columns."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        with get_connection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(secrets)")
            columns = {row["name"] for row in cursor.fetchall()}
        assert columns == {"id", "content", "start_utc", "end_utc", "created_at"}
    finally:
        os.unlink(db_path)


def test_init_db_is_idempotent():
    """Calling init_db() multiple times should not raise an error."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        init_db(db_path)  # second call should also be fine
    finally:
        os.unlink(db_path)
