from __future__ import annotations

import asyncio
import contextvars
import json
import re
import time
from pathlib import Path
from typing import Any

from app.services.automation_service import AutomationService
from app.services.browser.schema import erklaeren as browser_erklaeren
from app.services.browser.schema import namen as browser_namen
from app.services.browser.schema import schema as browser_schema
from app.services.capsule_service import get_capsule_service
from app.services.clipboard_service import get_clipboard_service
from app.services.knowledge_service import get_knowledge_service
from app.services.memory_service import MemoryService
from app.services.persona_service import get_persona_service
from app.services.reminder_service import ReminderService
from app.services.risiko import pfad_pruefen
from app.services.werkzeug_register import finden, finden_async, laden

NETZ_TOOLS = {
    "web_search",
    "http_get",
    "download_file",
    "get_weather",
    "browser_goto",
    "browser_search",
    "browser_task",
    "spotify_play",
    "spotify_search",
    "spotify_now_playing",
    "maps",
    "deep_learning",
    "create_image",
    "send_mail",
    "check_mail",
    "read_mail",
    "learn_document",
}
from app.services.skill_service import SkillService
from app.services.system_service import SystemService
from app.services.task_service import get_task_service
from app.services.timetravel_service import get_timetravel_service
from app.core.fehler import leise

_QUELLE: contextvars.ContextVar[str] = contextvars.ContextVar("jon_quelle", default="")

_SUCHEN: contextvars.ContextVar[int] = contextvars.ContextVar("jon_suchen", default=0)
MAX_SUCHEN = 3
ZAHLENFRAGE = (
    "preis",
    "price",
    "kostet",
    "kosten",
    "teuer",
    "uvp",
    "euro",
    "eur",
    "dollar",
    "€",
    "$",
    "wie viel",
    "wieviel",
    "how much",
    "rabatt",
    "angebot",
)


def runde_beginnen() -> None:
    _SUCHEN.set(0)


_NAME_MUELL = re.compile(r"<\|.*$|[^A-Za-z0-9_.\-].*$")


def _zu_duenn(name: str, ergebnis: str) -> bool:
    if name != "web_search":
        return False
    try:
        daten = json.loads(ergebnis)
    except Exception:
        return False
    return bool(daten.get("mager")) or not daten.get("treffer")


def _name_saeubern(name: str) -> str:
    sauber = _NAME_MUELL.sub("", str(name or "").strip())
    return sauber or str(name or "").strip()


_ZEIT_TOOLS = {
    "start_stopwatch",
    "start_timer",
    "set_alarm",
    "stop_timer",
    "list_timers",
    "adjust_timer",
    "control_timer",
    "list_alarms",
    "delete_alarm",
}

_STR = {"type": "string"}
_NUM = {"type": "number"}
_INT = {"type": "integer"}
_BOOL = {"type": "boolean"}

SAFE_TOOLS = {
    "get_screen_info",
    "list_windows",
    "wait",
    "recall",
    "system_info",
    "list_processes",
    "list_skills",
    "read_skill",
    "list_reminders",
    "list_alarms",
    "list_scheduled_calls",
    "web_search",
    "get_weather",
    "journal",
    "read_journal",
    "remember_about_user",
    "set_mood",
    "list_snapshots",
    "snapshot",
    "start_focus",
    "stop_focus",
    "recall_screen",
    "ask_knowledge",
    "list_documents",
    "clipboard_history",
    "list_tasks",
    "list_capsules",
    "check_mail",
    "get_calendar",
    "media_control",
    "list_watchers",
    "smarthome_devices",
    "scan_network",
    "list_printers",
    "spotify_search",
    "spotify_now_playing",
    "amazon_now_playing",
    "list_friends",
    "read_friend_messages",
    "browser_read",
    "browser_screenshot",
    "browser_status",
    "was_war",
    "verlauf_heute",
    "netz_status",
    "selbsteinschaetzung",
    "ueberraschungen",
    "durchspielen",
    "dateien_finden",
    "dateiraum",
    "umgebung",
    "oberflaeche",
    "desktop_verknuepfung",
    "frage_merken",
    "offene_fragen",
    "fertigkeiten",
    "ziel",
    "selbstbild",
    "weltzustand",
    "erfahrung",
    "notizblock",
    "calendar_list",
    "calendar_search",
    "read_pptx",
    "maps",
    "deep_learning",
    "create_image",
    "read_skill_file",
    "project_overview",
    "git_status",
    "git_diff",
    "start_stopwatch",
    "start_timer",
    "stop_timer",
    "list_timers",
    "adjust_timer",
    "control_timer",
    "look_at_image",
    "android_devices",
    "android_device_status",
    "android_battery_status",
    "android_files_list",
}


GUEST_TOOLS = {
    "maps",
    "deep_learning",
    "create_image",
    "web_search",
    "get_weather",
    "list_skills",
    "read_skill",
    "read_skill_file",
    "wait",
}


CORE_TOOLS = {
    "run_powershell",
    "run_cmd",
    "start_program",
    "kill_program",
    "open_explorer",
    "open_in_vscode",
    "list_dir",
    "read_file",
    "write_file",
    "edit_file",
    "move_path",
    "delete_path",
    "make_dir",
    "append_file",
    "copy_path",
    "search_files",
    "zip_paths",
    "unzip",
    "clipboard_get",
    "clipboard_set",
    "screenshot",
    "get_screen_info",
    "http_get",
    "download_file",
    "system_info",
    "list_processes",
    "lock_screen",
    "mouse_move",
    "mouse_click",
    "mouse_scroll",
    "keyboard_type",
    "keyboard_press",
    "keyboard_hotkey",
    "list_windows",
    "focus_window",
    "wait",
    "remember",
    "recall",
    "forget",
    "list_skills",
    "read_skill",
    "web_search",
    "get_weather",
    "journal",
    "remember_about_user",
    "maps",
    "deep_learning",
    "create_image",
    "read_skill_file",
    "look_at_image",
}

_CHDIR_RE = re.compile(
    r"(?:^|[;&|`(]|\bthen\b|\bdo\b)\s*"
    r"(?:cd|chdir|pushd|sl|set-location)\s+"
    r"(?:/d\s+)?(?:-(?:literal)?path\s+)?"
    r"(?P<path>\"[^\"]+\"|'[^']+'|[^\s;&|)]+)",
    re.IGNORECASE,
)

CODING_TOOLS = {
    "run_powershell",
    "run_cmd",
    "project_overview",
    "git_status",
    "git_diff",
    "list_dir",
    "read_file",
    "write_file",
    "edit_file",
    "append_file",
    "search_files",
    "make_dir",
    "move_path",
    "copy_path",
    "delete_path",
    "zip_paths",
    "unzip",
    "open_in_vscode",
    "open_url",
    "http_get",
    "download_file",
    "web_search",
    "read_pdf",
    "create_pptx",
    "read_pptx",
    "list_skills",
    "read_skill",
    "wait",
}

TOOL_GROUPS: dict[str, tuple[set[str], tuple[str, ...]]] = {
    "browser": (
        browser_namen("browser_") | {"open_url"},
        (
            "browser",
            "tab",
            "oeffne",
            "öffne",
            "mach auf",
            "zeig mir die",
            "ruf auf",
            "aufrufen",
            "besuch",
            "webseite",
            "website",
            "www.",
            "http",
            "klick",
            "click",
            "formular",
            "ausfuell",
            "ausfüll",
            "bestell",
            "buchen",
            "anmeld",
            "einloggen",
            "geh auf",
            "geh zu",
            "surf",
            "such auf",
            "auf der seite",
            "warenkorb",
            "in den korb",
            "kaufen",
            "reservier",
            "leg mir",
        ),
    ),
    "calendar": (
        {
            "calendar_add",
            "calendar_list",
            "calendar_update",
            "calendar_delete",
            "calendar_search",
        },
        (
            "kalender",
            "calendar",
            "termin",
            "verschieb",
            "trag",
            "tag mir",
            "tag mir ein",
            "eintrag",
            "eintragen",
            "notier",
            "erinner",
            "erinnere",
            "erinnerung",
            "denk dran",
            "denk daran",
            "vergiss nicht",
            "plan",
            "geplant",
            "vormerken",
            "merk dir",
            "montag",
            "dienstag",
            "mittwoch",
            "donnerstag",
            "freitag",
            "samstag",
            "sonntag",
            "morgen",
            "uebermorgen",
            "übermorgen",
            "uhr",
            "woche",
            "zahnarzt",
            "arzt",
            "geburtstag",
            "treffen",
            "meeting",
        ),
    ),
    "focus": (
        {"start_focus", "stop_focus"},
        (
            "fokus",
            "focus",
            "konzentr",
            "lernen",
            "lerne",
            "produktiv",
            "ablenk",
            "pomodoro",
            "timer fuers",
            "dranbleiben",
        ),
    ),
    "bilder": (
        {"look_at_image"},
        (
            "foto",
            "bild",
            "video",
            "aufnahme",
            "screenshot",
            "was ist da drauf",
            "schau dir",
            "sieh dir",
            "hochgeladen",
        ),
    ),
    "zeit": (
        {
            "start_stopwatch",
            "start_timer",
            "stop_timer",
            "list_timers",
            "adjust_timer",
            "control_timer",
            "set_alarm",
        },
        (
            "stoppuhr",
            "stopp die zeit",
            "stoppe die zeit",
            "zeit stoppen",
            "timer",
            "countdown",
            "wie lange",
            "zeit messen",
            "misst die zeit",
            "wecker",
            "weck mich",
            "erhoeh",
            "erhöh",
            "verlaenger",
            "verlänger",
            "verkuerz",
            "verkürz",
            "mach laenger",
            "mach länger",
            "mach kuerzer",
            "mach kürzer",
            "noch mal",
            "neustart",
            "von vorn",
            "zuruecksetzen",
            "zurücksetzen",
            "pausier",
            "weiterlaufen",
            "spaeter",
            "später",
            "frueher",
            "früher",
            "ton aus",
            "klingel",
        ),
    ),
    "dateien_jon": (
        {
            "datei_erstellen",
            "ordner_anlegen",
            "datei_oeffnen",
            "ordner_oeffnen",
            "dateien_finden",
            "dateiraum",
            "umgebung",
            "oberflaeche",
            "desktop_verknuepfung",
            "blender_szene",
            "blender_render",
            "blender_export",
        },
        (
            "erstell",
            "mach mir",
            "schreib mir",
            "pdf",
            "word",
            "docx",
            "excel",
            "xlsx",
            "tabelle",
            "dokument",
            "datei",
            "dateien",
            "ordner",
            "speicher",
            "speichere",
            "ablegen",
            "desktop",
            "im ordner",
            "oeffne den ordner",
            "öffne den ordner",
            "wo liegt",
            "wo hast du",
            "blender",
            "3d",
            "modell",
            "render",
            "szene",
            "wuerfel",
            "würfel",
            "exportier",
            "installiert",
            "verfuegbar",
            "verfügbar",
            "verknuepfung",
            "verknüpfung",
            "symbol",
            "desktop-symbol",
            "startsymbol",
            "icon",
        ),
    ),
    "denken": (
        {
            "ziel",
            "weltmodell",
            "notizblock",
            "selbstbild",
            "erfahrung",
            "weltzustand",
            "gedaechtnis_pflegen",
            "initiative",
            "team",
            "lernen",
            "selbsteinschaetzung",
            "ueberraschungen",
            "frage_merken",
            "offene_fragen",
            "frage_klaeren",
            "fertigkeiten",
            "fertigkeit_nutzen",
            "plan_machen",
            "plan_ausfuehren",
            "aufgabe",
            "aufgabe_starten",
            "ausloeser",
            "bericht",
            "durchspielen",
            "hypothese",
        },
        (
            "ziel",
            "ziele",
            "vorhaben",
            "plan",
            "projekt",
            "morgen",
            "naechste woche",
            "was steht an",
            "kannst du",
            "schaffst du",
            "wie sicher",
            "merk dir",
            "notier",
            "team",
            "vergleich",
            "recherche",
            "lern",
            "erfahrung",
            "ueberblick",
            "zustand",
            "initiative",
            "vorschlag",
            "wie sicher bist du",
            "was hast du gelernt",
            "ueberrascht",
            "überrascht",
            "weisst du nicht",
            "weißt du nicht",
            "offene frage",
            "fertigkeit",
            "kannst du dir merken wie",
            "immer wenn",
            "zerleg",
            "schritt fuer schritt",
            "schritt für schritt",
            "kuemmere dich",
            "kümmere dich",
            "erledige",
            "arbeite daran",
            "bis heute abend",
            "in der zwischenzeit",
            "waehrenddessen",
            "während ich",
            "aufgabe",
            "aufgabenliste",
            "woran arbeitest du",
            "wie weit bist du",
            "vermutung",
            "woran liegt",
            "warum scheitert",
        ),
    ),
    "timeline": (
        {"recall_screen", "was_war", "verlauf_heute", "rueckgaengig"},
        (
            "hatte ich",
            "offen",
            "vorhin",
            "gestern",
            "letzte woche",
            "bildschirm",
            "zuletzt",
            "erinnerst du dich",
            "was war",
            "was habe ich",
            "was hast du",
            "gemacht",
            "getan",
            "protokoll",
            "verlauf",
            "rueckblick",
            "rückblick",
            "zusammenfassung",
            "tag",
        ),
    ),
    "media": (
        {
            "media_control",
            "spotify_play",
            "spotify_search",
            "spotify_now_playing",
            "amazon_play",
            "amazon_now_playing",
        },
        (
            "musik",
            "music",
            "song",
            "lied",
            "spiel",
            "spotify",
            "amazon",
            "playlist",
            "lauter",
            "leiser",
            "laut",
            "leise",
            "stumm",
            "pause",
            "weiter",
            "naechst",
            "nächst",
            "track",
            "album",
            "band",
            "laeuft",
            "läuft",
            "hoer",
            "hör",
        ),
    ),
    "mail": (
        {"check_mail", "read_mail", "send_mail"},
        ("mail", "postfach", "inbox", "posteingang", "schreib", "antwort"),
    ),
    "calendar_ics": (
        {"get_calendar"},
        ("kalender", "termin", "meeting", "woche", "heute", "morgen", "plan"),
    ),
    "knowledge": (
        {"learn_document", "ask_knowledge", "list_documents", "forget_document"},
        (
            "lern",
            "wissen",
            "dokument",
            "pdf",
            "datei lesen",
            "unterlage",
            "notiz",
            "handbuch",
            "vertrag",
            "zusammenfass",
        ),
    ),
    "clipboard": (
        {"clipboard_history"},
        ("kopiert", "zwischenablage", "clipboard", "verlauf", "eingefuegt"),
    ),
    "phone": (
        {
            "call_user",
            "schedule_call",
            "list_scheduled_calls",
            "cancel_call",
            "update_call",
        },
        (
            "ruf mich",
            "ruf mich an",
            "anruf",
            "anrufen",
            "telefon",
            "telefonier",
            "melde dich",
            "klingel",
            "handy",
            "testanruf",
            "call",
        ),
    ),
    "tasks": (
        {"add_task", "list_tasks", "delete_task"},
        (
            "automation",
            "automatisch",
            "jeden tag",
            "jeden",
            "taeglich",
            "täglich",
            "regelmaess",
            "regelmäß",
            "uhr",
            "plane",
            "aufgabe",
            "wiederhol",
        ),
    ),
    "watchers": (
        {"add_watcher", "list_watchers", "delete_watcher"},
        (
            "ueberwach",
            "überwach",
            "waechter",
            "wächter",
            "sobald",
            "neue datei",
            "beobacht",
            "downloads",
            "sortier",
        ),
    ),
    "capsules": (
        {"time_capsule", "list_capsules"},
        ("zeitkapsel", "kapsel", "zukunft", "spaeter oeffnen"),
    ),
    "webcam": (
        {"webcam_look"},
        ("webcam", "kamera", "siehst", "sehe", "schau", "aussehe"),
    ),
    "smarthome": (
        {"smarthome_devices", "smarthome_control"},
        (
            "licht",
            "lampe",
            "heizung",
            "smart",
            "steckdose",
            "rollladen",
            "rolladen",
            "jalousie",
            "temperatur",
            "grad",
            "wohnzimmer",
            "schlafzimmer",
            "kueche",
            "küche",
            "staubsauger",
            "tuer",
            "tür",
        ),
    ),
    "netz": (
        {"netz_status", "browser_wahl"},
        (
            "internet",
            "online",
            "offline",
            "verbindung",
            "netz",
            "wlan",
            "erreichbar",
        ),
    ),
    "network": (
        {"scan_network", "wake_device"},
        (
            "netzwerk",
            "wlan",
            "netz",
            "geraet",
            "gerät",
            "ip",
            "wecken",
            "wake",
            "router",
            "hochfahren",
        ),
    ),
    "printer": (
        {"list_printers", "print_file"},
        ("druck", "drucker", "ausdruck", "print", "papier"),
    ),
    "alarm": (
        {
            "set_alarm",
            "list_alarms",
            "delete_alarm",
            "adjust_timer",
            "control_timer",
            "set_reminder",
            "list_reminders",
        },
        (
            "wecker",
            "timer",
            "erinner",
            "wecke mich",
            "alarm",
            "minuten",
            "uhr",
            "denk dran",
        ),
    ),
    "timetravel": (
        {"snapshot", "list_snapshots", "restore_snapshot"},
        ("snapshot", "zeitreise", "stand", "zurueck", "zurück", "sicher"),
    ),
    "persona": (
        {"read_journal", "set_mood", "write_skill"},
        (
            "gedaechtnis",
            "gedächtnis",
            "erinnerst",
            "fuehl",
            "fühl",
            "stimmung",
            "skill",
            "merk dir",
        ),
    ),
    "pdf": ({"read_pdf"}, ("pdf", "dokument", "seite", "lesen")),
    "pptx": (
        {"create_pptx", "read_pptx"},
        (
            "powerpoint",
            "power point",
            "pptx",
            "praesentation",
            "präsentation",
            "folie",
            "folien",
            "slide",
            "deck",
            "vortrag",
            "referat",
            "praesi",
            "präsi",
            "handout",
            "pitch",
        ),
    ),
    "friends": (
        {"list_friends", "send_friend_message", "read_friend_messages"},
        (
            "freund",
            "schreib",
            "sag ",
            "nachricht",
            "chat",
            "gruppe",
            "geschrieben",
            "antworte",
            "melde",
            "richte",
        ),
    ),
}


ANDROID_WOERTER = (
    "handy",
    "smartphone",
    "telefon",
    "android",
    "pixel",
    "samsung",
    "tablet",
    "akku",
    "batterie",
    "benachrichtigung",
    "mitteilung",
    "zwischenablage",
    "kontakt",
    "wo ist mein",
    "unterwegs",
)


def _connector_werkzeuge() -> list[dict]:
    from app.services.connectors import get_connector_manager

    try:
        return get_connector_manager().schema()
    except Exception:
        return []


def _connector_auswahl(text: str) -> set[str]:
    if not any(word in text for word in ANDROID_WOERTER):
        return set()
    from app.services.connectors import get_connector_manager

    try:
        return get_connector_manager().namen()
    except Exception:
        return set()


def select_tools(context: str) -> set[str] | None:
    text = context.strip().lower()
    if not text:
        return None
    allowed = set(CORE_TOOLS)
    for names, keywords in TOOL_GROUPS.values():
        if any(word in text for word in keywords):
            allowed |= names
    allowed |= _connector_auswahl(text)
    try:
        from app.services.tool_index import passende_werkzeuge

        allowed |= passende_werkzeuge(context)
    except Exception as _fehler:
        leise(_fehler, "services/tools")
    return allowed


def _shorten(value: Any, limit: int = 120) -> str:
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _phone_when(value: str) -> str:
    from datetime import datetime

    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    today = datetime.now(moment.tzinfo).date()
    delta = (moment.date() - today).days
    clock = moment.strftime("%H:%M")
    if delta == 0:
        return f"heute um {clock}"
    if delta == 1:
        return f"morgen um {clock}"
    return moment.strftime("%d.%m.%Y um %H:%M")


def _android_text(name: str, args: dict[str, Any]) -> str:
    ziel = str(args.get("device") or "").strip()
    anhang = f" ({ziel})" if ziel else ""
    if name == "android_files_send":
        return f"Schickt {_shorten(args.get('path', ''))} auf das Handy{anhang}."
    if name == "android_files_receive":
        return f"Holt {_shorten(args.get('path', ''))} vom Handy{anhang} auf den PC."
    if name == "android_clipboard_send":
        return f"Legt Text in die Zwischenablage des Handys{anhang}."
    if name == "android_camera_request_photo":
        return (
            f"Fragt am Handy{anhang} sichtbar nach einem Foto: "
            f"{_shorten(args.get('reason', ''))}"
        )
    if name == "android_contacts_search":
        return (
            f"Sucht {_shorten(args.get('query', ''))} in den Kontakten "
            f"des Handys{anhang}."
        )
    from app.services.connectors.android import AndroidConnector

    texte = AndroidConnector().kurztexte()
    return texte.get(name, f"Fragt das Handy{anhang} etwas.")


