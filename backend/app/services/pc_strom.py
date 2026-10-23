from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
import time

AKTIONEN = {
    "herunterfahren": "Herunterfahren",
    "neustarten": "Neustart",
    "energiesparen": "Energiesparmodus",
    "ruhezustand": "Ruhezustand",
    "sperren": "Sperren",
    "abmelden": "Abmelden",
    "abbrechen": "Abbrechen",
    "bildschirm_aus": "Bildschirm aus",
}

_geplant: dict = {"aktion": "", "um": 0.0}

MUSTER = [
    ("abbrechen", re.compile(r"\b(nicht\s+(herunter|runter)fahren|herunterfahren\s+abbrechen|shutdown\s+abbrechen|abbrechen.*(herunterfahren|neustart|shutdown)|doch\s+nicht\s+(aus|herunter|runter))", re.I)),
    ("neustarten", re.compile(r"\b(neu\s*starten|neustarten|neustart|restart|reboot|starte?\s+(den\s+|meinen\s+)?(pc|computer|rechner|laptop)\s+neu)\b", re.I)),
    ("herunterfahren", re.compile(r"\b((herunter|runter)\s*fahren|(herunter|runter)fahr|(fahr|fahre|fährst|faehrst)\b[^.!?]{0,50}\b(herunter|runter)\b|schalte?\s+(den\s+|meinen\s+)?(pc|computer|rechner|laptop)\s+aus|(pc|computer|rechner|laptop)\s+aus(schalten)?\b|shut\s*down|ausschalten)", re.I)),
    ("ruhezustand", re.compile(r"\bruhezustand|hibernate\b", re.I)),
    ("energiesparen", re.compile(r"\b(energiespar|standby|stand-by|schlafmodus|sleep|schlafen\s+legen|in\s+den\s+schlaf)", re.I)),
    ("sperren", re.compile(r"\b(sperr(e|en)?\s+(den\s+|meinen\s+)?(pc|computer|rechner|bildschirm|laptop)|(pc|computer|rechner|bildschirm)\s+sperren|lock\s+(the\s+)?(pc|screen))", re.I)),
    ("abmelden", re.compile(r"\b(abmelden|ausloggen|log\s*off|sign\s*out)\b", re.I)),
    ("bildschirm_aus", re.compile(r"\b(bildschirm|monitor|display)\s+(aus|ausschalten|abschalten)\b", re.I)),
]

BEZUG = re.compile(r"\b(pc|computer|rechner|laptop|windows|bildschirm|monitor|display|gerät|geraet|system)\b", re.I)


BEDINGT = re.compile(r"\b(wenn|sobald|nachdem|falls|bevor|wie\s+kann|wie\s+geht|warum|wieso|nicht\s+mehr)\b", re.I)
IN_ZEIT = re.compile(r"\bin\s+(\d{1,3}|einer|einem|einer halben|zwei|drei|fünf|fuenf|zehn|zwanzig|dreissig|dreißig)\s*(sek|sekunde|sekunden|s|min|minute|minuten|std|stunde|stunden|h)\b", re.I)
UM_ZEIT = re.compile(r"\bum\s+(\d{1,2})(?:[:.](\d{2}))?\s*(uhr)?\b", re.I)
ZAHLWORT = {"einer": 1, "einem": 1, "zwei": 2, "drei": 3, "fünf": 5, "fuenf": 5, "zehn": 10, "zwanzig": 20, "dreissig": 30, "dreißig": 30}


def vorlauf(text: str, standard: int = 30) -> int:
    roh = text or ""
    treffer = IN_ZEIT.search(roh)
    if treffer:
        menge_text = treffer.group(1).lower()
        if menge_text == "einer halben":
            menge = 0.5
        else:
            menge = float(ZAHLWORT.get(menge_text, menge_text) if not menge_text.isdigit() else menge_text)
        einheit = treffer.group(2).lower()
        faktor = 3600 if einheit.startswith(("std", "stunde", "h")) else 1 if einheit.startswith("s") else 60
        return int(max(10, min(menge * faktor, 86400)))
    treffer = UM_ZEIT.search(roh)
    if treffer and (treffer.group(3) or treffer.group(2)):
        from datetime import datetime, timedelta

        jetzt = datetime.now()
        stunde = int(treffer.group(1))
        minute = int(treffer.group(2) or 0)
        if stunde > 23 or minute > 59:
            return standard
        ziel = jetzt.replace(hour=stunde, minute=minute, second=0, microsecond=0)
        if ziel <= jetzt:
            ziel += timedelta(days=1)
        return int(max(10, min((ziel - jetzt).total_seconds(), 86400)))
    return standard


def erkennen(text: str) -> str | None:
    roh = (text or "").strip()
    if not roh or len(roh) > 140 or "?" in roh and not re.search(r"\b(kannst|könntest|koenntest)\b", roh, re.I):
        return None
    if BEDINGT.search(roh):
        return None
    for aktion, muster in MUSTER:
        if muster.search(roh):
            if aktion in ("abmelden", "energiesparen", "ruhezustand") and not BEZUG.search(roh) and len(roh.split()) > 3:
                continue
            if aktion in ("herunterfahren", "neustarten") and not BEZUG.search(roh) and len(roh.split()) > 2:
                continue
            return aktion
    return None


