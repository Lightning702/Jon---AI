from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path

from app.core.fehler import leise

TAKT = 20
WOCHENTAGE = {"montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3, "freitag": 4, "samstag": 5, "sonntag": 6}


def zeit_lesen(zeit: str, datum: str = "", jetzt: datetime | None = None) -> tuple[str, str] | None:
    jetzt = jetzt or datetime.now()
    text = " ".join(str(zeit or "").lower().split())
    tag = str(datum or "").strip()
    if not text and not tag:
        return None
    iso = re.match(r"^(\d{4}-\d{2}-\d{2})[ t](\d{1,2}):(\d{2})", text)
    if iso:
        return f"{int(iso.group(2)):02d}:{iso.group(3)}", iso.group(1)
    spaeter = re.search(r"in\s+(\d+|einer|einem|eine|zwei|drei|fuenf|fünf|zehn|zwanzig|dreissig|dreißig)\s*(minuten|minute|min|stunden|stunde|std|h)\b", text)
    if spaeter:
        zahlen = {"einer": 1, "einem": 1, "eine": 1, "zwei": 2, "drei": 3, "fuenf": 5, "fünf": 5, "zehn": 10, "zwanzig": 20, "dreissig": 30, "dreißig": 30}
        wert = int(spaeter.group(1)) if spaeter.group(1).isdigit() else zahlen[spaeter.group(1)]
        dauer = timedelta(hours=wert) if spaeter.group(2).startswith(("stund", "std", "h")) else timedelta(minutes=wert)
        ziel = jetzt + dauer
        return ziel.strftime("%H:%M"), ziel.strftime("%Y-%m-%d")
    uhr = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(?:uhr|h)?", text)
    if not uhr:
        return None
    stunde = int(uhr.group(1))
    minute = int(uhr.group(2) or 0)
    if ("abend" in text or "nachmittag" in text or "pm" in text) and stunde < 12:
        stunde += 12
    if "halb" in text and not uhr.group(2):
        stunde, minute = (stunde - 1) % 24, 30
    if stunde > 23 or minute > 59:
        return None
    if not tag:
        basis = jetzt.date()
        if "übermorgen" in text or "uebermorgen" in text:
            basis = basis + timedelta(days=2)
        elif "morgen" in text and "morgens" not in text.replace("morgen früh", "morgens"):
            basis = basis + timedelta(days=1)
        else:
            for name, nummer in WOCHENTAGE.items():
                if name in text:
                    abstand = (nummer - basis.weekday()) % 7 or 7
                    basis = basis + timedelta(days=abstand)
                    break
        if basis == jetzt.date() and (stunde, minute) <= (jetzt.hour, jetzt.minute):
            basis = basis + timedelta(days=1)
        tag = basis.isoformat()
    return f"{stunde:02d}:{minute:02d}", tag


def bereit() -> tuple[bool, str]:
    from app.services.settings_service import get_settings_service

    werte = get_settings_service().get()
    if not str(werte.get("telegram_bot_token", "") or "").strip():
        return False, "Telegram ist noch nicht eingerichtet. Trag in den Einstellungen unter Telegram den Bot-Token ein."
    if not str(werte.get("telegram_chat_id", "") or "").strip():
        return False, "Telegram kennt deinen Chat noch nicht. Schreib dem Jon-Bot einmal eine Nachricht, dann kann ich dir schreiben."
    return True, ""


def chat() -> str:
    from app.services.settings_service import get_settings_service

    return str(get_settings_service().get().get("telegram_chat_id", "") or "").strip()


async def senden(text: str) -> dict:
    from app.services.telegram_service import get_telegram_service

    ok, grund = bereit()
    if not ok:
        return {"error": grund}
    try:
        await get_telegram_service().send(chat(), text)
    except Exception as fehler:
        return {"error": f"Telegram hat die Nachricht nicht angenommen: {fehler}"}
    return {"ok": True, "gesendet": True, "text": text}


BILD_ENDUNGEN = (".png", ".jpg", ".jpeg", ".gif", ".webp")
MAX_DATEIEN = 10


def _bildschirmfoto() -> Path:
    from app.core.config import DATA_DIR
    from app.services.system_service import SystemService

    ziel = DATA_DIR / "browser" / f"screenshot-handy-{datetime.now():%Y%m%d-%H%M%S}.png"
    return Path(SystemService().screenshot(str(ziel))["path"])


async def zustellen(text: str = "", pfade: list[str] | None = None, bildschirm: bool = False) -> dict:
    from app.services.dateiraum_service import get_dateiraum_service
    from app.services.telegram_service import get_telegram_service

    ok, grund = bereit()
    if not ok:
        return {"error": grund}
    dateien: list[Path] = []
    for roh in [p for p in (pfade or []) if str(p or "").strip()][:MAX_DATEIEN]:
        pfad = Path(str(roh).strip().strip('"')).expanduser()
        if not pfad.is_file():
            return {"error": f"Diese Datei finde ich nicht: {roh}"}
        erlaubt, warum = get_dateiraum_service().frei(pfad)
        if not erlaubt:
            return {"error": warum}
        dateien.append(pfad)
    if bildschirm:
        try:
            dateien.append(await asyncio.to_thread(_bildschirmfoto))
        except Exception as fehler:
            return {"error": f"Das Bildschirmfoto ging nicht: {fehler}"}
    text = str(text or "").strip()
    if not text and not dateien:
        return {"error": "Sag mir, was ich schicken soll: text, datei oder bildschirm=true."}
    dienst = get_telegram_service()
    geschickt: list[str] = []
    try:
        if text:
            await dienst.send(chat(), text)
        for pfad in dateien:
            art = "bild" if pfad.suffix.lower() in BILD_ENDUNGEN else "datei"
            if not await dienst.send_datei(chat(), {"path": str(pfad), "title": pfad.stem, "kind": art}):
                return {"error": f"Telegram hat {pfad.name} nicht angenommen.", "geschickt": geschickt}
            geschickt.append(pfad.name)
    except Exception as fehler:
        return {"error": f"Telegram hat die Nachricht nicht angenommen: {fehler}", "geschickt": geschickt}
    return {"ok": True, "gesendet": True, "text": text, "dateien": geschickt}


def planen(text: str, zeit: str, datum: str = "", taeglich: bool = False) -> dict:
    from app.services.reminder_service import get_reminder_service

    gelesen = zeit_lesen(zeit, datum)
    if not gelesen:
        return {"error": "Ich verstehe die Uhrzeit nicht. Nenne sie z. B. als 20:00, 'in 10 Minuten' oder 'morgen 8 Uhr'."}
    uhrzeit, tag = gelesen
    eintrag = get_reminder_service().add(text, uhrzeit, "daily" if taeglich else "once", "", "telegram", "" if taeglich else tag)
    return {"ok": True, "geplant": True, "id": eintrag["id"], "zeit": uhrzeit, "datum": "" if taeglich else tag, "taeglich": taeglich, "text": text, "hinweis": "" if bereit()[0] else bereit()[1]}


def geplante() -> list[dict]:
    from app.services.reminder_service import get_reminder_service

    return [{"id": r["id"], "text": r["text"], "zeit": r.get("time", ""), "datum": r.get("datum", ""), "taeglich": r.get("repeat") == "daily"} for r in get_reminder_service().list() if r.get("kanal") == "telegram" and r.get("active")]


async def schleife() -> None:
    from app.services.reminder_service import get_reminder_service

    while True:
        try:
            if bereit()[0]:
                for eintrag in get_reminder_service().due("telegram"):
                    ergebnis = await senden(eintrag["text"])
                    if ergebnis.get("error"):
                        leise(RuntimeError(ergebnis["error"]), "services/telegram_plan")
        except Exception as fehler:
            leise(fehler, "services/telegram_plan")
        await asyncio.sleep(TAKT)
