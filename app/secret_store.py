from __future__ import annotations

import secrets
from datetime import datetime

from app.db import get_connection, init_db
from app.models import Secret, ValidationError

_MAX_CONTENT_LENGTH = 10_000


class SecretStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        init_db(db_path)

    # ------------------------------------------------------------------
    # Task 2.3
    # ------------------------------------------------------------------

    def create_secret(
        self,
        content: str,
        start_dt: datetime,
        end_dt: datetime,
        user_id: int | None = None,
    ) -> str:
        """Validate, persist, and return a cryptographically random token."""
        # Validate content
        if not content or not content.strip():
            raise ValidationError("Secret content must not be empty or whitespace.")
        if len(content) > _MAX_CONTENT_LENGTH:
            raise ValidationError(
                f"Secret content must not exceed {_MAX_CONTENT_LENGTH} characters "
                f"(got {len(content)})."
            )

        # Validate time window
        if start_dt is None or end_dt is None:
            raise ValidationError(
                "Both start datetime and end datetime are required."
            )
        if end_dt <= start_dt:
            raise ValidationError(
                "End datetime must be after start datetime."
            )

        # Generate token (32 hex chars = 128 bits of entropy)
        token = secrets.token_hex(16)

        # Persist
        now = datetime.utcnow().isoformat()
        with get_connection(self._db_path) as conn:
            conn.execute(
                "INSERT INTO secrets (id, user_id, content, start_utc, end_utc, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    token,
                    user_id,
                    content,
                    start_dt.isoformat(),
                    end_dt.isoformat(),
                    now,
                ),
            )
            conn.commit()

        return token

    # ------------------------------------------------------------------
    # Task 2.4
    # ------------------------------------------------------------------

    def get_secret(self, secret_id: str) -> Secret | None:
        """Return the Secret record for *secret_id*, or None if not found."""
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, content, start_utc, end_utc, created_at "
                "FROM secrets WHERE id = ?",
                (secret_id,),
            ).fetchone()

        if row is None:
            return None

        return Secret(
            id=row["id"],
            content=row["content"],
            start_utc=datetime.fromisoformat(row["start_utc"]),
            end_utc=datetime.fromisoformat(row["end_utc"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_secrets(self, user_id: int) -> list[Secret]:
        """Return all secrets belonging to user_id, newest first."""
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, content, start_utc, end_utc, created_at "
                "FROM secrets WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            Secret(
                id=row["id"],
                content=row["content"],
                start_utc=datetime.fromisoformat(row["start_utc"]),
                end_utc=datetime.fromisoformat(row["end_utc"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def delete_secret(self, secret_id: str, user_id: int) -> bool:
        """Delete a secret only if it belongs to user_id. Returns True if deleted."""
        with get_connection(self._db_path) as conn:
            cur = conn.execute(
                "DELETE FROM secrets WHERE id = ? AND user_id = ?",
                (secret_id, user_id),
            )
            conn.commit()
        return cur.rowcount > 0
