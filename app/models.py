from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Secret:
    id: str
    content: str
    start_utc: datetime
    end_utc: datetime
    created_at: datetime
    # Recurring weekly fields (all None for one-time secrets)
    is_recurring: bool = False
    recur_days: List[int] = field(default_factory=list)  # 0=Mon … 6=Sun
    recur_start_time: str | None = None   # "HH:MM" in creator's timezone
    recur_end_time: str | None = None     # "HH:MM" in creator's timezone
    recur_timezone: str | None = None     # IANA tz string


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
