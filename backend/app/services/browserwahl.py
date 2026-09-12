from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

from app.core.fehler import leise

JON = "jon"
SYSTEM = "system"

BEKANNTE = {
    "chrome": (
        "chrome",
        [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "google-chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ],
    ),
    "edge": (
        "msedge",
        [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "microsoft-edge",
        ],
    ),
    "firefox": (
        "firefox",
        [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            "firefox",
            "/Applications/Firefox.app/Contents/MacOS/firefox",
        ],
    ),
    "brave": (
        "brave",
        [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            "brave-browser",
        ],
    ),
    "opera": ("opera", [r"C:\Program Files\Opera\opera.exe", "opera"]),
    "vivaldi": (
        "vivaldi",
        [r"C:\Program Files\Vivaldi\Application\vivaldi.exe", "vivaldi"],
    ),
}

TITEL = {
    JON: "Jon-Browser",
    SYSTEM: "Standardbrowser",
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "firefox": "Firefox",
    "brave": "Brave",
    "opera": "Opera",
    "vivaldi": "Vivaldi",
}


WOERTER = {
    "jon": JON,
    "jonbrowser": JON,
    "jons": JON,
    "eigener": JON,
    "eigenen": JON,
    "intern": JON,
    "standard": SYSTEM,
    "standardbrowser": SYSTEM,
    "system": SYSTEM,
    "systembrowser": SYSTEM,
    "chrome": "chrome",
    "googlechrome": "chrome",
    "google": "chrome",
    "edge": "edge",
    "microsoftedge": "edge",
    "msedge": "edge",
    "firefox": "firefox",
    "mozilla": "firefox",
    "brave": "brave",
    "bravebrowser": "brave",
    "opera": "opera",
    "vivaldi": "vivaldi",
}


def aufloesen(wunsch: str) -> str:
    roh = str(wunsch or "").strip().lower()
    if not roh:
        return ""
    schlicht = "".join(z for z in roh if z.isalnum())
    if schlicht in WOERTER:
        return WOERTER[schlicht]
    for wort, schluessel in WOERTER.items():
        if wort in schlicht and len(wort) >= 4:
            return schluessel
    return ""


def wahl() -> str:
    try:
        from app.services.settings_service import get_settings_service

        wert = str(get_settings_service().get().get("web_browser", JON)).strip()
    except Exception as _fehler:
        leise(_fehler, "services/browserwahl")
        wert = JON
    return wert or JON


def name(wert: str = "") -> str:
    schluessel = wert or wahl()
    return TITEL.get(schluessel, Path(schluessel).stem or schluessel)


def nutzt_jon() -> bool:
    return wahl().lower() == JON


def _pfad(schluessel: str) -> str:
    eintrag = BEKANNTE.get(schluessel.lower())
    if eintrag is None:
        return schluessel if Path(schluessel).exists() else ""
    befehl, kandidaten = eintrag
    gefunden = shutil.which(befehl)
    if gefunden:
        return gefunden
    for kandidat in kandidaten:
        erweitert = os.path.expandvars(kandidat)
        if Path(erweitert).exists():
            return erweitert
        gefunden = shutil.which(kandidat)
        if gefunden:
            return gefunden
    return ""


def verfuegbare() -> list[dict]:
    liste = [
        {"wert": JON, "name": TITEL[JON], "da": True},
        {"wert": SYSTEM, "name": TITEL[SYSTEM], "da": True},
    ]
    for schluessel in BEKANNTE:
        liste.append(
            {
                "wert": schluessel,
                "name": TITEL[schluessel],
                "da": bool(_pfad(schluessel)),
            }
        )
    return liste


def _vollstaendig(url: str) -> str:
    adresse = str(url or "").strip()
    if not adresse:
        return ""
    if not adresse.startswith(("http://", "https://", "file://", "ms-settings:")):
        adresse = "https://" + adresse
    return adresse


def oeffnen(url: str, erzwinge: str = "") -> dict:
    adresse = _vollstaendig(url)
    if not adresse:
        return {"ok": False, "fehler": "Keine Adresse angegeben."}
    schluessel = (aufloesen(erzwinge) or wahl()).lower()

    if schluessel == JON and not adresse.startswith("ms-settings:"):
        from app.services.browser.werkzeuge import ausfuehren

        ergebnis = ausfuehren("goto", {"url": adresse})
        ergebnis["browser"] = TITEL[JON]
        return ergebnis

    if schluessel not in (SYSTEM, JON):
        pfad = _pfad(schluessel)
        if pfad:
            try:
                subprocess.Popen(
                    [pfad, adresse],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    if os.name == "nt"
                    else 0,
                )
                return {"ok": True, "geoeffnet": adresse, "browser": name(schluessel)}
            except Exception as exc:
                leise(exc, "services/browserwahl")
        return {
            "ok": bool(webbrowser.open(adresse)),
            "geoeffnet": adresse,
            "browser": TITEL[SYSTEM],
            "hinweis": f"{name(schluessel)} wurde nicht gefunden - "
            "es lief der Standardbrowser.",
        }

    return {
        "ok": bool(webbrowser.open(adresse)),
        "geoeffnet": adresse,
        "browser": TITEL[SYSTEM],
    }
