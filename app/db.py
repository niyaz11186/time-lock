import os

import psycopg2
import psycopg2.extras


class _PGConnection:
    """Thin adapter giving psycopg2 a sqlite3-compatible execute() interface.

    Allows ``with get_connection() as conn: conn.execute(sql, params)``
    to work throughout the codebase unchanged.
    """

    def __init__(self, **kwargs) -> None:
        self._conn = psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **kwargs)
        self._cur = self._conn.cursor()

    def execute(self, sql: str, params=None):
        self._cur.execute(sql, params)
        return self._cur

    def commit(self) -> None:
        self._conn.commit()

    def __enter__(self) -> "_PGConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
            self._cur.close()
            self._conn.close()


def get_connection(db_path: str | None = None) -> _PGConnection:
    """Return a Postgres connection adapter.

    *db_path* is accepted but ignored — kept for API compatibility.
    Reads DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD from the environment.
    """
    return _PGConnection(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode=os.environ.get("DB_SSLMODE", "disable"),
    )


def init_db(db_path: str | None = None) -> None:
    """Creates all tables if they don't exist. Safe to call on every startup."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            BIGSERIAL PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE,
                name          TEXT,
                password_hash TEXT,
                google_id     TEXT UNIQUE,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                id              TEXT PRIMARY KEY,
                user_id         BIGINT REFERENCES users(id),
                content         TEXT NOT NULL,
                start_utc       TEXT NOT NULL,
                end_utc         TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                is_recurring    BOOLEAN NOT NULL DEFAULT FALSE,
                recur_days      TEXT,
                recur_start_time TEXT,
                recur_end_time  TEXT,
                recur_timezone  TEXT
            )
        """)
