from __future__ import annotations

import asyncio
import json
from typing import Any

from app.services.automation_service import AutomationService
from app.services.memory_service import MemoryService
from app.services.reminder_service import ReminderService
from app.services.skill_service import SkillService
from app.services.system_service import SystemService

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
}


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
    ) -> None:
        self._service = service or SystemService()
        self._automation = automation or AutomationService()
        self._memory = memory or MemoryService()
        self._skills = skills or SkillService()
        self._reminders = reminders or ReminderService()

    def schema(self) -> list[dict]:
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
        ]

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        return await asyncio.to_thread(self._execute, name, args)

    def _execute(self, name: str, args: dict[str, Any]) -> str:
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
        return json.dumps({"error": f"unbekanntes Tool: {name}"})
