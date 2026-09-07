from __future__ import annotations

import asyncio
import base64
import json
import secrets
import socket
import threading
import time
from pathlib import Path
from typing import Any, AsyncIterator

from app.core.config import DATA_DIR
from app.core.logbook import logger as logbook_logger
from app.core.store import atomic_write_json, read_json

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
    "status": True,
    "dateien": True,
    "hinweise": False,
    "zwischenablage": False,
    "standort": False,
    "kontakte": False,
    "kamera": False,
    "mikrofon": False,
}

RECHTE_STUFEN = {
    "status": "standard",
    "dateien": "standard",
    "hinweise": "persoenlich",
    "zwischenablage": "persoenlich",
    "standort": "persoenlich",
    "kontakte": "persoenlich",
    "kamera": "sensibel",
    "mikrofon": "sensibel",
}

RECHTE_NAMEN = {
    "status": "Gerätestatus",
    "dateien": "Dateien",
    "hinweise": "Benachrichtigungen",
    "zwischenablage": "Zwischenablage",
    "standort": "Standort",
    "kontakte": "Kontakte",
    "kamera": "Kamera",
    "mikrofon": "Mikrofon",
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
        self._auftraege: dict[str, asyncio.Future] = {}
        self._postfaecher: dict[str, dict] = {}
        self._ausgang: dict[str, dict] = {}

    def _laden(self) -> dict:
        roh = read_json(STORE, None)
        if not isinstance(roh, dict):
            roh = {}
        geraete = roh.get("geraete")
        if not isinstance(geraete, list):
            geraete = []
        pc_id = str(roh.get("pc_id", "")).strip()
        if not pc_id:
            pc_id = secrets.token_hex(6)
        return {"pc_id": pc_id, "geraete": geraete}

    def _sichern(self) -> None:
        atomic_write_json(STORE, self._data)

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
        if not settings.jon_lan:
            return []
        return [f"http://{host}:{settings.port}" for host in lan_adressen()]

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

    def kopplung_starten(self) -> dict:
        code = code_erzeugen()
        kennung = self.kennung()
        makler = self._makler()
        adressen = self._adressen()
        adresse = adressen[0] if adressen else ""
        sitzung = {
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
            if sitzung is None:
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
                "rechte": dict(RECHTE_VORGABE),
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
            "erstellt": eintrag.get("erstellt", 0),
            "gesehen": eintrag.get("gesehen", 0),
            "online": self.online(kennung),
            "rechte": self.rechte(kennung),
            "stufen": dict(RECHTE_STUFEN),
            "namen": dict(RECHTE_NAMEN),
            "faehigkeiten": list(eintrag.get("faehigkeiten") or []),
            "zustand": dict(zustand) if isinstance(zustand, dict) else {},
            "zustand_zeit": float(eintrag.get("zustand_zeit") or 0.0),
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
        text = antwort.text
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
            async for stueck in self._chat_strom(ruf, anfrage.get("body")):
                yield stueck
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
            )
            if zustand.get(schluessel) is not None
        }
        with self._lock:
            for eintrag in self._data["geraete"]:
                if eintrag.get("id") != geraete_id:
                    continue
                eintrag["zustand"] = gekuerzt
                eintrag["zustand_zeit"] = time.time()
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
            self._auftraege[kennung] = zukunft
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
            zukunft = self._auftraege.get(kennung)
        if zukunft is None or zukunft.done():
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


def get_handy_service() -> HandyService:
    global _service
    if _service is None:
        _service = HandyService()
    return _service
