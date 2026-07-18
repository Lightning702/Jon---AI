from __future__ import annotations

from datetime import datetime

from app.services.reminder_service import get_reminder_service
from app.services.settings_service import get_settings_service
from app.services.system_service import SystemService

WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]

_system = SystemService()


class BriefingService:
    def build(self) -> dict:
        now = datetime.now()
        data: dict = {
            "weekday": WEEKDAYS[now.weekday()],
            "date": now.strftime("%d.%m.%Y"),
            "time": now.strftime("%H:%M"),
            "calendar_week": now.isocalendar()[1],
        }
        city = str(get_settings_service().get().get("briefing_city", "")).strip()
        data["city"] = city
        if city:
            try:
                weather = _system.get_weather(city, 1)
                today = (weather.get("vorhersage") or [{}])[0]
                data["weather"] = {
                    "ort": weather.get("ort"),
                    "jetzt": weather.get("jetzt"),
                    "heute_min": today.get("min"),
                    "heute_max": today.get("max"),
                    "regen_prozent": today.get("regen_prozent"),
                    "heute": today.get("wetter"),
                }
            except Exception as exc:
                data["weather_error"] = str(exc)
        try:
            reminders = [
                {"text": r.get("text"), "time": r.get("time"), "repeat": r.get("repeat")}
                for r in get_reminder_service().list()
                if r.get("active", True)
            ]
            data["reminders"] = reminders[:10]
        except Exception:
            data["reminders"] = []
        try:
            data["alarms"] = _system.list_alarms()[:10]
        except Exception:
            data["alarms"] = []
        try:
            from app.services.task_service import get_task_service

            data["automations"] = [
                {"task": t.get("task"), "time": t.get("time"), "repeat": t.get("repeat")}
                for t in get_task_service().list()
                if t.get("active", True)
            ][:10]
        except Exception:
            data["automations"] = []
        try:
            from app.services.mail_service import get_mail_service

            mail = get_mail_service().check_mail(5)
            data["unread_mails"] = mail.get("ungelesen", 0)
            data["mails"] = mail.get("mails", [])
        except Exception:
            pass
        try:
            from app.services.mail_service import get_mail_service

            events = get_mail_service().calendar_events(2)
            today = now.strftime("%Y-%m-%d")
            data["termine"] = [
                e for e in events if e["datum"] == today
            ] or events[:5]
        except Exception:
            pass
        try:
            from app.services.action_log_service import absence_actions

            data["in_abwesenheit_getan"] = absence_actions(24)
        except Exception:
            data["in_abwesenheit_getan"] = []
        return data

    def weekly_data(self) -> dict:
        from datetime import timedelta

        now = datetime.now()
        week_ago = now - timedelta(days=7)
        data: dict = {
            "zeitraum": f"{week_ago.strftime('%d.%m.')} – {now.strftime('%d.%m.%Y')}",
        }
        try:
            from app.services.persona_service import get_persona_service

            data["jons_gedaechtnis"] = get_persona_service().read_memory_file(
                max_chars=5000
            )
        except Exception:
            pass
        try:
            from app.db.database import session_scope
            from app.db.models import Conversation

            with session_scope() as session:
                rows = (
                    session.query(Conversation)
                    .filter(Conversation.updated_at >= week_ago)
                    .order_by(Conversation.updated_at.desc())
                    .limit(30)
                    .all()
                )
                data["unterhaltungen"] = [r.title for r in rows]
        except Exception:
            data["unterhaltungen"] = []
        try:
            from app.services.task_service import get_task_service

            data["automationen"] = [
                {"task": t["task"], "zuletzt": t.get("last_run_at")}
                for t in get_task_service().list()
            ][:10]
        except Exception:
            pass
        try:
            from app.services.dream_service import get_dream_service

            data["dreams_erledigt"] = [
                t["task"]
                for t in get_dream_service().list()
                if t.get("status") == "done"
            ][:10]
        except Exception:
            pass
        try:
            from app.services.usage_service import get_usage_service

            data["nutzung"] = get_usage_service().summary(None)
        except Exception:
            pass
        return data


_service: BriefingService | None = None


def get_briefing_service() -> BriefingService:
    global _service
    if _service is None:
        _service = BriefingService()
    return _service