def _shutdown(*argumente: str) -> None:
    subprocess.run(["shutdown", *argumente], capture_output=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def ausfuehren(aktion: str, sekunden: int = 30) -> dict:
    aktion = (aktion or "").strip().lower().replace("-", "_")
    ersatz = {"shutdown": "herunterfahren", "aus": "herunterfahren", "restart": "neustarten", "neustart": "neustarten", "sleep": "energiesparen", "standby": "energiesparen", "hibernate": "ruhezustand", "lock": "sperren", "logoff": "abmelden", "cancel": "abbrechen"}
    aktion = ersatz.get(aktion, aktion)
    if aktion not in AKTIONEN:
        return {"error": f"Unbekannte Aktion {aktion}. Moeglich: {', '.join(AKTIONEN)}"}
    sekunden = max(0, min(int(sekunden or 0), 86400))
    if sys.platform != "win32":
        befehle = {
            "herunterfahren": ["shutdown", "-h", f"+{max(1, sekunden // 60)}"] if sekunden >= 60 else ["shutdown", "-h", "now"],
            "neustarten": ["shutdown", "-r", "now"],
            "abbrechen": ["shutdown", "-c"],
            "energiesparen": ["systemctl", "suspend"],
            "ruhezustand": ["systemctl", "hibernate"],
        }
        if aktion not in befehle:
            return {"error": "Das geht auf diesem System nicht."}
        subprocess.run(befehle[aktion], capture_output=True, timeout=15)
        return {"ok": True, "aktion": AKTIONEN[aktion]}
    if aktion == "abbrechen":
        _shutdown("/a")
        war = _geplant.get("aktion")
        _geplant.update(aktion="", um=0.0)
        return {"ok": True, "aktion": "Abgebrochen", "abgebrochen": war or "nichts geplant"}
    if aktion == "herunterfahren":
        _shutdown("/s", "/t", str(sekunden), "/c", "Jon faehrt den PC herunter.")
        _geplant.update(aktion=aktion, um=time.time() + sekunden)
        return {"ok": True, "aktion": "Herunterfahren", "in_sekunden": sekunden, "abbrechen": "pc_strom mit aktion=abbrechen oder /abbrechen"}
    if aktion == "neustarten":
        _shutdown("/r", "/t", str(sekunden), "/c", "Jon startet den PC neu.")
        _geplant.update(aktion=aktion, um=time.time() + sekunden)
        return {"ok": True, "aktion": "Neustart", "in_sekunden": sekunden, "abbrechen": "pc_strom mit aktion=abbrechen oder /abbrechen"}
    if aktion == "abmelden":
        _shutdown("/l")
        return {"ok": True, "aktion": "Abmelden"}
    if aktion == "sperren":
        ctypes.windll.user32.LockWorkStation()
        return {"ok": True, "aktion": "Gesperrt"}
    if aktion == "bildschirm_aus":
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return {"ok": True, "aktion": "Bildschirm aus"}
    ruhe = aktion == "ruhezustand"
    if sekunden:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Sleep -Seconds {sekunden}; Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('{'Hibernate' if ruhe else 'Suspend'}', $false, $false)"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    else:
        ctypes.windll.powrprof.SetSuspendState(bool(ruhe), False, False)
    return {"ok": True, "aktion": AKTIONEN[aktion], "in_sekunden": sekunden}


def dauer(sekunden: int) -> str:
    if sekunden < 90:
        return f"{sekunden} Sekunden"
    if sekunden < 5400:
        return f"{round(sekunden / 60)} Minuten"
    stunden, rest = divmod(sekunden, 3600)
    return f"{stunden} Std. {round(rest / 60)} Min."


def text(ergebnis: dict) -> str:
    if ergebnis.get("error"):
        return f"Das ging nicht: {ergebnis['error']}"
    aktion = ergebnis.get("aktion", "")
    if aktion == "Abgebrochen":
        return "Alles gestoppt. Der PC bleibt an."
    sekunden = int(ergebnis.get("in_sekunden") or 0)
    if aktion in ("Herunterfahren", "Neustart"):
        was = "faehrt herunter" if aktion == "Herunterfahren" else "startet neu"
        return f"Der PC {was} in {dauer(sekunden)}. Mit /abbrechen halte ich das noch auf."
    if aktion == "Energiesparmodus":
        return "Der PC geht in den Energiesparmodus" + (f" in {dauer(sekunden)}." if sekunden else ".")
    if aktion == "Ruhezustand":
        return "Der PC geht in den Ruhezustand" + (f" in {dauer(sekunden)}." if sekunden else ".")
    if aktion == "Gesperrt":
        return "Der PC ist gesperrt."
    if aktion == "Abmelden":
        return "Ich melde dich ab."
    if aktion == "Bildschirm aus":
        return "Der Bildschirm ist aus. Eine Mausbewegung schaltet ihn wieder ein."
    return "Erledigt."


def verfuegbar() -> bool:
    return os.name == "nt" or sys.platform.startswith("linux")
