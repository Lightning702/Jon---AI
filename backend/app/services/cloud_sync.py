from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text
from app.services.backup_service import SECRET_KEYS
from app.services.premium import get_premium

DATEIEN = ("persona.json", "alltagsgedaechtnis.json")
GERAETEBEZOGEN = {"telegram_chat_id", "theme_window", "pet_x", "pet_y"}


def _schluessel(passwort: str, salz: bytes) -> bytes:
    return Scrypt(salt=salz, length=32, n=2**15, r=8, p=1).derive(passwort.encode("utf-8"))


def verschluesseln(daten: dict, passwort: str) -> str:
    if len(passwort) < 8:
        raise ValueError("Das Sicherungspasswort braucht mindestens 8 Zeichen.")
    salz, nonce = os.urandom(16), os.urandom(12)
    inhalt = AESGCM(_schluessel(passwort, salz)).encrypt(nonce, json.dumps(daten, ensure_ascii=False).encode("utf-8"), b"jon-cloud-sync-1")
    huelle = {"v": 1, "salz": base64.b64encode(salz).decode(), "nonce": base64.b64encode(nonce).decode(), "daten": base64.b64encode(inhalt).decode()}
    return base64.b64encode(json.dumps(huelle).encode()).decode()


def entschluesseln(text: str, passwort: str) -> dict:
    try:
        huelle = json.loads(base64.b64decode(text))
        roh = AESGCM(_schluessel(passwort, base64.b64decode(huelle["salz"]))).decrypt(base64.b64decode(huelle["nonce"]), base64.b64decode(huelle["daten"]), b"jon-cloud-sync-1")
    except InvalidTag:
        raise ValueError("Falsches Sicherungspasswort.")
    except (ValueError, KeyError, TypeError):
        raise ValueError("Die Cloud-Sicherung ist beschädigt.")
    return json.loads(roh)


def paket(verzeichnis: Path = DATA_DIR) -> dict:
    from app.services.memory_service import MemoryService

    try:
        einstellungen = json.loads((verzeichnis / "user_settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        einstellungen = {}
    for schluessel in SECRET_KEYS | GERAETEBEZOGEN:
        einstellungen.pop(schluessel, None)
    dateien = {}
    for name in DATEIEN:
        try:
            dateien[name] = (verzeichnis / name).read_text(encoding="utf-8")
        except OSError:
            continue
    erinnerungen = [{"content": m.get("content", ""), "source": m.get("source", "chat"), "wichtigkeit": m.get("wichtigkeit", 0.5)} for m in MemoryService().list(limit=5000)]
    return {"v": 1, "zeit": time.time(), "einstellungen": einstellungen, "dateien": dateien, "erinnerungen": erinnerungen}


def einspielen(daten: dict, verzeichnis: Path = DATA_DIR) -> dict:
    from app.services.memory_service import MemoryService
    from app.services.settings_service import get_settings_service

    if daten.get("v") != 1:
        raise ValueError("Diese Cloud-Sicherung stammt aus einer neueren Jon-Version.")
    einstellungen = {k: v for k, v in (daten.get("einstellungen") or {}).items() if k not in SECRET_KEYS and k not in GERAETEBEZOGEN}
    if einstellungen:
        get_settings_service().update(einstellungen)
    for name, inhalt in (daten.get("dateien") or {}).items():
        if name in DATEIEN and isinstance(inhalt, str):
            atomic_write_text(verzeichnis / name, inhalt)
    dienst = MemoryService()
    vorhanden = {m.get("content", "") for m in dienst.list(limit=5000)}
    neu = 0
    for eintrag in daten.get("erinnerungen") or []:
        text = str(eintrag.get("content", "")).strip()
        if text and text not in vorhanden:
            dienst.add(text, source=str(eintrag.get("source", "chat"))[:32], wichtigkeit=float(eintrag.get("wichtigkeit", 0.5)))
            vorhanden.add(text)
            neu += 1
    return {"einstellungen": len(einstellungen), "erinnerungen": neu, "dateien": len(daten.get("dateien") or {})}


async def hochladen(passwort: str) -> dict:
    premium = get_premium()
    premium.pruefen("sync")
    text = verschluesseln(paket(), passwort)
    antwort = await premium.rufen("sicherung", {"aktion": "hochladen", "token": premium.token(), "geraet": premium.geraet(), "daten": text})
    return {"zeit": antwort.get("zeit", time.time()), "groesse": len(text)}


async def holen(passwort: str) -> dict:
    premium = get_premium()
    premium.pruefen("sync")
    antwort = await premium.rufen("sicherung", {"aktion": "holen", "token": premium.token(), "geraet": premium.geraet()})
    return einspielen(entschluesseln(antwort["daten"], passwort))


async def info() -> dict:
    premium = get_premium()
    if not premium.premium():
        return {"zeit": 0, "verfuegbar": False}
    antwort = await premium.rufen("sicherung", {"aktion": "info", "token": premium.token(), "geraet": premium.geraet()})
    return {**antwort, "verfuegbar": True}
