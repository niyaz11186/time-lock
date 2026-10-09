import os
import pytest

from app.db import init_db, get_connection


# Skip all tests in this module if no DATABASE_URL is configured.
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — integration tests require a Postgres connection",
)


def test_init_db_runs_without_error():
    """init_db() should complete without raising any exception."""
    init_db()  # CREATE TABLE IF NOT EXISTS — always safe to call


def test_secrets_table_exists_after_init_db():
    """After init_db(), the secrets table should be present in the database."""
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'secrets'"
        ).fetchone()
    assert row is not None, "secrets table was not created"
    assert row["table_name"] == "secrets"


def test_users_table_exists_after_init_db():
    """After init_db(), the users table should be present in the database."""
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'users'"
        ).fetchone()
    assert row is not None, "users table was not created"
    assert row["table_name"] == "users"


def test_secrets_table_has_expected_columns():
    """The secrets table should have the correct columns."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'secrets'"
        ).fetchall()
    columns = {row["column_name"] for row in rows}
    assert {"id", "content", "start_utc", "end_utc", "created_at", "user_id"} == columns


def test_init_db_is_idempotent():
    """Calling init_db() multiple times should not raise an error."""
    init_db()
    init_db()  # second call should also be fine
