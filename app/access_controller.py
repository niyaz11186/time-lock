from __future__ import annotations

from datetime import datetime, time

from zoneinfo import ZoneInfo

from app.models import AccessResult, Secret

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class AccessController:
    def check_access(self, secret: Secret, now_utc: datetime) -> AccessResult:
        if secret.is_recurring:
            return self._check_recurring(secret, now_utc)
        return self._check_one_time(secret, now_utc)

    # ------------------------------------------------------------------
    # One-time window (original behaviour)
    # ------------------------------------------------------------------

    def _check_one_time(self, secret: Secret, now_utc: datetime) -> AccessResult:
        if now_utc < secret.start_utc:
            return AccessResult(status="not_yet", content=None, available_at=secret.start_utc)
        if now_utc > secret.end_utc:
            return AccessResult(status="expired", content=None, available_at=None)
        return AccessResult(status="available", content=secret.content, available_at=None)

    # ------------------------------------------------------------------
    # Recurring weekly window
    # ------------------------------------------------------------------

    def _check_recurring(self, secret: Secret, now_utc: datetime) -> AccessResult:
        tz = ZoneInfo(secret.recur_timezone or "UTC")
        now_local = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)

        today_dow = now_local.weekday()  # 0=Mon … 6=Sun
        current_time = now_local.time().replace(second=0, microsecond=0)

        start_t = time.fromisoformat(secret.recur_start_time)
        end_t = time.fromisoformat(secret.recur_end_time)

        if today_dow in secret.recur_days and start_t <= current_time <= end_t:
            return AccessResult(status="available", content=secret.content, available_at=None)

        # Find the next occurrence
        next_available = _next_occurrence(now_local, secret.recur_days, start_t)
        # Convert back to naive UTC for available_at
        next_available_utc = next_available.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        return AccessResult(status="not_yet", content=None, available_at=next_available_utc)


def _next_occurrence(now_local, recur_days: list[int], start_t: time):
    """Return the next datetime (tz-aware, local) when the window opens."""
    from datetime import timedelta
    today_dow = now_local.weekday()
    current_time = now_local.time().replace(second=0, microsecond=0)

    for delta in range(0, 8):
        candidate_dow = (today_dow + delta) % 7
        if candidate_dow in recur_days:
            candidate_date = (now_local + timedelta(days=delta)).date()
            candidate_dt = datetime.combine(candidate_date, start_t, tzinfo=now_local.tzinfo)
            if candidate_dt > now_local:
                return candidate_dt

    # Fallback: one week from now (should never be reached)
    from datetime import timedelta
    return now_local + timedelta(days=7)

