from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Secret:
    id: str
    content: str
    start_utc: datetime
    end_utc: datetime
    created_at: datetime


@dataclass
class AccessResult:
    status: str  # 'available' | 'not_yet' | 'expired'
    content: str | None
    available_at: datetime | None  # populated when status == 'not_yet'


class ValidationError(Exception):
    """Raised by the domain layer when input fails validation.

    The message is a descriptive string suitable for display to the user.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
