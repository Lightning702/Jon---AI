from __future__ import annotations

import asyncio
import json
import platform
import secrets
import threading
import time

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.logbook import logger as logbook_logger
from app.core.store import atomic_write_json, read_json
from app.services.handy_service import (
    _entschluesseln,
    _unb64,
    _verschluesseln,
    code_saeubern,
    schluessel_fuer_code,
    thema_fuer,
)

_log = logbook_logger("verbund")

SPEICHER = DATA_DIR / "verbund.json"
BASIS = "jon/handy/v1"
PROTOKOLL = 2
ANTWORT_TTL = 60.0
PAAR_WARTEN = 240.0
PAAR_VERSUCHE = 6


class VerbundFehler(Exception):
    pass


def _leer() -> dict:
    return {"geraete": []}


class Draht:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = int(port)
        self._client = None
        self._lock = threading.Lock()
        self._antworten: dict[str, dict] = {}
        self._ereignis: dict[str, threading.Event] = {}
        self._verbunden = False

    def verbunden(self) -> bool:
        return self._verbunden

    def verbinden(self, wartezeit: float = 12.0) -> None:
        with self._lock:
            if self._client is not None and self._verbunden:
                return
        try:
            import paho.mqtt.client as mqtt
        except Exception as fehler:
            raise VerbundFehler(
                "Fuer die Verbindung ueber das Internet fehlt paho-mqtt."
            ) from fehler
        client_id = f"jon-verbund-{secrets.token_hex(4)}"
        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                clean_session=True,
            )
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=client_id, clean_session=True)
        client.on_connect = self._auf_verbunden
        client.on_disconnect = self._auf_getrennt
        client.on_message = self._auf_nachricht
        try:
            client.connect(self.host, self.port, keepalive=30)
            client.loop_start()
        except Exception as fehler:
            raise VerbundFehler(f"Kein Zugang zum Vermittler: {fehler}") from fehler
        with self._lock:
            self._client = client
        ende = time.time() + wartezeit
        while time.time() < ende and not self._verbunden:
            time.sleep(0.1)
        if not self._verbunden:
            raise VerbundFehler("Der Vermittler antwortet nicht.")

    def trennen(self) -> None:
        with self._lock:
            client = self._client
            self._client = None
        self._verbunden = False
        if client is None:
            return
        try:
            client.loop_stop()
            client.disconnect()
        except Exception as fehler:
            leise(fehler, "services/verbund_service")

    def _auf_verbunden(self, _client, _userdata, _flags, _rc, *_args) -> None:
        self._verbunden = True

    def _auf_getrennt(self, *_args) -> None:
        self._verbunden = False

    def _auf_nachricht(self, _client, _userdata, message) -> None:
        try:
            umschlag = json.loads(message.payload.decode("utf-8", errors="replace"))
        except Exception:
            return
        if not isinstance(umschlag, dict):
            return
        kanal = str(message.topic).rsplit("/", 1)[-1]
        with self._lock:
            ereignis = self._ereignis.get(kanal)
            if ereignis is None:
                return
            self._antworten[kanal] = umschlag
        ereignis.set()

    def _aufraeumen(self, kanal: str) -> dict | None:
        with self._lock:
            self._ereignis.pop(kanal, None)
            roh = self._antworten.pop(kanal, None)
            client = self._client
        if client is not None:
            try:
                client.unsubscribe(f"{BASIS}/r/{kanal}")
            except Exception as fehler:
                leise(fehler, "services/verbund_service")
        return roh

    def frage(
        self,
        thema: str,
        art: str,
        kennung: str,
        schluessel: bytes,
        inhalt: dict,
        wartezeit: float = ANTWORT_TTL,
    ) -> dict:
        self.verbinden()
        kanal = secrets.token_hex(8)
        inhalt = {**inhalt, "rid": secrets.token_hex(6)}
        zusatz = f"{art}:{kennung}".encode("utf-8")
        umschlag = {
            "v": PROTOKOLL,
            "k": art,
            "i": kennung,
            "r": kanal,
            **_verschluesseln(schluessel, zusatz, inhalt),
        }
        ereignis = threading.Event()
        with self._lock:
            self._ereignis[kanal] = ereignis
            client = self._client
        if client is None:
            raise VerbundFehler("Keine Verbindung.")
        try:
            client.subscribe(f"{BASIS}/r/{kanal}", qos=1)
            client.publish(
                thema, json.dumps(umschlag, ensure_ascii=False), qos=1, retain=False
            )
        except Exception as fehler:
            self._aufraeumen(kanal)
            raise VerbundFehler(f"Konnte nicht senden: {fehler}") from fehler
        erreicht = ereignis.wait(wartezeit)
        roh = self._aufraeumen(kanal)
        if not erreicht:
            raise VerbundFehler("Das andere Geraet antwortet nicht.")
        if not isinstance(roh, dict):
            raise VerbundFehler("Leere Antwort.")
        if roh.get("fehler"):
            raise VerbundFehler(str(roh.get("fehler")))
        try:
            return _entschluesseln(schluessel, zusatz, roh)
        except Exception as fehler:
            raise VerbundFehler("Antwort passt nicht zum Schluessel.") from fehler


