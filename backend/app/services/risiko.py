from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.services.browser.sicherheit import HOCH, MITTEL, NIEDRIG, RANG

LESEN = "lesen"
AENDERN = "aendern"
EXTERN = "extern"
ZERSTOEREND = "zerstoerend"

LESE_TOOLS = {
    "get_screen_info",
    "list_windows",
    "wait",
    "recall",
    "system_info",
    "list_processes",
    "list_skills",
    "read_skill",
    "read_skill_file",
    "list_reminders",
    "list_alarms",
    "list_scheduled_calls",
    "web_search",
    "get_weather",
    "read_journal",
    "list_snapshots",
    "recall_screen",
    "ask_knowledge",
    "list_documents",
    "clipboard_history",
    "clipboard_get",
    "list_tasks",
    "list_capsules",
    "check_mail",
    "read_mail",
    "get_calendar",
    "list_watchers",
    "smarthome_devices",
    "scan_network",
    "list_printers",
    "spotify_search",
    "spotify_now_playing",
    "amazon_now_playing",
    "list_friends",
    "read_friend_messages",
    "calendar_list",
    "calendar_search",
    "read_pdf",
    "read_pptx",
    "maps",
    "look_at_image",
    "list_dir",
    "read_file",
    "search_files",
    "project_overview",
    "git_status",
    "git_diff",
    "http_get",
    "screenshot",
    "list_timers",
    "android_devices",
    "android_device_status",
    "android_battery_status",
    "android_files_list",
    "browser_read",
    "browser_screenshot",
    "browser_status",
    "verlauf_heute",
    "was_war",
    "ziele",
    "selbstbild",
}

EXTERNE_TOOLS = {
    "send_mail",
    "send_friend_message",
    "call_user",
    "schedule_call",
    "print_file",
    "telegram_send",
}

ZERSTOERENDE_TOOLS = {
    "delete_path",
    "forget",
    "forget_document",
    "clear_memory",
    "restore_snapshot",
    "kill_program",
    "delete_watcher",
    "uninstall",
}

SYSTEM_PFADE = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata\\microsoft",
    "c:\\$recycle.bin",
    "c:\\system volume information",
    "/etc",
    "/bin",
    "/usr/bin",
    "/boot",
    "/sys",
    "/proc",
)

GEFAEHRLICHE_BEFEHLE = (
    re.compile(r"(?i)remove-item[^\n]*-recurse[^\n]*-force"),
    re.compile(r"(?i)\brd\s+/s\b|\brmdir\s+/s\b"),
    re.compile(r"(?i)\bdel\s+/[sq]\b"),
    re.compile(r"(?i)\bformat\s+[a-z]:"),
    re.compile(r"(?i)\bdiskpart\b"),
    re.compile(r"(?i)\bStop-Computer\b|\bRestart-Computer\b|\bshutdown\b"),
    re.compile(r"(?i)\breg\s+delete\b|\bRemove-ItemProperty\b"),
    re.compile(r"(?i)\brm\s+-rf\b"),
    re.compile(r"(?i)\bmkfs\b|\bdd\s+if=.*of=/dev/"),
    re.compile(r"(?i)Set-ExecutionPolicy|Disable-.*Firewall|Set-MpPreference"),
    re.compile(r"(?i)net\s+user\s+\S+\s+/(add|delete)"),
    re.compile(r"(?i)\bcipher\s+/w\b|\bsdelete\b"),
)

PFAD_FELDER = ("path", "source", "destination", "root", "workspace", "file", "datei")


@dataclass
class Stufe:
    risiko: str
    art: str
    grund: str

    @property
    def braucht_bestaetigung(self) -> bool:
        return self.risiko == HOCH

    def als_dict(self) -> dict:
        return {"risiko": self.risiko, "art": self.art, "grund": self.grund}


def _heimat() -> Path:
    return Path.home().resolve()


def _texte(args: dict) -> list[str]:
    werte: list[str] = []
    for feld in PFAD_FELDER:
        wert = args.get(feld)
        if isinstance(wert, str) and wert.strip():
            werte.append(wert)
    sammlung = args.get("sources") or args.get("paths")
    if isinstance(sammlung, list):
        werte.extend(str(w) for w in sammlung if isinstance(w, str))
    return werte


