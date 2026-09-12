from __future__ import annotations

import re
from pathlib import Path

ADRESSE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)
DOMAIN = re.compile(
    r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)+(/\S*)?$", re.IGNORECASE
)
NICHT_WEB = {"exe", "bat", "cmd", "ps1", "msi", "lnk", "py", "sh", "app"}
SYSTEMPROGRAMME = {"command.com", "ftp.com", "more.com", "tree.com"}

PS_START = re.compile(
    r"^\s*(?:start-process|saps)\s+(?:-filepath\s+)?(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)
CMD_START = re.compile(
    r"^\s*start\s+(?:\"[^\"]*\"\s+)?(?P<rest>.+?)\s*$", re.IGNORECASE
)
EXPLORER = re.compile(r"^\s*explorer(?:\.exe)?\s+(?P<rest>.+?)\s*$", re.IGNORECASE)
PROTOKOLL = re.compile(
    r"rundll32(?:\.exe)?\s+url\.dll\s*,\s*FileProtocolHandler\s+(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)
KETTE = re.compile(r"[;&|]{1,2}|\$\(|`|\n")

BROWSER_NAMEN = {
    "chrome": "chrome",
    "chrome.exe": "chrome",
    "googlechrome": "chrome",
    "msedge": "edge",
    "msedge.exe": "edge",
    "microsoft-edge": "edge",
    "edge": "edge",
    "firefox": "firefox",
    "firefox.exe": "firefox",
    "brave": "brave",
    "brave.exe": "brave",
    "opera": "opera",
    "opera.exe": "opera",
    "vivaldi": "vivaldi",
    "vivaldi.exe": "vivaldi",
    "iexplore": "system",
    "start": "system",
}


def _entkleiden(wert: str) -> str:
    text = str(wert or "").strip()
    for zeichen in ('"', "'"):
        if len(text) > 1 and text.startswith(zeichen) and text.endswith(zeichen):
            text = text[1:-1].strip()
    return text


def ist_adresse(wert: str) -> bool:
    text = _entkleiden(wert)
    if not text or " " in text:
        return bool(ADRESSE.match(text))
    if ADRESSE.match(text):
        return True
    if text.startswith(("file:", "ms-settings:", "mailto:", "tel:")):
        return False
    if "." not in text or "\\" in text:
        return False
    if Path(text).suffix.lower().lstrip(".") in NICHT_WEB:
        return False
    if text.lower() in SYSTEMPROGRAMME:
        return False
    if not DOMAIN.match(text):
        return False
    try:
        return not Path(text).expanduser().exists()
    except OSError:
        return True


def _browser_aus(wert: str) -> str:
    name = Path(_entkleiden(wert)).name.lower()
    return BROWSER_NAMEN.get(name, "")


def _teile(rest: str) -> list[str]:
    return [t for t in re.findall(r'"[^"]*"|\S+', rest) if t.strip()]


def _aus_befehl(befehl: str) -> tuple[str, str] | None:
    text = str(befehl or "").strip()
    if not text or KETTE.search(text):
        return None
    for muster in (PROTOKOLL, PS_START, CMD_START, EXPLORER):
        treffer = muster.search(text)
        if not treffer:
            continue
        teile = _teile(treffer.group("rest"))
        if not teile:
            continue
        browser = ""
        erste = _entkleiden(teile[0])
        if not ist_adresse(erste):
            browser = _browser_aus(erste)
            if not browser:
                return None
            teile = teile[1:]
        for teil in teile:
            wert = _entkleiden(teil)
            if wert.lower().startswith("-argumentlist"):
                continue
            if ist_adresse(wert):
                return wert, browser
        return None
    return None


def pruefen(werkzeug: str, args: dict) -> tuple[str, str] | None:
    werte = args or {}
    if werkzeug == "start_program":
        pfad = _entkleiden(str(werte.get("path", "")))
        if ist_adresse(pfad):
            return pfad, ""
        browser = _browser_aus(pfad)
        if browser:
            for teil in werte.get("args") or []:
                wert = _entkleiden(str(teil))
                if ist_adresse(wert):
                    return wert, browser
        return None
    if werkzeug in ("run_powershell", "run_cmd"):
        return _aus_befehl(str(werte.get("command", "")))
    return None


def umleiten(werkzeug: str, args: dict) -> dict | None:
    treffer = pruefen(werkzeug, args)
    if treffer is None:
        return None
    adresse, browser = treffer
    from app.services.browserwahl import name as browsername
    from app.services.browserwahl import oeffnen, wahl

    ergebnis = oeffnen(adresse, browser)
    gewaehlt = browser or wahl()
    ergebnis["umgeleitet_von"] = werkzeug
    ergebnis["hinweis"] = (
        f"Die Adresse wurde in {browsername(gewaehlt)} geoeffnet"
        + (
            " - so hat der Nutzer es eingestellt."
            if not browser
            else " - so hat der Nutzer es verlangt."
        )
    )
    return ergebnis
