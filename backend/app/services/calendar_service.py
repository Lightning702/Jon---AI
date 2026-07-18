from __future__ import annotations

import json
import threading
import uuid
from datetime import date, datetime, timedelta

from app.core.config import DATA_DIR

CALENDAR_FILE = DATA_DIR / "calendar.json"
KINDS = ("termin", "task", "erinnerung")
WEEKDAYS = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}
TASK_WEEKDAY_KEYS = ["mo", "di", "mi", "do", "fr", "sa", "so"]


def parse_date(value: str) -> str:
    value = str(value or "").strip().lower()
    today = date.today()
    if value in ("", "heute", "today"):
        return today.isoformat()
    if value in ("morgen", "tomorrow"):
        return (today + timedelta(days=1)).isoformat()
    if value in ("uebermorgen", "übermorgen"):
        return (today + timedelta(days=2)).isoformat()
    for name, idx in WEEKDAYS.items():
        if value in (name, name[:2]):
            delta = (idx - today.weekday()) % 7 or 7
            return (today + timedelta(days=delta)).isoformat()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m."):
        try:
            parsed = datetime.strptime(value, fmt).date()
            if fmt == "%d.%m.":
                parsed = parsed.replace(year=today.year)
                if parsed < today - timedelta(days=180):
                    parsed = parsed.replace(year=today.year + 1)
            return parsed.isoformat()
        except ValueError:
            continue
    raise ValueError(
        f"Unbekanntes Datum '{value}'. Nutze YYYY-MM-DD, TT.MM., 'heute', "
        "'morgen' oder einen Wochentag."
    )


