from __future__ import annotations

import json
import re
import threading
from datetime import date, datetime, timedelta

from app.core.config import DATA_DIR, get_settings
from app.core.store import atomic_write_text
from app.providers.base import ChatMessage, ChatRequest
from app.providers.registry import get_registry
from app.core.fehler import leise

INBOX_FILE = DATA_DIR / "inbox.json"

CATEGORIES = [
    {"id": "alle", "label": "Alle"},
    {"id": "wichtig", "label": "Wichtig"},
    {"id": "email", "label": "E-Mail"},
    {"id": "termin", "label": "Termine"},
    {"id": "aufgabe", "label": "Aufgaben"},
    {"id": "projekt", "label": "Projekte"},
    {"id": "system", "label": "System"},
]

ACTION_TYPES = {
    "kalender_neu",
    "kalender_aendern",
    "aufgabe_neu",
    "erinnerung_neu",
    "notiz_neu",
}

FREIGABE_PFLICHT = {"kalender_aendern"}

_SERIE_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")

ANALYSE_SYSTEM = (
    "Du bist Jons Inbox-Verstand. Du liest eine einzelne Nachricht und ziehst "
    "heraus, was der Nutzer daraus wirklich braucht: Termine, Terminaenderungen, "
    "Absagen, Aufgaben, Deadlines, Erinnerungen, Bestellungen, Lieferungen, "
    "Projektupdates, Anfragen und noetige Antworten. "
    "Du erfindest nichts. Steht kein Datum in der Nachricht, laesst du das Feld leer. "
    "Du antwortest AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Text davor oder danach, "
    "in genau dieser Form:\n"
    '{"typ": "termin|terminaenderung|absage|aufgabe|deadline|erinnerung|info|'
    'bestellung|lieferung|projektupdate|anfrage|antwort_noetig", '
    '"titel": "kurzer Betreff in eigenen Worten", '
    '"zusammenfassung": "1-2 Saetze auf Deutsch", '
    '"wichtigkeit": "hoch|mittel|niedrig", '
    '"datum": "YYYY-MM-DD oder leer", "zeit": "HH:MM oder leer", '
    '"deadline": "YYYY-MM-DD oder leer", "personen": ["Name"], '
    '"projekt": "Projektname oder leer", '
    '"aktionen": [{"typ": "kalender_neu|kalender_aendern|aufgabe_neu|erinnerung_neu|'
    'notiz_neu", "label": "Kalendereintrag erstellen", "payload": {}}]}\n'
    "Erlaubte payload-Felder: kalender_neu und aufgabe_neu -> title, date, time, "
    "duration_minutes, note. kalender_aendern -> suche (Stichwort des bestehenden "
    "Termins), date, time. erinnerung_neu -> text, time. notiz_neu -> text. "
    "Datumsangaben immer absolut als YYYY-MM-DD, gerechnet ab heute. "
    "Gibt es nichts zu tun, gib eine leere Aktionsliste zurueck."
)


def _today_block() -> str:
    now = datetime.now()
    tage = [
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ]
    return (
        f"Heute ist {tage[now.weekday()]}, der {now.strftime('%d.%m.%Y')}, "
        f"{now.strftime('%H:%M')} Uhr."
    )