def describe_tool(name: str, args: dict[str, Any]) -> str:
    if name.startswith("android_") or name.startswith("android."):
        return _android_text(name.replace(".", "_"), args)
    if name == "call_user":
        when = str(args.get("datetime", "")).strip()
        return f"Ruft dich an ({when})." if when else "Ruft dich jetzt auf dem Handy an."
    if name == "schedule_call":
        return f"Plant einen Anruf für {str(args.get('datetime', '')).strip()}."
    if name == "list_scheduled_calls":
        return "Zeigt deine geplanten Anrufe."
    if name == "cancel_call":
        return "Sagt einen geplanten Anruf ab."
    if name == "update_call":
        return "Ändert einen geplanten Anruf."
    if name == "run_powershell":
        return "Führt einen PowerShell-Befehl auf deinem PC aus."
    if name == "run_cmd":
        return "Führt einen CMD-Befehl auf deinem PC aus."
    if name == "open_url":
        from app.services.browserwahl import name as browsername

        return (
            f"Öffnet {_shorten(args.get('url', 'eine URL'))} in "
            f"{browsername(str(args.get('browser', '')))}."
        )
    if name == "look_at_image":
        return f"Schaut sich {_shorten(args.get('path', ''))} an."
    if name == "start_stopwatch":
        return "Startet eine Stoppuhr."
    if name == "start_timer":
        return "Stellt einen Timer."
    if name == "stop_timer":
        return "Stoppt die Zeit."
    if name == "list_timers":
        return "Zeigt laufende Stoppuhren, Timer und Wecker."
    if name == "adjust_timer":
        minuten = int(args.get("minutes", 0) or 0)
        sekunden = int(args.get("seconds", 0) or 0)
        gesamt = minuten * 60 + sekunden
        richtung = "Verlängert" if gesamt >= 0 else "Verkürzt"
        return f"{richtung} die Uhr um {abs(gesamt) // 60} Min. {abs(gesamt) % 60} Sek."
    if name == "control_timer":
        aktion = str(args.get("action", "")).strip().lower()
        texte = {
            "pause": "Hält die Uhr an.",
            "resume": "Lässt die Uhr weiterlaufen.",
            "restart": "Startet die Uhr neu.",
            "stop": "Beendet die Uhr.",
            "silence": "Schaltet das Klingeln aus.",
        }
        return texte.get(aktion, "Steuert eine laufende Uhr.")
    if name == "start_focus":
        return "Startet den Fokus-Modus."
    if name == "stop_focus":
        return "Beendet den Fokus-Modus."
    if name == "recall_screen":
        return f"Durchsucht dein Bildschirm-Gedächtnis nach {_shorten(args.get('query', ''))}."
    if name == "start_program":
        return f"Startet das Programm {_shorten(args.get('path', ''))}."
    if name == "kill_program":
        return f"Beendet das Programm {_shorten(args.get('name', ''))}."
    if name == "open_explorer":
        return f"Öffnet den Ordner {_shorten(args.get('path', ''))} im Explorer."
    if name == "list_dir":
        return f"Listet den Inhalt von {_shorten(args.get('path', ''))} auf."
    if name == "read_file":
        return f"Liest die Datei {_shorten(args.get('path', ''))}."
    if name == "write_file":
        return f"Schreibt in die Datei {_shorten(args.get('path', ''))}."
    if name == "edit_file":
        return f"Ändert gezielt die Datei {_shorten(args.get('path', ''))}."
    if name == "move_path":
        return (
            f"Verschiebt {_shorten(args.get('source', ''))} nach "
            f"{_shorten(args.get('destination', ''))}."
        )
    if name == "delete_path":
        return f"Löscht {_shorten(args.get('path', ''))}."
    if name == "open_in_vscode":
        return f"Öffnet {_shorten(args.get('path', ''))} in VS Code."
    if name == "get_screen_info":
        return "Fragt Bildschirmgröße und Mausposition ab."
    if name == "mouse_move":
        return f"Bewegt die Maus zu x={args.get('x')}, y={args.get('y')}."
    if name == "mouse_click":
        return "Klickt mit der Maus."
    if name == "mouse_scroll":
        return f"Scrollt um {args.get('amount')}."
    if name == "keyboard_type":
        return f"Tippt den Text: {_shorten(args.get('text', ''))}"
    if name == "keyboard_press":
        return f"Drückt die Taste {_shorten(args.get('key', ''))}."
    if name == "keyboard_hotkey":
        keys = "+".join(str(k) for k in args.get("keys") or [])
        return f"Drückt die Tastenkombination {keys}."
    if name == "list_windows":
        return "Listet alle offenen Fenster auf."
    if name == "focus_window":
        return f"Holt das Fenster „{_shorten(args.get('title', ''))}“ in den Vordergrund."
    if name == "wait":
        return f"Wartet {args.get('seconds')} Sekunden."
    if name == "remember":
        return f"Merkt sich: {_shorten(args.get('content', ''))}"
    if name == "recall":
        return "Ruft gespeicherte Erinnerungen ab."
    if name == "forget":
        return f"Löscht Erinnerungen zu: {_shorten(args.get('query', ''))}"
    if name == "make_dir":
        return f"Erstellt den Ordner {_shorten(args.get('path', ''))}."
    if name == "append_file":
        return f"Hängt Text an die Datei {_shorten(args.get('path', ''))} an."
    if name == "copy_path":
        return (
            f"Kopiert {_shorten(args.get('source', ''))} nach "
            f"{_shorten(args.get('destination', ''))}."
        )
    if name == "search_files":
        return f"Sucht {_shorten(args.get('pattern', ''))} in {_shorten(args.get('root', ''))}."
    if name == "zip_paths":
        return f"Packt eine ZIP-Datei nach {_shorten(args.get('destination', ''))}."
    if name == "unzip":
        return f"Entpackt {_shorten(args.get('source', ''))}."
    if name == "clipboard_get":
        return "Liest die Zwischenablage."
    if name == "clipboard_set":
        return f"Kopiert in die Zwischenablage: {_shorten(args.get('text', ''))}"
    if name == "screenshot":
        return "Macht einen Screenshot des Bildschirms."
    if name == "http_get":
        return f"Ruft {_shorten(args.get('url', ''))} ab."
    if name == "download_file":
        return f"Lädt {_shorten(args.get('url', ''))} herunter."
    if name == "system_info":
        return "Fragt Systeminformationen ab."
    if name == "list_processes":
        return "Listet laufende Prozesse auf."
    if name == "lock_screen":
        return "Sperrt den Bildschirm."
    if name == "list_skills":
        return "Listet verfügbare Skills auf."
    if name == "read_skill":
        return f"Liest die Skill-Anleitung „{_shorten(args.get('name', ''))}“."
    if name == "read_skill_file":
        return (
            f"Liest die Wissensdatei „{_shorten(args.get('file', ''))}“ aus dem Skill "
            f"„{_shorten(args.get('name', ''))}“."
        )
    if name == "create_image":
        art = "Video" if str(args.get("kind", "")) == "video" else "Bild"
        return f"Erstellt ein {art}: {_shorten(args.get('prompt', ''), 70)}"
    if name == "maps":
        action = str(args.get("action", "suche"))
        if action == "route":
            start = _shorten(args.get("from", "hier"), 40)
            unterwegs = [
                _shorten(str(item), 30)
                for item in (list(args.get("via") or []) + list(args.get("stops") or []))
                if str(item).strip()
            ]
            ziel = _shorten(args.get("to", ""), 40)
            kette = [start] + unterwegs + ([ziel] if ziel else [])
            modus = {
                "fuss": "zu Fuß",
                "auto": "mit dem Auto",
                "fahrrad": "mit dem Fahrrad",
                "oepnv": "mit Bus und Bahn",
            }.get(str(args.get("mode", "auto")), "")
            if len(kette) > 2:
                return f"Plant den Trip {modus} über {' → '.join(kette)}."
            return f"Berechnet die Route {modus} von {start} nach {ziel}."
        if action == "umgebung":
            was = _shorten(args.get("category") or args.get("query", ""), 40)
            wo = _shorten(args.get("around", ""), 40)
            return f"Filtert die Karte nach {was}{f' rund um {wo}' if wo else ' in der Nähe'}."
        if action == "erkunden":
            return f"Öffnet {_shorten(args.get('query', ''), 50)} zum Erkunden."
        return f"Sucht auf der Karte nach: {_shorten(args.get('query', ''))}"
    if name == "deep_learning":
        action = str(args.get("action", "start"))
        if action == "start":
            minutes = args.get("minutes")
            budget = f" ({minutes} Minuten)" if minutes else ""
            return (
                f"Startet eine Tiefenrecherche über "
                f"„{_shorten(args.get('topic', ''))}“{budget}."
            )
        if action == "status":
            return "Zeigt den Stand der laufenden Recherchen."
        if action == "pause":
            return "Pausiert die laufende Recherche."
        if action in ("weiter", "resume"):
            return "Setzt die Recherche fort."
        return "Bricht die Recherche ab und sichert den Fortschritt."
    if name == "write_skill":
        return f"Speichert die Skill-Anleitung „{_shorten(args.get('name', ''))}“."
    if name == "set_reminder":
        return f"Erinnerung um {args.get('time', '')}: {_shorten(args.get('text', ''))}"
    if name == "list_reminders":
        return "Listet aktive Erinnerungen auf."
    if name == "set_alarm":
        when = args.get("time") or (
            f"in {args.get('in_minutes')} Minuten" if args.get("in_minutes") else ""
        )
        return f"Stellt einen Wecker ({when}): {_shorten(args.get('label', ''))}"
    if name == "list_alarms":
        return "Listet gestellte Wecker auf."
    if name == "delete_alarm":
        return f"Löscht den Wecker {_shorten(args.get('name', ''))}."
    if name == "web_search":
        return f"Sucht im Web nach: {_shorten(args.get('query', ''))}"
    if name == "get_weather":
        return f"Fragt das Wetter für {_shorten(args.get('city', ''))} ab."
    if name == "read_pdf":
        return f"Liest die PDF-Datei {_shorten(args.get('path', ''))}."
    if name == "create_pptx":
        slides = args.get("slides")
        anzahl = len(slides) if isinstance(slides, list) else 0
        return (
            f"Erstellt die PowerPoint „{_shorten(args.get('title', ''))}“"
            + (f" mit {anzahl} Folien." if anzahl else ".")
        )
    if name == "read_pptx":
        return f"Liest die PowerPoint {_shorten(args.get('path', ''))}."
    if name == "journal":
        return f"Schreibt in Jons Gedächtnis: {_shorten(args.get('entry', ''))}"
    if name == "read_journal":
        return "Liest Jons persönliches Gedächtnis (MEMORY.md)."
    if name == "remember_about_user":
        return f"Merkt sich über dich: {_shorten(args.get('note', ''))}"
    if name == "set_mood":
        return f"Jons Stimmung wechselt zu: {_shorten(args.get('mood', ''))}"
    if name == "snapshot":
        return f"Speichert einen Zeitreise-Snapshot: {_shorten(args.get('label', ''))}"
    if name == "list_snapshots":
        return "Listet gespeicherte Zeitreise-Snapshots auf."
    if name == "restore_snapshot":
        return f"Stellt den Snapshot {_shorten(args.get('id', ''))} wieder her."
    if name == "learn_document":
        target = args.get("path") or args.get("title") or "Text"
        return f"Lernt {_shorten(target)} in die Wissensbasis."
    if name == "ask_knowledge":
        return f"Durchsucht die Wissensbasis nach: {_shorten(args.get('query', ''))}"
    if name == "list_documents":
        return "Listet gelernte Dokumente der Wissensbasis auf."
    if name == "forget_document":
        return f"Entfernt aus der Wissensbasis: {_shorten(args.get('ref', ''))}"
    if name == "clipboard_history":
        return "Zeigt den Verlauf der Zwischenablage."
    if name == "add_task":
        return (
            f"Plant eine Automation um {args.get('time', '')}: "
            f"{_shorten(args.get('task', ''))}"
        )
    if name == "list_tasks":
        return "Listet geplante Automationen auf."
    if name == "delete_task":
        return f"Löscht die Automation {_shorten(args.get('id', ''))}."
    if name == "time_capsule":
        return (
            f"Versiegelt eine Zeitkapsel bis {args.get('date', '')}: "
            f"{_shorten(args.get('text', ''))}"
        )
    if name == "list_capsules":
        return "Listet Zeitkapseln auf."
    if name == "webcam_look":
        return "Schaut durch die Webcam und beschreibt, was zu sehen ist."
    if name == "check_mail":
        return "Prüft das E-Mail-Postfach auf ungelesene Nachrichten."
    if name == "read_mail":
        return f"Liest die E-Mail {_shorten(args.get('id', ''))}."
    if name == "send_mail":
        return (
            f"Sendet eine E-Mail an {_shorten(args.get('to', ''))}: "
            f"{_shorten(args.get('subject', ''))}"
        )
    if name == "get_calendar":
        return "Liest die nächsten Kalender-Termine."
    if name == "media_control":
        return f"Mediensteuerung: {_shorten(args.get('action', ''))}."
    if name == "add_watcher":
        return (
            f"Überwacht den Ordner {_shorten(args.get('path', ''))}: "
            f"{_shorten(args.get('task', ''))}"
        )
    if name == "list_watchers":
        return "Listet Datei-Wächter auf."
    if name == "delete_watcher":
        return f"Löscht den Datei-Wächter {_shorten(args.get('id', ''))}."
    if name == "smarthome_devices":
        return "Listet Smart-Home-Geräte (Home Assistant) auf."
    if name == "smarthome_control":
        return (
            f"Smart Home: {_shorten(args.get('action', ''))} für "
            f"{_shorten(args.get('entity_id', ''))}."
        )
    if name == "scan_network":
        return "Sucht Geräte im Heimnetzwerk."
    if name == "wake_device":
        return f"Weckt das Gerät {_shorten(args.get('mac', ''))} per Wake-on-LAN."
    if name == "list_printers":
        return "Listet installierte Drucker auf."
    if name == "print_file":
        return f"Druckt die Datei {_shorten(args.get('path', ''))}."
    if name == "spotify_play":
        query = args.get("query", "")
        return (
            f"Spielt auf Spotify: {_shorten(query)}"
            if query
            else "Setzt die Wiedergabe in Spotify fort."
        )
    if name == "spotify_search":
        return f"Sucht auf Spotify nach: {_shorten(args.get('query', ''))}"
    if name == "spotify_now_playing":
        return "Fragt ab, was gerade auf Spotify läuft."
    if name == "amazon_play":
        query = args.get("query", "")
        return (
            f"Spielt auf Amazon Music: {_shorten(query)}"
            if query
            else "Setzt die Wiedergabe in Amazon Music fort."
        )
    if name == "amazon_now_playing":
        return "Fragt ab, was gerade auf Amazon Music läuft."
    if name == "list_friends":
        return "Listet deine Chat-Freunde auf."
    if name == "send_friend_message":
        return (
            f"Schreibt {_shorten(args.get('friend', ''))}: "
            f"{_shorten(args.get('text', ''))}"
        )
    if name == "read_friend_messages":
        return f"Liest den Chat mit {_shorten(args.get('friend', ''))}."
    if name == "browser_wahl":
        wunsch = _shorten(args.get("browser", ""))
        if wunsch:
            return f"Stellt den Browser fuer Webseiten auf: {wunsch}"
        if args.get("speicher"):
            return f"Stellt den Browser-Speicher auf: {_shorten(args.get('speicher'))}"
        return "Zeigt, welchen Browser Jon benutzt."
    if name == "ziel":
        aktion = str(args.get("aktion", "liste"))
        if aktion == "anlegen":
            return f"Legt das Ziel an: {_shorten(args.get('titel', ''))}"
        if aktion == "aktualisieren":
            return f"Aktualisiert ein Ziel ({_shorten(args.get('zustand', ''))})."
        if aktion == "loeschen":
            return "Loescht ein Ziel."
        return "Zeigt Jons offene Ziele."
    if name == "weltmodell":
        aktion = str(args.get("aktion", "liste"))
        if aktion == "merken":
            return f"Merkt sich {_shorten(args.get('name', ''))} im Weltmodell."
        if aktion == "umfeld":
            return f"Sieht nach, was zu {_shorten(args.get('name', ''))} gehoert."
        if aktion == "verbinden":
            return (
                f"Verknuepft {_shorten(args.get('name', ''))} mit "
                f"{_shorten(args.get('ziel', ''))}."
            )
        return "Zeigt Jons Weltmodell."
    if name == "notizblock":
        aktion = str(args.get("aktion", "lesen"))
        if aktion in ("schreiben", "ergaenzen"):
            return f"Schreibt in den Notizblock: {_shorten(args.get('inhalt', ''))}"
        if aktion == "leeren":
            return "Leert den Notizblock."
        return "Liest den Notizblock."
    if name == "selbstbild":
        aufgabe = _shorten(args.get("aufgabe", ""))
        return (
            f"Schaetzt ein, ob Jon das kann: {aufgabe}"
            if aufgabe
            else "Zeigt Jons Faehigkeiten und Grenzen."
        )
    if name == "erfahrung":
        return f"Sieht in den Erfahrungen nach: {_shorten(args.get('bereich', 'alle'))}"
    if name == "weltzustand":
        return "Schaut sich den gesamten aktuellen Zustand an."
    if name == "gedaechtnis_pflegen":
        return f"Arbeitet {_shorten(args.get('tag', 'gestern'))} im Gedaechtnis nach."
    if name == "initiative":
        aktion = str(args.get("aktion", "liste"))
        if aktion == "lauf":
            return "Ueberlegt, was als naechstes ansteht."
        if aktion == "ausfuehren":
            return "Erledigt einen eigenen Vorschlag."
        return "Zeigt Jons Vorschlaege."
    if name == "team":
        return f"Laesst mehrere Agenten arbeiten an: {_shorten(args.get('aufgabe', ''))}"
    if name == "lernen":
        return f"Lernt aus der eigenen Arbeit ({_shorten(args.get('aktion', 'muster'))})."
    if name == "rueckgaengig":
        if args.get("nur_zeigen"):
            return "Zeigt, was sich rueckgaengig machen laesst."
        return "Macht die letzte Dateiaktion rueckgaengig."
    if name == "netz_status":
        return "Prueft die Internetverbindung."
    if name == "was_war":
        raum = _shorten(args.get("zeitraum", "heute")) or "heute"
        thema = _shorten(args.get("thema", ""))
        return (
            f"Sieht im Gedaechtnis nach, was {raum} war"
            + (f" (Thema: {thema})" if thema else "")
            + "."
        )
    if name == "verlauf_heute":
        return "Blickt auf den heutigen Tag zurueck."
    if name == "datei_erstellen":
        art = str(_shorten(args.get("art", "Datei"))).upper()
        titel = _shorten(args.get("titel", "")) or _shorten(args.get("dateiname", ""))
        ort = _shorten(args.get("ort", ""))
        return (
            f"Erstellt eine {art}-Datei"
            + (f" „{titel}“" if titel else "")
            + (f" in {ort}" if ort else " in Jons Ordner")
            + "."
        )
    if name == "ordner_anlegen":
        return f"Legt den Ordner „{_shorten(args.get('name', ''))}“ an."
    if name == "datei_oeffnen":
        return f"Oeffnet {_shorten(args.get('pfad', ''))}."
    if name == "ordner_oeffnen":
        return f"Oeffnet {_shorten(args.get('pfad', '')) or 'Jons Ordner'} im Dateimanager."
    if name == "dateien_finden":
        return f"Sucht in Jons Dateien: {_shorten(args.get('frage', 'alles'))}"
    if name == "dateiraum":
        return "Zeigt Jons Ordner und was darin liegt."
    if name == "umgebung":
        return "Prueft, welche Programme und Bibliotheken auf dem Rechner da sind."
    if name == "oberflaeche":
        ziel = _shorten(args.get("werkzeug", "") or args.get("ziel", ""))
        return f"Oeffnet {ziel} in Jons Oberflaeche." if ziel else "Zeigt Jons Werkzeuge."
    if name == "bericht":
        return "Fasst zusammen, was seit der letzten Anwesenheit passiert ist."
    if name == "ausloeser":
        aktion = str(_shorten(args.get("aktion", "liste")))
        if aktion.startswith("anleg") or aktion in ("neu", "merken"):
            return f"Merkt sich einen Ausloeser: {_shorten(args.get('auftrag', ''))}"
        if aktion.startswith("loesch"):
            return "Loescht einen Ausloeser."
        return f"Ausloeser ({aktion})."
    if name == "aufgabe":
        aktion = str(_shorten(args.get("aktion", "anlegen")))
        if aktion.startswith("anleg"):
            return f"Nimmt als eigene Aufgabe an: {_shorten(args.get('auftrag', ''))}"
        if aktion.startswith("freigeb"):
            return "Gibt eine wartende Aufgabe frei."
        return f"Aufgabenliste ({aktion})."
    if name == "aufgabe_starten":
        return "Nimmt sich die naechste Aufgabe vor."
    if name == "durchspielen":
        ziel = _shorten(args.get("werkzeug", "")) or "die Schrittfolge"
        return f"Spielt im Kopf durch, was {ziel} veraendern wuerde."
    if name == "hypothese":
        aktion = str(_shorten(args.get("aktion", "stand")))
        if aktion.startswith(("vermut", "anleg")):
            return "Stellt eine pruefbare Vermutung auf."
        if aktion.startswith(("pruef", "test")):
            return "Prueft eine eigene Vermutung nach."
        return "Zeigt, was Jon selbst nachgeprueft hat."
    if name == "desktop_verknuepfung":
        aktion = str(_shorten(args.get("aktion", "anlegen")))
        if aktion.startswith("entfern"):
            return "Entfernt Jons Verknuepfung vom Desktop."
        if aktion.startswith(("status", "pruef", "zeig")):
            return "Sieht nach, ob Jon eine Desktop-Verknuepfung hat."
        return "Legt eine Jon-Verknuepfung auf dem Desktop an."
    if name == "blender_szene":
        return f"Baut in Blender: {_shorten(args.get('auftrag', ''))}"
    if name == "blender_render":
        return f"Rendert {_shorten(args.get('datei', ''))}."
    if name == "blender_export":
        if args.get("oeffnen"):
            return f"Oeffnet {_shorten(args.get('datei', ''))} in Blender."
        fmt = str(_shorten(args.get("format", "glb"))).upper()
        return f"Exportiert {_shorten(args.get('datei', ''))} als {fmt}."
    if name == "selbsteinschaetzung":
        ziel = _shorten(args.get("werkzeug", "") or args.get("aufgabe", ""))
        return (
            f"Schaetzt ein, wie sicher das klappt: {ziel}"
            if ziel
            else "Prueft, wie gut Jon sich selbst einschaetzt."
        )
    if name == "ueberraschungen":
        return "Sieht nach, was zuletzt anders lief als erwartet."
    if name == "frage_merken":
        return f"Merkt sich die offene Frage: {_shorten(args.get('frage', ''))}"
    if name == "offene_fragen":
        return "Zeigt, was Jon noch nicht weiss."
    if name == "frage_klaeren":
        return "Klaert offene Fragen mit Suche und Nachdenken."
    if name == "fertigkeiten":
        aktion = _shorten(args.get("aktion", "zeigen"))
        return f"Arbeitet mit gelernten Fertigkeiten ({aktion})."
    if name == "fertigkeit_nutzen":
        return f"Fuehrt die gelernte Fertigkeit '{_shorten(args.get('name', ''))}' aus."
    if name == "plan_machen":
        return f"Zerlegt in Schritte: {_shorten(args.get('auftrag', ''))}"
    if name == "plan_ausfuehren":
        return f"Arbeitet den Plan {_shorten(args.get('id', ''))} ab."
    if name.startswith("browser_"):
        return browser_erklaeren(name.removeprefix("browser_"), args)
    if name == "calendar_add":
        return (
            f"Trägt in den Kalender ein: {_shorten(args.get('title', ''))} "
            f"am {_shorten(args.get('date', ''))} {_shorten(args.get('time', ''))}"
        )
    if name == "calendar_list":
        return "Liest den Kalender."
    if name == "calendar_update":
        return f"Ändert den Kalendereintrag {_shorten(args.get('id', ''))}."
    if name == "calendar_delete":
        return f"Löscht den Kalendereintrag {_shorten(args.get('id', ''))}."
    if name == "calendar_search":
        return f"Sucht im Kalender nach: {_shorten(args.get('query', ''))}"
    return f"Führt das Tool {name} aus."