class VerbundService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten = self._laden()
        self._draehte: dict[str, Draht] = {}

    def _laden(self) -> dict:
        daten = read_json(SPEICHER, _leer())
        if not isinstance(daten, dict) or "geraete" not in daten:
            return _leer()
        return daten

    def _sichern(self) -> None:
        atomic_write_json(SPEICHER, self._daten)

    def _eigener_name(self) -> str:
        from app.services.handy_service import get_handy_service

        return get_handy_service().kennung().get("name", "Jon")

    def _plattform(self) -> str:
        system = platform.system()
        if system == "Windows":
            return "Windows-PC"
        maschine = platform.machine().lower()
        if "arm" in maschine or "aarch" in maschine:
            return "Raspberry Pi"
        return system or "Jon"

    def _draht(self, host: str, port: int) -> Draht:
        schluessel = f"{host}:{port}"
        with self._lock:
            draht = self._draehte.get(schluessel)
            if draht is None:
                draht = Draht(host, port)
                self._draehte[schluessel] = draht
        return draht

    def geraete(self) -> list[dict]:
        with self._lock:
            return [self._sicht(g) for g in self._daten["geraete"]]

    def _sicht(self, eintrag: dict) -> dict:
        return {
            "id": str(eintrag.get("id", "")),
            "name": str(eintrag.get("name", "")),
            "plattform": str(eintrag.get("plattform", "")),
            "version": str(eintrag.get("version", "")),
            "adressen": list(eintrag.get("adressen", [])),
            "erstellt": float(eintrag.get("erstellt", 0.0)),
            "gesehen": float(eintrag.get("gesehen", 0.0)),
            "weg": str(eintrag.get("weg", "")),
        }

    def _eintrag(self, geraet_id: str) -> dict:
        with self._lock:
            for g in self._daten["geraete"]:
                if str(g.get("id")) == str(geraet_id):
                    return g
        raise VerbundFehler("Dieses Geraet kenne ich nicht.")

    def finden(self, name_oder_id: str) -> dict:
        gesucht = str(name_oder_id or "").strip().lower()
        if not gesucht:
            raise VerbundFehler("Welches Geraet denn?")
        with self._lock:
            geraete = list(self._daten["geraete"])
        for g in geraete:
            if str(g.get("id", "")).lower() == gesucht:
                return g
        for g in geraete:
            if str(g.get("name", "")).lower() == gesucht:
                return g
        for g in geraete:
            if gesucht in str(g.get("name", "")).lower():
                return g
        for g in geraete:
            if gesucht in str(g.get("plattform", "")).lower():
                return g
        raise VerbundFehler(f"Kein Geraet gefunden, das zu '{name_oder_id}' passt.")

    def entfernen(self, geraet_id: str) -> bool:
        with self._lock:
            vorher = len(self._daten["geraete"])
            self._daten["geraete"] = [
                g for g in self._daten["geraete"] if str(g.get("id")) != str(geraet_id)
            ]
            geaendert = len(self._daten["geraete"]) != vorher
            if geaendert:
                self._sichern()
        return geaendert

    def koppeln(self, code: str, makler: dict | None = None) -> dict:
        sauber = code_saeubern(str(code or ""))
        if len(sauber) < 8:
            raise VerbundFehler("Der Code sieht nicht vollstaendig aus.")
        host = str((makler or {}).get("host", "") or "broker.hivemq.com")
        port = int((makler or {}).get("port", 1883) or 1883)
        draht = self._draht(host, port)
        thema = f"{BASIS}/code/{thema_fuer(sauber)}"
        schluessel = schluessel_fuer_code(sauber)
        kennung = thema_fuer(sauber)
        antwort: dict = {}
        letzter = ""
        for versuch in range(PAAR_VERSUCHE):
            try:
                antwort = draht.frage(
                    thema,
                    "pair",
                    kennung,
                    schluessel,
                    {
                        "op": "pair",
                        "name": self._eigener_name(),
                        "plattform": self._plattform(),
                    },
                    wartezeit=12.0,
                )
                break
            except VerbundFehler as fehler:
                letzter = str(fehler)
                if versuch == PAAR_VERSUCHE - 1:
                    raise VerbundFehler(
                        "Das andere Geraet meldet sich nicht. Stimmt der Code, und "
                        "ist die Kopplung dort noch offen?"
                    ) from fehler
                time.sleep(3.0)
        if not antwort.get("ok"):
            raise VerbundFehler(
                str(antwort.get("fehler") or letzter or "Kopplung abgelehnt.")
            )
        ende = time.time() + PAAR_WARTEN
        ergebnis: dict = {}
        while time.time() < ende:
            time.sleep(2.0)
            stand = draht.frage(
                thema,
                "pair",
                kennung,
                schluessel,
                {"op": "pair-status"},
                wartezeit=25.0,
            )
            if not stand.get("ok"):
                raise VerbundFehler(str(stand.get("fehler") or "Kopplung abgebrochen."))
            if stand.get("geraet") and stand.get("schluessel"):
                ergebnis = stand
                break
        if not ergebnis:
            raise VerbundFehler(
                "Am anderen Geraet wurde die Anfrage nicht bestaetigt."
            )
        pc = ergebnis.get("pc") or {}
        broker = ergebnis.get("broker") or {"host": host, "port": port}
        eintrag = {
            "id": secrets.token_hex(6),
            "name": str(pc.get("name") or "Jon"),
            "version": str(pc.get("version") or ""),
            "pc_id": str(pc.get("id") or ""),
            "geraete_id": str(ergebnis.get("geraet") or ""),
            "schluessel": str(ergebnis.get("schluessel") or ""),
            "token": str(ergebnis.get("token") or ""),
            "adressen": [
                str(a) for a in (ergebnis.get("adressen") or []) if str(a).strip()
            ],
            "broker": {"host": str(broker.get("host")), "port": int(broker.get("port"))},
            "plattform": "",
            "erstellt": time.time(),
            "gesehen": time.time(),
            "weg": "",
        }
        with self._lock:
            self._daten["geraete"] = [
                g
                for g in self._daten["geraete"]
                if str(g.get("pc_id")) != eintrag["pc_id"]
            ] + [eintrag]
            self._sichern()
        _log.info("Geraet im Verbund: %s", eintrag["name"])
        return self._sicht(eintrag)

    async def rufen(
        self,
        geraet_id: str,
        methode: str = "GET",
        pfad: str = "/api/health",
        rumpf: dict | None = None,
        query: dict | None = None,
        wartezeit: float = 60.0,
    ) -> dict:
        eintrag = self._eintrag(geraet_id)
        direkt = await self._direkt(eintrag, methode, pfad, rumpf, query)
        if direkt is not None:
            self._merken(eintrag, "heimnetz")
            return direkt
        antwort = await asyncio.to_thread(
            self._ueber_relais, eintrag, methode, pfad, rumpf, query, wartezeit
        )
        self._merken(eintrag, "internet")
        return antwort

    def _merken(self, eintrag: dict, weg: str) -> None:
        with self._lock:
            eintrag["gesehen"] = time.time()
            eintrag["weg"] = weg
            self._sichern()

    async def _direkt(
        self,
        eintrag: dict,
        methode: str,
        pfad: str,
        rumpf: dict | None,
        query: dict | None,
    ) -> dict | None:
        adressen = [a for a in eintrag.get("adressen", []) if a]
        if not adressen:
            return None
        import httpx

        kopf = {"X-Jon-Token": str(eintrag.get("token", ""))}
        for basis in adressen[:3]:
            ziel = basis.rstrip("/") + (pfad if pfad.startswith("/") else "/" + pfad)
            try:
                async with httpx.AsyncClient(timeout=6.0) as klient:
                    antwort = await klient.request(
                        methode.upper(),
                        ziel,
                        params=query or None,
                        json=rumpf if isinstance(rumpf, (dict, list)) else None,
                        headers=kopf,
                    )
            except Exception:
                continue
            return {
                "ok": antwort.status_code < 400,
                "code": antwort.status_code,
                "text": antwort.text,
            }
        return None

    def _ueber_relais(
        self,
        eintrag: dict,
        methode: str,
        pfad: str,
        rumpf: dict | None,
        query: dict | None,
        wartezeit: float,
    ) -> dict:
        broker = eintrag.get("broker") or {}
        draht = self._draht(
            str(broker.get("host") or "broker.hivemq.com"),
            int(broker.get("port") or 1883),
        )
        thema = f"{BASIS}/pc/{eintrag.get('pc_id')}"
        schluessel = _unb64(str(eintrag.get("schluessel", "")))
        inhalt = {
            "op": "call",
            "method": methode.upper(),
            "path": pfad,
        }
        if isinstance(rumpf, (dict, list)):
            inhalt["body"] = rumpf
        if query:
            inhalt["query"] = query
        antwort = draht.frage(
            thema,
            "dev",
            str(eintrag.get("geraete_id", "")),
            schluessel,
            inhalt,
            wartezeit=wartezeit,
        )
        if not antwort.get("ok") and antwort.get("fehler"):
            raise VerbundFehler(str(antwort.get("fehler")))
        return {
            "ok": bool(antwort.get("ok")),
            "code": int(antwort.get("code", 0) or 0),
            "text": str(antwort.get("text", "")),
        }

    async def pruefen(self, geraet_id: str) -> dict:
        eintrag = self._eintrag(geraet_id)
        try:
            antwort = await self.rufen(geraet_id, "GET", "/api/health", wartezeit=25.0)
        except VerbundFehler as fehler:
            return {**self._sicht(eintrag), "erreichbar": False, "grund": str(fehler)}
        daten: dict = {}
        try:
            daten = json.loads(antwort.get("text") or "{}")
        except Exception:
            daten = {}
        if daten.get("version"):
            with self._lock:
                eintrag["version"] = str(daten["version"])
                self._sichern()
        return {
            **self._sicht(eintrag),
            "erreichbar": bool(antwort.get("ok")),
            "version": str(daten.get("version") or eintrag.get("version") or ""),
        }

    async def stand(self) -> dict:
        geraete = self.geraete()
        ergebnis = []
        for g in geraete:
            ergebnis.append(await self.pruefen(g["id"]))
        return {"geraete": ergebnis}

    async def fragen(self, geraet_id: str, frage: str) -> str:
        antwort = await self.rufen(
            geraet_id,
            "POST",
            "/api/chat",
            {"messages": [{"role": "user", "content": frage}], "stream": False},
            wartezeit=180.0,
        )
        try:
            daten = json.loads(antwort.get("text") or "{}")
        except Exception:
            return str(antwort.get("text") or "")
        inhalt = daten.get("content") or daten.get("message") or ""
        if isinstance(inhalt, dict):
            inhalt = inhalt.get("content", "")
        return str(inhalt or antwort.get("text") or "")

    async def bildschirm(self, geraet_id: str, welcher: str = "alle") -> bytes:
        import base64

        antwort = await self.rufen(
            geraet_id,
            "GET",
            "/api/live/bild64",
            query={"welcher": welcher, "breite": "1100", "qualitaet": "55"},
            wartezeit=45.0,
        )
        if not antwort.get("ok"):
            raise VerbundFehler("Das Geraet hat kein Bild geschickt.")
        try:
            daten = json.loads(antwort.get("text") or "{}")
        except Exception as fehler:
            raise VerbundFehler("Das Bild kam beschaedigt an.") from fehler
        if daten.get("fehler"):
            raise VerbundFehler(str(daten["fehler"]))
        try:
            return base64.b64decode(str(daten.get("bild", "")))
        except Exception as fehler:
            raise VerbundFehler("Das Bild kam beschaedigt an.") from fehler


_dienst: VerbundService | None = None


def get_verbund_service() -> VerbundService:
    global _dienst
    if _dienst is None:
        _dienst = VerbundService()
    return _dienst
