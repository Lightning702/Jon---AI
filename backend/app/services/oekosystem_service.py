from __future__ import annotations

import asyncio
import json
import math
import threading
import time
import unicodedata
from typing import Any

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.logbook import logger as logbook_logger
from app.core.store import atomic_write_text

_log = logbook_logger("oekosystem")

SPEICHER = DATA_DIR / "oekosystem.json"
AKTIV_TTL = 1200.0
STANDORT_FRISCH = 600.0
VERBUND_TTL = 45.0
GEDAECHTNIS_TAKT = 600.0
TAKT = 15.0
ZUHAUSE_M = 150.0
TYP_RANG = {"handy": 0, "uhr": 1, "tablet": 2, "pc": 3}
TYP_NAMEN = {"handy": "Handy", "uhr": "Uhr", "tablet": "Tablet", "pc": "Computer"}


class OekoFehler(Exception):
    pass


def einfach(text: object) -> str:
    roh = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join("".join(z if z.isalnum() else " " for z in roh).split())


def name_passt(gesucht: str, *kandidaten: object) -> int:
    ziel = einfach(gesucht)
    if not ziel:
        return 0
    besten = 0
    for kandidat in kandidaten:
        text = einfach(kandidat)
        if not text:
            continue
        if text == ziel:
            return 3
        woerter = text.split()
        if ziel in woerter or all(teil in woerter for teil in ziel.split()):
            besten = max(besten, 2)
        elif ziel in text or (len(ziel) >= 4 and any(wort.startswith(ziel) for wort in woerter)):
            besten = max(besten, 1)
    return besten


def abstand_m(a: dict, b: dict) -> float:
    breite = math.radians((float(a["lat"]) + float(b["lat"])) / 2)
    dx = (float(a["lon"]) - float(b["lon"])) * 111320 * math.cos(breite)
    dy = (float(a["lat"]) - float(b["lat"])) * 110540
    return math.hypot(dx, dy)


def wann_text(sekunden: float) -> str:
    if sekunden < 90:
        return "gerade eben"
    if sekunden < 3600:
        return f"vor {int(sekunden // 60)} Minuten"
    if sekunden < 86400:
        stunden = int(sekunden // 3600)
        return "vor 1 Stunde" if stunden == 1 else f"vor {stunden} Stunden"
    return time.strftime("am %d.%m. um %H:%M", time.localtime(time.time() - sekunden))


def osm_link(lat: float, lon: float) -> str:
    return f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lon:.5f}#map=17/{lat:.5f}/{lon:.5f}"


