from __future__ import annotations

from datetime import datetime

from app.models import AccessResult, Secret


class AccessController:
    def check_access(self, secret: Secret, now_utc: datetime) -> AccessResult:
        if now_utc < secret.start_utc:
            return AccessResult(
                status="not_yet",
                content=None,
                available_at=secret.start_utc,
            )
        if now_utc > secret.end_utc:
            return AccessResult(
                status="expired",
                content=None,
                available_at=None,
            )
        return AccessResult(
            status="available",
            content=secret.content,
            available_at=None,
        )