def parse_time(value: str) -> str:
    value = str(value or "").strip().lower()
    if not value:
        return ""
    value = value.replace(" uhr", "").replace("uhr", "").strip()
    for fmt in ("%H:%M", "%H.%M", "%H"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue
    raise ValueError(f"Unbekannte Uhrzeit '{value}'. Nutze HH:MM.")


class CalendarService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: list[dict] = []
        try:
            self._data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
        except Exception:
            self._data = []

    def _save(self) -> None:
        try:
            CALENDAR_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _overlaps(self, entry: dict, other: dict) -> bool:
        if entry["date"] != other["date"] or not entry["time"] or not other["time"]:
            return False
        def span(item: dict) -> tuple[int, int]:
            h, m = [int(x) for x in item["time"].split(":")]
            start = h * 60 + m
            return start, start + int(item.get("duration_minutes") or 60)
        a1, a2 = span(entry)
        b1, b2 = span(other)
        return a1 < b2 and b1 < a2

    def conflicts(self, entry: dict, exclude_id: str = "") -> list[dict]:
        with self._lock:
            return [
                {"titel": o["title"], "zeit": o["time"], "datum": o["date"]}
                for o in self._data
                if o["id"] != exclude_id
                and o["kind"] != "task"
                and not o.get("done")
                and self._overlaps(entry, o)
            ]

    def add(
        self,
        title: str,
        day: str,
        time: str = "",
        duration_minutes: int = 0,
        note: str = "",
        kind: str = "termin",
    ) -> dict:
        entry = {
            "id": uuid.uuid4().hex,
            "title": str(title).strip()[:200],
            "date": parse_date(day),
            "time": parse_time(time),
            "duration_minutes": max(0, int(duration_minutes or 0)),
            "note": str(note or "").strip()[:500],
            "kind": kind if kind in KINDS else "termin",
            "done": False,
            "notified": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        if not entry["title"]:
            raise ValueError("Titel fehlt")
        clashes = self.conflicts(entry)
        with self._lock:
            self._data.append(entry)
            self._save()
        result = dict(entry)
        if clashes:
            result["konflikte"] = clashes
        return result

    def update(self, entry_id: str, fields: dict) -> dict:
        with self._lock:
            entry = next((e for e in self._data if e["id"] == entry_id), None)
            if entry is None:
                raise ValueError("Eintrag nicht gefunden")
            if "title" in fields and str(fields["title"]).strip():
                entry["title"] = str(fields["title"]).strip()[:200]
            if "date" in fields and fields["date"]:
                entry["date"] = parse_date(fields["date"])
                entry["notified"] = False
            if "time" in fields:
                entry["time"] = parse_time(fields["time"])
                entry["notified"] = False
            if "duration_minutes" in fields:
                entry["duration_minutes"] = max(0, int(fields["duration_minutes"] or 0))
            if "note" in fields:
                entry["note"] = str(fields["note"] or "").strip()[:500]
            if "kind" in fields and fields["kind"] in KINDS:
                entry["kind"] = fields["kind"]
            if "done" in fields:
                entry["done"] = bool(fields["done"])
            snapshot = dict(entry)
            self._save()
        clashes = self.conflicts(snapshot, exclude_id=entry_id)
        if clashes:
            snapshot["konflikte"] = clashes
        return snapshot

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [e for e in self._data if e["id"] != entry_id]
            if len(self._data) < before:
                self._save()
                return True
            return False

    def list(self, start: str = "", days: int = 0) -> list[dict]:
        with self._lock:
            items = [dict(e) for e in self._data]
        if start or days:
            first = date.fromisoformat(parse_date(start or "heute"))
            last = first + timedelta(days=max(1, days or 7))
            items = [
                e for e in items if first <= date.fromisoformat(e["date"]) < last
            ]
        return sorted(items, key=lambda e: (e["date"], e["time"] or "99:99"))

    def search(self, query: str) -> list[dict]:
        query = str(query or "").strip().lower()
        if not query:
            return []
        with self._lock:
            return sorted(
                (
                    dict(e)
                    for e in self._data
                    if query in e["title"].lower() or query in e["note"].lower()
                ),
                key=lambda e: (e["date"], e["time"] or "99:99"),
            )

    def merged(self, start: str = "", days: int = 7) -> list[dict]:
        first = date.fromisoformat(parse_date(start or "heute"))
        span = max(1, min(int(days or 7), 62))
        events: list[dict] = []
        for e in self.list(start=first.isoformat(), days=span):
            events.append(
                {
                    "id": e["id"],
                    "quelle": "jon",
                    "titel": e["title"],
                    "datum": e["date"],
                    "zeit": e["time"],
                    "dauer_minuten": e.get("duration_minutes") or 0,
                    "notiz": e.get("note", ""),
                    "typ": e["kind"],
                    "erledigt": bool(e.get("done")),
                }
            )
        try:
            from app.services.task_service import get_task_service

            tasks = [t for t in get_task_service().list() if t.get("active", True)]
        except Exception:
            tasks = []
        try:
            from app.services.reminder_service import get_reminder_service

            reminders = [
                r for r in get_reminder_service().list() if r.get("active", True)
            ]
        except Exception:
            reminders = []
        for offset in range(span):
            day = first + timedelta(days=offset)
            key = TASK_WEEKDAY_KEYS[day.weekday()]
            for t in tasks:
                repeat = t.get("repeat", "daily")
                if repeat != "daily" and repeat != key:
                    continue
                events.append(
                    {
                        "id": f"task-{t.get('id', '')}-{day.isoformat()}",
                        "quelle": "automation",
                        "titel": t.get("task", ""),
                        "datum": day.isoformat(),
                        "zeit": t.get("time", ""),
                        "typ": "task",
                        "erledigt": t.get("last_run") == day.isoformat(),
                    }
                )
            for r in reminders:
                if not r.get("time"):
                    continue
                if r.get("repeat") == "once" and r.get("last_fired"):
                    continue
                events.append(
                    {
                        "id": f"reminder-{r.get('id', '')}-{day.isoformat()}",
                        "quelle": "erinnerung",
                        "titel": r.get("text", ""),
                        "datum": day.isoformat(),
                        "zeit": r.get("time", ""),
                        "typ": "erinnerung",
                        "erledigt": False,
                    }
                )
        try:
            from app.services.mail_service import get_mail_service

            for e in get_mail_service().calendar_events(span):
                if first <= date.fromisoformat(e["datum"]) < first + timedelta(
                    days=span
                ):
                    events.append(
                        {
                            "id": f"ics-{e['datum']}-{e['titel'][:30]}",
                            "quelle": "ics",
                            "titel": e["titel"],
                            "datum": e["datum"],
                            "zeit": e.get("zeit", ""),
                            "ort": e.get("ort", ""),
                            "typ": "termin",
                            "erledigt": False,
                        }
                    )
        except Exception:
            pass
        return sorted(events, key=lambda e: (e["datum"], e["zeit"] or "99:99"))

    def due(self) -> list[dict]:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current = now.strftime("%H:%M")
        fired: list[dict] = []
        with self._lock:
            for e in self._data:
                if (
                    e.get("notified")
                    or e.get("done")
                    or not e.get("time")
                    or e["date"] != today
                    or e["time"] > current
                ):
                    continue
                e["notified"] = True
                fired.append(dict(e))
            if fired:
                self._save()
        return fired

    def upcoming_summary(self, days: int = 7) -> list[dict]:
        return self.merged(days=days)


_service: CalendarService | None = None


def get_calendar_service() -> CalendarService:
    global _service
    if _service is None:
        _service = CalendarService()
    return _service