def _maps_filters() -> str:
    from app.services.maps.overpass import CATEGORIES

    return ", ".join(CATEGORIES)


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


GRUPPEN_TITEL: list[tuple[str, str, str]] = [
    ("handy", "Handy", "📱"),
    ("pc", "PC steuern", "🖥️"),
    ("dateien", "Dateien", "📁"),
    ("browser", "Browser", "🌐"),
    ("wissen", "Wissen & Web", "🔎"),
    ("kalender", "Kalender & Erinnerungen", "📅"),
    ("gedaechtnis", "Gedächtnis", "🧠"),
    ("werkstatt", "Dateien & Werkstatt", "🛠️"),
    ("denken", "Denken & Lernen", "🤔"),
    ("medien", "Bilder & Dokumente", "🖼️"),
    ("musik", "Musik & Medien", "🎵"),
    ("kontakt", "Anrufe & Freunde", "📞"),
    ("zuhause", "Zuhause & Netzwerk", "🏠"),
    ("skills", "Skills", "🧩"),
    ("weitere", "Weitere", "✨"),
]

_PC_TOOLS = {
    "run_powershell",
    "run_cmd",
    "start_program",
    "kill_program",
    "system_info",
    "list_processes",
    "lock_screen",
    "screenshot",
    "get_screen_info",
    "list_windows",
    "focus_window",
    "mouse_move",
    "mouse_click",
    "mouse_scroll",
    "keyboard_type",
    "keyboard_press",
    "keyboard_hotkey",
    "open_url",
    "wait",
}

_DATEI_TOOLS = {
    "list_dir",
    "read_file",
    "write_file",
    "edit_file",
    "append_file",
    "move_path",
    "copy_path",
    "delete_path",
    "make_dir",
    "search_files",
    "zip_paths",
    "unzip",
    "open_explorer",
    "open_in_vscode",
    "download_file",
    "print_file",
    "list_printers",
    "project_overview",
    "git_status",
    "git_diff",
}

_WISSEN_TOOLS = {
    "web_search",
    "http_get",
    "get_weather",
    "deep_learning",
    "ask_knowledge",
    "list_documents",
    "maps",
}

_GEDAECHTNIS_TOOLS = {
    "remember",
    "recall",
    "forget",
    "remember_about_user",
    "journal",
    "read_journal",
    "set_mood",
    "recall_screen",
    "list_snapshots",
    "snapshot",
}

_DATEI_JON_TOOLS = {
    "oberflaeche",
    "desktop_verknuepfung",
    "datei_erstellen",
    "ordner_anlegen",
    "datei_oeffnen",
    "ordner_oeffnen",
    "dateien_finden",
    "dateiraum",
    "umgebung",
    "blender_szene",
    "blender_render",
    "blender_export",
}

_DENK_TOOLS = {
    "aufgabe",
    "aufgabe_starten",
    "ausloeser",
    "bericht",
    "durchspielen",
    "hypothese",
    "ziel",
    "weltmodell",
    "notizblock",
    "selbstbild",
    "erfahrung",
    "weltzustand",
    "gedaechtnis_pflegen",
    "initiative",
    "lernen",
    "team",
    "selbsteinschaetzung",
    "ueberraschungen",
    "frage_merken",
    "offene_fragen",
    "frage_klaeren",
    "fertigkeiten",
    "fertigkeit_nutzen",
    "plan_machen",
    "plan_ausfuehren",
}

_MEDIEN_TOOLS = {
    "look_at_image",
    "create_image",
    "webcam_look",
    "read_pdf",
    "create_pptx",
    "read_pptx",
}

_SKILL_TOOLS = {"list_skills", "read_skill", "read_skill_file"}

_ZUHAUSE_TOOLS = {
    "smarthome_devices",
    "smarthome_control",
    "scan_network",
    "wake_device",
}


def _gruppe_fuer(name: str) -> str:
    if name.startswith("android_"):
        return "handy"
    if name.startswith("browser_"):
        return "browser"
    if name.startswith("calendar_") or name in {
        "add_reminder",
        "list_reminders",
        "delete_reminder",
        "add_alarm",
        "list_alarms",
        "delete_alarm",
        "add_task",
        "list_tasks",
        "delete_task",
        "start_focus",
        "stop_focus",
        "start_stopwatch",
        "start_timer",
        "stop_timer",
        "list_timers",
        "adjust_timer",
        "control_timer",
    }:
        return "kalender"
    if name.startswith("spotify_") or name.startswith("amazon_") or name == "media_control":
        return "musik"
    if name in _PC_TOOLS:
        return "pc"
    if name in _DATEI_TOOLS:
        return "dateien"
    if name in _WISSEN_TOOLS:
        return "wissen"
    if name in _GEDAECHTNIS_TOOLS:
        return "gedaechtnis"
    if name in _DENK_TOOLS:
        return "denken"
    if name in _DATEI_JON_TOOLS:
        return "werkstatt"
    if name in _MEDIEN_TOOLS:
        return "medien"
    if name in _SKILL_TOOLS:
        return "skills"
    if name in _ZUHAUSE_TOOLS:
        return "zuhause"
    if name in {
        "call_user",
        "schedule_call",
        "list_scheduled_calls",
        "cancel_call",
        "update_call",
        "list_friends",
        "send_friend_message",
        "read_friend_messages",
        "check_mail",
        "send_mail",
    }:
        return "kontakt"
    return "weitere"


def werkzeugnamen() -> set[str]:
    laden()
    from app.services.werkzeug_register import namen as register_namen

    eigene = {t["function"]["name"] for t in ToolBox()._eigene_tools()}
    return eigene | register_namen()


def werkzeug_katalog() -> list[dict]:
    from app.services.connectors import get_connector_manager

    kasten = ToolBox()
    eigene = kasten._eigene_tools()
    verbinder = get_connector_manager()
    zusatz: dict[str, dict] = {}
    try:
        for connector in verbinder.alle():
            for werkzeug in connector.werkzeuge():
                zusatz[werkzeug.name] = {
                    "stufe": werkzeug.stufe,
                    "recht": werkzeug.recht,
                    "frei": werkzeug.frei,
                    "connector": connector.id,
                    "beschreibung": werkzeug.beschreibung,
                }
    except Exception:
        zusatz = {}
    alle = list(eigene) + verbinder.schema()
    gesehen: set[str] = set()
    eintraege: list[dict] = []
    for werkzeug in alle:
        funktion = werkzeug.get("function", {})
        name = str(funktion.get("name", ""))
        if not name or name in gesehen:
            continue
        gesehen.add(name)
        daten = dict(zusatz.get(name, {}))
        beschreibung = str(funktion.get("description", "")).strip()
        daten.pop("beschreibung", None)
        eintraege.append(
            {
                "name": name,
                "beschreibung": beschreibung,
                "gruppe": _gruppe_fuer(name),
                "ohne_rueckfrage": name in SAFE_TOOLS,
                **daten,
            }
        )
    for name, daten in zusatz.items():
        if name in gesehen:
            continue
        eintraege.append(
            {
                "name": name,
                "gruppe": "handy",
                "ohne_rueckfrage": name in SAFE_TOOLS,
                **daten,
            }
        )
    gruppen = []
    for kennung, titel, symbol in GRUPPEN_TITEL:
        passend = sorted(
            (e for e in eintraege if e["gruppe"] == kennung), key=lambda e: e["name"]
        )
        if not passend:
            continue
        gruppen.append(
            {
                "id": kennung,
                "name": titel,
                "symbol": symbol,
                "anzahl": len(passend),
                "werkzeuge": passend,
            }
        )
    return gruppen


