from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.services.automation_service import AutomationService
from app.services.capsule_service import get_capsule_service
from app.services.clipboard_service import get_clipboard_service
from app.services.knowledge_service import get_knowledge_service
from app.services.memory_service import MemoryService
from app.services.persona_service import get_persona_service
from app.services.reminder_service import ReminderService
from app.services.skill_service import SkillService
from app.services.system_service import SystemService
from app.services.task_service import get_task_service
from app.services.timetravel_service import get_timetravel_service

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
    "calendar_list",
    "calendar_search",
}


CORE_TOOLS = {
    "run_powershell",
    "run_cmd",
    "open_url",
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
}

TOOL_GROUPS: dict[str, tuple[set[str], tuple[str, ...]]] = {
    "browser": (
        {
            "browser_goto",
            "browser_click",
            "browser_fill",
            "browser_read",
            "browser_screenshot",
            "browser_back",
            "browser_close",
        },
        (
            "browser",
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
            "google",
            "amazon",
            "ebay",
            "youtube",
            "geh auf",
            "geh zu",
            "surf",
            "such auf",
            "seite",
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
            "eintrag",
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
    "timeline": (
        {"recall_screen"},
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
    "calendar": (
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


def select_tools(context: str) -> set[str] | None:
    text = context.strip().lower()
    if not text:
        return None
    allowed = set(CORE_TOOLS)
    for names, keywords in TOOL_GROUPS.values():
        if any(word in text for word in keywords):
            allowed |= names
    return allowed


def _shorten(value: Any, limit: int = 120) -> str:
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def describe_tool(name: str, args: dict[str, Any]) -> str:
    if name == "run_powershell":
        return "Führt einen PowerShell-Befehl auf deinem PC aus."
    if name == "run_cmd":
        return "Führt einen CMD-Befehl auf deinem PC aus."
    if name == "open_url":
        return f"Öffnet {_shorten(args.get('url', 'eine URL'))} im Browser."
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
        return f"Stellt einen Windows-Wecker ({when}): {_shorten(args.get('label', ''))}"
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
    if name == "browser_goto":
        return f"Öffnet im Jon-Browser: {_shorten(args.get('url', ''))}"
    if name == "browser_click":
        return f"Klickt im Browser auf: {_shorten(args.get('target', ''))}"
    if name == "browser_fill":
        return (
            f"Füllt im Browser {_shorten(args.get('target', ''))} aus: "
            f"{_shorten(args.get('text', ''))}"
        )
    if name == "browser_read":
        return "Liest die aktuelle Browser-Seite."
    if name == "browser_screenshot":
        return "Macht einen Screenshot der Browser-Seite."
    if name == "browser_back":
        return "Geht im Browser eine Seite zurück."
    if name == "browser_close":
        return "Schließt den Jon-Browser."
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

    def _guard_args(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        guarded = dict(args)
        for key in ("path", "source", "destination", "root", "workspace"):
            if guarded.get(key):
                guarded[key] = self._guard_path(guarded[key])
        if isinstance(guarded.get("sources"), list):
            guarded["sources"] = [self._guard_path(s) for s in guarded["sources"]]
        if name == "run_powershell" and guarded.get("command"):
            guarded["command"] = (
                f'Set-Location -LiteralPath "{self._root}"; ' + str(guarded["command"])
            )
        if name == "run_cmd" and guarded.get("command"):
            guarded["command"] = f'cd /d "{self._root}" && ' + str(guarded["command"])
        return guarded

    def schema(self, context: str = "") -> list[dict]:
        tools = self._all_tools()
        allowed = select_tools(context)
        if allowed is None:
            return tools
        return [t for t in tools if t["function"]["name"] in allowed]

    def _all_tools(self) -> list[dict]:
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
                "Fuehrt einen Windows-CMD-Befehl aus.",
                {"command": _STR},
                ["command"],
            ),
            _tool(
                "open_url",
                "Oeffnet eine URL im Standardbrowser.",
                {"url": _STR},
                ["url"],
            ),
            _tool(
                "start_program",
                "Startet ein Programm oder eine .exe.",
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
                "browser_goto",
                "Oeffnet eine URL in Jons eigenem sichtbarem Browser-Fenster "
                "(Playwright/Chromium). Die Session bleibt zwischen Aufrufen offen. "
                "Nutze danach browser_read, um die Seite zu verstehen.",
                {"url": _STR},
                ["url"],
            ),
            _tool(
                "browser_click",
                "Klickt im Jon-Browser auf ein Element. target ist ein Selektor "
                "aus browser_read ODER sichtbarer Text (z.B. 'Anmelden').",
                {"target": _STR},
                ["target"],
            ),
            _tool(
                "browser_fill",
                "Fuellt im Jon-Browser ein Eingabefeld aus. target ist ein Selektor "
                "aus browser_read ODER die sichtbare Beschriftung des Felds. "
                "press_enter=true drueckt danach Enter.",
                {"target": _STR, "text": _STR, "press_enter": _BOOL},
                ["target", "text"],
            ),
            _tool(
                "browser_read",
                "Liest die aktuelle Seite im Jon-Browser: Titel, URL, sichtbarer "
                "Text und interaktive Elemente (Links, Buttons, Eingabefelder) mit "
                "stabilen Selektoren zum gezielten Klicken.",
                {},
                [],
            ),
            _tool(
                "browser_screenshot",
                "Macht einen Screenshot der aktuellen Browser-Seite und liefert "
                "den Dateipfad.",
                {},
                [],
            ),
            _tool(
                "browser_back",
                "Geht im Jon-Browser eine Seite zurueck.",
                {},
                [],
            ),
            _tool(
                "browser_close",
                "Schliesst das Jon-Browser-Fenster und beendet die Session.",
                {},
                [],
            ),
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
                "Stellt einen echten Windows-Wecker mit Klingelton und Popup, der "
                "auch klingelt, wenn Jon geschlossen ist. Nutze das bei 'Stelle einen "
                "Wecker fuer 07:00' (time='07:00') oder 'Timer 10 Minuten' "
                "(in_minutes=10). Liegt die Uhrzeit heute in der Vergangenheit, "
                "klingelt der Wecker morgen.",
                {
                    "label": _STR,
                    "time": {"type": "string", "description": "HH:MM (24h)"},
                    "in_minutes": _NUM,
                },
                ["label"],
            ),
            _tool(
                "list_alarms",
                "Listet alle gestellten Windows-Wecker mit Name, Beschriftung und "
                "Klingelzeit auf.",
                {},
                [],
            ),
            _tool(
                "delete_alarm",
                "Loescht einen gestellten Windows-Wecker anhand seines Namens "
                "(JonWecker_...). Rufe vorher list_alarms auf.",
                {"name": _STR},
                ["name"],
            ),
            _tool(
                "web_search",
                "Sucht im Internet (DuckDuckGo) und liefert Titel, URL und "
                "Beschreibung der Treffer. Nutze das fuer aktuelle Infos wie News, "
                "Preise, Oeffnungszeiten oder Fakten, die du nicht sicher weisst. "
                "Oeffne bei Bedarf einen Treffer mit http_get fuer Details.",
                {"query": _STR, "max_results": _INT},
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
                "recall_screen",
                "Durchsucht das lokale Bildschirm-Gedaechtnis (Bildschirm-Zeitreise) "
                "danach, was der Nutzer frueher offen hatte ('Was hatte ich Dienstag "
                "zu Grafikkarten offen?'). query = Suchbegriffe, day = optional "
                "Datum als YYYY-MM-DD.",
                {"query": _STR, "day": _STR},
                [],
            ),
        ]

    async def execute(
        self, name: str, args: dict[str, Any], source: str | None = None
    ) -> str:
        from app.services.action_log_service import log_action

        src = source or self._source
        try:
            result = await self._dispatch(name, args)
        except Exception as exc:
            log_action(src, name, args, f"Fehler: {exc}", ok=False)
            raise
        log_action(src, name, args, result, ok='"error"' not in result[:200])
        return result

    async def _dispatch(self, name: str, args: dict[str, Any]) -> str:
        if name == "webcam_look":
            from app.services.webcam_service import get_webcam_service

            result = await get_webcam_service().describe(
                str(args.get("question", ""))
            )
            return json.dumps(result, ensure_ascii=False)
        if name in ("list_friends", "send_friend_message", "read_friend_messages"):
            return await self._friends(name, args)
        return await asyncio.to_thread(self._execute, name, args)

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

    def _execute(self, name: str, args: dict[str, Any]) -> str:
        if self._root:
            try:
                args = self._guard_args(name, args)
            except PermissionError as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name.startswith("browser_"):
            from app.services.browser_service import get_browser_service

            op = name.removeprefix("browser_")
            return get_browser_service().call(op, args)
        if name.startswith("calendar_"):
            return self._calendar(name, args)
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
            return json.dumps({"opened": svc.open_url(str(args.get("url", "")))})
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
        if name == "set_alarm":
            try:
                minutes = args.get("in_minutes")
                return json.dumps(
                    svc.set_alarm(
                        str(args.get("label", "") or args.get("text", "")),
                        str(args.get("time", "") or ""),
                        float(minutes) if minutes is not None else None,
                    ),
                    ensure_ascii=False,
                )
            except (ValueError, RuntimeError) as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "list_alarms":
            return json.dumps(svc.list_alarms(), ensure_ascii=False)
        if name == "delete_alarm":
            try:
                return json.dumps({"deleted": svc.delete_alarm(str(args.get("name", "")))})
            except ValueError as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
        if name == "web_search":
            try:
                return json.dumps(
                    svc.web_search(
                        str(args.get("query", "")),
                        int(args.get("max_results", 6)),
                    ),
                    ensure_ascii=False,
                )
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
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
        persona = get_persona_service()
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