def system_pfad(pfad: str) -> bool:
    roh = str(pfad or "").strip().strip('"').strip("'")
    if not roh:
        return False
    try:
        aufgeloest = str(Path(os.path.expandvars(roh)).expanduser()).lower()
    except Exception:
        aufgeloest = roh.lower()
    aufgeloest = aufgeloest.replace("/", "\\") if ":" in aufgeloest else aufgeloest
    for verboten in SYSTEM_PFADE:
        if aufgeloest.startswith(verboten):
            return True
    if re.fullmatch(r"[a-z]:\\?", aufgeloest):
        return True
    if aufgeloest in ("/", "\\"):
        return True
    return False


def ausserhalb_heimat(pfad: str) -> bool:
    roh = str(pfad or "").strip().strip('"').strip("'")
    if not roh:
        return False
    try:
        ziel = Path(os.path.expandvars(roh)).expanduser().resolve()
    except Exception:
        return False
    heim = _heimat()
    return ziel != heim and heim not in ziel.parents


def pfad_pruefen(name: str, args: dict) -> str:
    if name not in ZERSTOERENDE_TOOLS and name not in {
        "write_file",
        "edit_file",
        "append_file",
        "move_path",
        "make_dir",
        "unzip",
        "download_file",
    }:
        return ""
    for wert in _texte(args):
        if system_pfad(wert):
            return (
                f"Geschuetzter Systempfad: {wert}. Jon veraendert nichts in Windows-, "
                "Programm- oder Systemordnern."
            )
    return ""


def _befehl_gefaehrlich(befehl: str) -> str:
    for muster in GEFAEHRLICHE_BEFEHLE:
        treffer = muster.search(befehl or "")
        if treffer:
            return treffer.group(0)[:80]
    return ""


def bewerten(name: str, args: dict | None = None) -> Stufe:
    werte = dict(args or {})
    werkzeug = str(name or "")

    if werkzeug.startswith("browser_"):
        from app.services.browser.sicherheit import get_guard
        from app.services.browser.zustand import get_zustand

        op = werkzeug.removeprefix("browser_")
        if op == "task":
            return Stufe(MITTEL, AENDERN, "Browser-Agent arbeitet selbstaendig.")
        if op == "confirm":
            return Stufe(HOCH, EXTERN, "Gibt eine kritische Browser-Aktion frei.")
        zustand = get_zustand().lesen()
        ziel = str(werte.get("element") or werte.get("target") or "")
        bewertung = get_guard().bewerten(op, werte, url=zustand.url, ziel=ziel)
        return Stufe(bewertung.risiko, bewertung.art, bewertung.grund)

    if werkzeug in ("run_powershell", "run_cmd"):
        befehl = str(werte.get("command", ""))
        treffer = _befehl_gefaehrlich(befehl)
        if treffer:
            return Stufe(HOCH, ZERSTOEREND, f"Gefaehrlicher Befehl: {treffer}")
        return Stufe(MITTEL, AENDERN, "Fuehrt einen Befehl auf dem PC aus.")

    if werkzeug in EXTERNE_TOOLS:
        return Stufe(HOCH, EXTERN, "Schickt etwas nach aussen und ist kaum umkehrbar.")

    if werkzeug in ZERSTOERENDE_TOOLS:
        for wert in _texte(werte):
            if system_pfad(wert):
                return Stufe(HOCH, ZERSTOEREND, f"Systempfad betroffen: {wert}")
            if ausserhalb_heimat(wert):
                return Stufe(
                    HOCH, ZERSTOEREND, f"Loeschen ausserhalb deines Benutzerordners: {wert}"
                )
        return Stufe(HOCH, ZERSTOEREND, "Loescht oder verwirft Daten.")

    if werkzeug in LESE_TOOLS:
        return Stufe(NIEDRIG, LESEN, "Nur lesend.")

    if werkzeug in ("write_file", "edit_file", "append_file", "move_path", "copy_path"):
        for wert in _texte(werte):
            if system_pfad(wert):
                return Stufe(HOCH, ZERSTOEREND, f"Systempfad betroffen: {wert}")
        return Stufe(MITTEL, AENDERN, "Aendert Dateien.")

    if werkzeug.startswith("calendar_") or werkzeug.startswith("android_"):
        return Stufe(MITTEL, AENDERN, "Aendert Daten.")

    return Stufe(MITTEL, AENDERN, "Veraendernde Aktion.")


def braucht_freigabe(name: str, args: dict | None, nachfragen: bool) -> bool:
    stufe = bewerten(name, args)
    if stufe.risiko == HOCH:
        return True
    if stufe.risiko == NIEDRIG:
        return False
    return nachfragen


def hoechste(stufen: list[Stufe]) -> str:
    ergebnis = NIEDRIG
    for stufe in stufen:
        if RANG[stufe.risiko] > RANG[ergebnis]:
            ergebnis = stufe.risiko
    return ergebnis