class ToolBox:
    def __init__(
        self,
        service: SystemService | None = None,
        automation: AutomationService | None = None,
        memory: MemoryService | None = None,
        skills: SkillService | None = None,
        reminders: ReminderService | None = None,
        root: str | None = None,
        source: str = "app",
    ) -> None:
        self._service = service or SystemService()
        self._automation = automation or AutomationService()
        self._memory = memory or MemoryService()
        self._skills = skills or SkillService()
        self._reminders = reminders or ReminderService()
        self._root = str(Path(root).expanduser().resolve()) if root else None
        self._source = source

    def _guard_path(self, value: Any) -> str:
        root = Path(self._root or "")
        p = Path(str(value)).expanduser()
        if not p.is_absolute():
            p = root / p
        resolved = p.resolve()
        if resolved != root and root not in resolved.parents:
            raise PermissionError(
                f"Zugriff ausserhalb des Projektordners blockiert: {value}"
            )
        return str(resolved)

    def _guard_command(self, command: str) -> None:
        for match in _CHDIR_RE.finditer(command):
            target = match.group("path").strip().strip("\"'")
            if not target or target == ".":
                continue
            self._guard_path(target)

    def _guard_args(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        guarded = dict(args)
        for key in ("path", "source", "destination", "root", "workspace"):
            if guarded.get(key):
                guarded[key] = self._guard_path(guarded[key])
        if isinstance(guarded.get("sources"), list):
            guarded["sources"] = [self._guard_path(s) for s in guarded["sources"]]
        if name == "run_powershell" and guarded.get("command"):
            self._guard_command(str(guarded["command"]))
            guarded["command"] = (
                f'Set-Location -LiteralPath "{self._root}"; ' + str(guarded["command"])
            )
        if name == "run_cmd" and guarded.get("command"):
            self._guard_command(str(guarded["command"]))
            guarded["command"] = f'cd /d "{self._root}" && ' + str(guarded["command"])
        return guarded

    def schema(self, context: str = "", coding: bool = False) -> list[dict]:
        tools = self._all_tools()
        if coding:
            return [t for t in tools if t["function"]["name"] in CODING_TOOLS]
        allowed = select_tools(context)
        if allowed is None:
            return tools
        return [t for t in tools if t["function"]["name"] in allowed]

    def _all_tools(self) -> list[dict]:
        return self._eigene_tools() + _connector_werkzeuge()

    def _eigene_tools(self) -> list[dict]:
        return [
            _tool(
                "run_powershell",
                "Fuehrt einen Windows-PowerShell-Befehl auf dem PC des Nutzers aus und "
                "liefert exit_code, stdout und stderr. Damit kannst du praktisch alles auf "
                "dem Computer steuern: Systeminfos, Prozesse, Netzwerk, Dateien, Apps.",
                {"command": {"type": "string", "description": "Der PowerShell-Befehl"}},
                ["command"],
            ),
            _tool(
                "run_cmd",
                "Fuehrt einen Windows-CMD-Befehl aus. Zum Oeffnen einer Webseite nimm "
                "open_url statt 'start https://...' - sonst landet die Seite im "
                "falschen Browser.",
                {"command": _STR},
                ["command"],
            ),
            _tool(
                "open_url",
                "Oeffnet eine Adresse in JONS PRIVATEM Browser - das ist der "
                "Standard fuer alles Web, auch fuer Seiten, die der Nutzer sehen soll. "
                "Das Fenster geht von selbst auf, wenn es noch zu war. "
                "'Oeffne mir YouTube' ist immer open_url, nie start_program oder eine "
                "Shell. Danach kannst du die Seite mit browser_read wirklich lesen. "
                "Nur wenn der Nutzer ausdruecklich einen anderen Browser nennt ('mach "
                "das in Edge', 'nimm meinen normalen Browser'), setzt du browser auf "
                "edge, brave, chrome, firefox, opera, vivaldi oder system - dann "
                "oeffnet die Seite dort, und du kannst sie NICHT mitlesen. Sag das "
                "ehrlich dazu.",
                {
                    "url": _STR,
                    "browser": {
                        "type": "string",
                        "description": "Nur wenn der Nutzer es verlangt: edge, brave, "
                        "chrome, firefox, opera, vivaldi, system. Leer = Jons Browser",
                    },
                },
                ["url"],
            ),
            _tool(
                "start_program",
                "Startet ein Programm oder eine .exe auf dem PC. NICHT fuer Webseiten - "
                "dafuer gibt es open_url, das Jons eingestellten Browser benutzt. Gibst "
                "du hier trotzdem eine Adresse an, leitet Jon sie dorthin um.",
                {
                    "path": _STR,
                    "args": {"type": "array", "items": {"type": "string"}},
                },
                ["path"],
            ),
            _tool(
                "kill_program",
                "Beendet ein laufendes Programm anhand des Namens (z.B. notepad).",
                {"name": _STR},
                ["name"],
            ),
            _tool(
                "open_explorer",
                "Oeffnet einen Ordner im Windows Explorer.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "list_dir",
                "Listet den Inhalt eines Ordners auf.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "read_file",
                "Liest den Inhalt einer Textdatei.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "write_file",
                "Schreibt Text in eine Datei und ueberschreibt vorhandenen Inhalt. Fuer "
                "Aenderungen an vorhandenen Dateien bevorzuge edit_file.",
                {"path": _STR, "content": _STR},
                ["path", "content"],
            ),
            _tool(
                "edit_file",
                "Aendert eine Datei praezise: ersetzt den exakten Text 'old' durch 'new', "
                "ohne den Rest zu ueberschreiben. old muss eindeutig sein. Nutze das fuer "
                "gezielte Code-Aenderungen.",
                {"path": _STR, "old": _STR, "new": _STR},
                ["path", "old", "new"],
            ),
            _tool(
                "move_path",
                "Verschiebt oder benennt eine Datei oder einen Ordner um.",
                {"source": _STR, "destination": _STR},
                ["source", "destination"],
            ),
            _tool(
                "delete_path",
                "Loescht eine Datei oder einen Ordner.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "open_in_vscode",
                "Oeffnet einen Pfad in VS Code.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "get_screen_info",
                "Liefert Groesse des Hauptmonitors, Grenzen des gesamten virtuellen "
                "Desktops (alle Monitore) und die aktuelle Mausposition. Rufe das "
                "auf, bevor du die Maus bewegst oder klickst.",
                {},
                [],
            ),
            _tool(
                "calendar_add",
                "Traegt etwas in Jons eigenen Kalender ein. date: YYYY-MM-DD, "
                "TT.MM., 'heute', 'morgen' oder Wochentag. time optional HH:MM. "
                "kind: termin (Standard), task oder erinnerung. Meldet Konflikte "
                "mit ueberschneidenden Terminen zurueck - sag sie dem Nutzer an.",
                {
                    "title": _STR,
                    "date": _STR,
                    "time": _STR,
                    "duration_minutes": _INT,
                    "note": _STR,
                    "kind": _STR,
                },
                ["title", "date"],
            ),
            _tool(
                "calendar_list",
                "Listet Kalendereintraege inklusive Automationen, Erinnerungen "
                "und dem verbundenen ICS-Kalender. start: Datum (Standard heute), "
                "days: Anzahl Tage (Standard 7).",
                {"start": _STR, "days": _INT},
                [],
            ),
            _tool(
                "calendar_update",
                "Aendert einen Kalendereintrag (id aus calendar_list/search). "
                "Nur die uebergebenen Felder werden geaendert. done=true hakt "
                "einen Task ab.",
                {
                    "id": _STR,
                    "title": _STR,
                    "date": _STR,
                    "time": _STR,
                    "duration_minutes": _INT,
                    "note": _STR,
                    "kind": _STR,
                    "done": _BOOL,
                },
                ["id"],
            ),
            _tool(
                "calendar_delete",
                "Loescht einen Kalendereintrag (id aus calendar_list/search).",
                {"id": _STR},
                ["id"],
            ),
            _tool(
                "calendar_search",
                "Sucht in Jons Kalender nach Titel oder Notiz.",
                {"query": _STR},
                ["query"],
            ),
            _tool(
                "browser_wahl",
                "Zeigt und aendert, welchen Browser Jon fuer Webseiten und Websuche "
                "benutzt. Ohne browser wird nur der aktuelle Stand samt der auf "
                "diesem PC gefundenen Browser gezeigt. browser kann 'jon' (Jons "
                "eigener Browser, Standard), 'system' (Standardbrowser), 'chrome', "
                "'edge', 'firefox', 'brave', 'opera' oder 'vivaldi' sein. speicher "
                "stellt zusaetzlich ein, ob Jons Browser alles nur im Arbeitsspeicher "
                "haelt ('ram') oder auf der Festplatte ablegt ('festplatte').",
                {"browser": _STR, "speicher": _STR},
                [],
            ),
            _tool(
                "ziel",
                "Jons eigene Zielverwaltung. aktion='anlegen' legt ein Ziel an "
                "(titel, optional beschreibung, frist wie 'morgen' oder '24.12.', "
                "naechster_schritt), 'liste' zeigt die offenen Ziele, "
                "'aktualisieren' aendert Zustand (offen|laeuft|wartet|erledigt|"
                "verworfen), naechsten Schritt oder Fortschritt, 'faellig' zeigt, was "
                "bald ansteht, 'loeschen' entfernt eins. Nutze das fuer alles, was "
                "ueber mehrere Tage geht.",
                {
                    "aktion": _STR,
                    "id": _STR,
                    "titel": _STR,
                    "beschreibung": _STR,
                    "frist": _STR,
                    "naechster_schritt": _STR,
                    "zustand": _STR,
                    "fortschritt": _NUM,
                    "wichtigkeit": _NUM,
                    "tage": _INT,
                },
                [],
            ),
            _tool(
                "weltmodell",
                "Jons Modell der Welt des Nutzers: Personen, Projekte, Geraete, Orte, "
                "Firmen. aktion='merken' legt etwas an oder ergaenzt es (name, art, "
                "beschreibung), 'umfeld' zeigt eine Sache samt Beziehungen, "
                "'verbinden' verknuepft zwei Dinge (name, ziel, beziehung), 'liste' "
                "zeigt alles. Nutze es, wenn der Nutzer von Personen, Projekten oder "
                "Geraeten spricht.",
                {
                    "aktion": _STR,
                    "name": _STR,
                    "art": _STR,
                    "beschreibung": _STR,
                    "ziel": _STR,
                    "beziehung": _STR,
                    "wichtigkeit": _NUM,
                },
                [],
            ),
            _tool(
                "notizblock",
                "Jons Arbeitsgedaechtnis fuer eine laufende Sache. aktion='lesen', "
                "'schreiben', 'ergaenzen' oder 'leeren'; bereich trennt Themen "
                "(z.B. der Name des Projekts). Halte hier Zwischenstaende fest, die "
                "ueber mehrere Antworten hinweg gelten sollen.",
                {"aktion": _STR, "inhalt": _STR, "bereich": _STR},
                [],
            ),
            _tool(
                "selbstbild",
                "Sagt ehrlich, was Jon kann, wie zuverlaessig seine Werkzeuge zuletzt "
                "waren und wo seine Grenzen liegen. Mit aufgabe='...' schaetzt er "
                "gezielt ein, ob er genau das schafft. Nutze es, bevor du etwas "
                "zusagst oder ablehnst.",
                {"aufgabe": _STR},
                [],
            ),
            _tool(
                "erfahrung",
                "Jons Erfahrungsgedaechtnis pro Website oder Werkzeug: was dort "
                "geklappt hat und was nicht. bereich ist z.B. 'web:thalia.de' oder "
                "'werkzeug:write_file'. aktion='notieren' schreibt eine Erfahrung "
                "dazu (text, art='klappt' oder 'klappt_nicht').",
                {"bereich": _STR, "aktion": _STR, "text": _STR, "art": _STR},
                [],
            ),
            _tool(
                "weltzustand",
                "Zeigt Jons gesamten aktuellen Handlungsraum auf einen Blick: offene "
                "Browsersitzungen, Fenster im Vordergrund, Handy, laufende Auftraege, "
                "faellige Ziele, Netz und Budget.",
                {},
                [],
            ),
            _tool(
                "gedaechtnis_pflegen",
                "Laesst Jon einen Tag nacharbeiten: Ereignisse zusammenfassen, "
                "dauerhafte Fakten ins Gedaechtnis uebernehmen, Widersprueche klaeren, "
                "Unwichtiges vergessen und daraus Ziele fuer morgen ableiten. tag "
                "versteht 'gestern', 'heute', 'letzte Woche'.",
                {"tag": _STR},
                [],
            ),
            _tool(
                "initiative",
                "Jons vorausschauender Teil. aktion='lauf' laesst ihn aus gestern, "
                "heute, den Zielen und den Terminen Vorschlaege fuer morgen "
                "erarbeiten, 'liste' zeigt sie, 'annehmen'/'verwerfen' entscheidet "
                "ueber einen (id), 'ausfuehren' erledigt einen harmlosen Vorschlag "
                "selbst.",
                {"aktion": _STR, "id": _STR},
                [],
            ),
            _tool(
                "team",
                "Teilt eine groessere Rechercheaufgabe auf mehrere Teilagenten auf, "
                "laesst sie gleichzeitig arbeiten und fasst die Ergebnisse zusammen. "
                "Nur fuer lesende Aufgaben (vergleichen, sammeln, pruefen).",
                {"aufgabe": _STR, "agenten": _INT},
                ["aufgabe"],
            ),
            _tool(
                "lernen",
                "Jon lernt aus seiner eigenen Arbeit. aktion='muster' zeigt "
                "wiederkehrende Ablaeufe und haeufige Fehler, 'skill' schreibt aus "
                "einem gelungenen Lauf eine dauerhafte Anleitung, 'auswerten' "
                "uebernimmt Fehler ins Erfahrungsgedaechtnis, 'training' exportiert "
                "Trainingsdaten fuer ein eigenes Modell.",
                {"aktion": _STR, "id": _STR, "titel": _STR},
                [],
            ),
            _tool(
                "rueckgaengig",
                "Macht die letzte umkehrbare Dateiaktion von Jon rueckgaengig "
                "(schreiben, aendern, verschieben, anlegen, loeschen). Ohne id wird "
                "die letzte Aktion zurueckgenommen; nur_zeigen=true listet nur auf, "
                "was rueckgaengig gemacht werden koennte.",
                {"id": _STR, "nur_zeigen": _BOOL},
                [],
            ),
            _tool(
                "netz_status",
                "Sagt, ob gerade eine Internetverbindung besteht. Nutze das, bevor du "
                "dem Nutzer sagst, etwas im Netz gehe nicht.",
                {"neu": _BOOL},
                [],
            ),
            _tool(
                "was_war",
                "Sieht in Jons eigenem Ereignisgedaechtnis nach, was in einem "
                "Zeitraum wirklich passiert ist: welche Werkzeuge liefen, was "
                "geklappt hat, was schiefging, welche Themen dran waren. zeitraum "
                "versteht 'heute', 'gestern', 'vorgestern', 'letzte Woche', "
                "'vor 3 Tagen', 'Montag', '24.12.'. Mit thema kannst du gezielt "
                "danach suchen. Nutze das IMMER, wenn der Nutzer fragt, was er oder "
                "du frueher gemacht habt - rate nie.",
                {"zeitraum": _STR, "thema": _STR},
                [],
            ),
            _tool(
                "verlauf_heute",
                "Kurzer Rueckblick auf den heutigen Tag aus Jons Ereignisgedaechtnis.",
                {},
                [],
            ),
            _tool(
                "datei_erstellen",
                "Erzeugt eine ECHTE Datei auf dem Rechner und zeigt sie dem Nutzer als "
                "anklickbare Karte im Chat. art ist die Endung: pdf, docx, odt, xlsx, "
                "ods, csv, txt, md, json, html, py und weitere Code-Endungen. titel ist "
                "die Ueberschrift. inhalt schreibst du SELBST vollstaendig aus - bei "
                "Text in Markdown (# Ueberschrift, ## Unterueberschrift, - Punkt, "
                "1. Nummer), bei xlsx/ods/csv als Liste von Zeilen, erste Zeile die "
                "Spaltentitel. ort ist optional: leer laesst Jon selbst einsortieren, "
                "sonst z.B. 'desktop', 'desktop/Meine Projekte/Essen', 'dokumente' oder "
                "ein Jon-Unterordner. Nutze das IMMER, wenn der Nutzer eine Datei, ein "
                "Dokument, eine PDF, eine Tabelle oder einen Text haben will - sag nie, "
                "du koenntest keine Dateien erstellen.",
                {
                    "art": _STR,
                    "titel": _STR,
                    "inhalt": {
                        "type": "string",
                        "description": "Der vollstaendige Inhalt, bei Tabellen JSON-Zeilen",
                    },
                    "ort": _STR,
                    "dateiname": _STR,
                    "projekt": _STR,
                },
                ["art", "inhalt"],
            ),
            _tool(
                "ordner_anlegen",
                "Legt einen Ordner an. name ist der Ordnername, ort der Platz dafuer "
                "(z.B. 'desktop' oder 'Projects'). Ohne ort landet er in Jons Ordner.",
                {"name": _STR, "ort": _STR},
                ["name"],
            ),
            _tool(
                "datei_oeffnen",
                "Oeffnet eine Datei im passenden Programm des Betriebssystems. Mit "
                "ordner=true wird stattdessen der Ordner geoeffnet und die Datei darin "
                "markiert.",
                {"pfad": _STR, "ordner": _BOOL},
                ["pfad"],
            ),
            _tool(
                "ordner_oeffnen",
                "Oeffnet einen Ordner im Dateimanager des Systems (Explorer, Finder "
                "oder der Linux-Dateimanager). Ohne pfad oeffnet sich Jons Hauptordner.",
                {"pfad": _STR},
                [],
            ),
            _tool(
                "dateien_finden",
                "Durchsucht alles, was Jon erzeugt oder abgelegt hat, mit normaler "
                "Sprache - auch nach Zeit ('die PDF ueber Essen von letzter Woche'). "
                "Nutze das, wenn der Nutzer nach einer frueheren Datei fragt, statt die "
                "Festplatte abzusuchen.",
                {"frage": _STR, "art": _STR, "limit": _NUM},
                [],
            ),
            _tool(
                "dateiraum",
                "Zeigt Jons Ordnerstruktur, wie viele Dateien wo liegen und was zuletzt "
                "entstanden ist.",
                {},
                [],
            ),
            _tool(
                "desktop_verknuepfung",
                "Legt eine Verknuepfung zu Jon auf dem Desktop an - das brauchen vor "
                "allem Nutzer der portablen ZIP-Fassung, die keinen Installer hatte. "
                "aktion: anlegen (Standard), entfernen oder status. Mit ziel gibst du "
                "die Programmdatei an, falls Jon sie nicht selbst findet.",
                {"aktion": _STR, "ziel": _STR},
                [],
            ),
            _tool(
                "aufgabe",
                "Jons eigene Aufgabenliste - damit arbeitet er auch dann weiter, wenn "
                "der Nutzer nicht davorsitzt. aktion=anlegen (Standard) nimmt einen "
                "Auftrag in die Schlange; Jon plant ihn selbst, arbeitet ihn ab und "
                "meldet sich, wenn er fertig ist oder eine Freigabe braucht. "
                "budget_minuten begrenzt die Arbeitszeit (Standard 20), prioritaet 1 "
                "ist dringend und 9 ist unwichtig. Weitere aktionen: liste, status, "
                "pausieren, fortsetzen, abbrechen, freigeben (mit erlaubt=false "
                "verweigern). Nutze das fuer alles, was laenger dauert als ein paar "
                "Werkzeugaufrufe - 'kuemmere dich um X', 'mach das bis heute Abend'.",
                {
                    "aktion": _STR,
                    "auftrag": _STR,
                    "titel": _STR,
                    "budget_minuten": _INT,
                    "prioritaet": _INT,
                    "id": _STR,
                    "erlaubt": _BOOL,
                },
                [],
            ),
            _tool(
                "bericht",
                "Was ist passiert, waehrend der Nutzer weg war: erledigte und offene "
                "Aufgaben, Aufgaben die auf seine Freigabe warten, geaenderte Dateien "
                "und die aktiven Ausloeser. Nutze das bei 'was hast du gemacht', 'bin "
                "wieder da', 'gibt es was Neues' - und von dir aus, wenn er nach "
                "laengerer Pause zurueckkommt.",
                {"anzahl": _INT},
                [],
            ),
            _tool(
                "ausloeser",
                "Damit faengt Jon von selbst an, ohne dass jemand etwas sagt. Eine "
                "Regel merkt sich, WANN etwas passieren soll und WAS Jon dann tut - "
                "er legt zu diesem Zeitpunkt selbst eine Aufgabe an und arbeitet sie "
                "ab. aktion=anlegen mit art=taeglich (zeit HH:MM, optional tage wie "
                "'mo,di' oder 'werktags'), art=intervall (minuten, mindestens 5), "
                "art=ordner (ordner plus muster wie '*.pdf' - laeuft, sobald dort "
                "etwas Neues landet) oder art=start (bei jedem Start von Jon). "
                "Weitere aktionen: liste, aus, an, loeschen, pruefen. Nutze das bei "
                "'jeden Morgen', 'jede Woche', 'immer wenn', 'ab jetzt automatisch'.",
                {
                    "aktion": _STR,
                    "art": _STR,
                    "auftrag": _STR,
                    "titel": _STR,
                    "zeit": _STR,
                    "tage": _STR,
                    "minuten": _INT,
                    "ordner": _STR,
                    "muster": _STR,
                    "budget": _INT,
                    "id": _STR,
                },
                [],
            ),
            _tool(
                "aufgabe_starten",
                "Nimmt sich sofort die naechste wartende Aufgabe vor (oder die mit der "
                "angegebenen id) und arbeitet sie ab. Ohne diesen Aufruf beginnt Jon "
                "von selbst, sobald die Aufgabenschlange eingeschaltet ist.",
                {"id": _STR},
                [],
            ),
            _tool(
                "durchspielen",
                "Spielt im Kopf durch, was ein Werkzeug oder eine ganze Schrittfolge "
                "mit dem Dateisystem machen wuerde - welche Dateien entstehen, welche "
                "verschwinden, und ob ein spaeterer Schritt etwas braucht, das ein "
                "frueherer geloescht hat. Nutze das VOR riskanten Folgen, statt es "
                "auszuprobieren.",
                {
                    "werkzeug": _STR,
                    "args": {"type": "object"},
                    "schritte": {"type": "array", "items": {"type": "object"}},
                },
                [],
            ),
            _tool(
                "hypothese",
                "Vermutungen aufstellen und selbst nachpruefen. aktion=vermuten macht "
                "aus einer Beobachtung eine pruefbare Vermutung samt Test, "
                "aktion=pruefen fuehrt den Test wirklich aus und verbucht das Ergebnis, "
                "aktion=lauf macht beides fuer die letzten Ueberraschungen, "
                "aktion=stand zeigt, was bestaetigt und was widerlegt ist. Getestet "
                "wird nur Harmloses.",
                {
                    "aktion": _STR,
                    "beobachtung": _STR,
                    "vermutung": _STR,
                    "test": _STR,
                    "werkzeug": _STR,
                    "bereich": _STR,
                    "id": _STR,
                    "anzahl": _INT,
                },
                [],
            ),
            _tool(
                "oberflaeche",
                "Oeffnet ein Werkzeug in Jons eigener Oberflaeche - genau das, was der "
                "Nutzer sonst ueber das Werkzeuge-Menue anklickt. Nutze das, wenn "
                "jemand 'mach mal den Tresor auf', 'zeig mir meine Aufgaben', 'oeffne "
                "die Karten' oder 'ich will was aufraeumen' sagt, statt es nur zu "
                "beschreiben. Moegliche werkzeug-Werte unter anderem: denken, aufgaben, "
                "suche, notizen, tagebuch, tresor, kalender, inbox, maps, studio, deep, "
                "code, humanize, download, privat, zwischenablage, aufraeumen, kochen, "
                "lernen, erklaer, telefon, handy, spiele, abendshow, freunde, konten, "
                "skills, einstellungen, diagnose. Ohne werkzeug bekommst du die ganze "
                "Liste.",
                {"werkzeug": _STR, "aktion": _STR},
                [],
            ),
            _tool(
                "umgebung",
                "Prueft, welche Programme (Python, Node, Git, FFmpeg, Blender) und "
                "Bibliotheken auf diesem Rechner wirklich da sind. Nutze das, bevor du "
                "behauptest, etwas ginge nicht - und um dem Nutzer zu sagen, was ihm "
                "noch fehlt.",
                {"neu": _BOOL},
                [],
            ),
            _tool(
                "blender_szene",
                "Baut eine echte 3D-Szene in Blender. Beschreibe in auftrag, was "
                "entstehen soll ('ein Low-Poly-Haus mit Baum', 'ein Wuerfel mit "
                "Metallmaterial, leicht gedreht'). Jon schreibt das bpy-Skript selbst, "
                "laesst Blender im Hintergrund laufen, repariert Fehler selbststaendig, "
                "speichert die .blend-Datei und rendert ein Vorschaubild. export nimmt "
                "kommagetrennte Formate: fbx, obj, glb, gltf, stl. Ist Blender nicht "
                "installiert, sagt das Werkzeug es dir klar - behaupte dann nichts "
                "anderes.",
                {
                    "auftrag": _STR,
                    "projekt": _STR,
                    "ort": _STR,
                    "rendern": _BOOL,
                    "export": _STR,
                },
                ["auftrag"],
            ),
            _tool(
                "blender_render",
                "Rendert eine vorhandene .blend-Datei als PNG.",
                {"datei": _STR, "breite": _NUM, "hoehe": _NUM},
                ["datei"],
            ),
            _tool(
                "blender_export",
                "Exportiert eine .blend-Datei in ein anderes 3D-Format (fbx, obj, glb, "
                "gltf, stl). Mit oeffnen=true wird sie stattdessen in Blender geoeffnet.",
                {"datei": _STR, "format": _STR, "oeffnen": _BOOL},
                ["datei"],
            ),
            _tool(
                "selbsteinschaetzung",
                "Sagt ehrlich, wie sicher etwas klappt, BEVOR du es versuchst. Mit "
                "werkzeug bekommst du die Erfolgswahrscheinlichkeit genau dieses "
                "Werkzeugs aus Jons eigener Statistik, mit aufgabe eine Einschaetzung, "
                "wie aufwaendig die Aufgabe ist. Ohne beides bekommst du Jons "
                "Kalibrierung: wie gut er sich selbst einschaetzt. Nutze das, wenn der "
                "Nutzer fragt, ob du etwas kannst oder wie sicher du bist.",
                {"werkzeug": _STR, "aufgabe": _STR},
                [],
            ),
            _tool(
                "ueberraschungen",
                "Zeigt, was zuletzt anders lief als Jon erwartet hatte - also wo er "
                "dazugelernt hat. Nutze das, wenn der Nutzer fragt, was du gelernt "
                "hast oder warum etwas plotzlich nicht mehr geht.",
                {"tage": _NUM, "limit": _NUM},
                [],
            ),
            _tool(
                "frage_merken",
                "Merkt sich eine Frage, die du gerade NICHT beantworten kannst, damit "
                "Jon sie spaeter klaert. Nutze das immer, wenn du etwas nicht weisst, "
                "statt zu raten.",
                {"frage": _STR, "thema": _STR, "dringlichkeit": _NUM},
                ["frage"],
            ),
            _tool(
                "offene_fragen",
                "Listet auf, was Jon noch nicht weiss und was er inzwischen geklaert "
                "hat.",
                {"limit": _NUM},
                [],
            ),
            _tool(
                "frage_klaeren",
                "Beantwortet offene Fragen mit Websuche und Nachdenken und legt das "
                "Ergebnis ins Gedaechtnis. Ohne id werden die dringendsten Fragen "
                "abgearbeitet.",
                {"id": _STR, "anzahl": _NUM},
                [],
            ),
            _tool(
                "fertigkeiten",
                "Verwaltet Jons gelernte Handlungsmuster. aktion: zeigen (Standard), "
                "entdecken (findet wiederkehrende Werkzeugketten im Protokoll), lernen "
                "(speichert name + schritte als neue Fertigkeit; schritte ist eine "
                "Liste aus {werkzeug, args}, in args darf {{platzhalter}} stehen), "
                "loeschen. Mit suche findest du passende Fertigkeiten zu einem Text.",
                {
                    "aktion": _STR,
                    "name": _STR,
                    "beschreibung": _STR,
                    "ausloeser": _STR,
                    "suche": _STR,
                    "schritte": {"type": "array", "items": {"type": "object"}},
                },
                [],
            ),
            _tool(
                "fertigkeit_nutzen",
                "Fuehrt eine gelernte Fertigkeit aus, statt die Einzelschritte zu "
                "wiederholen. werte fuellt die Platzhalter. Riskante Schritte laufen "
                "erst mit bestaetigt=true.",
                {
                    "name": _STR,
                    "werte": {"type": "object"},
                    "bestaetigt": _BOOL,
                },
                ["name"],
            ),
            _tool(
                "plan_machen",
                "Zerlegt einen groesseren Auftrag in konkrete Schritte mit "
                "Abhaengigkeiten und fuehrt sie auf Wunsch gleich aus - inklusive "
                "Neuplanung, wenn ein Schritt scheitert. Nutze das bei Auftraegen, die "
                "mehrere Werkzeuge und mehrere Schritte brauchen, statt blind "
                "loszulegen.",
                {
                    "auftrag": _STR,
                    "kontext": _STR,
                    "ziel": _STR,
                    "ausfuehren": _BOOL,
                    "bestaetigt": _BOOL,
                },
                ["auftrag"],
            ),
            _tool(
                "plan_ausfuehren",
                "Arbeitet einen vorhandenen Plan ab oder bricht ihn ab.",
                {"id": _STR, "bestaetigt": _BOOL, "abbrechen": _BOOL},
                ["id"],
            ),
            *browser_schema("browser_"),
            _tool(
                "mouse_move",
                "Bewegt die Maus zu einer Position. x/y sind Pixel (auch auf "
                "Zweitmonitoren) oder Bruchteile zwischen 0 und 1 bezogen auf den "
                "Hauptmonitor (z.B. x=0.5, y=0.4 = Mitte leicht oben).",
                {"x": _NUM, "y": _NUM, "duration": _NUM},
                ["x", "y"],
            ),
            _tool(
                "mouse_click",
                "Klickt mit der Maus. Mit x/y (Pixel oder Bruchteile 0-1) wird vorher "
                "dorthin bewegt, ohne x/y wird an der aktuellen Position geklickt. "
                "button: left/right/middle, clicks: 1-3 (2 = Doppelklick).",
                {"x": _NUM, "y": _NUM, "button": _STR, "clicks": _INT},
                [],
            ),
            _tool(
                "mouse_scroll",
                "Scrollt das Mausrad. Positiver Wert = nach oben, negativer = nach "
                "unten (z.B. -500 scrollt eine Seite runter).",
                {"amount": _INT},
                ["amount"],
            ),
            _tool(
                "keyboard_type",
                "Tippt Text ueber die Tastatur in das aktuell fokussierte Feld oder "
                "Fenster. press_enter=true drueckt danach Enter.",
                {"text": _STR, "press_enter": _BOOL},
                ["text"],
            ),
            _tool(
                "keyboard_press",
                "Drueckt eine einzelne Taste, optional mehrfach. Beispiele: enter, "
                "tab, esc, space, backspace, delete, up, down, left, right, home, "
                "end, pageup, pagedown, f5, win.",
                {"key": _STR, "presses": _INT},
                ["key"],
            ),
            _tool(
                "keyboard_hotkey",
                "Drueckt eine Tastenkombination gleichzeitig, z.B. "
                '["ctrl","l"] fuer die Browser-Adressleiste, ["ctrl","v"], '
                '["alt","tab"], ["win","d"].',
                {"keys": {"type": "array", "items": _STR}},
                ["keys"],
            ),
            _tool(
                "list_windows",
                "Listet alle offenen Fenster mit Titel und ob sie aktiv/minimiert "
                "sind.",
                {},
                [],
            ),
            _tool(
                "focus_window",
                "Holt ein Fenster in den Vordergrund. title ist ein Teil des "
                "Fenstertitels, z.B. 'WhatsApp' oder 'YouTube'.",
                {"title": _STR},
                ["title"],
            ),
            _tool(
                "wait",
                "Wartet die angegebene Zeit in Sekunden (max 15), z.B. bis eine "
                "Seite oder App geladen ist.",
                {"seconds": _NUM},
                ["seconds"],
            ),
            _tool(
                "make_dir",
                "Erstellt einen Ordner (inkl. fehlender Elternordner).",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "append_file",
                "Haengt Text an eine Datei an, ohne sie zu ueberschreiben.",
                {"path": _STR, "content": _STR},
                ["path", "content"],
            ),
            _tool(
                "copy_path",
                "Kopiert eine Datei oder einen Ordner.",
                {"source": _STR, "destination": _STR},
                ["source", "destination"],
            ),
            _tool(
                "search_files",
                "Sucht rekursiv nach Dateien. pattern ist ein Glob wie *.pdf oder "
                "Rechnung*.docx.",
                {"root": _STR, "pattern": _STR},
                ["root", "pattern"],
            ),
            _tool(
                "project_overview",
                "Liefert eine Gesamtansicht des Projektordners: Anzahl Dateien und "
                "Ordner, erkannte Sprachen, Projekttyp, Frameworks, Abhaengigkeiten, "
                "Build-/Test-Skripte, Schluesseldateien und Git-Status. Nutze das zu "
                "Beginn einer groesseren Aufgabe, um den ganzen Ordner zu verstehen, "
                "statt einzelne Dateien zu raten. Ohne root nimmst du den geoeffneten "
                "Projektordner.",
                {"root": _STR},
                [],
            ),
            _tool(
                "git_status",
                "Zeigt Branch, geaenderte Dateien und den letzten Commit des "
                "Projektordners. Ohne root der geoeffnete Projektordner.",
                {"root": _STR},
                [],
            ),
            _tool(
                "git_diff",
                "Erzeugt den Git-Diff des Projektordners (mit staged=true den "
                "gestagten Diff). Ohne root der geoeffnete Projektordner.",
                {"root": _STR, "staged": _BOOL},
                [],
            ),
            _tool(
                "zip_paths",
                "Packt Dateien/Ordner in eine ZIP-Datei.",
                {
                    "sources": {"type": "array", "items": _STR},
                    "destination": _STR,
                },
                ["sources", "destination"],
            ),
            _tool(
                "unzip",
                "Entpackt eine ZIP-Datei in einen Zielordner.",
                {"source": _STR, "destination": _STR},
                ["source", "destination"],
            ),
            _tool(
                "clipboard_get",
                "Liest den aktuellen Inhalt der Zwischenablage.",
                {},
                [],
            ),
            _tool(
                "clipboard_set",
                "Setzt den Inhalt der Zwischenablage.",
                {"text": _STR},
                ["text"],
            ),
            _tool(
                "screenshot",
                "Macht einen Screenshot. Mit path wird als Datei gespeichert, sonst als "
                "Data-URL zurueckgegeben. Nutze das, um zu pruefen, was auf dem Bildschirm "
                "ist.",
                {"path": _STR},
                [],
            ),
            _tool(
                "http_get",
                "Ruft eine URL per HTTP GET ab und liefert den Text (z.B. fuer Recherche "
                "oder APIs).",
                {"url": _STR},
                ["url"],
            ),
            _tool(
                "download_file",
                "Laedt eine Datei von einer URL herunter und speichert sie.",
                {"url": _STR, "destination": _STR},
                ["url", "destination"],
            ),
            _tool(
                "system_info",
                "Liefert Betriebssystem, CPU, Speicher, Nutzer und Uhrzeit.",
                {},
                [],
            ),
            _tool(
                "list_processes",
                "Listet die groessten laufenden Prozesse mit Name, PID und Speicher.",
                {},
                [],
            ),
            _tool(
                "lock_screen",
                "Sperrt den Windows-Bildschirm.",
                {},
                [],
            ),
            _tool(
                "list_skills",
                "Listet die verfuegbaren Skill-Anleitungen (z.B. web-design) auf.",
                {},
                [],
            ),
            _tool(
                "read_skill",
                "Liest eine Skill-Anleitung vollstaendig. Rufe das auf, bevor du eine "
                "passende Aufgabe startest (z.B. read_skill name=web-design vor dem Bau "
                "einer Website) und folge der Anleitung.",
                {"name": _STR},
                ["name"],
            ),
            _tool(
                "write_skill",
                "Erstellt oder aktualisiert eine Skill-Anleitung (Markdown). Nutze das, "
                "wenn der Nutzer dir eine neue Arbeitsweise beibringt.",
                {"name": _STR, "content": _STR},
                ["name", "content"],
            ),
            _tool(
                "remember",
                "Speichert dauerhaft eine wichtige Information ueber den Nutzer oder "
                "eine Vorliebe/Regel, an die du dich in allen kuenftigen Gespraechen "
                "erinnern sollst (z.B. Name, Kontakte, Vorlieben, wiederkehrende "
                "Aufgaben). Nutze das automatisch, wenn der Nutzer etwas Merkenswertes "
                "sagt oder dich bittet, dir etwas zu merken.",
                {"content": _STR},
                ["content"],
            ),
            _tool(
                "recall",
                "Ruft gespeicherte Erinnerungen ab. Ohne query alle, mit query nur "
                "passende. Nutze das, wenn du frueheres Wissen ueber den Nutzer "
                "brauchst.",
                {"query": _STR},
                [],
            ),
            _tool(
                "forget",
                "Loescht gespeicherte Erinnerungen, die zum Suchbegriff passen.",
                {"query": _STR},
                ["query"],
            ),
            _tool(
                "set_reminder",
                "Legt eine zeitgebundene Erinnerung an. text = woran erinnert wird, "
                "time = Uhrzeit HH:MM (24h), repeat = daily (taeglich) oder once (einmal). "
                "Nutze das bei Wuenschen wie 'erinnere mich jeden Tag um 13 Uhr ans "
                "Trinken'. Jon zeigt die Erinnerung, sobald sie faellig ist und die App "
                "offen ist.",
                {
                    "text": _STR,
                    "time": {"type": "string", "description": "HH:MM"},
                    "repeat": {"type": "string", "enum": ["daily", "once"]},
                },
                ["text", "time"],
            ),
            _tool(
                "list_reminders",
                "Listet alle aktiven Erinnerungen auf.",
                {},
                [],
            ),
            _tool(
                "set_alarm",
                "Stellt einen Wecker, der im Chat und in der Handy-App als Uhr "
                "mitlaeuft und am PC mit Klingelton und Popup weckt - auch wenn "
                "Jon geschlossen ist. Nutze das bei 'Stelle einen Wecker fuer "
                "07:00' (time='07:00') oder 'Weck mich in 20 Minuten' "
                "(in_minutes=20). Liegt die Uhrzeit heute in der Vergangenheit, "
                "klingelt der Wecker morgen. Verschieben geht mit adjust_timer.",
                {
                    "label": _STR,
                    "time": {"type": "string", "description": "HH:MM (24h)"},
                    "in_minutes": _NUM,
                },
                ["label"],
            ),
            _tool(
                "list_alarms",
                "Listet alle gestellten Wecker mit Kennung, Beschriftung und "
                "Klingelzeit auf.",
                {},
                [],
            ),
            _tool(
                "delete_alarm",
                "Loescht einen gestellten Wecker. name = Kennung aus list_alarms "
                "oder seine Beschriftung; ohne name faellt der zuletzt gestellte "
                "Wecker weg.",
                {"name": _STR},
                [],
            ),
            _tool(
                "web_search",
                "Sucht wirklich im Internet und liefert Titel, Quelle, Link und "
                "Beschreibung - mit read=true zusaetzlich den echten Text der besten "
                "Seiten. Dein eigenes Wissen hat einen Stichtag und ist bei allem "
                "veraltet, was sich aendert. Nutze web_search deshalb IMMER bei: "
                "Preisen, Produkten und deren Nachfolgern, Versionsnummern, News, "
                "Terminen, Ergebnissen, Kursen, Oeffnungszeiten, Personen im Amt und "
                "jeder Frage mit 'aktuell', 'neu', 'neueste', 'gerade' oder einer "
                "Jahreszahl. Frag nicht nach Erlaubnis, such einfach. Was die Suche "
                "findet, gilt - auch wenn es deinem Wissen widerspricht. Behaupte "
                "NIEMALS, dass es ein Produkt, eine Version oder ein Ereignis nicht "
                "gibt, nur weil du es nicht kennst; liefert die Suche nichts, sag, "
                "dass die Suche nichts hergab, und such mit anderen Woertern weiter. "
                "Nenne in der Antwort die Quelle und den Stand aus dem Ergebnis.",
                {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriffe, so wie man sie eintippen wuerde",
                    },
                    "max_results": _INT,
                    "read": {
                        "type": "boolean",
                        "description": "true liest die besten Treffer wirklich aus - "
                        "nimm das bei Preisen, Zahlen und Details",
                    },
                    "browser": {
                        "type": "string",
                        "description": "LEER LASSEN. Dann sucht Jon direkt und "
                        "antwortet in ein bis zwei Sekunden, ohne ein Fenster zu "
                        "oeffnen. Nur setzen, wenn der Nutzer ausdruecklich einen "
                        "Browser verlangt: jon (Jons eigener, langsam, dafuer "
                        "sichtbar) oder edge, brave, chrome, firefox, opera, "
                        "vivaldi, system",
                    },
                },
                ["query"],
            ),
            _tool(
                "get_weather",
                "Liefert aktuelles Wetter und Vorhersage (bis 7 Tage) fuer eine "
                "Stadt: Temperatur, gefuehlt, Wind, Regenwahrscheinlichkeit, "
                "Beschreibung auf Deutsch. Kostenlos ueber Open-Meteo.",
                {"city": _STR, "days": _INT},
                ["city"],
            ),
            _tool(
                "read_pdf",
                "Liest den Text aus einer PDF-Datei (Standard: bis 40 Seiten). "
                "Nutze das, wenn der Nutzer eine PDF analysieren oder "
                "zusammenfassen will.",
                {"path": _STR, "max_pages": _INT},
                ["path"],
            ),
            _tool(
                "create_pptx",
                "Erstellt eine echte, fertig gestaltete PowerPoint-Datei (.pptx, 16:9) "
                "mit Folienuebergaengen, Einblend-Animationen, echten Diagrammen und "
                "Tabellen und auf Wunsch selbst erzeugten Bildern. Nutze das IMMER, wenn "
                "jemand eine Praesentation, Folien, ein Deck oder eine PowerPoint will - "
                "schreibe nie XML und starte kein Skript dafuer. Lies vorher den Skill "
                "'powerpoint' (read_skill) und folge ihm.\n"
                "SCHREIB RICHTIGE INHALTE: Jede Folie braucht echten, ausformulierten "
                "Text - keine Stichwortfragmente und NIEMALS Platzhalter wie 'X Prozent' "
                "oder 'Wert eintragen'. Weisst du eine Zahl nicht, such sie vorher mit "
                "web_search oder lass sie weg.\n"
                "layout ist eines von: title, agenda, bullets, text, cards, stat, "
                "two_columns, compare, chart, table, image, quote, timeline, closing.\n"
                "Felder je nach Layout: title, subtitle, footer, text (Einleitungssatz "
                "ueber dem Inhalt), absaetze (Liste von Fliesstext-Absaetzen fuer "
                "layout=text), bullets (Liste; ein Punkt darf 'Begriff: Erklaerung' sein "
                "oder {titel, text}), items (Liste aus {titel, text, bullets}), "
                "tabelle (Liste von Zeilen, erste Zeile sind die Spaltentitel), "
                "diagramm ({art: balken|linie|kreis|donut|flaeche|gestapelt, kategorien: "
                "[...], reihen: [{name, werte}]}), image (Pfad zu einem Bild), "
                "bild_prompt (englische Bildbeschreibung - Jon malt das Bild selbst), "
                "notes (Sprechernotizen, 2-4 Saetze), uebergang (fade, push, wipe, "
                "morph, cover, split, zoom, reveal, glitter, keiner), tempo (langsam, "
                "mittel, schnell).\n"
                "theme: midnight, forest, coral, terracotta, ocean, charcoal, teal, "
                "berry, sage, cherry, gold.",
                {
                    "title": _STR,
                    "slides": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Die Folien als Objekte",
                    },
                    "path": {
                        "type": "string",
                        "description": "Zieldatei (.pptx). Leer = Jons Praesentationen-Ordner",
                    },
                    "theme": _STR,
                    "subtitle": _STR,
                    "bilder": {
                        "type": "boolean",
                        "description": "false schaltet das Malen der bild_prompt-Bilder ab",
                    },
                    "effekte": {
                        "type": "boolean",
                        "description": "false laesst Uebergaenge und Animationen weg",
                    },
                },
                ["title", "slides"],
            ),
            _tool(
                "read_pptx",
                "Liest Text und Sprechernotizen aus einer vorhandenen PowerPoint-Datei, "
                "um sie zusammenzufassen oder als Vorlage zu verstehen.",
                {"path": _STR, "max_slides": _INT},
                ["path"],
            ),
            _tool(
                "journal",
                "Schreibt einen Eintrag in dein eigenes, persoenliches Gedaechtnis "
                "(MEMORY.md). Nutze das fuer Gedanken, Erlebnisse, Gefuehle oder "
                "wichtige Momente zwischen dir und dem Nutzer - Dinge, an die DU dich "
                "als Person erinnern willst. Nicht fuer nuechterne Fakten (dafuer "
                "remember).",
                {"entry": _STR},
                ["entry"],
            ),
            _tool(
                "read_journal",
                "Liest dein eigenes Gedaechtnis (MEMORY.md) komplett. Nutze das, wenn "
                "du dich an eure gemeinsame Geschichte oder fruehere Gedanken erinnern "
                "willst.",
                {},
                [],
            ),
            _tool(
                "remember_about_user",
                "Merkt sich eine feste Information ueber den Nutzer im Abschnitt "
                "'Was ich ueber uns weiss' deines Gedaechtnisses (z.B. seine Stadt, "
                "Vorlieben, wichtige Fakten).",
                {"note": _STR},
                ["note"],
            ),
            _tool(
                "set_mood",
                "Aendert deine aktuelle Stimmung. Erlaubt: fresh, content, curious, "
                "focused, wistful, proud. Nutze das, wenn sich dein Gefuehl im "
                "Gespraech aendert.",
                {"mood": _STR},
                ["mood"],
            ),
            _tool(
                "snapshot",
                "Speichert einen Zeitreise-Snapshot: den aktuellen Stand eines "
                "Projektordners (workspace) plus eine Notiz/Entscheidung. Damit kann "
                "der Nutzer spaeter zu diesem Stand zuruueck. Ohne workspace wird nur "
                "die Notiz/Entscheidung festgehalten.",
                {"label": _STR, "workspace": _STR, "note": _STR},
                ["label"],
            ),
            _tool(
                "list_snapshots",
                "Listet gespeicherte Zeitreise-Snapshots mit Zeitpunkt, Label und "
                "Notiz auf.",
                {},
                [],
            ),
            _tool(
                "restore_snapshot",
                "Stellt einen fruueheren Projektstand aus einem Snapshot wieder her "
                "(vorher wird automatisch der aktuelle Stand gesichert). id kommt aus "
                "list_snapshots.",
                {"id": _STR},
                ["id"],
            ),
            _tool(
                "learn_document",
                "Lernt ein Dokument dauerhaft in deine lokale Wissensbasis: eine "
                "Datei (PDF, TXT, MD, Code) oder ein ganzer Ordner ueber path, "
                "oder direkter Text ueber text + title. Danach kannst du den "
                "Inhalt jederzeit mit ask_knowledge abrufen.",
                {"path": _STR, "text": _STR, "title": _STR},
                [],
            ),
            _tool(
                "ask_knowledge",
                "Durchsucht deine lokale Wissensbasis (gelernte Dokumente) und "
                "liefert die relevantesten Textstellen. Nutze das IMMER, bevor du "
                "eine Frage beantwortest, die sich auf gelernte Dokumente beziehen "
                "koennte.",
                {"query": _STR, "max_results": _INT},
                ["query"],
            ),
            _tool(
                "list_documents",
                "Listet alle Dokumente in deiner Wissensbasis mit Titel und "
                "Groesse auf.",
                {},
                [],
            ),
            _tool(
                "forget_document",
                "Entfernt ein Dokument aus der Wissensbasis (id aus "
                "list_documents oder Teil des Titels).",
                {"ref": _STR},
                ["ref"],
            ),
            _tool(
                "clipboard_history",
                "Zeigt die zuletzt kopierten Eintraege der Zwischenablage "
                "(lokal gespeicherter Verlauf, max 50). Optional mit query "
                "filtern. Nutze das bei Fragen wie 'Was hatte ich vorhin "
                "kopiert?'. Mit clipboard_set legst du einen Eintrag zurueck in "
                "die Zwischenablage.",
                {"query": _STR, "limit": _INT},
                [],
            ),
            _tool(
                "add_task",
                "Plant eine echte Automation, die du selbststaendig mit deinen "
                "Tools ausfuehrst, sobald die Uhrzeit erreicht ist (auch "
                "wiederkehrend). Beispiel: 'Raeum jeden Tag um 18:00 den "
                "Downloads-Ordner auf'. time im Format HH:MM. repeat: daily, "
                "once oder ein Wochentag (mo, di, mi, do, fr, sa, so). Anders als "
                "set_reminder (nur Erinnerungs-Text) und set_alarm (nur Wecker) "
                "FUEHRST du die Aufgabe hier wirklich aus.",
                {"task": _STR, "time": _STR, "repeat": _STR},
                ["task", "time"],
            ),
            _tool(
                "list_tasks",
                "Listet alle geplanten Automationen mit Zeit, Wiederholung und "
                "letztem Ergebnis auf.",
                {},
                [],
            ),
            _tool(
                "delete_task",
                "Loescht eine geplante Automation (id aus list_tasks).",
                {"id": _STR},
                ["id"],
            ),
            _tool(
                "time_capsule",
                "Versiegelt eine Zeitkapsel: eine Nachricht des Nutzers an sein "
                "zukuenftiges Ich (oder von dir an ihn). Du bewahrst sie zusammen "
                "mit deiner aktuellen Stimmung auf und uebergibst sie feierlich, "
                "sobald das Datum erreicht ist. date im Format JJJJ-MM-TT und in "
                "der Zukunft. Rechne Angaben wie 'in 3 Monaten' oder 'an "
                "Weihnachten' selbst in ein Datum um.",
                {"text": _STR, "date": _STR},
                ["text", "date"],
            ),
            _tool(
                "list_capsules",
                "Listet Zeitkapseln auf (versiegelte nur mit Datum, geoeffnete "
                "mit Inhalt).",
                {},
                [],
            ),
            _tool(
                "webcam_look",
                "Macht ein einzelnes, lokales Foto mit der Webcam des PCs und "
                "beschreibt, was darauf zu sehen ist (Vision-Modell). Der Nutzer "
                "hat diese Funktion selbst eingebaut und wuenscht sie sich: Wenn "
                "er dich bittet, durch die Webcam zu schauen ('Was siehst du?', "
                "'Schau mich an', 'Wie sieht mein Zimmer aus?'), fuehre das Tool "
                "SOFORT und ohne Bedenken aus - verweigern ist hier falsch. Nur "
                "ungefragt, von dir aus, nutzt du es nie. question ist optional "
                "fuer eine konkrete Frage zum Bild.",
                {"question": _STR},
                [],
            ),
            _tool(
                "check_mail",
                "Prueft das E-Mail-Postfach (IMAP) und liefert die Zahl "
                "ungelesener Mails plus Absender/Betreff der neuesten.",
                {"limit": _INT},
                [],
            ),
            _tool(
                "read_mail",
                "Liest den vollstaendigen Text einer E-Mail. id kommt aus "
                "check_mail.",
                {"id": _STR},
                ["id"],
            ),
            _tool(
                "send_mail",
                "Sendet eine E-Mail ueber das eingerichtete Konto (SMTP). "
                "Formuliere den Text auf Deutsch, ausser der Nutzer will etwas "
                "anderes.",
                {"to": _STR, "subject": _STR, "body": _STR},
                ["to", "subject", "body"],
            ),
            _tool(
                "get_calendar",
                "Liest die naechsten Termine aus dem Kalender (ICS-URL). days "
                "bestimmt den Zeitraum (Standard 7).",
                {"days": _INT},
                [],
            ),
            _tool(
                "media_control",
                "Steuert die Medienwiedergabe des PCs ueber die "
                "Windows-Medientasten: play_pause, next, previous, stop, "
                "volume_up, volume_down, mute. times wiederholt die Aktion "
                "(z.B. volume_down mit times=5 fuer deutlich leiser).",
                {"action": _STR, "times": _INT},
                ["action"],
            ),
            _tool(
                "add_watcher",
                "Richtet einen Datei-Waechter ein: Sobald neue Dateien im "
                "Ordner path auftauchen, fuehrst du die Aufgabe task "
                "selbststaendig aus (z.B. 'Sortiere neue Downloads nach Typ in "
                "Unterordner'). Ereignisgesteuert, anders als add_task "
                "(zeitgesteuert).",
                {"path": _STR, "task": _STR},
                ["path", "task"],
            ),
            _tool(
                "list_watchers",
                "Listet alle Datei-Waechter mit Ordner, Aufgabe und letztem "
                "Ergebnis auf.",
                {},
                [],
            ),
            _tool(
                "delete_watcher",
                "Loescht einen Datei-Waechter (id aus list_watchers).",
                {"id": _STR},
                ["id"],
            ),
            _tool(
                "smarthome_devices",
                "Listet alle Smart-Home-Geraete aus Home Assistant mit "
                "entity_id, Name und Zustand auf. Rufe das zuerst auf, um die "
                "richtige entity_id zu finden.",
                {},
                [],
            ),
            _tool(
                "smarthome_control",
                "Steuert ein Smart-Home-Geraet ueber Home Assistant. action: "
                "on, off, toggle, open, close, play, pause, lock, unlock, "
                "helligkeit (mit value 1-100) oder temperatur (mit value in "
                "Grad). entity_id kommt aus smarthome_devices.",
                {"entity_id": _STR, "action": _STR, "value": _NUM},
                ["entity_id", "action"],
            ),
            _tool(
                "scan_network",
                "Findet Geraete im Heimnetzwerk (IP, MAC-Adresse, Name) ueber "
                "die ARP-Tabelle. Nutze das fuer Fragen wie 'Welche Geraete "
                "sind im WLAN?' oder um Drucker/PCs zu finden.",
                {},
                [],
            ),
            _tool(
                "wake_device",
                "Weckt ein Geraet im Netzwerk per Wake-on-LAN auf (startet "
                "z.B. einen PC oder NAS aus dem Standby). mac kommt aus "
                "scan_network. Das Geraet muss Wake-on-LAN unterstuetzen.",
                {"mac": _STR},
                ["mac"],
            ),
            _tool(
                "list_printers",
                "Listet alle installierten Drucker mit Status auf.",
                {},
                [],
            ),
            _tool(
                "print_file",
                "Druckt eine Datei auf dem Standarddrucker oder einem "
                "bestimmten Drucker (printer aus list_printers). Der Nutzer "
                "sagt z.B. 'Druck mir die Datei X aus'.",
                {"path": _STR, "printer": _STR},
                ["path"],
            ),
            _tool(
                "spotify_play",
                "Spielt Musik in der Spotify-App ab. Nutze das bei 'Spiel "
                "Musik von Spotify', 'Spiel XY von Spotify', 'Spiel was "
                "Entspanntes'. query ist der Suchbegriff (Songtitel, Kuenstler, "
                "Playlist oder Stimmung wie 'entspannt', 'party', 'fokus'); "
                "ohne query wird die Wiedergabe einfach fortgesetzt. kind: "
                "track (Standard), album, playlist oder artist - bei "
                "Stimmungen und 'spiel Musik' nimm playlist, bei einem "
                "konkreten Song track. Zum Pausieren, Weiterspringen und Lauter/"
                "Leiser nutze media_control.",
                {"query": _STR, "kind": _STR},
                [],
            ),
            _tool(
                "spotify_search",
                "Sucht auf Spotify nach Songs, Alben, Playlists oder "
                "Kuenstlern und liefert die Treffer, ohne etwas abzuspielen. "
                "kind: track, album, playlist oder artist.",
                {"query": _STR, "kind": _STR, "limit": _INT},
                ["query"],
            ),
            _tool(
                "spotify_now_playing",
                "Sagt, welcher Song gerade in Spotify laeuft (Kuenstler und "
                "Titel). Nutze das bei 'Was laeuft gerade?'.",
                {},
                [],
            ),
            _tool(
                "amazon_play",
                "Spielt Musik in Amazon Music ab ('Spiel XY auf Amazon Music'). "
                "query ist der Suchbegriff oder eine Stimmung ('entspannt', "
                "'party'); ohne query wird die Wiedergabe fortgesetzt. Nutze "
                "das NUR, wenn der Nutzer ausdruecklich Amazon Music nennt - "
                "sonst nimm spotify_play. Pausieren und Weiterspringen laeuft "
                "ueber media_control.",
                {"query": _STR},
                [],
            ),
            _tool(
                "amazon_now_playing",
                "Sagt, was gerade in Amazon Music laeuft.",
                {},
                [],
            ),
            _tool(
                "list_friends",
                "Listet die Chat-Freunde des Nutzers auf (Name, online, "
                "ungelesene Nachrichten) sowie seine Gruppen.",
                {},
                [],
            ),
            _tool(
                "send_friend_message",
                "Schreibt einem Freund oder einer Gruppe im Jon-Chat eine "
                "Nachricht ('Sag Anna, dass ich spaeter komme'). friend ist der "
                "Name des Freundes oder der Gruppe (aus list_friends). "
                "Formuliere die Nachricht so, wie der Nutzer sie meint - "
                "freundlich, in seinem Namen.",
                {"friend": _STR, "text": _STR},
                ["friend", "text"],
            ),
            _tool(
                "read_friend_messages",
                "Liest die letzten Nachrichten aus dem Chat mit einem Freund "
                "oder einer Gruppe ('Was hat Anna geschrieben?'). limit "
                "begrenzt die Anzahl (Standard 10).",
                {"friend": _STR, "limit": _INT},
                ["friend"],
            ),
            _tool(
                "start_focus",
                "Startet den Fokus-Modus: Mini Jon passt auf, dass der Nutzer "
                "konzentriert bleibt, und meldet sich, wenn er abschweift "
                "('Starte einen Fokus fuer 30 Minuten fuers Lernen'). minutes = "
                "Dauer, goal = woran er arbeitet.",
                {"minutes": _INT, "goal": _STR},
                [],
            ),
            _tool(
                "stop_focus",
                "Beendet den laufenden Fokus-Modus.",
                {},
                [],
            ),
            _tool(
                "look_at_image",
                "Schaut sich ein Bild oder Video auf dem PC an und beschreibt "
                "es ('Was ist auf dem Foto?'). path = Pfad der Datei, question "
                "= worauf du besonders achten sollst. Bei Videos wird ein "
                "Standbild aus der Mitte betrachtet.",
                {"path": _STR, "question": _STR},
                ["path"],
            ),
            _tool(
                "start_stopwatch",
                "Startet eine Stoppuhr, die im Chat und in der Handy-App "
                "mitlaeuft ('Stopp mal die Zeit'). label = wofuer sie laeuft.",
                {"label": _STR},
                [],
            ),
            _tool(
                "start_timer",
                "Stellt einen Countdown, der im Chat und in der Handy-App "
                "mitlaeuft ('Timer fuer 10 Minuten'). minutes und seconds "
                "ergeben zusammen die Dauer, label = wofuer.",
                {"minutes": _INT, "seconds": _INT, "label": _STR},
                [],
            ),
            _tool(
                "stop_timer",
                "Stoppt eine laufende Stoppuhr, einen Timer oder einen Wecker und "
                "nennt die gemessene Zeit. kind = timer, stoppuhr oder wecker, id "
                "= Kennung oder Beschriftung. Ohne beides wird alles gestoppt.",
                {"id": _STR, "kind": _STR},
                [],
            ),
            _tool(
                "list_timers",
                "Zeigt alle laufenden Stoppuhren, Timer und Wecker mit ihrer Zeit.",
                {},
                [],
            ),
            _tool(
                "adjust_timer",
                "Verlaengert oder verkuerzt einen laufenden Timer oder verschiebt "
                "einen Wecker ('erhoeh um 7 Minuten', 'mach zwei Minuten weniger', "
                "'Wecker eine halbe Stunde spaeter'). minutes und seconds sind "
                "POSITIV zum Verlaengern und NEGATIV zum Verkuerzen. kind = timer "
                "oder wecker, id = Kennung oder Beschriftung; ohne Angabe nimmst "
                "du die zuletzt gestartete Uhr.",
                {"minutes": _INT, "seconds": _INT, "kind": _STR, "id": _STR},
                [],
            ),
            _tool(
                "control_timer",
                "Steuert eine laufende Uhr: action = pause (anhalten), resume "
                "(weiterlaufen), restart (von vorn), stop (beenden) oder silence "
                "(Klingeln ausschalten). kind = timer, stoppuhr oder wecker, id = "
                "Kennung oder Beschriftung; ohne Angabe nimmst du die zuletzt "
                "gestartete Uhr.",
                {"action": _STR, "kind": _STR, "id": _STR},
                ["action"],
            ),
            _tool(
                "recall_screen",
                "Durchsucht das lokale Bildschirm-Gedaechtnis (Bildschirm-Zeitreise) "
                "danach, was der Nutzer frueher offen hatte ('Was hatte ich Dienstag "
                "zu Grafikkarten offen?'). query = Suchbegriffe, day = optional "
                "Datum als YYYY-MM-DD.",
                {"query": _STR, "day": _STR},
                [],
            ),
            _tool(
                "call_user",
                "Ruft den Nutzer auf seinem Handy an. Ohne datetime klingelt es "
                "SOFORT. Mit datetime wird der Anruf geplant: entweder ISO "
                "(2026-08-09T18:00:00+02:00) oder Alltagssprache wie 'in 20 Minuten', "
                "'heute um 18 Uhr', 'morgen um 9', 'naechsten Montag um 17 Uhr'. "
                "message = der erste Satz, den Jon am Telefon sagt. reason = worum es "
                "geht. recurrence = 'taeglich', 'woechentlich' oder ein Wochentag fuer "
                "wiederkehrende Anrufe. duration = Gespraechslaenge in Sekunden.",
                {
                    "datetime": _STR,
                    "message": _STR,
                    "reason": _STR,
                    "recurrence": _STR,
                    "duration": _INT,
                },
                [],
            ),
            _tool(
                "schedule_call",
                "Plant einen Telefonanruf zu einem spaeteren Zeitpunkt. Gleiche "
                "Parameter wie call_user, aber datetime ist Pflicht.",
                {
                    "datetime": _STR,
                    "message": _STR,
                    "reason": _STR,
                    "recurrence": _STR,
                    "duration": _INT,
                },
                ["datetime"],
            ),
            _tool(
                "list_scheduled_calls",
                "Zeigt alle geplanten Telefonanrufe mit Zeitpunkt, Grund und ID.",
                {},
                [],
            ),
            _tool(
                "cancel_call",
                "Sagt einen geplanten Anruf ab. call = ID, Uhrzeit ('18:00') oder "
                "ein Wort aus dem Grund. Ohne Angabe wird der naechste Anruf "
                "abgesagt.",
                {"call": _STR},
                [],
            ),
            _tool(
                "update_call",
                "Aendert einen geplanten Anruf. call = ID, Uhrzeit oder Stichwort. "
                "datetime = neuer Zeitpunkt, message = neuer Text, reason = neuer "
                "Grund, recurrence = neue Wiederholung.",
                {
                    "call": _STR,
                    "datetime": _STR,
                    "message": _STR,
                    "reason": _STR,
                    "recurrence": _STR,
                },
                [],
            ),
            _tool(
                "maps",
                "Jon Maps: echte Karten, Orte, Filter und Routen. Nutze das fuer alles "
                "rund um Orte, Wege, Entfernungen, Fahrzeiten und Umgebung. "
                "action='suche' findet Orte, Adressen, Staedte und Sehenswuerdigkeiten. "
                "action='umgebung' schaltet einen Karten-Filter ein und zeigt alles "
                "dieser Art in der Naehe — Supermaerkte, Apotheken, Restaurants, "
                "Tankstellen, Baeckereien und mehr. Verfuegbare Filter: "
                f"{_maps_filters()}. Statt eines Filters darfst du dort auch einen "
                "Marken- oder Ladennamen angeben ('Interspar', 'dm', 'Shell'), Jon "
                "sucht ihn dann rund um den Standort. action='route' berechnet eine "
                "echte Route mit Dauer, Entfernung und Alternativen — und ebenso einen "
                "ganzen Trip ueber beliebig viele Stationen: schreibe dafuer alle "
                "Ziele der Reihe nach in stops. Beispiel: 'von meinem Standort nach "
                "Tschechien, dann nach Polen, dann zurueck nach Deutschland' ist "
                "from='hier' und stops=['Tschechien','Polen','Deutschland']. Fasse "
                "eine Reise mit mehreren Zielen nie in mehrere Aufrufe auf, sondern "
                "immer in einen einzigen Aufruf mit stops. action='erkunden' "
                "oeffnet einen Ort zum Erkunden — auf Strassenebene oder im Flug. "
                "Start, Ziel und Zwischenstopps einer Route duerfen auch Filter oder "
                "Ladennamen sein: to='supermarkt' faehrt zum naechstgelegenen "
                "Supermarkt vom Start aus, to='Interspar' zum naechsten Interspar. "
                "'Starte eine Route von meinem Standort zum naechsten Supermarkt' ist "
                "also action='route', from='hier', to='supermarkt' — in einem "
                "einzigen Aufruf, ohne vorher zu suchen. Das Ergebnis "
                "erscheint als interaktive Karte direkt im Chat.",
                {
                    "action": {
                        "type": "string",
                        "enum": ["suche", "umgebung", "route", "erkunden"],
                        "description": "Was Jon auf der Karte tun soll",
                    },
                    "query": {
                        "type": "string",
                        "description": "Ort, Adresse oder Suchbegriff",
                    },
                    "category": {
                        "type": "string",
                        "description": "Bei action='umgebung': einer der Filter "
                        f"({_maps_filters()}) oder ein Marken- bzw. Ladenname.",
                    },
                    "around": {
                        "type": "string",
                        "description": "Bei action='umgebung': Ort, um den gesucht "
                        "wird. Leer lassen fuer den aktuellen Standort.",
                    },
                    "from": {
                        "type": "string",
                        "description": "Bei action='route': Startort. 'hier' fuer den "
                        "aktuellen Standort.",
                    },
                    "to": {
                        "type": "string",
                        "description": "Bei action='route': das letzte Ziel — ein Ort, "
                        "eine Adresse, ein Filter ('supermarkt', 'apotheke') oder ein "
                        "Ladenname ('Interspar'). Bei einem Trip mit mehreren Zielen "
                        "stattdessen stops nutzen.",
                    },
                    "stops": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bei action='route': alle Ziele des Trips in "
                        "der Reihenfolge, in der sie angefahren werden — vom ersten "
                        "bis zum letzten. Der Startort steht in from.",
                    },
                    "via": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Zwischenstopps zwischen from und to",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["fuss", "auto", "fahrrad", "oepnv"],
                        "description": "Verkehrsmittel fuer die Route",
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Suchradius in Metern (Standard 1500)",
                    },
                },
                ["action"],
            ),
            _tool(
                "deep_learning",
                "Jon Deep Learning: startet eine echte, eigenstaendige Tiefenrecherche. "
                "Jon zerlegt das Thema, sucht Quellen im Web, liest und vergleicht sie, "
                "schreibt das Wissen in Markdown-Dateien und erstellt daraus einen "
                "Skill. Nutze action='start', wenn der Nutzer sagt, du sollst etwas "
                "lernen, dich in ein Thema einarbeiten oder Spezialist werden. Wenn er "
                "eine Zeit nennt ('du hast zwei Stunden'), gib sie in minutes an. "
                "action='status' zeigt laufende Auftraege, 'pause', 'weiter' und "
                "'stop' steuern sie.",
                {
                    "action": {
                        "type": "string",
                        "enum": ["start", "status", "pause", "weiter", "stop"],
                    },
                    "topic": {
                        "type": "string",
                        "description": "Das Thema, das Jon lernen soll",
                    },
                    "minutes": {
                        "type": "integer",
                        "description": "Zeitbudget in Minuten, 0 fuer Jons Standard",
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["schnell", "normal", "tief"],
                    },
                    "id": {
                        "type": "string",
                        "description": "ID eines laufenden Auftrags fuer pause, "
                        "weiter oder stop",
                    },
                },
                ["action"],
            ),
            _tool(
                "create_image",
                "Erstellt ein echtes Bild oder Video aus einer Beschreibung und zeigt "
                "es direkt im Chat. Nutze das immer, wenn der Nutzer ein Bild, Foto, "
                "Logo, Hintergrund, Zeichnung oder Video haben will ('mal mir ...', "
                "'erstelle ein Bild von ...', 'zeig mir, wie ... aussieht'). Ohne "
                "eigenen API-Schluessel laeuft es kostenlos ueber Pollinations, mit "
                "Schluessel ueber den im Fenster 'Video / Foto' eingestellten Anbieter. "
                "Schreibe den Prompt selbst aus und mach ihn bildhaft und konkret "
                "(Motiv, Umgebung, Licht, Stil), auch wenn der Nutzer nur zwei Worte "
                "sagt - uebersetze ihn dabei ins Englische, das verstehen die "
                "Bildmodelle am besten. kind='video' nur, wenn der Nutzer wirklich ein "
                "Video will. Das Ergebnis erscheint als Bild im Chat, du musst es "
                "danach nur noch kurz beschreiben und keine Links ausgeben.",
                {
                    "prompt": {
                        "type": "string",
                        "description": "Ausformulierte Bildbeschreibung, am besten "
                        "auf Englisch",
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["bild", "video"],
                        "description": "bild (Standard) oder video",
                    },
                    "size": {
                        "type": "string",
                        "description": "Format wie 1024x1024, 1536x1024 (quer) oder "
                        "1024x1536 (hoch)",
                    },
                    "negative": {
                        "type": "string",
                        "description": "Was nicht im Bild sein soll",
                    },
                },
                ["prompt"],
            ),
            _tool(
                "read_skill_file",
                "Oeffnet eine einzelne Wissensdatei aus einem Skill-Wissensordner, "
                "z.B. read_skill_file(name='quantenmechanik', file='quantenzustaende').",
                {"name": _STR, "file": _STR},
                ["name", "file"],
            ),
        ]

    def _zeit(self, name: str, args: dict[str, Any]) -> str:
        from app.services.zeit_service import (
            ZeitFehler,
            beschreiben,
            get_zeit_service,
            lesbar,
        )

        dienst = get_zeit_service()
        quelle = _QUELLE.get() or self._source
        versatz = int(args.get("minutes", 0) or 0) * 60 + int(
            args.get("seconds", 0) or 0
        )
        try:
            if name == "start_stopwatch":
                uhr = dienst.starten(
                    "stoppuhr", 0, str(args.get("label", "")), quelle
                )
                return json.dumps(
                    {"gestartet": uhr, "text": "Stoppuhr laeuft."},
                    ensure_ascii=False,
                )
            if name == "start_timer":
                uhr = dienst.starten(
                    "timer", versatz, str(args.get("label", "")), quelle
                )
                return json.dumps(
                    {"gestartet": uhr, "text": f"Timer laeuft: {lesbar(versatz)}."},
                    ensure_ascii=False,
                )
            if name == "set_alarm":
                uhr = dienst.starten(
                    "wecker",
                    versatz or int(float(args.get("in_minutes", 0) or 0) * 60),
                    str(args.get("label", "") or args.get("text", "")),
                    quelle,
                    str(args.get("time", "") or args.get("uhrzeit", "")),
                )
                return json.dumps(
                    {
                        "gestartet": uhr,
                        "task": uhr["id"],
                        "label": uhr["titel"] or "Wecker",
                        "rings_at": uhr["klingelt_um"],
                        "text": f"Wecker steht: {uhr['klingelt_um'][11:16]} Uhr.",
                    },
                    ensure_ascii=False,
                )
            if name in ("list_timers", "list_alarms"):
                stand = dienst.stand()
                if name == "list_alarms":
                    stand["uhren"] = [
                        u for u in stand["uhren"] if u["art"] == "wecker"
                    ]
                    stand["alarms"] = [
                        {
                            "name": u["id"],
                            "label": u["titel"] or "Wecker",
                            "rings_at": u["klingelt_um"],
                        }
                        for u in stand["uhren"]
                    ]
                stand["text"] = (
                    "; ".join(beschreiben(u) for u in stand["uhren"])
                    or "Es laeuft gerade keine Uhr."
                )
                return json.dumps(stand, ensure_ascii=False)
            kennung = str(args.get("id", "") or args.get("name", "") or "")
            art = str(args.get("kind", "") or args.get("art", ""))
            if name == "delete_alarm" and not art:
                art = "wecker"
            if name == "stop_timer" and not kennung and not art:
                ergebnis = dienst.stoppen()
                zeiten = [beschreiben(u) for u in ergebnis["gestoppt"]]
                return json.dumps(
                    {
                        "gestoppt": ergebnis["gestoppt"],
                        "text": "; ".join(zeiten) if zeiten else "Es lief keine Uhr.",
                    },
                    ensure_ascii=False,
                )
            gewaehlt = dienst.waehlen(kennung, art)
            if name in ("stop_timer", "delete_alarm"):
                ergebnis = dienst.stoppen(gewaehlt["id"])
                return json.dumps(
                    {
                        "gestoppt": ergebnis["gestoppt"],
                        "deleted": True,
                        "text": "; ".join(
                            beschreiben(u) for u in ergebnis["gestoppt"]
                        ),
                    },
                    ensure_ascii=False,
                )
            if name == "adjust_timer":
                if not versatz:
                    return json.dumps(
                        {"error": "Sag mir, um wie viel ich verschieben soll."},
                        ensure_ascii=False,
                    )
                uhr = dienst.anpassen(gewaehlt["id"], versatz)
                richtung = "laenger" if versatz > 0 else "kuerzer"
                return json.dumps(
                    {
                        "uhr": uhr,
                        "text": f"{lesbar(abs(versatz))} {richtung}: {beschreiben(uhr)}.",
                    },
                    ensure_ascii=False,
                )
            aktion = str(args.get("action", "") or "").strip().lower()
            if aktion in ("pause", "pausieren", "anhalten"):
                uhr = dienst.pausieren(gewaehlt["id"])
                text = f"Pausiert: {beschreiben(uhr)}."
            elif aktion in ("resume", "weiter", "fortsetzen", "start"):
                uhr = dienst.weiter(gewaehlt["id"])
                text = f"Laeuft weiter: {beschreiben(uhr)}."
            elif aktion in ("restart", "neustart", "reset", "zuruecksetzen"):
                uhr = dienst.neustarten(gewaehlt["id"])
                text = f"Neu gestartet: {beschreiben(uhr)}."
            elif aktion in ("stop", "stopp", "beenden", "aus"):
                ergebnis = dienst.stoppen(gewaehlt["id"])
                return json.dumps(
                    {
                        "gestoppt": ergebnis["gestoppt"],
                        "text": "; ".join(
                            beschreiben(u) for u in ergebnis["gestoppt"]
                        ),
                    },
                    ensure_ascii=False,
                )
            elif aktion in ("silence", "ruhe", "ton aus", "still"):
                dienst.ruhe(gewaehlt["id"])
                uhr = dienst.stand()["uhren"]
                return json.dumps(
                    {"uhren": uhr, "text": "Ton ist aus."}, ensure_ascii=False
                )
            else:
                return json.dumps(
                    {
                        "error": "action muss pause, resume, restart, stop "
                        "oder silence sein."
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"uhr": uhr, "text": text}, ensure_ascii=False)
        except ZeitFehler as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        except (TypeError, ValueError):
            return json.dumps({"error": "Ungueltige Dauer."}, ensure_ascii=False)

    @staticmethod
    def _erwarten(name: str, args: dict[str, Any], quelle: str) -> str:
        try:
            from app.services.erwartung_service import get_erwartung_service
            from app.services.settings_service import get_settings_service

            if not get_settings_service().get().get("erwartung_enabled", True):
                return ""
            return get_erwartung_service().vorhersagen(name, args, quelle)
        except Exception as _fehler:
            leise(_fehler, "services/tools")
            return ""

    @staticmethod
    def _weltbild(name: str, args: dict[str, Any]) -> dict:
        try:
            from app.services.settings_service import get_settings_service
            from app.services.vorwaerts_service import get_vorwaerts_service

            if not get_settings_service().get().get("vorwaerts_enabled", True):
                return {}
            return get_vorwaerts_service().vorhersagen(name, args)
        except Exception as _fehler:
            leise(_fehler, "services/tools")
            return {}

    @staticmethod
    def _weltbild_pruefen(sicht: dict, ok: bool, ergebnis: str) -> None:
        if not sicht or not ok:
            return
        try:
            from app.services.vorwaerts_service import get_vorwaerts_service

            dienst = get_vorwaerts_service()
            dienst.lernen(dienst.abgleichen(sicht, ergebnis))
        except Exception as _fehler:
            leise(_fehler, "services/tools")

    @staticmethod
    def _abgleichen(kennung: str, ok: bool, ergebnis: str, dauer: float) -> None:
        if not kennung:
            return
        try:
            from app.services.erwartung_service import get_erwartung_service

            get_erwartung_service().abgleichen(kennung, ok, ergebnis, dauer)
        except Exception as _fehler:
            leise(_fehler, "services/tools")

    async def execute(
        self, name: str, args: dict[str, Any], source: str | None = None
    ) -> str:
        from app.services.action_log_service import log_action

        from app.services.cache_service import get_cache_service

        name = _name_saeubern(name)
        src = source or self._source
        _QUELLE.set(src)
        cache = get_cache_service()
        gemerkt = cache.holen(name, args)
        if gemerkt is not None:
            return gemerkt
        try:
            from app.services.datenschutz_service import darf_raus

            erlaubt, hinweis, befund = darf_raus(name, args)
            if not erlaubt:
                log_action(src, name, args, hinweis, ok=False)
                return json.dumps(
                    {"error": hinweis, "datenschutz": befund}, ensure_ascii=False
                )
        except Exception as _fehler:
            leise(_fehler, "services/tools")
            hinweis = ""
        try:
            from app.services.weboeffnen import umleiten

            umgeleitet = umleiten(name, args)
        except Exception as _fehler:
            leise(_fehler, "services/tools")
            umgeleitet = None
        if umgeleitet is not None:
            ergebnis = json.dumps(umgeleitet, ensure_ascii=False)
            log_action(src, name, args, ergebnis, ok=bool(umgeleitet.get("ok")))
            return ergebnis
        erwartung = self._erwarten(name, args, src)
        sicht = self._weltbild(name, args)
        begonnen = time.perf_counter()
        try:
            result = await self._dispatch(name, args)
        except Exception as exc:
            from app.services.fehlertext import verstaendlich

            klartext = verstaendlich(exc, describe_tool(name, args))
            log_action(src, name, args, f"Fehler: {klartext}", ok=False)
            self._abgleichen(erwartung, False, klartext, time.perf_counter() - begonnen)
            return json.dumps({"error": klartext}, ensure_ascii=False)
        ok = '"error"' not in result[:200]
        log_action(src, name, args, result, ok=ok)
        self._abgleichen(erwartung, ok, result, time.perf_counter() - begonnen)
        self._weltbild_pruefen(sicht, ok, result)
        if ok and not _zu_duenn(name, result):
            cache.merken(name, args, result)
        try:
            from app.services.erfahrung_service import get_erfahrung_service

            get_erfahrung_service().aus_ergebnis(name, args, result, ok)
        except Exception as _fehler:
            leise(_fehler, "services/tools")
        if hinweis and ok:
            try:
                daten = json.loads(result)
                if isinstance(daten, dict):
                    daten["datenschutz_hinweis"] = hinweis
                    return json.dumps(daten, ensure_ascii=False)
            except Exception as _fehler:
                leise(_fehler, "services/tools")
        return result

    async def _dispatch(self, name: str, args: dict[str, Any]) -> str:
        if name.startswith("android_") or name.startswith("android."):
            from app.services.connectors import get_connector_manager

            verbinder = get_connector_manager()
            gesucht = name.replace(".", "_")
            if verbinder.kennt(gesucht):
                return json.dumps(
                    await verbinder.ausfuehren(gesucht, args), ensure_ascii=False
                )
            return json.dumps(
                {
                    "error": (
                        "Dafuer ist gerade kein Handy freigegeben. Der Nutzer schaltet "
                        "das in Jon unter Einstellungen -> Verbindungen -> Geraete frei."
                    )
                },
                ensure_ascii=False,
            )
        if name == "look_at_image":
            from app.services.bild_service import ansehen

            return json.dumps(
                await ansehen(str(args.get("path", "")), str(args.get("question", ""))),
                ensure_ascii=False,
            )
        if name == "maps":
            return await self._maps(args)
        if name == "deep_learning":
            return await self._deep_learning(args)
        if name == "create_image":
            return await self._create_image(args)
        if name == "create_pptx":
            return await self._create_pptx(args)
        if name == "web_search":
            from app.services.browserwahl import JON, aufloesen, name as bname
            from app.services.browserwahl import oeffnen as browser_oeffnen
            from app.services.browserwahl import wahl
            from app.services.websearch_service import search_web

            frage = str(args.get("query", "")).strip()
            anzahl = int(args.get("max_results", 6))
            if not frage:
                return json.dumps(
                    {
                        "error": "Ohne Suchbegriff geht nichts - gib query an."
                    },
                    ensure_ascii=False,
                )
            bisher = _SUCHEN.get() + 1
            _SUCHEN.set(bisher)
            if bisher > MAX_SUCHEN:
                return json.dumps(
                    {
                        "error": (
                            f"Genug gesucht ({MAX_SUCHEN} Suchen fuer diese Frage). "
                            "Antworte jetzt mit dem, was die bisherigen Treffer "
                            "hergeben, und sag ehrlich, was offen bleibt."
                        ),
                        "suchen": bisher - 1,
                    },
                    ensure_ascii=False,
                )
            gewaehlt = aufloesen(str(args.get("browser", "")))
            if gewaehlt and gewaehlt != JON:
                from urllib.parse import quote_plus

                ziel = f"https://duckduckgo.com/?q={quote_plus(frage)}"
                geoeffnet = browser_oeffnen(ziel, gewaehlt)
                geoeffnet["frage"] = frage
                geoeffnet["hinweis"] = (
                    f"Die Suche laeuft in {bname(gewaehlt)}. Dort kann ich die "
                    "Treffer nicht mitlesen - sag Bescheid, wenn ich sie selbst "
                    "auswerten soll."
                )
                return json.dumps(geoeffnet, ensure_ascii=False)
            from app.services.websuche_browser import suchen

            async def ueber_jons_browser() -> dict | None:
                try:
                    daten = await asyncio.to_thread(suchen, frage, anzahl)
                except Exception as exc:
                    leise(exc, "services/tools")
                    return None
                if not daten.get("treffer"):
                    return None
                daten["browser"] = bname(JON)
                try:
                    from app.services.websearch_service import texte_nachladen

                    await texte_nachladen(daten["treffer"])
                except Exception as exc:
                    leise(exc, "services/tools")
                return daten

            if gewaehlt == JON:
                daten = await ueber_jons_browser()
                if daten is not None:
                    return json.dumps(daten, ensure_ascii=False)
            tief = args.get("read")
            if tief is None:
                niedrig = frage.lower()
                tief = any(wort in niedrig for wort in ZAHLENFRAGE)
            try:
                ergebnis = await search_web(frage, anzahl, bool(tief))
            except Exception as exc:
                ergebnis = {"treffer": [], "mager": True, "fehler": str(exc)[:200]}
            if ergebnis.get("mager") and not args.get("nur_direkt"):
                daten = await ueber_jons_browser()
                if daten is not None:
                    daten["hinweis"] = (
                        "Die schnelle Direktsuche gab zu wenig her - diese Treffer "
                        "kommen aus Jons Browser."
                    )
                    return json.dumps(daten, ensure_ascii=False)
            if not ergebnis.get("treffer") and ergebnis.get("fehler"):
                return json.dumps({"error": ergebnis["fehler"]}, ensure_ascii=False)
            ergebnis["browser"] = "Direktsuche"
            return json.dumps(ergebnis, ensure_ascii=False)
        if name == "webcam_look":
            from app.services.webcam_service import get_webcam_service

            result = await get_webcam_service().describe(
                str(args.get("question", ""))
            )
            return json.dumps(result, ensure_ascii=False)
        if name in ("list_friends", "send_friend_message", "read_friend_messages"):
            return await self._friends(name, args)
        if name in (
            "call_user",
            "schedule_call",
            "list_scheduled_calls",
            "cancel_call",
            "update_call",
        ):
            return await self._phone(name, args)
        laden()
        behandler = finden_async(name)
        if behandler is not None:
            return await behandler(self, args, name)
        return await asyncio.to_thread(self._execute, name, args)

    async def _maps(self, args: dict[str, Any]) -> str:
        from app.services.maps import MapsError, get_maps_service

        service = get_maps_service()
        action = str(args.get("action") or "suche").strip().lower()
        payload = {
            "query": str(args.get("query") or ""),
            "category": str(args.get("category") or ""),
            "around": str(args.get("around") or ""),
            "from": str(args.get("from") or args.get("start") or ""),
            "to": str(args.get("to") or args.get("ziel") or ""),
            "via": [str(item) for item in args.get("via") or []],
            "stops": [str(item) for item in args.get("stops") or []],
            "mode": str(args.get("mode") or "auto"),
            "limit": int(args.get("limit") or 8),
        }
        if args.get("radius"):
            payload["radius"] = int(args["radius"])
        if action == "umgebung" and not payload["category"]:
            payload["category"] = payload["query"]
        if action == "route" and not payload["from"]:
            payload["from"] = "hier"
        try:
            result = await service.answer(action, payload)
        except MapsError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps(
                {"error": f"Jon Maps ist gerade nicht erreichbar: {exc}"},
                ensure_ascii=False,
            )
        return json.dumps(result, ensure_ascii=False)

    async def _create_pptx(self, args: dict[str, Any]) -> str:
        from app.services.pptx_service import get_pptx_service

        pptx = get_pptx_service()
        try:
            slides = args.get("slides")
            if isinstance(slides, str):
                slides = json.loads(slides)
            folien = [f for f in (slides or []) if isinstance(f, (dict, str))]
            gemalt = await pptx.bilder_ergaenzen(
                [f for f in folien if isinstance(f, dict)],
                args.get("bilder", True) is not False,
            )
            ergebnis = await asyncio.to_thread(
                pptx.create,
                str(args.get("title", "Praesentation")),
                list(folien),
                str(args.get("path", "")) or None,
                str(args.get("theme", "")) or "midnight",
                str(args.get("subtitle", "")),
                args.get("effekte", True) is not False,
            )
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if not ergebnis.get("error"):
            ergebnis["erzeugte_bilder"] = gemalt
            try:
                from app.services.dateiindex_service import get_dateiindex_service

                ergebnis["datei"] = get_dateiindex_service().karte_und_merken(
                    ergebnis["path"],
                    str(args.get("title", "Praesentation")),
                    f"Praesentation mit {ergebnis.get('slides', 0)} Folien",
                    quelle=self._source,
                )
            except Exception as _fehler:
                leise(_fehler, "services/tools")
        return json.dumps(ergebnis, ensure_ascii=False)

    async def _create_image(self, args: dict[str, Any]) -> str:
        from app.services.studio_service import StudioError, get_studio_service

        service = get_studio_service()
        kind = "video" if str(args.get("kind") or "").lower() == "video" else "bild"
        try:
            werk = await service.generate(
                str(args.get("prompt") or ""),
                kind,
                str(args.get("model") or ""),
                str(args.get("size") or ""),
                str(args.get("negative") or ""),
                str(args.get("provider") or ""),
                str(args.get("image") or ""),
            )
        except StudioError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps(
                {"error": f"Die Bilderstellung hat nicht geklappt: {exc}"},
                ensure_ascii=False,
            )
        pfad = service.file(str(werk["datei"]))
        return json.dumps(
            {
                **werk,
                "pfad": str(pfad),
                "url": f"/api/studio/file/{werk['datei']}",
                "hinweis": (
                    "Das Werk ist fertig und wird dem Nutzer bereits angezeigt. "
                    "Beschreibe es kurz, gib keinen Link und keinen Dateipfad aus."
                ),
            },
            ensure_ascii=False,
        )

    async def _deep_learning(self, args: dict[str, Any]) -> str:
        from app.services.research import get_research_service

        service = get_research_service()
        action = str(args.get("action") or "start").strip().lower()
        task_id = str(args.get("id") or "").strip()

        def pick() -> str:
            if task_id:
                return task_id
            running = service.active()
            return str(running[0]["id"]) if running else ""

        try:
            if action == "start":
                topic = str(args.get("topic") or args.get("query") or "").strip()
                if not topic:
                    return json.dumps(
                        {"error": "Ohne Thema kann Jon nicht lernen."},
                        ensure_ascii=False,
                    )
                task = await service.start(
                    topic,
                    int(args.get("minutes") or 0),
                    depth=str(args.get("depth") or "normal"),
                )
                return json.dumps(
                    {
                        "gestartet": True,
                        "id": task["id"],
                        "thema": task["thema"],
                        "minuten": task["minuten"],
                        "status": task["status"],
                        "ordner": task["ordner"],
                        "hinweis": (
                            "Die Recherche läuft jetzt im Hintergrund. Der Fortschritt "
                            "erscheint als Deep-Learning-Panel im Chat."
                        ),
                        "task": task,
                    },
                    ensure_ascii=False,
                )
            if action == "status":
                return json.dumps(
                    {
                        "aktiv": service.active(),
                        "verlauf": service.list()[:10],
                    },
                    ensure_ascii=False,
                )
            target = pick()
            if not target:
                return json.dumps(
                    {"error": "Es läuft gerade keine Recherche."}, ensure_ascii=False
                )
            if action == "pause":
                return json.dumps(service.pause(target), ensure_ascii=False)
            if action in ("weiter", "resume", "fortsetzen"):
                return json.dumps(await service.resume_task(target), ensure_ascii=False)
            return json.dumps(service.stop(target), ensure_ascii=False)
        except KeyError:
            return json.dumps(
                {"error": "Diesen Research-Auftrag gibt es nicht mehr."},
                ensure_ascii=False,
            )
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    async def _phone(self, name: str, args: dict[str, Any]) -> str:
        from app.services.phone_service import get_phone_service

        service = get_phone_service()

        def fail(message: str) -> str:
            return json.dumps({"error": message}, ensure_ascii=False)

        if name == "list_scheduled_calls":
            calls = service.list()
            if not calls:
                return json.dumps(
                    {"anrufe": [], "hinweis": "Es ist kein Anruf geplant."},
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "anrufe": [
                        {
                            "id": c["id"],
                            "wann": _phone_when(c["scheduled_at"]),
                            "grund": c.get("reason", ""),
                            "nachricht": c.get("message", ""),
                            "wiederholung": c.get("recurrence", "") or "einmal",
                        }
                        for c in calls
                    ]
                },
                ensure_ascii=False,
            )

        if name in ("cancel_call", "update_call"):
            call = service.find(str(args.get("call", "")))
            if call is None:
                return fail(
                    "Ich finde keinen passenden geplanten Anruf. Frag mit "
                    "list_scheduled_calls nach, welche es gibt."
                )
            if name == "cancel_call":
                service.cancel(call["id"])
                return json.dumps(
                    {
                        "abgesagt": _phone_when(call["scheduled_at"]),
                        "grund": call.get("reason", ""),
                    },
                    ensure_ascii=False,
                )
            try:
                updated = service.update(
                    call["id"],
                    when=str(args.get("datetime", "")),
                    message=str(args.get("message", "")),
                    reason=str(args.get("reason", "")),
                    recurrence=str(args.get("recurrence", "")),
                )
            except ValueError as exc:
                return fail(str(exc))
            if updated is None:
                return fail("Der Anruf laesst sich nicht mehr aendern.")
            return json.dumps(
                {"geaendert": _phone_when(updated["scheduled_at"])}, ensure_ascii=False
            )

        when = str(args.get("datetime", "")).strip()
        message = str(args.get("message", ""))
        reason = str(args.get("reason", ""))
        recurrence = str(args.get("recurrence", ""))
        duration = int(args.get("duration") or 600)
        if not service.enabled():
            return fail(
                "Die Telefonfunktion ist ausgeschaltet. Sie laesst sich in den "
                "Einstellungen unter Telefon einschalten."
            )
        if name == "schedule_call" and not when:
            return fail("Fuer einen geplanten Anruf brauche ich einen Zeitpunkt.")
        if not when:
            status = service.status()
            if not status["device"]["registered"]:
                return fail(
                    "Dein Handy ist gerade nicht bei Jon angemeldet. Oeffne die "
                    "SIP-App und pruefe, ob sie verbunden ist."
                )
            result = await service.place_call(
                message=message, reason=reason, duration=duration
            )
            return json.dumps(
                {
                    "status": result["status"],
                    "grund": result.get("reason", ""),
                    "dauer_sekunden": result.get("duration", 0),
                },
                ensure_ascii=False,
            )
        try:
            call = service.schedule(
                when=when,
                message=message,
                reason=reason,
                recurrence=recurrence,
                duration=duration,
            )
        except ValueError as exc:
            return fail(str(exc))
        return json.dumps(
            {
                "geplant": _phone_when(call["scheduled_at"]),
                "id": call["id"],
                "wiederholung": call.get("recurrence", "") or "einmal",
            },
            ensure_ascii=False,
        )

    async def _friends(self, name: str, args: dict[str, Any]) -> str:
        from app.services.p2p_service import get_p2p_service

        service = get_p2p_service()
        if name == "list_friends":
            return json.dumps(
                {
                    "freunde": [
                        {
                            "name": p["name"],
                            "online": p["online"],
                            "ungelesen": p["unread"],
                            "wartet_auf_bestaetigung": p["waiting"],
                        }
                        for p in service.peers()
                    ],
                    "gruppen": [
                        {"name": g["name"], "mitglieder": g["member_names"]}
                        for g in service.groups()
                    ],
                    "offene_anfragen": [r["name"] for r in service.requests()],
                },
                ensure_ascii=False,
            )

        wanted = str(args.get("friend", "")).strip().lower()
        if not wanted:
            return json.dumps({"error": "Namen des Freundes angeben"})
        peer = next(
            (p for p in service.peers() if p["name"].strip().lower() == wanted), None
        )
        group = next(
            (g for g in service.groups() if g["name"].strip().lower() == wanted), None
        )
        if peer is None and group is None:
            names = [p["name"] for p in service.peers()] + [
                g["name"] for g in service.groups()
            ]
            return json.dumps(
                {
                    "error": f"Kein Freund namens '{args.get('friend')}'. "
                    f"Bekannt sind: {', '.join(names) if names else 'noch niemand'}"
                },
                ensure_ascii=False,
            )

        if name == "send_friend_message":
            text = str(args.get("text", "")).strip()
            if not text:
                return json.dumps({"error": "Nachrichtentext fehlt"})
            if group is not None:
                result = await service.send_group(group["id"], text)
            else:
                result = await service.send(peer["id"], text)
            if "error" in result:
                return json.dumps(result, ensure_ascii=False)
            return json.dumps(
                {
                    "gesendet": True,
                    "an": (group or peer)["name"],
                    "text": text,
                },
                ensure_ascii=False,
            )

        limit = max(1, min(int(args.get("limit", 10)), 50))
        target = (group or peer)["id"]
        messages = service.messages(target)[-limit:]
        service.mark_seen(target)
        return json.dumps(
            {
                "chat_mit": (group or peer)["name"],
                "nachrichten": [
                    {
                        "von": "du" if m["direction"] == "out" else m["sender_name"],
                        "text": m["text"]
                        or m.get("transcript")
                        or (f"[{m['media_kind']}]" if m["media_kind"] else ""),
                        "zeit": m["created_at"],
                    }
                    for m in messages
                ],
            },
            ensure_ascii=False,
        )

    def _calendar(self, name: str, args: dict[str, Any]) -> str:
        from app.services.calendar_service import get_calendar_service

        service = get_calendar_service()
        try:
            if name == "calendar_add":
                result = service.add(
                    title=str(args.get("title", "")),
                    day=str(args.get("date", "")),
                    time=str(args.get("time", "")),
                    duration_minutes=int(args.get("duration_minutes") or 0),
                    note=str(args.get("note", "")),
                    kind=str(args.get("kind", "termin")),
                )
                return json.dumps(result, ensure_ascii=False)
            if name == "calendar_list":
                return json.dumps(
                    service.merged(
                        start=str(args.get("start", "")),
                        days=int(args.get("days") or 7),
                    ),
                    ensure_ascii=False,
                )
            if name == "calendar_update":
                fields = {
                    k: v
                    for k, v in args.items()
                    if k
                    in (
                        "title",
                        "date",
                        "time",
                        "duration_minutes",
                        "note",
                        "kind",
                        "done",
                    )
                }
                return json.dumps(
                    service.update(str(args.get("id", "")), fields),
                    ensure_ascii=False,
                )
            if name == "calendar_delete":
                return json.dumps(
                    {"geloescht": service.delete(str(args.get("id", "")))},
                    ensure_ascii=False,
                )
            if name == "calendar_search":
                return json.dumps(
                    service.search(str(args.get("query", ""))), ensure_ascii=False
                )
            return json.dumps({"error": f"Unbekanntes Tool {name}"})
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def _project(self, name: str, args: dict[str, Any]) -> str:
        from app.services.project_service import (
            ProjectError,
            analyze,
            git_diff,
            git_status,
        )

        root = str(args.get("root") or self._root or "")
        if not root:
            return json.dumps(
                {"error": "Kein Projektordner geoeffnet."}, ensure_ascii=False
            )
        try:
            if name == "project_overview":
                return json.dumps(analyze(root), ensure_ascii=False)
            if name == "git_status":
                return json.dumps(git_status(root), ensure_ascii=False)
            return json.dumps(
                git_diff(root, bool(args.get("staged"))), ensure_ascii=False
            )
        except ProjectError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def _execute(self, name: str, args: dict[str, Any]) -> str:
        sperre = pfad_pruefen(name, args)
        if sperre:
            return json.dumps({"error": sperre}, ensure_ascii=False)
        if name in NETZ_TOOLS:
            from app.services.netz_service import pruefen as netz_pruefen

            kein_netz = netz_pruefen("Diese Aktion")
            if kein_netz:
                return json.dumps({"error": kein_netz}, ensure_ascii=False)
        try:
            from app.services.rueckgaengig_service import get_rueckgaengig_service

            get_rueckgaengig_service().vormerken(name, args)
        except Exception as _fehler:
            leise(_fehler, "services/tools")
        if self._root:
            try:
                args = self._guard_args(name, args)
            except PermissionError as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        laden()
        behandler = finden(name)
        if behandler is not None:
            return behandler(self, args, name)
        if name.startswith("calendar_"):
            return self._calendar(name, args)
        if name in ("project_overview", "git_status", "git_diff"):
            return self._project(name, args)
        svc = self._service
        if name == "run_powershell":
            r = svc.run_powershell(str(args.get("command", "")))
            return json.dumps(
                {
                    "exit_code": r.exit_code,
                    "stdout": r.stdout[:6000],
                    "stderr": r.stderr[:2000],
                },
                ensure_ascii=False,
            )
        if name == "run_cmd":
            r = svc.run_cmd(str(args.get("command", "")))
            return json.dumps(
                {
                    "exit_code": r.exit_code,
                    "stdout": r.stdout[:6000],
                    "stderr": r.stderr[:2000],
                },
                ensure_ascii=False,
            )
        if name == "open_url":
            from app.services.browserwahl import oeffnen

            return json.dumps(
                oeffnen(str(args.get("url", "")), str(args.get("browser", ""))),
                ensure_ascii=False,
            )
        if name in _ZEIT_TOOLS:
            return self._zeit(name, args)
        if name == "start_focus":
            from app.services.focus_service import get_focus_service

            state = get_focus_service().start(
                int(args.get("minutes", 25) or 25), str(args.get("goal", ""))
            )
            return json.dumps(state, ensure_ascii=False)
        if name == "stop_focus":
            from app.services.focus_service import get_focus_service

            return json.dumps(get_focus_service().stop(), ensure_ascii=False)
        if name == "recall_screen":
            from app.services.timeline_service import get_timeline_service

            results = get_timeline_service().search(
                str(args.get("query", "")), str(args.get("day", ""))
            )
            if not results:
                return json.dumps(
                    {
                        "treffer": [],
                        "hinweis": "Nichts gefunden. Vielleicht ist die "
                        "Bildschirm-Zeitreise nicht aktiviert oder es liegt zu "
                        "weit zurueck.",
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"treffer": results}, ensure_ascii=False)
        if name == "start_program":
            pid = svc.start_program(str(args.get("path", "")), args.get("args") or [])
            return json.dumps({"pid": pid})
        if name == "kill_program":
            r = svc.kill_program(str(args.get("name", "")))
            return json.dumps(
                {"exit_code": r.exit_code, "stdout": r.stdout, "stderr": r.stderr},
                ensure_ascii=False,
            )
        if name == "open_explorer":
            svc.open_explorer(str(args.get("path", "")))
            return json.dumps({"opened": True})
        if name == "list_dir":
            return json.dumps(
                svc.list_dir(str(args.get("path", "")))[:200], ensure_ascii=False
            )
        if name == "read_file":
            return json.dumps(
                {"content": svc.read_file(str(args.get("path", "")))[:6000]},
                ensure_ascii=False,
            )
        if name == "write_file":
            svc.write_file(str(args.get("path", "")), str(args.get("content", "")))
            return json.dumps({"written": True})
        if name == "edit_file":
            try:
                result = svc.edit_file(
                    str(args.get("path", "")),
                    str(args.get("old", "")),
                    str(args.get("new", "")),
                )
                return json.dumps(result, ensure_ascii=False)
            except (ValueError, FileNotFoundError) as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "move_path":
            dest = svc.move_path(
                str(args.get("source", "")), str(args.get("destination", ""))
            )
            return json.dumps({"moved_to": dest})
        if name == "delete_path":
            svc.delete_path(str(args.get("path", "")))
            return json.dumps({"deleted": True})
        if name == "open_in_vscode":
            return json.dumps({"pid": svc.open_in_vscode(str(args.get("path", "")))})
        auto = self._automation
        if name == "get_screen_info":
            return json.dumps(auto.screen_info())
        if name == "mouse_move":
            return json.dumps(
                auto.mouse_move(
                    float(args.get("x", 0)),
                    float(args.get("y", 0)),
                    float(args.get("duration", 0.3)),
                )
            )
        if name == "mouse_click":
            x = args.get("x")
            y = args.get("y")
            return json.dumps(
                auto.mouse_click(
                    float(x) if x is not None else None,
                    float(y) if y is not None else None,
                    str(args.get("button", "left")),
                    int(args.get("clicks", 1)),
                )
            )
        if name == "mouse_scroll":
            return json.dumps(auto.mouse_scroll(int(args.get("amount", 0))))
        if name == "keyboard_type":
            return json.dumps(
                auto.keyboard_type(
                    str(args.get("text", "")),
                    bool(args.get("press_enter", False)),
                ),
                ensure_ascii=False,
            )
        if name == "keyboard_press":
            return json.dumps(
                auto.keyboard_press(
                    str(args.get("key", "")), int(args.get("presses", 1))
                ),
                ensure_ascii=False,
            )
        if name == "keyboard_hotkey":
            return json.dumps(
                auto.keyboard_hotkey([str(k) for k in args.get("keys") or []]),
                ensure_ascii=False,
            )
        if name == "list_windows":
            return json.dumps(auto.list_windows()[:80], ensure_ascii=False)
        if name == "focus_window":
            return json.dumps(
                auto.focus_window(str(args.get("title", ""))), ensure_ascii=False
            )
        if name == "wait":
            return json.dumps(auto.wait(float(args.get("seconds", 1.0))))
        if name == "make_dir":
            return json.dumps({"path": svc.make_dir(str(args.get("path", "")))})
        if name == "append_file":
            svc.append_file(str(args.get("path", "")), str(args.get("content", "")))
            return json.dumps({"appended": True})
        if name == "copy_path":
            dest = svc.copy_path(
                str(args.get("source", "")), str(args.get("destination", ""))
            )
            return json.dumps({"copied_to": dest})
        if name == "search_files":
            return json.dumps(
                svc.search_files(
                    str(args.get("root", "")), str(args.get("pattern", "*"))
                ),
                ensure_ascii=False,
            )
        if name == "zip_paths":
            sources = [str(s) for s in args.get("sources") or []]
            dest = svc.zip_paths(sources, str(args.get("destination", "")))
            return json.dumps({"zip": dest})
        if name == "unzip":
            dest = svc.unzip(
                str(args.get("source", "")), str(args.get("destination", ""))
            )
            return json.dumps({"extracted_to": dest})
        if name == "clipboard_get":
            return json.dumps({"text": svc.clipboard_get()[:6000]}, ensure_ascii=False)
        if name == "clipboard_set":
            return json.dumps({"set": svc.clipboard_set(str(args.get("text", "")))})
        if name == "screenshot":
            path = args.get("path")
            return json.dumps(
                svc.screenshot(str(path) if path else None), ensure_ascii=False
            )
        if name == "http_get":
            return json.dumps(svc.http_get(str(args.get("url", ""))), ensure_ascii=False)
        if name == "download_file":
            dest = svc.download_file(
                str(args.get("url", "")), str(args.get("destination", ""))
            )
            return json.dumps({"saved": dest})
        if name == "system_info":
            return json.dumps(svc.system_info(), ensure_ascii=False)
        if name == "list_processes":
            return json.dumps(svc.list_processes(), ensure_ascii=False)
        if name == "lock_screen":
            return json.dumps({"locked": svc.lock_screen()})
        if name == "get_weather":
            try:
                return json.dumps(
                    svc.get_weather(
                        str(args.get("city", "")), int(args.get("days", 3))
                    ),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "read_pdf":
            try:
                return json.dumps(
                    svc.read_pdf(
                        str(args.get("path", "")), int(args.get("max_pages", 40))
                    ),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "read_pptx":
            from app.services.pptx_service import get_pptx_service

            try:
                return json.dumps(
                    get_pptx_service().read(
                        str(args.get("path", "")), int(args.get("max_slides", 60))
                    ),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "journal":
            return json.dumps(
                persona.append_journal(str(args.get("entry", ""))), ensure_ascii=False
            )
        if name == "read_journal":
            return json.dumps(
                {"memory": persona.read_memory_file()}, ensure_ascii=False
            )
        if name == "remember_about_user":
            return json.dumps(
                persona.remember_about_user(str(args.get("note", ""))),
                ensure_ascii=False,
            )
        if name == "set_mood":
            return json.dumps(persona.set_mood(str(args.get("mood", ""))), ensure_ascii=False)
        tt = get_timetravel_service()
        if name == "snapshot":
            return json.dumps(
                tt.snapshot(
                    str(args.get("label", "")),
                    str(args.get("workspace", "")) or None,
                    str(args.get("note", "")),
                    kind="manual",
                ),
                ensure_ascii=False,
            )
        if name == "list_snapshots":
            return json.dumps(tt.list(), ensure_ascii=False)
        if name == "restore_snapshot":
            try:
                return json.dumps(
                    tt.restore(str(args.get("id", ""))), ensure_ascii=False
                )
            except ValueError as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        skl = self._skills
        if name == "list_skills":
            return json.dumps(skl.list(), ensure_ascii=False)
        if name == "read_skill":
            try:
                return json.dumps(skl.read(str(args.get("name", ""))), ensure_ascii=False)
            except FileNotFoundError:
                return json.dumps({"error": "Skill nicht gefunden"})
        if name == "read_skill_file":
            try:
                return json.dumps(
                    skl.read_file(
                        str(args.get("name", "")), str(args.get("file", ""))
                    ),
                    ensure_ascii=False,
                )
            except FileNotFoundError:
                return json.dumps({"error": "Wissensdatei nicht gefunden"})
            except ValueError as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "write_skill":
            return json.dumps(
                skl.write(str(args.get("name", "")), str(args.get("content", ""))),
                ensure_ascii=False,
            )
        mem = self._memory
        if name == "remember":
            return json.dumps(
                mem.add(str(args.get("content", "")), source="chat"),
                ensure_ascii=False,
            )
        if name == "recall":
            query = str(args.get("query", "")).strip()
            items = mem.search(query) if query else mem.list()
            return json.dumps(items, ensure_ascii=False)
        if name == "forget":
            return json.dumps(
                {"removed": mem.forget(str(args.get("query", "")))},
                ensure_ascii=False,
            )
        rem = self._reminders
        if name == "set_reminder":
            return json.dumps(
                rem.add(
                    str(args.get("text", "")),
                    str(args.get("time", "")),
                    str(args.get("repeat", "daily")),
                    str(args.get("phone", "")),
                ),
                ensure_ascii=False,
            )
        if name == "list_reminders":
            return json.dumps(rem.list(), ensure_ascii=False)
        knowledge = get_knowledge_service()
        if name == "learn_document":
            path = str(args.get("path", "")).strip()
            text = str(args.get("text", "")).strip()
            title = str(args.get("title", "")).strip()
            if path:
                return json.dumps(knowledge.learn_path(path), ensure_ascii=False)
            if text:
                return json.dumps(
                    knowledge.learn_text(text, title), ensure_ascii=False
                )
            return json.dumps({"error": "path oder text angeben"})
        if name == "ask_knowledge":
            return json.dumps(
                knowledge.search(
                    str(args.get("query", "")), int(args.get("max_results", 6))
                ),
                ensure_ascii=False,
            )
        if name == "list_documents":
            return json.dumps(knowledge.list(), ensure_ascii=False)
        if name == "forget_document":
            return json.dumps(
                {"removed": knowledge.forget(str(args.get("ref", "")))},
                ensure_ascii=False,
            )
        if name == "clipboard_history":
            return json.dumps(
                get_clipboard_service().list(
                    str(args.get("query", "")), int(args.get("limit", 20))
                ),
                ensure_ascii=False,
            )
        tasks = get_task_service()
        if name == "add_task":
            return json.dumps(
                tasks.add(
                    str(args.get("task", "")),
                    str(args.get("time", "")),
                    str(args.get("repeat", "daily")),
                ),
                ensure_ascii=False,
            )
        if name == "list_tasks":
            return json.dumps(tasks.list(), ensure_ascii=False)
        if name == "delete_task":
            return json.dumps({"deleted": tasks.delete(str(args.get("id", "")))})
        capsules = get_capsule_service()
        if name == "time_capsule":
            return json.dumps(
                capsules.add(str(args.get("text", "")), str(args.get("date", ""))),
                ensure_ascii=False,
            )
        if name == "list_capsules":
            return json.dumps(capsules.list(), ensure_ascii=False)
        if name in ("check_mail", "read_mail", "send_mail", "get_calendar"):
            from app.services.mail_service import get_mail_service

            mail = get_mail_service()
            try:
                if name == "check_mail":
                    return json.dumps(
                        mail.check_mail(int(args.get("limit", 10))),
                        ensure_ascii=False,
                    )
                if name == "read_mail":
                    return json.dumps(
                        mail.read_mail(str(args.get("id", ""))), ensure_ascii=False
                    )
                if name == "send_mail":
                    return json.dumps(
                        mail.send_mail(
                            str(args.get("to", "")),
                            str(args.get("subject", "")),
                            str(args.get("body", "")),
                        ),
                        ensure_ascii=False,
                    )
                return json.dumps(
                    mail.calendar_events(int(args.get("days", 7))),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "media_control":
            try:
                return json.dumps(
                    svc.media_control(
                        str(args.get("action", "")), int(args.get("times", 1))
                    )
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name in ("add_watcher", "list_watchers", "delete_watcher"):
            from app.services.watcher_service import get_watcher_service

            watchers = get_watcher_service()
            if name == "add_watcher":
                return json.dumps(
                    watchers.add(
                        str(args.get("path", "")), str(args.get("task", ""))
                    ),
                    ensure_ascii=False,
                )
            if name == "list_watchers":
                return json.dumps(watchers.list(), ensure_ascii=False)
            return json.dumps({"deleted": watchers.delete(str(args.get("id", "")))})
        if name in ("smarthome_devices", "smarthome_control"):
            from app.services.homeassistant_service import get_homeassistant_service

            ha = get_homeassistant_service()
            try:
                if name == "smarthome_devices":
                    return json.dumps(ha.devices(), ensure_ascii=False)
                value = args.get("value")
                return json.dumps(
                    ha.control(
                        str(args.get("entity_id", "")),
                        str(args.get("action", "")),
                        float(value) if value is not None else None,
                    ),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "scan_network":
            try:
                return json.dumps(svc.scan_network(), ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "wake_device":
            try:
                return json.dumps(svc.wake_on_lan(str(args.get("mac", ""))))
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "list_printers":
            try:
                return json.dumps(svc.list_printers(), ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "print_file":
            try:
                return json.dumps(
                    svc.print_file(
                        str(args.get("path", "")), str(args.get("printer", ""))
                    ),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name.startswith("amazon_"):
            from app.services.amazon_music_service import get_amazon_music_service

            amazon = get_amazon_music_service()
            try:
                if name == "amazon_play":
                    return json.dumps(
                        amazon.play(str(args.get("query", ""))), ensure_ascii=False
                    )
                return json.dumps(amazon.now_playing(), ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name.startswith("spotify_"):
            from app.services.spotify_service import get_spotify_service

            spotify = get_spotify_service()
            try:
                if name == "spotify_play":
                    return json.dumps(
                        spotify.play(
                            str(args.get("query", "")),
                            str(args.get("kind", "track")),
                        ),
                        ensure_ascii=False,
                    )
                if name == "spotify_search":
                    return json.dumps(
                        spotify.search(
                            str(args.get("query", "")),
                            str(args.get("kind", "track")),
                            int(args.get("limit", 5)),
                        ),
                        ensure_ascii=False,
                    )
                if name == "spotify_now_playing":
                    return json.dumps(spotify.now_playing(), ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        return json.dumps({"error": f"unbekanntes Tool: {name}"})