def _json_block(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(raw[start : end + 1])
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sender_name(value: str) -> str:
    match = re.match(r'\s*"?([^"<]+)"?\s*<', value)
    if match:
        return match.group(1).strip()
    return value.strip()


def _mail_time(value: str) -> str:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(value.strip(), fmt).isoformat()
        except Exception:
            continue
    return ""


class InboxService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        base = {"analysen": {}, "gesehen": [], "ausgefuehrt": []}
        try:
            data = json.loads(INBOX_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base.update(data)
        except Exception as _fehler:
            leise(_fehler, "services/inbox_service")
        return base

    def _save(self) -> None:
        try:
            atomic_write_text(
                INBOX_FILE,
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/inbox_service")

    def analysis_for(self, key: str) -> dict | None:
        with self._lock:
            found = self._data["analysen"].get(key)
            return dict(found) if found else None

    def _store_analysis(self, key: str, value: dict) -> None:
        with self._lock:
            self._data["analysen"][key] = value
            if len(self._data["analysen"]) > 300:
                for old in list(self._data["analysen"])[:80]:
                    self._data["analysen"].pop(old, None)
            self._save()

    def mark_seen(self, key: str) -> None:
        with self._lock:
            seen = self._data.setdefault("gesehen", [])
            if key not in seen:
                seen.append(key)
                del seen[:-500]
                self._save()

    def _mails(self, limit: int) -> tuple[list[dict], str]:
        from app.services.mail_service import get_mail_service

        try:
            data = get_mail_service().check_mail(limit)
        except Exception as exc:
            return [], str(exc)
        items: list[dict] = []
        for mail in data.get("mails", []):
            key = f"mail:{mail['id']}"
            analysis = self.analysis_for(key)
            wichtig = bool(
                analysis and analysis.get("wichtigkeit") == "hoch"
            ) or bool(
                analysis
                and analysis.get("typ")
                in {"termin", "terminaenderung", "deadline", "absage"}
            )
            items.append(
                {
                    "id": key,
                    "kategorie": "email",
                    "titel": analysis.get("titel") if analysis else mail.get("betreff", ""),
                    "untertitel": _sender_name(mail.get("von", "")),
                    "text": (analysis or {}).get("zusammenfassung", ""),
                    "zeit": _mail_time(mail.get("datum", "")),
                    "wichtig": wichtig,
                    "quelle": "email",
                    "mail_id": mail.get("id", ""),
                    "betreff": mail.get("betreff", ""),
                    "von": mail.get("von", ""),
                    "analyse": analysis,
                }
            )
        return items, ""

    def _calendar(self, days: int) -> list[dict]:
        from app.services.calendar_service import get_calendar_service

        items: list[dict] = []
        try:
            events = get_calendar_service().merged(days=days)
        except Exception:
            return items
        today = date.today()
        gesehen: set[str] = set()
        for event in events:
            if event.get("erledigt"):
                continue
            if event.get("quelle") in {"erinnerung", "automation"}:
                serie = _SERIE_RE.sub("", str(event.get("id", "")))
                if serie in gesehen:
                    continue
                gesehen.add(serie)
            try:
                day = date.fromisoformat(event["datum"])
            except Exception:
                continue
            kind = event.get("typ", "termin")
            kategorie = "aufgabe" if kind in {"task", "erinnerung"} else "termin"
            items.append(
                {
                    "id": f"kalender:{event['id']}",
                    "kategorie": kategorie,
                    "titel": event.get("titel", ""),
                    "untertitel": (
                        f"{day.strftime('%d.%m.')} {event.get('zeit', '')}".strip()
                        + (f" · {event['ort']}" if event.get("ort") else "")
                    ),
                    "text": event.get("notiz", ""),
                    "zeit": f"{event['datum']}T{event.get('zeit') or '00:00'}:00",
                    "wichtig": day <= today + timedelta(days=1),
                    "quelle": event.get("quelle", "jon"),
                    "analyse": None,
                }
            )
        return items

    def _projects(self) -> list[dict]:
        from app.services.project_service import get_project_service

        items: list[dict] = []
        for project in get_project_service().list()[:6]:
            note = (project.get("notizen") or [""])[0]
            items.append(
                {
                    "id": f"projekt:{project['id']}",
                    "kategorie": "projekt",
                    "titel": project.get("name", ""),
                    "untertitel": project.get("technik") or project.get("root", ""),
                    "text": note,
                    "zeit": project.get("zuletzt", ""),
                    "wichtig": False,
                    "quelle": "projekt",
                    "root": project.get("root", ""),
                    "analyse": None,
                }
            )
        return items

    def _system(self) -> list[dict]:
        from app.services.task_service import get_task_service

        items: list[dict] = []
        try:
            tasks = get_task_service().list()
        except Exception:
            return items
        for task in tasks:
            if not task.get("last_result"):
                continue
            items.append(
                {
                    "id": f"automation:{task['id']}",
                    "kategorie": "system",
                    "titel": task.get("task", ""),
                    "untertitel": "Automation",
                    "text": str(task.get("last_result", ""))[:400],
                    "zeit": task.get("last_run_at") or "",
                    "wichtig": not task.get("seen", True),
                    "quelle": "automation",
                    "analyse": None,
                }
            )
        return items[:8]

    def feed(self, limit: int = 12, days: int = 7) -> dict:
        mails, mail_error = self._mails(limit)
        items = mails + self._calendar(days) + self._projects() + self._system()
        with self._lock:
            seen = set(self._data.get("gesehen") or [])
        for item in items:
            item["gesehen"] = item["id"] in seen
        items.sort(
            key=lambda entry: (not entry["wichtig"], entry.get("zeit") or ""),
        )
        zaehler = {category["id"]: 0 for category in CATEGORIES}
        for item in items:
            zaehler["alle"] += 1
            zaehler[item["kategorie"]] = zaehler.get(item["kategorie"], 0) + 1
            if item["wichtig"]:
                zaehler["wichtig"] += 1
        return {
            "kategorien": CATEGORIES,
            "zaehler": zaehler,
            "eintraege": items,
            "mail_fehler": mail_error,
            "stand": datetime.now().isoformat(timespec="seconds"),
        }

    async def analyze(
        self,
        key: str,
        text: str,
        subject: str = "",
        sender: str = "",
        provider: str | None = None,
        model: str | None = None,
        force: bool = False,
    ) -> dict:
        if not force:
            cached = self.analysis_for(key)
            if cached:
                return cached
        settings = get_settings()
        provider_name = provider or settings.default_provider
        model_name = model or settings.jon_model
        body = text.strip()[:6000]
        if not body:
            raise RuntimeError("Kein Text zum Analysieren.")
        prompt = (
            f"{_today_block()}\n\nAbsender: {sender or 'unbekannt'}\n"
            f"Betreff: {subject or '(kein Betreff)'}\n\nNachricht:\n{body}"
        )
        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=ANALYSE_SYSTEM),
                ChatMessage(role="user", content=prompt),
            ],
            model=model_name,
            temperature=0.2,
            top_p=1.0,
            max_tokens=1200,
            tools=[],
        )
        parts: list[str] = []
        async for chunk in get_registry().get(provider_name).stream(request, None):
            if chunk.kind == "content":
                parts.append(chunk.delta)
        data = _json_block("".join(parts))
        if not data:
            raise RuntimeError("Jon konnte die Nachricht nicht auswerten.")
        result = self._clean_analysis(data, subject)
        result["stand"] = datetime.now().isoformat(timespec="seconds")
        self._store_analysis(key, result)
        return result

    def _clean_analysis(self, data: dict, fallback_title: str) -> dict:
        actions: list[dict] = []
        for raw in data.get("aktionen") or []:
            if not isinstance(raw, dict):
                continue
            kind = str(raw.get("typ", "")).strip()
            if kind not in ACTION_TYPES:
                continue
            payload = raw.get("payload")
            actions.append(
                {
                    "typ": kind,
                    "label": str(raw.get("label") or kind)[:80],
                    "payload": payload if isinstance(payload, dict) else {},
                    "freigabe": kind in FREIGABE_PFLICHT,
                }
            )
        return {
            "typ": str(data.get("typ") or "info")[:40],
            "titel": str(data.get("titel") or fallback_title)[:160],
            "zusammenfassung": str(data.get("zusammenfassung") or "")[:600],
            "wichtigkeit": str(data.get("wichtigkeit") or "mittel")[:10],
            "datum": str(data.get("datum") or "")[:10],
            "zeit": str(data.get("zeit") or "")[:5],
            "deadline": str(data.get("deadline") or "")[:10],
            "personen": [str(p)[:60] for p in (data.get("personen") or [])][:6],
            "projekt": str(data.get("projekt") or "")[:80],
            "aktionen": actions[:4],
        }

    def apply(self, kind: str, payload: dict, source: str = "inbox") -> dict:
        from app.services.action_log_service import log_action
        from app.services.calendar_service import get_calendar_service

        if kind not in ACTION_TYPES:
            raise ValueError(f"Unbekannte Aktion: {kind}")
        calendar = get_calendar_service()
        result: dict
        if kind == "kalender_neu" or kind == "aufgabe_neu":
            result = calendar.add(
                title=str(payload.get("title") or payload.get("titel") or ""),
                day=str(payload.get("date") or payload.get("datum") or "heute"),
                time=str(payload.get("time") or payload.get("zeit") or ""),
                duration_minutes=int(payload.get("duration_minutes") or 0),
                note=str(payload.get("note") or payload.get("notiz") or ""),
                kind="task" if kind == "aufgabe_neu" else "termin",
            )
        elif kind == "kalender_aendern":
            query = str(payload.get("suche") or payload.get("title") or "").strip()
            treffer = calendar.search(query) if query else []
            if not treffer:
                raise ValueError(
                    f"Kein bestehender Eintrag zu '{query}' gefunden. "
                    "Lege ihn stattdessen neu an."
                )
            fields: dict = {}
            if payload.get("date") or payload.get("datum"):
                fields["date"] = str(payload.get("date") or payload.get("datum"))
            if payload.get("time") or payload.get("zeit"):
                fields["time"] = str(payload.get("time") or payload.get("zeit"))
            if payload.get("title"):
                fields["title"] = str(payload["title"])
            result = calendar.update(treffer[0]["id"], fields)
        elif kind == "erinnerung_neu":
            from app.services.reminder_service import ReminderService

            result = ReminderService().add(
                str(payload.get("text") or payload.get("title") or ""),
                str(payload.get("time") or payload.get("zeit") or ""),
                str(payload.get("repeat") or "once"),
            )
        else:
            from app.services.notes_service import get_notes_service

            result = get_notes_service().add(
                str(payload.get("text") or payload.get("titel") or "")
            )
        with self._lock:
            done = self._data.setdefault("ausgefuehrt", [])
            done.append(
                {
                    "typ": kind,
                    "zeit": datetime.now().isoformat(timespec="seconds"),
                    "payload": payload,
                }
            )
            del done[:-200]
            self._save()
        log_action(source, f"inbox:{kind}", payload, json.dumps(result, ensure_ascii=False)[:400], ok=True)
        return {"aktion": kind, "ergebnis": result}


_service: InboxService | None = None


def get_inbox_service() -> InboxService:
    global _service
    if _service is None:
        _service = InboxService()
    return _service
