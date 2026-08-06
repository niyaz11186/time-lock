from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.access_controller import AccessController
from app.db import get_connection
from app.models import ValidationError
from app.secret_store import SecretStore

bp = Blueprint("main", __name__)
_store = SecretStore()
_controller = AccessController()

# Group IANA timezones by region (e.g. "America", "Europe") for the dropdown
def _grouped_timezones() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for tz in sorted(available_timezones()):
        region = tz.split("/", 1)[0]
        groups[region].append(tz)
    return dict(sorted(groups.items()))

_TIMEZONES = _grouped_timezones()


@bp.route("/health")
def health():
    """Lightweight endpoint for external uptime pings (e.g. cron-job.org).
    Runs a trivial DB query to keep Supabase's inactivity timer from expiring."""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


@bp.route("/", methods=["GET"])
@login_required
def create_form():
    return render_template("create.html", error=None, timezones=_TIMEZONES)


@bp.route("/", methods=["POST"])
@login_required
def create_secret():
    content = request.form.get("content", "")
    tz_name = request.form.get("timezone", "")
    is_recurring = request.form.get("is_recurring") == "1"

    try:
        if not tz_name:
            raise ValidationError("A time zone is required.")
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, KeyError):
            raise ValidationError(f"Unknown time zone: {tz_name}")

        if is_recurring:
            recur_days = [int(d) for d in request.form.getlist("recur_days")]
            # Reuse the times from start_dt / end_dt — no separate time inputs needed
            start_str = request.form.get("start_dt", "")
            end_str = request.form.get("end_dt", "")
            try:
                start_local = datetime.fromisoformat(start_str)
                end_local = datetime.fromisoformat(end_str)
            except ValueError:
                raise ValidationError("Invalid datetime format. Use YYYY-MM-DDTHH:MM.")
            recur_start_time = start_local.strftime("%H:%M")
            recur_end_time = end_local.strftime("%H:%M")
            from datetime import date
            today = date.today()
            start_utc = datetime.combine(today, start_local.time())
            end_utc = datetime.combine(today, end_local.time())
            token = _store.create_secret(
                content, start_utc, end_utc,
                user_id=current_user.id,
                is_recurring=True,
                recur_days=recur_days,
                recur_start_time=recur_start_time,
                recur_end_time=recur_end_time,
                recur_timezone=tz_name,
            )
        else:
            start_str = request.form.get("start_dt", "")
            end_str = request.form.get("end_dt", "")
            try:
                start_local = datetime.fromisoformat(start_str)
                end_local = datetime.fromisoformat(end_str)
            except ValueError:
                raise ValidationError("Invalid datetime format. Use YYYY-MM-DDTHH:MM.")
            start_utc = start_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = end_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            token = _store.create_secret(content, start_utc, end_utc, user_id=current_user.id)

        return redirect(url_for("main.success", token=token))

    except ValidationError as exc:
        return render_template("create.html", error=exc.message, timezones=_TIMEZONES), 400


@bp.route("/success")
def success():
    token = request.args.get("token", "")
    secret_url = url_for("main.view_secret", secret_id=token, _external=True)
    return render_template("success.html", secret_url=secret_url)


@bp.route("/my-secrets")
@login_required
def my_secrets():
    secrets = _store.list_secrets(current_user.id)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    # Annotate each secret with its current access status
    annotated = [
        (s, _controller.check_access(s, now_utc).status)
        for s in secrets
    ]
    return render_template("my_secrets.html", annotated=annotated)


@bp.route("/secret/<secret_id>/delete", methods=["POST"])
@login_required
def delete_secret(secret_id: str):
    _store.delete_secret(secret_id, current_user.id)
    return redirect(url_for("main.my_secrets"))


@bp.route("/secret/<secret_id>")
def view_secret(secret_id: str):
    secret = _store.get_secret(secret_id)
    if secret is None:
        abort(404)

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    result = _controller.check_access(secret, now_utc)
    return render_template("view.html", result=result, secret=secret)


@bp.app_errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404
