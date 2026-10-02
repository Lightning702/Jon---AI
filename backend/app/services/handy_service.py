from __future__ import annotations

import asyncio
import base64
import json
import re
import secrets
import socket
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator

from app.core.config import DATA_DIR
from app.core.logbook import logger as logbook_logger

_log = logbook_logger("handy")

STORE = DATA_DIR / "handy.json"
DATEI_ORDNER = DATA_DIR / "handy"
PROTOKOLL = 2
PAAR_TTL = 600.0
CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LAENGE = 12
FEHLVERSUCHE_MAX = 12
NACHLAUF = 90.0
NACHRICHT_MAX = 6_000_000
DATEI_MAX = 300 * 1024 * 1024
TEIL_MAX = 32_768
TEIL_DIREKT = 262_144
UEBERTRAGUNG_TTL = 900.0
AUFTRAG_TTL = 45.0
AUSGANG_TTL = 1800.0
ZUSTAND_TTL = 120.0
POSTFACH_TTL = 75.0
ABHOL_MAX = 12.0
TEXT_BUENDEL = 180
TEXT_PAUSE = 0.35

RECHTE_VORGABE = {
    "apps": False,
    "musik": False,
    "status": True,
    "dateien": True,
    "hinweise": False,
    "zwischenablage": False,
    "standort": False,
    "kontakte": False,
    "kamera": False,
    "mikrofon": False,
    "durchsage": True,
    "klingeln": True,
    "regeln": True,
}

MELDUNG_ARTEN = ("sos", "gelesen", "zeitanfrage")
_APP_KENNUNG = re.compile(r"[A-Za-z][A-Za-z0-9_.]{1,120}")
_HINTERGRUND: set = set()
MELDUNGEN_MAX = 30
DURCHSAGEN_MAX = 20

RECHTE_STUFEN = {
    "apps": "standard",
    "musik": "standard",
    "status": "standard",
    "dateien": "standard",
    "hinweise": "persoenlich",
    "zwischenablage": "persoenlich",
    "standort": "persoenlich",
    "kontakte": "persoenlich",
    "kamera": "sensibel",
    "mikrofon": "sensibel",
    "durchsage": "standard",
    "klingeln": "standard",
    "regeln": "standard",
}

RECHTE_NAMEN = {
    "apps": "Erlaubte Apps",
    "musik": "Amazon Music",
    "status": "Gerätestatus",
    "dateien": "Dateien",
    "hinweise": "Benachrichtigungen",
    "zwischenablage": "Zwischenablage",
    "standort": "Standort",
    "kontakte": "Kontakte",
    "kamera": "Kamera",
    "mikrofon": "Mikrofon",
    "durchsage": "Durchsagen",
    "klingeln": "Klingeln lassen",
    "regeln": "Bildschirmzeit",
}


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _ableiten(geheimnis: bytes, zweck: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"jon-handy-v1",
        info=zweck,
    ).derive(geheimnis)


def _verschluesseln(schluessel: bytes, zusatz: bytes, klartext: dict) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = secrets.token_bytes(12)
    roh = json.dumps(klartext, ensure_ascii=False).encode("utf-8")
    daten = AESGCM(schluessel).encrypt(nonce, roh, zusatz)
    return {"n": _b64(nonce), "c": _b64(daten)}


def _entschluesseln(schluessel: bytes, zusatz: bytes, umschlag: dict) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = _unb64(str(umschlag.get("n", "")))
    daten = _unb64(str(umschlag.get("c", "")))
    roh = AESGCM(schluessel).decrypt(nonce, daten, zusatz)
    geladen = json.loads(roh.decode("utf-8"))
    if not isinstance(geladen, dict):
        raise ValueError("Ungueltiger Inhalt")
    return geladen


class HandyFehler(Exception):
    pass


def code_erzeugen() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LAENGE))


def code_saeubern(roh: str) -> str:
    ersatz = {"I": "1", "L": "1", "O": "0", "U": "V"}
    sauber = ""
    for zeichen in roh.upper():
        if zeichen in "- _	":
            continue
        sauber += ersatz.get(zeichen, zeichen)
    return sauber


def code_gruppiert(code: str) -> str:
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def thema_fuer(code: str) -> str:
    return _ableiten(code.encode("utf-8"), b"topic")[:8].hex()


def schluessel_fuer_code(code: str) -> bytes:
    return _ableiten(code.encode("utf-8"), b"pairing")


def _sauberer_name(roh: str) -> str:
    erlaubt = "".join(
        zeichen if zeichen.isalnum() or zeichen in "._- " else "_"
        for zeichen in roh.strip()
    ).strip(" .")
    return (erlaubt or "datei")[:80]


def zielordner() -> Path:
    from app.services.settings_service import get_settings_service

    roh = ""
    try:
        roh = str(get_settings_service().get().get("handy_ordner", "") or "").strip()
    except Exception:
        roh = ""
    if roh:
        gewaehlt = Path(roh).expanduser()
        try:
            gewaehlt.mkdir(parents=True, exist_ok=True)
            probe = gewaehlt / ".jon-schreibprobe"
            probe.write_bytes(b"")
            probe.unlink()
            return gewaehlt
        except OSError as exc:
            _log.warning("Ordner %s nicht nutzbar (%s), nehme den Standard", roh, exc)
    DATEI_ORDNER.mkdir(parents=True, exist_ok=True)
    return DATEI_ORDNER


def _datei_schreiben(name: str, inhalt: bytes) -> str:
    ordner = zielordner()
    stempel = time.strftime("%Y%m%d-%H%M%S")
    ziel = ordner / f"{stempel}-{name}"
    zaehler = 1
    while ziel.exists():
        ziel = ordner / f"{stempel}-{zaehler}-{name}"
        zaehler += 1
    ziel.write_bytes(inhalt)
    return str(ziel)


