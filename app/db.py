import sqlite3
import os


def get_db_path() -> str:
    """Returns the path to secrets.db in the project root."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "secrets.db")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Returns a sqlite3 connection. Uses get_db_path() if no path provided."""
    path = db_path if db_path is not None else get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    """Creates all tables if they don't exist."""
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT NOT NULL UNIQUE,
                name          TEXT,
                password_hash TEXT,
                google_id     TEXT UNIQUE,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                id          TEXT PRIMARY KEY,
                user_id     INTEGER REFERENCES users(id),
                content     TEXT NOT NULL,
                start_utc   TEXT NOT NULL,
                end_utc     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()
