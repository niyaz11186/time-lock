from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import List

from app.db import get_connection, init_db
from app.models import Secret, ValidationError

_MAX_CONTENT_LENGTH = 10_000


class SecretStore:
    def __init__(self) -> None:
        init_db()

    # ------------------------------------------------------------------
    # Task 2.3
    # ------------------------------------------------------------------

    def create_secret(
        self,
        content: str,
        start_dt: datetime,
        end_dt: datetime,
        user_id: int | None = None,
        is_recurring: bool = False,
        recur_days: List[int] | None = None,
        recur_start_time: str | None = None,
        recur_end_time: str | None = None,
        recur_timezone: str | None = None,
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

        # Validate recurring fields if opted in
        if is_recurring:
            if not recur_days:
                raise ValidationError("Select at least one day for the weekly schedule.")
            if not recur_start_time or not recur_end_time:
                raise ValidationError("Start time and end time are required for recurring secrets.")
            if recur_start_time >= recur_end_time:
                raise ValidationError("Recurring end time must be after start time.")

        # Generate token (32 hex chars = 128 bits of entropy)
        token = secrets.token_hex(16)

        # Persist
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO secrets (id, user_id, content, start_utc, end_utc, created_at, "
                "is_recurring, recur_days, recur_start_time, recur_end_time, recur_timezone) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    token,
                    user_id,
                    content,
                    start_dt.isoformat(),
                    end_dt.isoformat(),
                    now,
                    is_recurring,
                    json.dumps(recur_days or []),
                    recur_start_time,
                    recur_end_time,
                    recur_timezone,
                ),
            )
            conn.commit()

        return token

    # ------------------------------------------------------------------
    # Task 2.4
    # ------------------------------------------------------------------

    def get_secret(self, secret_id: str) -> Secret | None:
        """Return the Secret record for *secret_id*, or None if not found."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, content, start_utc, end_utc, created_at, "
                "is_recurring, recur_days, recur_start_time, recur_end_time, recur_timezone "
                "FROM secrets WHERE id = %s",
                (secret_id,),
            ).fetchone()

        if row is None:
            return None

        return _row_to_secret(row)

    def list_secrets(self, user_id: int) -> list[Secret]:
        """Return all secrets belonging to user_id, newest first."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, content, start_utc, end_utc, created_at, "
                "is_recurring, recur_days, recur_start_time, recur_end_time, recur_timezone "
                "FROM secrets WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [_row_to_secret(row) for row in rows]

    def delete_secret(self, secret_id: str, user_id: int) -> bool:
        """Delete a secret only if it belongs to user_id. Returns True if deleted."""
        with get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM secrets WHERE id = %s AND user_id = %s",
                (secret_id, user_id),
            )
            conn.commit()
        return cur.rowcount > 0


def _row_to_secret(row) -> Secret:
    raw_days = row["recur_days"]
    if raw_days:
        try:
            recur_days = json.loads(raw_days)
        except (TypeError, ValueError):
            recur_days = []
    else:
        recur_days = []
    return Secret(
        id=row["id"],
        content=row["content"],
        start_utc=datetime.fromisoformat(row["start_utc"]),
        end_utc=datetime.fromisoformat(row["end_utc"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        is_recurring=bool(row["is_recurring"]),
        recur_days=recur_days,
        recur_start_time=row["recur_start_time"],
        recur_end_time=row["recur_end_time"],
        recur_timezone=row["recur_timezone"],
    )