class HandyService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data = self._laden()
        self._sitzung: dict | None = None
        self._warteschlangen: dict[str, list[asyncio.Queue]] = {}
        self._uebertragungen: dict[str, dict] = {}
        self._auftraege: dict[str, tuple[str, asyncio.Future]] = {}
        self._postfaecher: dict[str, dict] = {}
        self._ausgang: dict[str, dict] = {}
        self._neue_meldungen: list[dict] = []

    def _laden(self) -> dict:
        from app.core.krypto import ist_klartext_datei, json_lesen

        roh = json_lesen(STORE, None, "handy")
        if isinstance(roh, dict) and ist_klartext_datei(STORE):
            from app.core.krypto import json_schreiben

            json_schreiben(STORE, roh, "handy")
        if not isinstance(roh, dict):
            roh = {}
        geraete = roh.get("geraete")
        if not isinstance(geraete, list):
            geraete = []
        pc_id = str(roh.get("pc_id", "")).strip()
        if not pc_id:
            pc_id = secrets.token_hex(6)
        return {"pc_id": pc_id, "geraete": geraete, "bericht_woche": str(roh.get("bericht_woche") or "")}

    def _sichern(self) -> None:
        from app.core.krypto import json_schreiben

        json_schreiben(STORE, self._data, "handy")

    def rechnername(self) -> str:
        try:
            return socket.gethostname()
        except OSError:
            return "Jon PC"

    def kennung(self) -> dict:
        from app.core.config import get_settings

        with self._lock:
            pc_id = self._data["pc_id"]
        return {
            "id": pc_id,
            "name": self.rechnername(),
            "version": get_settings().app_version,
        }

    def _adressen(self) -> list[str]:
        from app.core.auth import lan_adressen
        from app.core.config import get_settings

        settings = get_settings()
        from app.core.heimnetz import lan_aktiv

        if not lan_aktiv():
            return []
        from app.services.geraete_vpn import tailscale_status
        vpn = tailscale_status().get("adressen", [])
        return [f"http://{host}:{settings.port}" for host in dict.fromkeys([h for h in vpn if ":" not in h] + lan_adressen())]

    def _adresse(self) -> str:
        alle = self._adressen()
        return alle[0] if alle else ""

    def _makler(self) -> dict:
        from app.services.settings_service import get_settings_service

        daten = get_settings_service().get()
        broker = str(daten.get("handy_broker", "") or "broker.hivemq.com")
        try:
            port = int(daten.get("handy_broker_port", 1883) or 1883)
        except (TypeError, ValueError):
            port = 1883
        return {"host": broker, "port": port}

    def kopplung_starten(self, direct_only: bool = False) -> dict:
        code = code_erzeugen()
        kennung = self.kennung()
        makler = self._makler()
        adressen = self._adressen()
        adresse = adressen[0] if adressen else ""
        sitzung = {
            "direct_only": direct_only,
            "code": code,
            "thema": thema_fuer(code),
            "schluessel": schluessel_fuer_code(code),
            "start": time.time(),
            "ablauf": time.time() + PAAR_TTL,
            "status": "offen",
            "geraet": None,
            "ergebnis": None,
            "fehlversuche": 0,
        }
        with self._lock:
            self._sitzung = sitzung
        nutzlast = {
            "v": PROTOKOLL,
            "t": "jon-pair",
            "direct_only": direct_only,
            "n": kennung["name"],
            "c": code,
            "u": adresse,
            "us": adressen,
            "b": makler["host"],
            "p": makler["port"],
        }
        _log.info("Kopplung offen, Code gueltig fuer %s Minuten", int(PAAR_TTL // 60))
        return {
            "nutzlast": json.dumps(nutzlast, ensure_ascii=False, separators=(",", ":")),
            "code": code,
            "code_gruppiert": code_gruppiert(code),
            "thema": sitzung["thema"],
            "ablauf": sitzung["ablauf"],
            "pc": kennung,
            "adresse": adresse,
            "adressen": adressen,
            "heimnetz": bool(adressen),
            "broker": makler,
        }

    def offenes_thema(self) -> str:
        with self._lock:
            sitzung = self._sitzung
            if sitzung is None or sitzung.get("direct_only"):
                return ""
            if time.time() > sitzung["ablauf"] + NACHLAUF:
                return ""
            return str(sitzung["thema"])

    def kopplung_status(self) -> dict:
        with self._lock:
            sitzung = self._sitzung
            if sitzung is None:
                return {"status": "leer"}
            if sitzung["status"] in ("offen", "wartet") and time.time() > sitzung["ablauf"]:
                sitzung["status"] = "abgelaufen"
            return {
                "status": sitzung["status"],
                "direct_only": bool(sitzung.get("direct_only")),
                "geraet": sitzung.get("geraet"),
                "rest": max(0, int(sitzung["ablauf"] - time.time())),
                "code": sitzung["code"],
                "code_gruppiert": code_gruppiert(sitzung["code"]),
            }

    def kopplung_beantworten(self, angenommen: bool) -> dict:
        kennung = self.kennung()
        adressen = self._adressen()
        adresse = adressen[0] if adressen else ""
        makler = self._makler()
        with self._lock:
            sitzung = self._sitzung
            if sitzung is None or sitzung["status"] != "wartet":
                raise HandyFehler("Keine wartende Anfrage.")
            if time.time() > sitzung["ablauf"]:
                raise HandyFehler("Der Kopplungscode ist abgelaufen.")
            geraet = dict(sitzung.get("geraet") or {})
            if not angenommen:
                sitzung["status"] = "abgelehnt"
                sitzung["ergebnis"] = {"status": "abgelehnt"}
                return {"status": "abgelehnt"}
            geraete_id = secrets.token_hex(8)
            schluessel = secrets.token_bytes(32)
            token = secrets.token_urlsafe(32)
            eintrag = {
                "id": geraete_id,
                "name": geraet.get("name") or "Android",
                "plattform": geraet.get("plattform") or "Android",
                "schluessel": _b64(schluessel),
                "token": token,
                "erstellt": time.time(),
                "gesehen": time.time(),
                "direct_only": bool(sitzung.get("direct_only")),
                "rechte": {**RECHTE_VORGABE, **({"apps": True, "musik": True} if sitzung.get("direct_only") else {})},
                "faehigkeiten": [],
                "zustand": {},
                "zustand_zeit": 0.0,
            }
            self._data["geraete"] = [
                g for g in self._data["geraete"] if g.get("name") != eintrag["name"]
            ] + [eintrag]
            self._sichern()
            sitzung["status"] = "verbunden"
            sitzung["ergebnis"] = {
                "status": "ok",
                "direct_only": bool(sitzung.get("direct_only")),
                "geraet": geraete_id,
                "schluessel": _b64(schluessel),
                "token": token,
                "pc": kennung,
                "adresse": adresse,
                "adressen": adressen,
                "broker": makler,
            }
        _log.info("Handy gekoppelt: %s", eintrag["name"])
        return {"status": "ok", "geraet": geraete_id}

    def kopplung_abbrechen(self) -> dict:
        with self._lock:
            self._sitzung = None
        return {"status": "leer"}

    def geraete(self) -> list[dict]:
        with self._lock:
            eintraege = [dict(g) for g in self._data["geraete"]]
        return [self.geraet_sicht(eintrag) for eintrag in eintraege]

    def geraet_sicht(self, eintrag: dict) -> dict:
        kennung = str(eintrag.get("id", ""))
        zustand = eintrag.get("zustand")
        return {
            "id": kennung,
            "name": eintrag.get("name", ""),
            "plattform": eintrag.get("plattform", ""),
            "direct_only": bool(eintrag.get("direct_only")),
            "erstellt": eintrag.get("erstellt", 0),
            "gesehen": eintrag.get("gesehen", 0),
            "online": self.online(kennung),
            "rechte": self.rechte(kennung),
            "stufen": dict(RECHTE_STUFEN),
            "namen": dict(RECHTE_NAMEN),
            "faehigkeiten": list(eintrag.get("faehigkeiten") or []),
            "zustand": dict(zustand) if isinstance(zustand, dict) else {},
            "zustand_zeit": float(eintrag.get("zustand_zeit") or 0.0),
            "meldungen": list(reversed(list(eintrag.get("meldungen") or [])[-10:])),
            "durchsagen": list(reversed(list(eintrag.get("durchsagen") or [])[-5:])),
        }

    def geraet_entfernen(self, geraete_id: str) -> bool:
        with self._lock:
            vorher = len(self._data["geraete"])
            self._data["geraete"] = [
                g for g in self._data["geraete"] if g.get("id") != geraete_id
            ]
            entfernt = len(self._data["geraete"]) != vorher
            if entfernt:
                self._sichern()
        return entfernt

    def _geraet(self, geraete_id: str) -> dict | None:
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    return dict(eintrag)
        return None

    def token_gueltig(self, kandidat: str) -> bool:
        with self._lock:
            for eintrag in self._data["geraete"]:
                if secrets.compare_digest(str(eintrag.get("token", "")), kandidat):
                    return True
        return False

    def _gesehen(self, geraete_id: str) -> None:
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    eintrag["gesehen"] = time.time()
                    self._sichern()
                    return

    def _schluessel_fuer(self, umschlag: dict) -> tuple[bytes, bytes, dict | None]:
        art = str(umschlag.get("k", ""))
        kennung = str(umschlag.get("i", ""))
        zusatz = f"{art}:{kennung}".encode("utf-8")
        if art == "pair":
            with self._lock:
                sitzung = self._sitzung
                if sitzung is None:
                    raise HandyFehler("Keine gueltige Kopplung offen.")
                if time.time() > sitzung["ablauf"] and not sitzung.get("ergebnis"):
                    raise HandyFehler("Keine gueltige Kopplung offen.")
                if sitzung.get("fehlversuche", 0) >= FEHLVERSUCHE_MAX:
                    raise HandyFehler("Zu viele Fehlversuche. Erzeuge einen neuen Code.")
                if kennung != sitzung["thema"] and kennung != self._data["pc_id"]:
                    sitzung["fehlversuche"] = sitzung.get("fehlversuche", 0) + 1
                    raise HandyFehler("Code passt nicht.")
                return sitzung["schluessel"], zusatz, None
        if art == "dev":
            geraet = self._geraet(kennung)
            if geraet is None:
                raise HandyFehler("Unbekanntes Geraet.")
            return _unb64(str(geraet["schluessel"])), zusatz, geraet
        raise HandyFehler("Unbekannter Umschlag.")

    async def umschlag(self, umschlag: dict) -> dict:
        schluessel, zusatz, geraet = self._schluessel_fuer(umschlag)
        try:
            anfrage = _entschluesseln(schluessel, zusatz, umschlag)
        except Exception as exc:
            self._fehlversuch(umschlag)
            raise HandyFehler("Code passt nicht.") from exc
        antwort = await self._bearbeiten(anfrage, geraet)
        return {
            "v": PROTOKOLL,
            "k": umschlag.get("k"),
            "i": umschlag.get("i"),
            **_verschluesseln(schluessel, zusatz, antwort),
        }

    def _fehlversuch(self, umschlag: dict) -> None:
        if str(umschlag.get("k", "")) != "pair":
            return
        with self._lock:
            sitzung = self._sitzung
            if sitzung is not None:
                sitzung["fehlversuche"] = sitzung.get("fehlversuche", 0) + 1

    async def umschlag_strom(self, umschlag: dict) -> AsyncIterator[dict]:
        schluessel, zusatz, geraet = self._schluessel_fuer(umschlag)
        try:
            anfrage = _entschluesseln(schluessel, zusatz, umschlag)
        except Exception as exc:
            raise HandyFehler("Umschlag nicht lesbar.") from exc
        async for stueck in self._strom(anfrage, geraet):
            yield {
                "v": PROTOKOLL,
                "k": umschlag.get("k"),
                "i": umschlag.get("i"),
                **_verschluesseln(schluessel, zusatz, stueck),
            }

    async def _bearbeiten(self, anfrage: dict, geraet: dict | None) -> dict:
        op = str(anfrage.get("op", ""))
        ruf = anfrage.get("rid")
        if op == "hello":
            return {"rid": ruf, "ok": True, "pc": self.kennung()}
        if op == "pair":
            return {"rid": ruf, **self._pair_anmelden(anfrage)}
        if op == "pair-status":
            return {"rid": ruf, **self._pair_stand()}
        if geraet is None:
            return {"rid": ruf, "ok": False, "fehler": "Nicht gekoppelt."}
        self._gesehen(geraet["id"])
        if op == "ping":
            return {"rid": ruf, "ok": True, "pc": self.kennung()}
        if op in ("audio-stt", "audio-tts"):
            from app.services.geraete_funktionen import audio_ausfuehren
            return {"rid": ruf, **await audio_ausfuehren(anfrage)}
        if op == "call":
            return {"rid": ruf, **await self._api(anfrage, geraet)}
        if op == "datei-start":
            return {"rid": ruf, **self.datei_start(anfrage)}
        if op == "datei-teil":
            return {"rid": ruf, **self.datei_teil(anfrage)}
        if op == "datei-ende":
            return {"rid": ruf, **await self.datei_ende(anfrage)}
        if op == "zustand":
            return {"rid": ruf, **self.zustand_melden(geraet["id"], anfrage)}
        if op == "rechte":
            return {
                "rid": ruf,
                "ok": True,
                "rechte": self.rechte(geraet["id"]),
                "stufen": dict(RECHTE_STUFEN),
            }
        if op == "recht":
            return {"rid": ruf, **self.recht_sperren(geraet["id"], anfrage)}
        if op == "antwort":
            return {"rid": ruf, **self.antwort_annehmen(geraet["id"], anfrage)}
        if op == "warten":
            return {"rid": ruf, **await self.abholen(geraet["id"], anfrage)}
        if op == "datei-holen":
            return {"rid": ruf, **self.datei_holen(geraet["id"], anfrage)}
        if op == "melden":
            return {"rid": ruf, **await self.meldung_annehmen(geraet["id"], anfrage)}
        if op == "abmelden":
            return {"rid": ruf, "ok": self.geraet_entfernen(geraet["id"])}
        return {"rid": ruf, "ok": False, "fehler": "Unbekannte Anweisung."}

    def _aufraeumen(self) -> None:
        jetzt = time.time()
        alt = [
            kennung
            for kennung, lauf in self._uebertragungen.items()
            if jetzt - lauf["start"] > UEBERTRAGUNG_TTL
        ]
        for kennung in alt:
            self._uebertragungen.pop(kennung, None)

    def datei_start(self, anfrage: dict) -> dict:
        with self._lock:
            self._aufraeumen()
            if len(self._uebertragungen) > 6:
                return {"ok": False, "fehler": "Zu viele Uebertragungen."}
            try:
                groesse = int(anfrage.get("groesse", 0) or 0)
            except (TypeError, ValueError):
                groesse = 0
            if groesse <= 0 or groesse > DATEI_MAX:
                return {"ok": False, "fehler": "Diese Datei ist zu gross."}
            kennung = secrets.token_hex(8)
            self._uebertragungen[kennung] = {
                "name": _sauberer_name(str(anfrage.get("name", "datei"))),
                "art": str(anfrage.get("art", "")),
                "groesse": groesse,
                "teile": {},
                "start": time.time(),
            }
        return {
            "ok": True,
            "id": kennung,
            "teilgroesse": TEIL_DIREKT,
            "teilgroesse_relay": TEIL_MAX,
        }

    def datei_teil(self, anfrage: dict) -> dict:
        kennung = str(anfrage.get("id", ""))
        try:
            nummer = int(anfrage.get("nr", -1))
        except (TypeError, ValueError):
            return {"ok": False, "fehler": "Ungueltige Teilnummer."}
        roh = str(anfrage.get("daten", ""))
        if not roh:
            return {"ok": False, "fehler": "Leerer Teil."}
        try:
            daten = _unb64(roh)
        except Exception:
            return {"ok": False, "fehler": "Teil nicht lesbar."}
        with self._lock:
            lauf = self._uebertragungen.get(kennung)
            if lauf is None:
                return {"ok": False, "fehler": "Uebertragung unbekannt."}
            if nummer < 0 or len(lauf["teile"]) > 4000:
                return {"ok": False, "fehler": "Zu viele Teile."}
            lauf["teile"][nummer] = daten
            gesammelt = sum(len(t) for t in lauf["teile"].values())
            if gesammelt > DATEI_MAX:
                self._uebertragungen.pop(kennung, None)
                return {"ok": False, "fehler": "Datei zu gross."}
        return {"ok": True, "nr": nummer}

    async def datei_ende(self, anfrage: dict) -> dict:
        kennung = str(anfrage.get("id", ""))
        try:
            erwartet = int(anfrage.get("teile", 0) or 0)
        except (TypeError, ValueError):
            erwartet = 0
        with self._lock:
            lauf = self._uebertragungen.get(kennung)
            if lauf is None:
                return {"ok": False, "fehler": "Uebertragung unbekannt."}
            fehlend = [nr for nr in range(erwartet) if nr not in lauf["teile"]]
            if fehlend:
                return {"ok": False, "fehlend": fehlend[:60], "anzahl": len(fehlend)}
            inhalt = b"".join(lauf["teile"][nr] for nr in sorted(lauf["teile"]))
            name = lauf["name"]
            self._uebertragungen.pop(kennung, None)
        pfad = await asyncio.to_thread(_datei_schreiben, name, inhalt)
        _log.info("Datei vom Handy gespeichert: %s (%s Bytes)", pfad, len(inhalt))
        try:
            from app.services.dateiindex_service import get_dateiindex_service

            await asyncio.to_thread(get_dateiindex_service().merken, pfad, "", "", "", "", "handy")
        except Exception as exc:
            _log.warning("Datei vom Handy nicht im Index: %s", exc)
        return {"ok": True, "pfad": pfad, "groesse": len(inhalt), "name": name}

    def _pair_anmelden(self, anfrage: dict) -> dict:
        with self._lock:
            sitzung = self._sitzung
            if sitzung is None or time.time() > sitzung["ablauf"]:
                return {"ok": False, "fehler": "Kopplung abgelaufen."}
            if sitzung["status"] in ("verbunden", "abgelehnt"):
                return {"ok": False, "fehler": "Kopplung bereits erledigt."}
            sitzung["status"] = "wartet"
            sitzung["geraet"] = {
                "name": str(anfrage.get("name", "") or "Android"),
                "plattform": str(anfrage.get("plattform", "") or "Android"),
            }
        return {"ok": True, "status": "wartet"}

    def _pair_stand(self) -> dict:
        with self._lock:
            sitzung = self._sitzung
            if sitzung is None:
                return {"ok": False, "fehler": "Keine Kopplung offen."}
            if sitzung["status"] == "verbunden" and sitzung.get("ergebnis"):
                ergebnis = dict(sitzung["ergebnis"])
                sitzung["abgeholt"] = time.time()
                sitzung["ablauf"] = min(sitzung["ablauf"], time.time())
                return {"ok": True, **ergebnis}
            if sitzung["status"] == "abgelehnt":
                sitzung["ablauf"] = min(sitzung["ablauf"], time.time())
                return {"ok": False, "fehler": "Am PC abgelehnt."}
            if time.time() > sitzung["ablauf"]:
                return {"ok": False, "fehler": "Kopplung abgelaufen."}
            return {"ok": True, "status": sitzung["status"]}

    def kopplung_aufraeumen(self) -> None:
        with self._lock:
            sitzung = self._sitzung
            if sitzung is None:
                return
            if time.time() > sitzung["ablauf"] + NACHLAUF:
                self._sitzung = None

    async def _api(self, anfrage: dict, geraet: dict) -> dict:
        import httpx

        from app.main import app as jon_app

        methode = str(anfrage.get("method", "GET")).upper()
        pfad = str(anfrage.get("path", "/api/health"))
        if not pfad.startswith("/"):
            pfad = "/" + pfad
        kopf = {"X-Jon-Token": str(geraet.get("token", ""))}
        rumpf = anfrage.get("body")
        transport = httpx.ASGITransport(app=jon_app)
        from app.services.geraete_funktionen import HANDY_KONTEXT
        marke = HANDY_KONTEXT.set(geraet["id"])
        try:
            async with httpx.AsyncClient(
                transport=transport, base_url="http://handy", timeout=180.0
            ) as klient:
                antwort = await klient.request(
                    methode,
                    pfad,
                    params=anfrage.get("query") or None,
                    json=rumpf if isinstance(rumpf, (dict, list)) else None,
                    headers=kopf,
                )
        finally:
            HANDY_KONTEXT.reset(marke)
        if anfrage.get("binary"):
            import base64
            if len(antwort.content) > 4_000_000:
                return {"ok": False, "fehler": "Datei für direkte Vorschau zu groß."}
            return {"ok": antwort.status_code < 400, "code": antwort.status_code, "data": base64.b64encode(antwort.content).decode("ascii"), "mime": antwort.headers.get("content-type", "application/octet-stream")}
        text = antwort.text
        if antwort.status_code >= 400:
            try:
                detail = antwort.json().get("detail", "Anfrage abgelehnt")
            except Exception:
                detail = "Anfrage abgelehnt"
            return {"ok": False, "code": antwort.status_code, "fehler": str(detail)[:500]}
        if len(text) > NACHRICHT_MAX:
            return {"ok": False, "fehler": "Antwort zu gross."}
        return {
            "ok": antwort.status_code < 400,
            "code": antwort.status_code,
            "text": text,
        }

    async def _strom(self, anfrage: dict, geraet: dict | None) -> AsyncIterator[dict]:
        op = str(anfrage.get("op", ""))
        ruf = anfrage.get("rid")
        if geraet is None:
            yield {"rid": ruf, "ok": False, "fehler": "Nicht gekoppelt.", "ende": True}
            return
        self._gesehen(geraet["id"])
        if op == "events":
            async for stueck in self._ereignisse(ruf, geraet):
                yield stueck
            return
        if op != "stream":
            yield {"rid": ruf, "ok": False, "fehler": "Unbekannter Strom.", "ende": True}
            return
        import httpx

        from app.main import app as jon_app

        methode = str(anfrage.get("method", "POST")).upper()
        pfad = str(anfrage.get("path", "/api/chat"))
        if pfad == "/api/chat":
            from app.services.geraete_funktionen import HANDY_KONTEXT
            marke = HANDY_KONTEXT.set(geraet["id"])
            try:
                async for stueck in self._chat_strom(ruf, anfrage.get("body")):
                    yield stueck
            finally:
                HANDY_KONTEXT.reset(marke)
            return
        kopf = {"X-Jon-Token": str(geraet.get("token", ""))}
        rumpf = anfrage.get("body")
        transport = httpx.ASGITransport(app=jon_app)
        try:
            async with httpx.AsyncClient(
                transport=transport, base_url="http://handy", timeout=None
            ) as klient:
                async with klient.stream(
                    methode,
                    pfad,
                    json=rumpf if isinstance(rumpf, (dict, list)) else None,
                    headers=kopf,
                ) as antwort:
                    async for zeile in antwort.aiter_lines():
                        if not zeile.startswith("data:"):
                            continue
                        yield {"rid": ruf, "ok": True, "daten": zeile[5:].strip()}
        except Exception as exc:
            yield {"rid": ruf, "ok": False, "fehler": str(exc)}
        yield {"rid": ruf, "ok": True, "ende": True}

    async def _chat_strom(self, ruf: Any, rumpf: Any) -> AsyncIterator[dict]:
        from app.api.routes import _chat_service
        from app.schemas import ChatIn

        def paket(ereignis: dict) -> dict:
            return {
                "rid": ruf,
                "ok": True,
                "daten": json.dumps(ereignis, ensure_ascii=False),
            }

        try:
            nutzlast = ChatIn(**(rumpf if isinstance(rumpf, dict) else {}))
        except Exception as exc:
            yield {"rid": ruf, "ok": False, "fehler": f"Anfrage nicht lesbar: {exc}"}
            yield {"rid": ruf, "ok": True, "ende": True}
            return
        puffer = {"reasoning": "", "content": ""}
        seit = time.monotonic()
        try:
            async for ereignis in _chat_service.stream(nutzlast):
                art = str(ereignis.get("type", ""))
                if art in puffer:
                    puffer[art] += str(ereignis.get("delta", ""))
                    voll = len(puffer[art]) >= TEXT_BUENDEL
                    if not voll and time.monotonic() - seit < TEXT_PAUSE:
                        continue
                for name in ("reasoning", "content"):
                    if puffer[name]:
                        yield paket({"type": name, "delta": puffer[name]})
                        puffer[name] = ""
                seit = time.monotonic()
                if art not in puffer:
                    yield paket(ereignis)
        except Exception as exc:
            for name in ("reasoning", "content"):
                if puffer[name]:
                    yield paket({"type": name, "delta": puffer[name]})
                    puffer[name] = ""
            yield {"rid": ruf, "ok": False, "fehler": str(exc)}
        for name in ("reasoning", "content"):
            if puffer[name]:
                yield paket({"type": name, "delta": puffer[name]})
        yield {"rid": ruf, "ok": True, "ende": True}

    async def _ereignisse(self, ruf: Any, geraet: dict) -> AsyncIterator[dict]:
        warteschlange: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self._lock:
            for alte in self._warteschlangen.get(geraet["id"]) or []:
                try:
                    alte.put_nowait({"art": "ende", "zeit": time.time(), "daten": {}})
                except asyncio.QueueFull:
                    continue
            self._warteschlangen[geraet["id"]] = [warteschlange]
        _log.info("Ereignis-Strom offen fuer %s", geraet.get("name", geraet["id"]))
        try:
            yield {"rid": ruf, "ok": True, "bereit": True}
            while True:
                try:
                    ereignis = await asyncio.wait_for(warteschlange.get(), timeout=25.0)
                except asyncio.TimeoutError:
                    yield {"rid": ruf, "ok": True, "puls": time.time()}
                    continue
                if ereignis.get("art") == "ende":
                    yield {"rid": ruf, "ok": True, "ende": True}
                    return
                yield {"rid": ruf, "ok": True, "ereignis": ereignis}
        finally:
            with self._lock:
                liste = self._warteschlangen.get(geraet["id"]) or []
                if warteschlange in liste:
                    liste.remove(warteschlange)
            _log.info("Ereignis-Strom zu fuer %s", geraet.get("name", geraet["id"]))

    def melden(self, art: str, daten: dict) -> None:
        ereignis = {"art": art, "zeit": time.time(), "daten": daten}
        with self._lock:
            listen = [q for liste in self._warteschlangen.values() for q in liste]
        for warteschlange in listen:
            try:
                warteschlange.put_nowait(ereignis)
            except asyncio.QueueFull:
                continue

    def online(self, geraete_id: str) -> bool:
        if self._postfach(geraete_id) is not None:
            return True
        with self._lock:
            if self._warteschlangen.get(geraete_id):
                return True
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    return time.time() - float(eintrag.get("gesehen") or 0) < ZUSTAND_TTL
        return False

    def rechte(self, geraete_id: str) -> dict:
        werte = dict(RECHTE_VORGABE)
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    gespeichert = eintrag.get("rechte")
                    if isinstance(gespeichert, dict):
                        for schluessel, vorgabe in RECHTE_VORGABE.items():
                            werte[schluessel] = bool(gespeichert.get(schluessel, vorgabe))
                    return werte
        return werte

    def recht_erlaubt(self, geraete_id: str, schluessel: str) -> bool:
        if schluessel not in RECHTE_VORGABE:
            return False
        return bool(self.rechte(geraete_id).get(schluessel))

    def faehig(self, geraete_id: str, schluessel: str) -> bool:
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    gemeldet = eintrag.get("faehigkeiten")
                    if not isinstance(gemeldet, list) or not gemeldet:
                        return True
                    return schluessel in gemeldet
        return False

    def rechte_setzen(self, geraete_id: str, schluessel: str, wert: bool) -> dict:
        if schluessel not in RECHTE_VORGABE:
            raise HandyFehler("Diese Berechtigung gibt es nicht.")
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                gespeichert = eintrag.get("rechte")
                werte = dict(RECHTE_VORGABE)
                if isinstance(gespeichert, dict):
                    for name, vorgabe in RECHTE_VORGABE.items():
                        werte[name] = bool(gespeichert.get(name, vorgabe))
                werte[schluessel] = bool(wert)
                eintrag["rechte"] = werte
                self._sichern()
                _log.info(
                    "Berechtigung %s fuer %s auf %s gesetzt",
                    schluessel,
                    eintrag.get("name", geraete_id),
                    "an" if wert else "aus",
                )
                self.melden_an(geraete_id, "rechte", {"rechte": werte})
                return werte
        raise HandyFehler("Unbekanntes Geraet.")

    def recht_sperren(self, geraete_id: str, anfrage: dict) -> dict:
        schluessel = str(anfrage.get("recht", ""))
        if bool(anfrage.get("wert")):
            return {
                "ok": False,
                "fehler": "Freischalten geht nur am PC.",
                "rechte": self.rechte(geraete_id),
            }
        try:
            rechte = self.rechte_setzen(geraete_id, schluessel, False)
        except HandyFehler as exc:
            return {"ok": False, "fehler": str(exc), "rechte": self.rechte(geraete_id)}
        return {"ok": True, "rechte": rechte}

    def geraet_umbenennen(self, geraete_id: str, name: str) -> dict:
        sauber = str(name).strip()[:60]
        if not sauber:
            raise HandyFehler("Der Name darf nicht leer sein.")
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    eintrag["name"] = sauber
                    eintrag["umbenannt"] = True
                    self._sichern()
                    return self.geraet_sicht(dict(eintrag))
        raise HandyFehler("Unbekanntes Geraet.")

    def zustand_melden(self, geraete_id: str, anfrage: dict) -> dict:
        zustand = anfrage.get("zustand")
        if not isinstance(zustand, dict):
            zustand = {}
        faehigkeiten = anfrage.get("faehigkeiten")
        gefiltert = [
            str(wert)
            for wert in (faehigkeiten if isinstance(faehigkeiten, list) else [])
            if str(wert) in RECHTE_VORGABE
        ]
        gekuerzt = {
            schluessel: zustand.get(schluessel)
            for schluessel in (
                "akku",
                "laedt",
                "netz",
                "android",
                "modell",
                "sdk",
                "name",
                "speicher_frei",
                "diagnose",
                "device_owner", "kiosk", "wake_word", "sprach_status", "amazon", "tiktok", "whatsapp",
                "bildschirmzeit", "wecker", "version", "schritte", "apps", "kinder",
            )
            if zustand.get(schluessel) is not None
        }
        if len(json.dumps(gekuerzt.get("bildschirmzeit") or {}, ensure_ascii=False)) > 8000:
            gekuerzt.pop("bildschirmzeit", None)
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                eintrag["zustand"] = gekuerzt
                eintrag["zustand_zeit"] = time.time()
                verlauf_merken(eintrag, gekuerzt)
                eintrag["gesehen"] = time.time()
                if faehigkeiten is not None:
                    eintrag["faehigkeiten"] = gefiltert
                name = str(zustand.get("name") or "").strip()
                if name and not eintrag.get("umbenannt"):
                    eintrag["name"] = name[:60]
                self._sichern()
                break
        return {
            "ok": True,
            "rechte": self.rechte(geraete_id),
            "stufen": dict(RECHTE_STUFEN),
            "adressen": self._adressen(),
            "pc": self.kennung(),
        }

    async def meldung_annehmen(self, geraete_id: str, anfrage: dict) -> dict:
        art = str(anfrage.get("art", ""))
        if art not in MELDUNG_ARTEN:
            return {"ok": False, "fehler": "Diese Meldung kennt Jon nicht."}
        roh = anfrage.get("daten")
        daten = roh if isinstance(roh, dict) else {}
        if len(json.dumps(daten, ensure_ascii=False)) > 4000:
            return {"ok": False, "fehler": "Meldung zu gross."}
        sauber = {
            schluessel: wert
            for schluessel, wert in daten.items()
            if isinstance(schluessel, str) and isinstance(wert, (str, int, float, bool)) and len(schluessel) <= 40
        }
        meldung = {
            "id": secrets.token_hex(6),
            "art": art,
            "zeit": time.time(),
            "daten": sauber,
            "quittiert": art not in ("sos", "zeitanfrage"),
        }
        name = "Handy"
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                name = str(eintrag.get("name") or name)
                liste = list(eintrag.get("meldungen") or [])
                liste.append(meldung)
                eintrag["meldungen"] = liste[-MELDUNGEN_MAX:]
                if art == "gelesen":
                    kennung = str(sauber.get("kennung", ""))
                    for durchsage in eintrag.get("durchsagen") or []:
                        if durchsage.get("kennung") == kennung and not durchsage.get("gelesen"):
                            durchsage["gelesen"] = meldung["zeit"]
                self._sichern()
                break
            else:
                return {"ok": False, "fehler": "Unbekanntes Geraet."}
            self._neue_meldungen.append({**meldung, "geraet": geraete_id, "name": name})
            self._neue_meldungen = self._neue_meldungen[-50:]
        if art == "sos":
            _log.warning("SOS von %s", name)
            aufgabe = asyncio.create_task(_telegram_melden(sos_text(name, sauber), sauber))
            _HINTERGRUND.add(aufgabe)
            aufgabe.add_done_callback(_HINTERGRUND.discard)
        if art == "zeitanfrage":
            aufgabe = asyncio.create_task(_telegram_melden(zeitanfrage_text(name, sauber, meldung["id"])))
            _HINTERGRUND.add(aufgabe)
            aufgabe.add_done_callback(_HINTERGRUND.discard)
        return {"ok": True, "id": meldung["id"]}

    def wochenbericht(self, geraete_id: str, bis: str = "") -> dict:
        eintrag = self._geraet(geraete_id)
        if eintrag is None:
            raise HandyFehler("Unbekanntes Geraet.")
        return bericht_bauen(eintrag, bis)

    def bericht_faellig(self, jetzt: datetime | None = None) -> str:
        jetzt = jetzt or datetime.now()
        if jetzt.weekday() != 6 or jetzt.hour < 18:
            return ""
        woche = jetzt.strftime("%G-W%V")
        with self._lock:
            if self._data.get("bericht_woche") == woche:
                return ""
        return woche

    async def berichte_senden(self, woche: str) -> int:
        with self._lock:
            self._data["bericht_woche"] = woche
            self._sichern()
            eintraege = [dict(g) for g in self._data["geraete"] if g.get("verlauf")]
        gesendet = 0
        for eintrag in eintraege:
            bericht = bericht_bauen(eintrag)
            if not bericht["gesamt"] and not bericht["schritte"]:
                continue
            with self._lock:
                self._neue_meldungen.append({
                    "id": secrets.token_hex(6), "art": "bericht", "zeit": time.time(), "quittiert": True,
                    "daten": {"bis": bericht["bis"], "gesamt": bericht["gesamt"]},
                    "geraet": eintrag.get("id"), "name": str(eintrag.get("name") or "Handy"),
                })
                self._neue_meldungen = self._neue_meldungen[-50:]
            await _telegram_melden(bericht_text(bericht))
            gesendet += 1
        return gesendet

    def kinder_alter(self, geraete_id: str) -> int:
        from app.core.kinderschutz import alter_pruefen

        eintrag = self._geraet(geraete_id)
        kinder = ((eintrag or {}).get("zustand") or {}).get("kinder")
        if not isinstance(kinder, dict) or not kinder.get("an"):
            return 0
        return alter_pruefen(kinder.get("alter"))

    def offene_zeitanfragen(self) -> list[dict]:
        offen: list[dict] = []
        with self._lock:
            for eintrag in self._data["geraete"]:
                for meldung in eintrag.get("meldungen") or []:
                    if meldung.get("art") == "zeitanfrage" and not meldung.get("quittiert"):
                        offen.append({**meldung, "geraet": eintrag.get("id"), "name": eintrag.get("name", "")})
        return offen

    async def zeitanfrage_beantworten(self, geraete_id: str, meldung_id: str, erlaubt: bool, minuten: int | None = None) -> dict:
        self._pruefen(geraete_id, "regeln")
        with self._lock:
            gefunden = None
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                for meldung in eintrag.get("meldungen") or []:
                    if meldung.get("id") == meldung_id and meldung.get("art") == "zeitanfrage":
                        gefunden = meldung
            if gefunden is None:
                raise HandyFehler("Diese Anfrage gibt es nicht mehr.")
            if gefunden.get("quittiert"):
                raise HandyFehler("Diese Anfrage ist schon beantwortet.")
            daten = dict(gefunden.get("daten") or {})
        app = str(daten.get("app") or "")
        try:
            dauer = max(5, min(240, int(minuten if minuten is not None else daten.get("minuten") or 30)))
        except (TypeError, ValueError):
            dauer = 30
        stand = None
        if erlaubt:
            stand = await self.regeln_setzen(geraete_id, {"extra": {app: dauer}})
        zugestellt = True
        try:
            await self._ausfuehren(geraete_id, "zeitantwort", {"app": app, "name": str(daten.get("name") or app), "erlaubt": bool(erlaubt), "minuten": dauer, "anfrage": meldung_id}, wartezeit=20.0)
        except HandyFehler:
            zugestellt = False
        with self._lock:
            gefunden["quittiert"] = True
            gefunden["antwort"] = {"erlaubt": bool(erlaubt), "minuten": dauer, "zeit": time.time()}
            self._sichern()
        return {"ok": True, "erlaubt": bool(erlaubt), "minuten": dauer, "bildschirmzeit": stand, "zugestellt": zugestellt}

    def meldungen_neu(self) -> list[dict]:
        with self._lock:
            neu = self._neue_meldungen
            self._neue_meldungen = []
        return neu

    def meldung_quittieren(self, geraete_id: str, meldung_id: str) -> bool:
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                for meldung in eintrag.get("meldungen") or []:
                    if meldung.get("id") == meldung_id:
                        meldung["quittiert"] = True
                        self._sichern()
                        return True
        return False

    def _pruefen(self, geraete_id: str, recht: str) -> None:
        if self._geraet(geraete_id) is None:
            raise HandyFehler("Unbekanntes Geraet.")
        if not self.recht_erlaubt(geraete_id, recht):
            raise HandyFehler(f"„{RECHTE_NAMEN.get(recht, recht)}“ ist für dieses Gerät ausgeschaltet.")
        if not self.faehig(geraete_id, recht):
            raise HandyFehler("Die App auf diesem Gerät kann das noch nicht. Bitte Jon Gerät aktualisieren.")

    async def _ausfuehren(self, geraete_id: str, op: str, daten: dict, wartezeit: float = AUFTRAG_TTL) -> dict:
        antwort = await self.auftrag(geraete_id, op, daten, wartezeit=wartezeit)
        if not antwort.get("ok"):
            raise HandyFehler(antwort.get("fehler") or "Das Gerät konnte das nicht ausführen.")
        return dict(antwort.get("daten") or {})

    async def durchsage(self, geraete_id: str, text: str, vorlesen: bool = True, von: str = "") -> dict:
        self._pruefen(geraete_id, "durchsage")
        sauber = " ".join(str(text).split())[:500]
        if not sauber:
            raise HandyFehler("Die Durchsage ist leer.")
        kennung = secrets.token_hex(5)
        absender = str(von).strip()[:40] or self.kennung().get("name") or "Jon"
        ergebnis = await self._ausfuehren(
            geraete_id,
            "durchsage",
            {"text": sauber, "vorlesen": bool(vorlesen), "von": absender, "kennung": kennung},
        )
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    liste = list(eintrag.get("durchsagen") or [])
                    liste.append({"kennung": kennung, "text": sauber, "zeit": time.time(), "gelesen": None})
                    eintrag["durchsagen"] = liste[-DURCHSAGEN_MAX:]
                    self._sichern()
                    break
        return {**ergebnis, "kennung": kennung}

    async def klingeln(self, geraete_id: str, sekunden: int = 30) -> dict:
        self._pruefen(geraete_id, "klingeln")
        try:
            dauer = int(sekunden)
        except (TypeError, ValueError):
            dauer = 30
        return await self._ausfuehren(geraete_id, "klingeln", {"sekunden": max(5, min(120, dauer))})

    def _app_kennungen(self, geraete_id: str) -> set[str]:
        bekannt = {"whatsapp", "tiktok", "amazon"}
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                zustand = eintrag.get("zustand") or {}
                apps = zustand.get("apps") or (zustand.get("bildschirmzeit") or {}).get("apps") or []
                for app in apps if isinstance(apps, list) else []:
                    kennung = str(app.get("id") or "") if isinstance(app, dict) else ""
                    if _APP_KENNUNG.fullmatch(kennung):
                        bekannt.add(kennung)
        return bekannt

    async def regeln_setzen(self, geraete_id: str, regeln: dict) -> dict:
        self._pruefen(geraete_id, "regeln")
        bekannt = self._app_kennungen(geraete_id)
        erlaubt: dict = {}
        limits = regeln.get("limits")
        if isinstance(limits, dict):
            erlaubt["limits"] = {
                str(app): max(0, min(24 * 60, int(wert)))
                for app, wert in list(limits.items())[:60]
                if str(app) in bekannt and isinstance(wert, (int, float))
            }
        nacht = regeln.get("nacht")
        if isinstance(nacht, dict):
            erlaubt["nacht"] = {
                schluessel: nacht[schluessel]
                for schluessel in ("an", "von", "bis", "tage", "apps")
                if schluessel in nacht
            }
            if isinstance(erlaubt["nacht"].get("apps"), list):
                erlaubt["nacht"]["apps"] = [str(app) for app in erlaubt["nacht"]["apps"][:60] if str(app) in bekannt]
        extra = regeln.get("extra")
        if isinstance(extra, dict):
            jetzt = time.time()
            erlaubt["ausnahmen"] = {
                str(app): int((jetzt + max(1, min(240, int(wert))) * 60) * 1000)
                for app, wert in list(extra.items())[:20]
                if str(app) in bekannt and isinstance(wert, (int, float))
            }
        if "pause_minuten" in regeln:
            try:
                erlaubt["pause_minuten"] = max(0, min(24 * 60, int(regeln["pause_minuten"])))
            except (TypeError, ValueError):
                raise HandyFehler("Die Pause braucht eine Minutenzahl.")
        if not erlaubt:
            raise HandyFehler("Keine gültigen Regeln übergeben.")
        stand = await self._ausfuehren(geraete_id, "regeln", erlaubt)
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    zustand = dict(eintrag.get("zustand") or {})
                    zustand["bildschirmzeit"] = stand
                    eintrag["zustand"] = zustand
                    self._sichern()
                    break
        return stand

    def zustand(self, geraete_id: str) -> dict:
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") == geraete_id:
                    zustand = eintrag.get("zustand")
                    return {
                        "zustand": dict(zustand) if isinstance(zustand, dict) else {},
                        "zeit": float(eintrag.get("zustand_zeit") or 0.0),
                    }
        return {"zustand": {}, "zeit": 0.0}

    def _postfach(self, geraete_id: str) -> dict | None:
        with self._lock:
            fach = self._postfaecher.get(geraete_id)
            if fach is None:
                return None
            if time.time() - fach["zeit"] > POSTFACH_TTL:
                self._postfaecher.pop(geraete_id, None)
                return None
            return fach

    async def abholen(self, geraete_id: str, anfrage: dict) -> dict:
        try:
            wartezeit = float(anfrage.get("warten", 20.0) or 20.0)
        except (TypeError, ValueError):
            wartezeit = 20.0
        wartezeit = max(1.0, min(wartezeit, ABHOL_MAX))
        with self._lock:
            fach = self._postfaecher.get(geraete_id)
            if fach is None:
                fach = {"queue": asyncio.Queue(maxsize=200), "zeit": time.time()}
                self._postfaecher[geraete_id] = fach
            else:
                fach["zeit"] = time.time()
        warteschlange: asyncio.Queue = fach["queue"]
        gesammelt: list[dict] = []
        try:
            erstes = await asyncio.wait_for(warteschlange.get(), timeout=wartezeit)
            gesammelt.append(erstes)
        except asyncio.TimeoutError:
            pass
        while len(gesammelt) < 20:
            try:
                gesammelt.append(warteschlange.get_nowait())
            except asyncio.QueueEmpty:
                break
        with self._lock:
            fach["zeit"] = time.time()
        return {"ok": True, "ereignisse": gesammelt}

    def melden_an(self, geraete_id: str, art: str, daten: dict) -> bool:
        ereignis = {"art": art, "zeit": time.time(), "daten": daten}
        zugestellt = False
        fach = self._postfach(geraete_id)
        if fach is not None:
            try:
                fach["queue"].put_nowait(ereignis)
                zugestellt = True
            except asyncio.QueueFull:
                pass
        with self._lock:
            listen = list(self._warteschlangen.get(geraete_id) or [])
        for warteschlange in listen:
            try:
                warteschlange.put_nowait(ereignis)
                zugestellt = True
            except asyncio.QueueFull:
                continue
        return zugestellt

    async def auftrag(
        self,
        geraete_id: str,
        op: str,
        daten: dict | None = None,
        wartezeit: float = AUFTRAG_TTL,
    ) -> dict:
        if self._geraet(geraete_id) is None:
            raise HandyFehler("Unbekanntes Geraet.")
        kennung = secrets.token_hex(8)
        schleife = asyncio.get_running_loop()
        zukunft: asyncio.Future = schleife.create_future()
        with self._lock:
            self._auftraege[kennung] = (geraete_id, zukunft)
        nutzlast = {"auftrag": kennung, "op": op}
        nutzlast.update(daten or {})
        try:
            if not self.melden_an(geraete_id, "auftrag", nutzlast):
                raise HandyFehler("Das Handy ist gerade offline.")
            try:
                return await asyncio.wait_for(zukunft, timeout=wartezeit)
            except asyncio.TimeoutError as exc:
                raise HandyFehler("Das Handy hat nicht rechtzeitig geantwortet.") from exc
        finally:
            with self._lock:
                self._auftraege.pop(kennung, None)

    def antwort_annehmen(self, geraete_id: str, anfrage: dict) -> dict:
        kennung = str(anfrage.get("auftrag", ""))
        with self._lock:
            eintrag = self._auftraege.get(kennung)
        if eintrag is None or eintrag[0] != geraete_id:
            return {"ok": False, "fehler": "Auftrag unbekannt."}
        zukunft = eintrag[1]
        if zukunft.done():
            return {"ok": False, "fehler": "Auftrag unbekannt."}
        daten = anfrage.get("daten")
        zukunft.set_result(
            {
                "ok": bool(anfrage.get("ok")),
                "daten": daten if isinstance(daten, dict) else {},
                "fehler": str(anfrage.get("fehler", "")),
                "geraet": geraete_id,
            }
        )
        return {"ok": True}

    def _ausgang_aufraeumen(self) -> None:
        jetzt = time.time()
        alt = [
            kennung
            for kennung, eintrag in self._ausgang.items()
            if jetzt - eintrag["start"] > AUSGANG_TTL
        ]
        for kennung in alt:
            self._ausgang.pop(kennung, None)

    def datei_bereitstellen(self, geraete_id: str, pfad: str) -> dict:
        ziel = Path(pfad).expanduser()
        if not ziel.is_file():
            raise HandyFehler(f"Diese Datei gibt es nicht: {pfad}")
        groesse = ziel.stat().st_size
        if groesse <= 0:
            raise HandyFehler("Die Datei ist leer.")
        if groesse > DATEI_MAX:
            raise HandyFehler("Die Datei ist zu gross fuer die Uebertragung.")
        kennung = secrets.token_hex(8)
        teile = (groesse + TEIL_MAX - 1) // TEIL_MAX
        with self._lock:
            self._ausgang_aufraeumen()
            self._ausgang[kennung] = {
                "geraet": geraete_id,
                "pfad": str(ziel),
                "name": ziel.name,
                "groesse": groesse,
                "teile": teile,
                "start": time.time(),
            }
        return {
            "marke": kennung,
            "name": ziel.name,
            "groesse": groesse,
            "teile": teile,
            "teilgroesse": TEIL_MAX,
        }

    def datei_holen(self, geraete_id: str, anfrage: dict) -> dict:
        kennung = str(anfrage.get("marke", ""))
        try:
            nummer = int(anfrage.get("nr", -1))
        except (TypeError, ValueError):
            return {"ok": False, "fehler": "Ungueltige Teilnummer."}
        with self._lock:
            eintrag = self._ausgang.get(kennung)
            if eintrag is None or eintrag["geraet"] != geraete_id:
                return {"ok": False, "fehler": "Diese Datei steht nicht bereit."}
            if nummer < 0 or nummer >= eintrag["teile"]:
                return {"ok": False, "fehler": "Teil gibt es nicht."}
            pfad = eintrag["pfad"]
            teile = eintrag["teile"]
            name = eintrag["name"]
            groesse = eintrag["groesse"]
        try:
            with open(pfad, "rb") as datei:
                datei.seek(nummer * TEIL_MAX)
                block = datei.read(TEIL_MAX)
        except OSError as exc:
            return {"ok": False, "fehler": f"Datei nicht lesbar: {exc}"}
        return {
            "ok": True,
            "nr": nummer,
            "teile": teile,
            "name": name,
            "groesse": groesse,
            "daten": _b64(block),
        }


_service: HandyService | None = None


VERLAUF_TAGE = 42


def _zahl(wert: object) -> int | None:
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        return None
    return int(wert)


def verlauf_merken(eintrag: dict, zustand: dict) -> None:
    zeit = zustand.get("bildschirmzeit") if isinstance(zustand.get("bildschirmzeit"), dict) else {}
    tag = str(zeit.get("tag") or date.today().isoformat())
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", tag):
        return
    genutzt = {}
    for app, wert in (zeit.get("genutzt") or {}).items():
        minuten = _zahl(wert)
        if minuten is not None and 0 <= minuten <= 1440 and re.match(r"^[A-Za-z][A-Za-z0-9_.]{0,120}$", str(app)):
            genutzt[str(app)] = minuten
    namen = {
        str(a.get("id")): str(a.get("name") or a.get("id"))[:40]
        for a in (zeit.get("apps") or [])
        if isinstance(a, dict) and a.get("id")
    }
    schritte = zustand.get("schritte")
    schritte = _zahl(schritte.get("heute") if isinstance(schritte, dict) else schritte) or 0
    verlauf = dict(eintrag.get("verlauf") or {})
    alt = dict(verlauf.get(tag) or {})
    vorher = dict(alt.get("genutzt") or {})
    for app, minuten in genutzt.items():
        vorher[app] = max(int(vorher.get(app) or 0), minuten)
    verlauf[tag] = {
        "genutzt": vorher,
        "namen": {**dict(alt.get("namen") or {}), **namen},
        "schritte": max(int(alt.get("schritte") or 0), max(0, schritte)),
    }
    for alt_tag in sorted(verlauf)[:-VERLAUF_TAGE]:
        verlauf.pop(alt_tag, None)
    eintrag["verlauf"] = verlauf


def bericht_bauen(eintrag: dict, bis: str = "") -> dict:
    try:
        ende = date.fromisoformat(bis) if bis else date.today()
    except ValueError:
        ende = date.today()
    verlauf = eintrag.get("verlauf") or {}
    woche = [ende - timedelta(days=i) for i in range(6, -1, -1)]
    davor = [ende - timedelta(days=i) for i in range(13, 6, -1)]
    namen: dict[str, str] = {}
    apps: dict[str, int] = {}
    tage = []
    for tag in woche:
        daten = verlauf.get(tag.isoformat()) or {}
        genutzt = {k: int(v) for k, v in (daten.get("genutzt") or {}).items()}
        namen.update(daten.get("namen") or {})
        for app, minuten in genutzt.items():
            apps[app] = apps.get(app, 0) + minuten
        tage.append({
            "tag": tag.isoformat(),
            "wochentag": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")[tag.weekday()],
            "minuten": sum(genutzt.values()),
            "schritte": int(daten.get("schritte") or 0),
            "erfasst": tag.isoformat() in verlauf,
        })
    gesamt = sum(t["minuten"] for t in tage)
    vorwoche = sum(sum(int(v) for v in ((verlauf.get(t.isoformat()) or {}).get("genutzt") or {}).values()) for t in davor)
    erfasst = [t for t in tage if t["erfasst"]]
    beginn = datetime.combine(woche[0], datetime.min.time()).timestamp()
    schluss = datetime.combine(ende + timedelta(days=1), datetime.min.time()).timestamp()
    meldungen = [m for m in eintrag.get("meldungen") or [] if beginn <= float(m.get("zeit") or 0) < schluss]
    anfragen = [m for m in meldungen if m.get("art") == "zeitanfrage"]
    return {
        "geraet": eintrag.get("id"),
        "name": str(eintrag.get("name") or "Handy"),
        "von": woche[0].isoformat(),
        "bis": ende.isoformat(),
        "tage": tage,
        "gesamt": gesamt,
        "schnitt": round(gesamt / len(erfasst)) if erfasst else 0,
        "vorwoche": vorwoche,
        "apps": [
            {"id": app, "name": namen.get(app) or app, "minuten": minuten}
            for app, minuten in sorted(apps.items(), key=lambda paar: -paar[1])
            if minuten > 0
        ][:6],
        "schritte": sum(t["schritte"] for t in tage),
        "anfragen": len(anfragen),
        "erlaubt": sum(1 for m in anfragen if (m.get("antwort") or {}).get("erlaubt")),
        "sos": sum(1 for m in meldungen if m.get("art") == "sos"),
    }


def dauer_text(minuten: int) -> str:
    stunden, rest = divmod(max(0, int(minuten)), 60)
    if stunden and rest:
        return f"{stunden} h {rest} min"
    return f"{stunden} h" if stunden else f"{rest} min"


def bericht_text(bericht: dict) -> str:
    von = date.fromisoformat(bericht["von"])
    bis = date.fromisoformat(bericht["bis"])
    zeilen = [f"📊 Wochenbericht für {bericht['name']} ({von.day}.{von.month}. – {bis.day}.{bis.month}.)"]
    zeile = f"Bildschirmzeit: {dauer_text(bericht['gesamt'])}"
    if bericht["schnitt"]:
        zeile += f" (Ø {dauer_text(bericht['schnitt'])} am Tag"
        if bericht["vorwoche"]:
            aenderung = round((bericht["gesamt"] - bericht["vorwoche"]) * 100 / bericht["vorwoche"])
            zeile += f", {'+' if aenderung > 0 else '−' if aenderung < 0 else '±'}{abs(aenderung)} % zur Vorwoche"
        zeile += ")"
    zeilen.append(zeile)
    if bericht["apps"]:
        zeilen.append("Am meisten: " + " · ".join(f"{a['name']} {dauer_text(a['minuten'])}" for a in bericht["apps"][:3]))
    if bericht["schritte"]:
        zeilen.append(f"Schritte: {bericht['schritte']:,}".replace(",", ".") + f" (Ø {round(bericht['schritte'] / 7):,} am Tag)".replace(",", "."))
    if bericht["anfragen"]:
        zeilen.append(f"Extra-Zeit: {bericht['anfragen']} Anfrage{'n' if bericht['anfragen'] != 1 else ''}, {bericht['erlaubt']} erlaubt")
    if bericht["sos"]:
        zeilen.append(f"SOS ausgelöst: {bericht['sos']}×")
    return chr(10).join(zeilen)


def zeitanfrage_text(name: str, daten: dict, kennung: str) -> str:
    app = str(daten.get("name") or daten.get("app") or "eine App")
    minuten = daten.get("minuten") or 30
    zeilen = [f"⏳ {name} möchte {minuten} Minuten mehr {app}."]
    notiz = str(daten.get("text") or "").strip()
    if notiz:
        zeilen.append(f"„{notiz}“")
    kurz = kennung[:4]
    zeilen.append(f"Antworte /ja {kurz} oder /nein {kurz} – oder in Jon unter Einstellungen → Geräte.")
    return chr(10).join(zeilen)


def sos_karte(daten: dict) -> str:
    breite, laenge = daten.get("lat"), daten.get("lon")
    if isinstance(breite, bool) or isinstance(laenge, bool):
        return ""
    if not isinstance(breite, (int, float)) or not isinstance(laenge, (int, float)):
        return ""
    if not (-90 <= breite <= 90 and -180 <= laenge <= 180):
        return ""
    return f"https://www.openstreetmap.org/?mlat={breite:.5f}&mlon={laenge:.5f}#map=17/{breite:.5f}/{laenge:.5f}"


def sos_text(name: str, daten: dict) -> str:
    zeilen = [f"🆘 SOS von {name}!"]
    zeitpunkt = daten.get("zeit")
    if isinstance(zeitpunkt, (int, float)) and zeitpunkt > 0:
        zeilen.append("Ausgelöst um " + time.strftime("%H:%M Uhr", time.localtime(float(zeitpunkt) / 1000)))
    akku = daten.get("akku")
    if isinstance(akku, (int, float)) and akku >= 0:
        zeilen.append(f"Akku: {int(akku)} %" + (" (lädt)" if daten.get("laedt") else ""))
    notiz = str(daten.get("text") or "").strip()
    if notiz:
        zeilen.append(f"Nachricht: {notiz}")
    karte = sos_karte(daten)
    if karte:
        genau = daten.get("genau")
        zeilen.append("Standort: " + karte + (f" (± {int(genau)} m)" if isinstance(genau, (int, float)) and genau > 0 else ""))
    zeilen.append("Bitte gleich melden.")
    return chr(10).join(zeilen)


async def _telegram_melden(text: str, daten: dict | None = None) -> None:
    try:
        from app.services.settings_service import get_settings_service
        from app.services.telegram_service import get_telegram_service

        chat = str(get_settings_service().get().get("telegram_chat_id", "")).strip()
        if chat:
            await get_telegram_service().send(chat, text)
            if sos_karte(daten or {}):
                await get_telegram_service().send_location(chat, {"lat": float(daten["lat"]), "lon": float(daten["lon"]), "titel": "SOS-Standort"})
    except Exception as exc:
        _log.warning("SOS ging nicht an Telegram: %s", exc)


def get_handy_service() -> HandyService:
    global _service
    if _service is None:
        _service = HandyService()
    return _service