class Oekosystem:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten = self._laden()
        self._aktiv = dict(self._daten.get("aktiv") or {})
        self._verbund_orte: dict[str, tuple[float, list[dict]]] = {}
        self._gedaechtnis_zuletzt = 0.0
        self._nachholen: dict[str, list[dict]] = {"erinnerungen": [], "termine": []}
        self._speicher = None

    def _laden(self) -> dict:
        try:
            roh = json.loads(SPEICHER.read_text(encoding="utf-8"))
            if isinstance(roh, dict):
                return roh
        except FileNotFoundError:
            pass
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")
        return {}

    def _sichern(self) -> None:
        try:
            atomic_write_text(SPEICHER, json.dumps(self._daten, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")

    def _handy(self):
        from app.services.handy_service import get_handy_service

        return get_handy_service()

    def _verbund(self):
        from app.services.verbund_service import get_verbund_service

        return get_verbund_service()

    def eigener_name(self) -> str:
        return self._handy().kennung().get("name") or "Jon"

    def eigene_plattform(self) -> str:
        return self._verbund()._plattform()

    def aktiv_merken(self, quelle: str) -> None:
        kennung = str(quelle or "pc")
        jetzt = time.time()
        with self._lock:
            gleich = self._aktiv.get("id") == kennung
            self._aktiv = {"id": kennung, "zeit": jetzt}
            if not gleich:
                self._daten["aktiv"] = dict(self._aktiv)
                self._sichern()

    def aktiv(self) -> dict:
        with self._lock:
            stand = dict(self._aktiv)
        kennung = str(stand.get("id") or "pc")
        alter = time.time() - float(stand.get("zeit") or 0)
        pc = {"id": "pc", "typ": "pc", "name": self.eigener_name(), "alter_s": round(alter)}
        if kennung == "pc" or alter > AKTIV_TTL:
            return pc
        for geraet in self._handy().geraete():
            if geraet["id"] == kennung:
                return {"id": kennung, "typ": geraet.get("typ", "handy"), "name": geraet.get("name", ""), "besitzer": geraet.get("besitzer", ""), "alter_s": round(alter)}
        return pc

    def unterwegs(self) -> dict | None:
        stand = self.aktiv()
        return stand if stand["id"] != "pc" and stand.get("typ") in ("handy", "uhr", "tablet") else None

    def nachholen(self, art: str) -> list[dict]:
        with self._lock:
            liste = self._nachholen.get(art) or []
            self._nachholen[art] = []
        return liste

    async def benachrichtigen(self, text: str, von: str = "Jon") -> bool:
        ziel = self.unterwegs()
        if ziel is None:
            return False
        from app.services.handy_service import HandyFehler

        try:
            await self._handy().durchsage(ziel["id"], text, True, von)
            return True
        except HandyFehler as fehler:
            _log.info("Hinweis ging nicht an %s: %s", ziel.get("name"), fehler)
            return False

    async def schleife(self) -> None:
        while True:
            try:
                await self._takt()
            except asyncio.CancelledError:
                raise
            except Exception as fehler:
                leise(fehler, "services/oekosystem_service")
            await asyncio.sleep(TAKT)

    async def _takt(self) -> None:
        if self.unterwegs() is not None:
            from app.services.calendar_service import get_calendar_service
            from app.services.reminder_service import get_reminder_service

            for erinnerung in get_reminder_service().due():
                if not await self.benachrichtigen(f"Erinnerung: {erinnerung.get('text', '')}"):
                    with self._lock:
                        self._nachholen["erinnerungen"].append(erinnerung)
            for termin in get_calendar_service().due():
                uhrzeit = f" um {termin.get('time')}" if termin.get("time") else ""
                if not await self.benachrichtigen(f"Termin{uhrzeit}: {termin.get('title', '')}"):
                    with self._lock:
                        self._nachholen["termine"].append(termin)
        if time.time() - self._gedaechtnis_zuletzt > GEDAECHTNIS_TAKT:
            self._gedaechtnis_zuletzt = time.time()
            if self._verbund().geraete():
                await self.gedaechtnis_abgleichen()

    def _ich(self) -> dict:
        from app.services.geraet_service import uebersicht

        try:
            system = uebersicht()
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")
            system = {}
        return {
            "id": "ich",
            "name": self.eigener_name(),
            "typ": "pc",
            "plattform": self.eigene_plattform(),
            "online": True,
            "version": system.get("version", ""),
            "cpu": system.get("cpu"),
            "ram": (system.get("ram") or {}).get("prozent") if isinstance(system.get("ram"), dict) else None,
            "laufzeit": system.get("laufzeit"),
        }

    def _geraet_karte(self, geraet: dict) -> dict:
        zustand = geraet.get("zustand") or {}
        ort = geraet.get("standort")
        return {
            "id": geraet["id"],
            "name": geraet.get("name", ""),
            "typ": geraet.get("typ", "handy"),
            "besitzer": geraet.get("besitzer", ""),
            "plattform": geraet.get("plattform", ""),
            "online": bool(geraet.get("online")),
            "akku": zustand.get("akku"),
            "laedt": bool(zustand.get("laedt")),
            "netz": zustand.get("netz"),
            "version": zustand.get("version"),
            "gesehen": geraet.get("gesehen", 0),
            "ueber": geraet.get("ueber", ""),
            "rechte": geraet.get("rechte") or {},
            "faehigkeiten": geraet.get("faehigkeiten") or [],
            "standort": ort,
            "standort_teilen": bool(geraet.get("standort_teilen")),
        }

    async def uebersicht(self, verbund_pruefen: bool = False) -> dict:
        geraete = [self._geraet_karte(g) for g in self._handy().geraete()]
        verbund = []
        for eintrag in self._verbund().geraete():
            daten = {**eintrag, "typ": "pc", "online": time.time() - float(eintrag.get("gesehen") or 0) < 180}
            verbund.append(daten)
        if verbund_pruefen and verbund:
            ergebnisse = await asyncio.gather(*(self._verbund().pruefen(v["id"]) for v in verbund), return_exceptions=True)
            for daten, ergebnis in zip(verbund, ergebnisse):
                if isinstance(ergebnis, dict):
                    daten["online"] = bool(ergebnis.get("erreichbar"))
                    daten["version"] = ergebnis.get("version") or daten.get("version", "")
        return {"ich": self._ich(), "geraete": geraete, "verbund": verbund, "aktiv": self.aktiv()}

    def lokale_standorte(self) -> list[dict]:
        jetzt = time.time()
        orte = []
        for geraet in self._handy().geraete():
            ort = geraet.get("standort")
            if not isinstance(ort, dict):
                continue
            alter = max(0.0, jetzt - float(ort.get("zeit") or jetzt))
            zustand = geraet.get("zustand") or {}
            orte.append({
                "id": geraet["id"],
                "name": geraet.get("name", ""),
                "besitzer": geraet.get("besitzer", ""),
                "typ": geraet.get("typ", "handy"),
                "lat": ort["lat"],
                "lon": ort["lon"],
                "genau": ort.get("genau"),
                "zeit": ort.get("zeit"),
                "alter_s": round(alter),
                "frisch": alter < STANDORT_FRISCH,
                "online": bool(geraet.get("online")),
                "akku": zustand.get("akku"),
                "laedt": bool(zustand.get("laedt")),
                "spur": [],
                "jon": self.eigener_name(),
                "fern": False,
            })
        return orte

    async def _verbund_standorte(self, eintrag: dict) -> list[dict]:
        kennung = str(eintrag["id"])
        with self._lock:
            zwischen = self._verbund_orte.get(kennung)
        if zwischen and time.time() - zwischen[0] < VERBUND_TTL:
            return zwischen[1]
        try:
            antwort = await asyncio.wait_for(
                self._verbund().rufen(kennung, "GET", "/api/oekosystem/standorte", query={"lokal": "1"}, wartezeit=20.0),
                timeout=25.0,
            )
            daten = json.loads(antwort.get("text") or "{}")
            orte = [
                {**ort, "id": f"{kennung}:{ort.get('id', '')}", "jon": eintrag.get("name", ""), "fern": True}
                for ort in daten.get("orte") or []
                if isinstance(ort, dict) and isinstance(ort.get("lat"), (int, float)) and isinstance(ort.get("lon"), (int, float))
            ]
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")
            orte = zwischen[1] if zwischen else []
        with self._lock:
            self._verbund_orte[kennung] = (time.time(), orte)
        return orte

    async def standorte(self, nur_lokal: bool = False) -> dict:
        orte = self.lokale_standorte()
        if not nur_lokal:
            fern = await asyncio.gather(*(self._verbund_standorte(v) for v in self._verbund().geraete()), return_exceptions=True)
            for liste in fern:
                if isinstance(liste, list):
                    orte.extend(liste)
        zuhause = None
        try:
            from app.services.maps.service import get_maps_service

            heim = await asyncio.wait_for(get_maps_service().home_details(), timeout=6.0)
            if isinstance(heim, dict) and isinstance(heim.get("lat"), (int, float)) and heim.get("quelle") not in ("", "voreinstellung", "ip", None):
                zuhause = {"lat": heim["lat"], "lon": heim["lon"], "name": heim.get("name") or "Zuhause"}
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")
        if zuhause:
            for ort in orte:
                ort["zuhause"] = abstand_m(ort, zuhause) <= max(ZUHAUSE_M, float(ort.get("genau") or 0))
        return {"orte": orte, "zuhause": zuhause, "jon": self.eigener_name(), "zeit": time.time()}

    def spur(self, geraete_id: str) -> list[list[float]]:
        eintrag = self._handy()._geraet(geraete_id)
        if eintrag is None or not self._handy().recht_erlaubt(geraete_id, "standort"):
            return []
        return [list(punkt) for punkt in eintrag.get("standort_spur") or []]

    async def standort_anfragen(self, geraete_id: str, fuer: str = "") -> dict:
        from app.services.handy_service import HandyFehler

        dienst = self._handy()
        if dienst._geraet(geraete_id) is None:
            raise OekoFehler("Dieses Gerät kenne ich nicht.")
        if not dienst.recht_erlaubt(geraete_id, "standort"):
            raise OekoFehler("Der Standort ist für dieses Gerät nicht freigegeben.")
        if not dienst.faehig(geraete_id, "standort"):
            raise OekoFehler("Dieses Gerät kann seinen Standort nicht senden. Bitte die Jon-App aktualisieren.")
        try:
            antwort = await dienst.auftrag(geraete_id, "ort", {"fuer": fuer or self.eigener_name()}, wartezeit=40.0)
        except HandyFehler as fehler:
            raise OekoFehler(str(fehler)) from fehler
        if not antwort.get("ok"):
            raise OekoFehler(antwort.get("fehler") or "Das Gerät hat keinen Standort geliefert.")
        ort = dienst.standort_merken(geraete_id, antwort.get("daten"))
        if ort is None:
            raise OekoFehler("Das Gerät hat keinen gültigen Standort geliefert.")
        return ort

    async def _ortsantwort(self, person: str, geraet: dict, ort: dict, live: bool) -> dict:
        adresse = ""
        try:
            from app.services.maps.service import get_maps_service

            platz = await asyncio.wait_for(get_maps_service().reverse(float(ort["lat"]), float(ort["lon"])), timeout=8.0)
            if platz is not None:
                adresse = platz.label or platz.name
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")
        alter = max(0.0, time.time() - float(ort.get("zeit") or time.time()))
        zuhause = False
        try:
            from app.services.maps.service import get_maps_service

            heim = await asyncio.wait_for(get_maps_service().home_details(), timeout=5.0)
            if isinstance(heim, dict) and isinstance(heim.get("lat"), (int, float)) and heim.get("quelle") not in ("", "voreinstellung", "ip", None):
                zuhause = abstand_m(ort, heim) <= max(ZUHAUSE_M, float(ort.get("genau") or 0))
        except Exception as fehler:
            leise(fehler, "services/oekosystem_service")
        zustand = geraet.get("zustand") or {}
        return {
            "ok": True,
            "person": person,
            "geraet": geraet.get("name", ""),
            "typ": TYP_NAMEN.get(geraet.get("typ", "handy"), "Gerät"),
            "lat": ort["lat"],
            "lon": ort["lon"],
            "genau_m": ort.get("genau"),
            "adresse": adresse,
            "zuhause": zuhause,
            "wann": wann_text(alter),
            "alter_s": round(alter),
            "live": live,
            "akku": zustand.get("akku"),
            "karte": osm_link(float(ort["lat"]), float(ort["lon"])),
            "jon": self.eigener_name(),
        }

    def _kandidaten(self, person: str) -> list[dict]:
        bewertet = []
        for geraet in self._handy().geraete():
            punkte = max(name_passt(person, geraet.get("besitzer")) * 2, name_passt(person, geraet.get("name")))
            if punkte:
                bewertet.append((punkte, TYP_RANG.get(geraet.get("typ", "handy"), 5), not geraet.get("online"), geraet))
        bewertet.sort(key=lambda eintrag: eintrag[:3])
        return [eintrag[3] for eintrag in bewertet]

    async def wo_ist(self, person: str, fragender: str = "", weiterfragen: bool = True) -> dict:
        from app.services.handy_service import HandyFehler

        gesucht = " ".join(str(person or "").split())[:40]
        if not gesucht:
            raise OekoFehler("Wen soll ich suchen?")
        dienst = self._handy()
        kandidaten = self._kandidaten(gesucht)
        gesperrt = []
        for geraet in kandidaten:
            if not dienst.recht_erlaubt(geraet["id"], "standort"):
                gesperrt.append(geraet)
                continue
            ort = None
            live = False
            if dienst.faehig(geraet["id"], "standort") and (geraet.get("online") or dienst.direkt_erreichbar(geraet["id"])):
                try:
                    antwort = await dienst.auftrag(geraet["id"], "ort", {"fuer": fragender or "Jon"}, wartezeit=40.0)
                    if antwort.get("ok"):
                        ort = dienst.standort_merken(geraet["id"], antwort.get("daten"))
                        live = ort is not None
                except HandyFehler as fehler:
                    _log.info("Live-Standort von %s nicht geholt: %s", geraet.get("name"), fehler)
            if ort is None and isinstance(geraet.get("standort"), dict):
                ort = geraet["standort"]
            if ort is not None:
                return await self._ortsantwort(gesucht, geraet, ort, live)
        if gesperrt and not any(dienst.recht_erlaubt(g["id"], "standort") for g in kandidaten):
            name = gesperrt[0].get("name") or "das Gerät"
            raise OekoFehler(
                f"Für „{name}“ von {gesucht} ist das Teilen des Standorts nicht freigegeben. "
                f"Das schaltet man in Jon unter Geräte → {name} → Standort ein."
            )
        if kandidaten:
            raise OekoFehler(
                f"Das Gerät von {gesucht} hat gerade keinen Standort geliefert. Es ist offline "
                "oder die Ortung ist am Gerät ausgeschaltet."
            )
        if weiterfragen:
            for eintrag in self._verbund().geraete():
                try:
                    antwort = await self._verbund().rufen(
                        eintrag["id"], "GET", "/api/oekosystem/wo-ist",
                        query={"person": gesucht, "fragender": fragender or self.eigener_name(), "weiter": "0"},
                        wartezeit=60.0,
                    )
                    daten = json.loads(antwort.get("text") or "{}")
                except Exception as fehler:
                    leise(fehler, "services/oekosystem_service")
                    continue
                if isinstance(daten, dict) and daten.get("ok"):
                    return {**daten, "ueber_jon": eintrag.get("name", "")}
        raise OekoFehler(
            f"Ich kenne kein Gerät von {gesucht}. Trag in der Geräte-Zentrale beim Handy "
            f"als Besitzer „{gesucht}“ ein und schalte dort den Standort frei."
        )

    def _eigentuemer_von(self, geraete_id: str) -> tuple[str, str]:
        eintrag = self._handy()._geraet(geraete_id) or {}
        return str(eintrag.get("besitzer") or ""), str(eintrag.get("ueber") or "")

    async def klingeln(self, von_geraet: str = "", ziel: str = "", sekunden: int = 30) -> dict:
        from app.services.handy_service import HandyFehler

        dienst = self._handy()
        alle = dienst.geraete()
        if ziel:
            wahl = [g for g in alle if g["id"] == ziel or name_passt(ziel, g.get("name"), g.get("besitzer"))]
        else:
            besitzer, ueber = self._eigentuemer_von(von_geraet) if von_geraet else ("", "")
            wahl = [
                g for g in alle
                if g["id"] != von_geraet and g.get("typ", "handy") in ("handy", "tablet")
                and (g["id"] == ueber or (besitzer and einfach(g.get("besitzer")) == einfach(besitzer)))
            ]
            if not wahl and not von_geraet:
                wahl = [g for g in alle if g.get("typ", "handy") == "handy"]
        if not wahl:
            raise OekoFehler("Ich finde kein passendes Handy zum Klingeln. Trag bei beiden Geräten denselben Besitzer ein.")
        if von_geraet:
            besitzer, ueber = self._eigentuemer_von(von_geraet)
            fremd = [g for g in wahl if g["id"] != ueber and not (besitzer and einfach(g.get("besitzer")) == einfach(besitzer))]
            if fremd:
                raise OekoFehler("Von diesem Gerät aus kannst du nur deine eigenen Geräte klingeln lassen.")
        ergebnisse = []
        for geraet in sorted(wahl, key=lambda g: not g.get("online"))[:3]:
            try:
                await dienst.klingeln(geraet["id"], sekunden)
                ergebnisse.append({"geraet": geraet.get("name", ""), "ok": True})
            except HandyFehler as fehler:
                ergebnisse.append({"geraet": geraet.get("name", ""), "ok": False, "fehler": str(fehler)})
        if not any(e["ok"] for e in ergebnisse):
            raise OekoFehler(ergebnisse[0].get("fehler") or "Das Handy hat nicht reagiert.")
        return {"ok": True, "geraete": ergebnisse}

    async def uhr_koppeln(self, handy_id: str) -> dict:
        from app.services.handy_service import code_gruppiert

        dienst = self._handy()
        handy = dienst._geraet(handy_id)
        if handy is None:
            raise OekoFehler("Nur ein gekoppeltes Handy kann eine Uhr koppeln.")
        if handy.get("typ") == "uhr":
            raise OekoFehler("Eine Uhr kann keine weitere Uhr koppeln.")
        daten = await asyncio.to_thread(
            dienst.kopplung_starten, False,
            {"typ": "uhr", "besitzer": str(handy.get("besitzer") or ""), "ueber": handy_id},
        )
        return {
            "ok": True,
            "code": daten["code"],
            "code_gruppiert": code_gruppiert(daten["code"]),
            "adressen": daten.get("adressen") or [],
            "pc": daten.get("pc") or {},
            "besitzer": str(handy.get("besitzer") or ""),
            "ablauf": daten.get("ablauf"),
        }

    def _memory(self):
        from app.services.memory_service import MemoryService

        if self._speicher is None:
            self._speicher = MemoryService()
        return self._speicher

    def gedaechtnis_export(self, seit: str = "", ohne: str = "", grenze: int = 300) -> dict:
        eintraege = []
        for eintrag in self._memory().list(5000):
            quelle = str(eintrag.get("source") or "")
            if ohne and quelle == ohne:
                continue
            if seit and str(eintrag.get("created_at") or "") <= seit:
                continue
            eintraege.append({"content": eintrag["content"], "zeit": eintrag["created_at"], "wichtigkeit": eintrag.get("wichtigkeit", 0.5)})
        eintraege = eintraege[-grenze:]
        return {"eintraege": eintraege, "stand": eintraege[-1]["zeit"] if eintraege else seit, "jon": self.eigener_name()}

    def gedaechtnis_import(self, eintraege: list, quelle: str) -> int:
        neu = 0
        for eintrag in list(eintraege or [])[:500]:
            if isinstance(eintrag, dict):
                text = str(eintrag.get("content") or "").strip()
                try:
                    wichtig = max(0.1, min(1.0, float(eintrag.get("wichtigkeit") or 0.5)))
                except (TypeError, ValueError):
                    wichtig = 0.5
            else:
                text = str(eintrag or "").strip()
                wichtig = 0.5
            if not text:
                continue
            ergebnis = self._memory().add(text[:1000], source=quelle[:32], wichtigkeit=wichtig)
            if not ergebnis.get("duplicate") and not ergebnis.get("error"):
                neu += 1
        return neu

    async def gedaechtnis_abgleichen(self) -> dict:
        verbund = self._verbund()
        with self._lock:
            geholt = dict(self._daten.get("gedaechtnis_geholt") or {})
            gegeben = dict(self._daten.get("gedaechtnis_gegeben") or {})
        bericht: dict[str, Any] = {}
        for eintrag in verbund.geraete():
            kennung = str(eintrag["id"])
            quelle = f"verbund:{kennung}"[:32]
            eigene = await asyncio.to_thread(self.gedaechtnis_export, gegeben.get(kennung, ""), quelle)
            try:
                antwort = await verbund.rufen(
                    kennung, "POST", "/api/oekosystem/gedaechtnis",
                    {"eintraege": eigene["eintraege"], "seit": geholt.get(kennung, "")},
                    wartezeit=45.0,
                )
                daten = json.loads(antwort.get("text") or "{}")
            except Exception as fehler:
                leise(fehler, "services/oekosystem_service")
                bericht[eintrag.get("name", kennung)] = "nicht erreichbar"
                continue
            neu = await asyncio.to_thread(self.gedaechtnis_import, daten.get("eintraege") or [], quelle)
            if daten.get("stand"):
                geholt[kennung] = str(daten["stand"])
            if eigene.get("stand"):
                gegeben[kennung] = str(eigene["stand"])
            bericht[eintrag.get("name", kennung)] = {"neu": neu, "gegeben": len(eigene["eintraege"])}
        with self._lock:
            self._daten["gedaechtnis_geholt"] = geholt
            self._daten["gedaechtnis_gegeben"] = gegeben
            self._sichern()
        return bericht

    async def gedaechtnis_tauschen(self, geraete_id: str, eintraege: list, seit: str) -> dict:
        quelle = f"geraet:{geraete_id}"[:32] if geraete_id else "geraet"
        neu = await asyncio.to_thread(self.gedaechtnis_import, eintraege, quelle)
        antwort = await asyncio.to_thread(self.gedaechtnis_export, seit, quelle)
        return {**antwort, "neu": neu}


_dienst: Oekosystem | None = None


def get_oekosystem() -> Oekosystem:
    global _dienst
    if _dienst is None:
        _dienst = Oekosystem()
    return _dienst
