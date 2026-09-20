from __future__ import annotations

import asyncio
import ctypes
import os
import threading
import time
from io import BytesIO

from app.core.fehler import leise
from app.core.logbook import logger as logbook_logger

_log = logbook_logger("live")

TAKT_MIN = 0.2
TAKT_MAX = 10.0
BREITE_VORGABE = 1280
QUALITAET_VORGABE = 60


class LiveFehler(Exception):
    pass


def _monitore_windows() -> list[dict]:
    user32 = ctypes.windll.user32
    gefunden: list[dict] = []

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    proto = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(RECT),
        ctypes.c_double,
    )

    def sammeln(_griff, _dc, rechteck, _daten):
        r = rechteck.contents
        gefunden.append(
            {
                "links": int(r.left),
                "oben": int(r.top),
                "rechts": int(r.right),
                "unten": int(r.bottom),
            }
        )
        return 1

    user32.EnumDisplayMonitors(0, 0, proto(sammeln), 0)
    return gefunden


def _virtueller_ursprung() -> tuple[int, int]:
    if os.name != "nt":
        return (0, 0)
    try:
        user32 = ctypes.windll.user32
        return (int(user32.GetSystemMetrics(76)), int(user32.GetSystemMetrics(77)))
    except Exception:
        return (0, 0)


def monitore() -> list[dict]:
    liste: list[dict] = []
    if os.name == "nt":
        try:
            roh = _monitore_windows()
        except Exception as fehler:
            leise(fehler, "services/live_service")
            roh = []
        for nummer, feld in enumerate(roh, start=1):
            liste.append(
                {
                    "id": str(nummer),
                    "name": f"Bildschirm {nummer}",
                    "breite": feld["rechts"] - feld["links"],
                    "hoehe": feld["unten"] - feld["oben"],
                    "feld": feld,
                }
            )
    if not liste:
        liste.append(
            {"id": "1", "name": "Bildschirm 1", "breite": 0, "hoehe": 0, "feld": None}
        )
    if len(liste) > 1:
        liste.insert(
            0,
            {
                "id": "alle",
                "name": "Alle Bildschirme",
                "breite": 0,
                "hoehe": 0,
                "feld": None,
            },
        )
    return liste


def _rohbild(welcher: str):
    try:
        from PIL import ImageGrab
    except Exception as fehler:
        raise LiveFehler("Fuer die Uebertragung fehlt Pillow.") from fehler
    alle = welcher == "alle" or welcher == ""
    try:
        if os.name == "nt":
            bild = ImageGrab.grab(all_screens=True)
        else:
            bild = ImageGrab.grab()
    except Exception as fehler:
        raise LiveFehler(
            "Dieses Geraet hat keinen Bildschirm, den ich aufnehmen kann."
        ) from fehler
    if alle:
        return bild
    passend = [m for m in monitore() if m["id"] == welcher and m.get("feld")]
    if not passend:
        return bild
    feld = passend[0]["feld"]
    ursprung_x, ursprung_y = _virtueller_ursprung()
    kasten = (
        max(0, feld["links"] - ursprung_x),
        max(0, feld["oben"] - ursprung_y),
        max(1, feld["rechts"] - ursprung_x),
        max(1, feld["unten"] - ursprung_y),
    )
    try:
        return bild.crop(kasten)
    except Exception:
        return bild


def bild(
    welcher: str = "alle",
    breite: int = BREITE_VORGABE,
    qualitaet: int = QUALITAET_VORGABE,
) -> bytes:
    roh = _rohbild(welcher)
    if breite and roh.width > breite:
        anteil = breite / roh.width
        roh = roh.resize((breite, max(1, int(roh.height * anteil))))
    if roh.mode != "RGB":
        roh = roh.convert("RGB")
    puffer = BytesIO()
    roh.save(puffer, format="JPEG", quality=max(20, min(95, qualitaet)))
    return puffer.getvalue()


class LiveService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._laeuft = False
        self._welcher = "alle"
        self._takt = 2.0
        self._breite = BREITE_VORGABE
        self._qualitaet = QUALITAET_VORGABE
        self._seit = 0.0
        self._letztes: bytes = b""
        self._letzte_zeit = 0.0
        self._zuschauer = 0
        self._ziele: dict[str, dict] = {}
        self._aufgabe: asyncio.Task | None = None

    def stand(self) -> dict:
        with self._lock:
            return {
                "laeuft": self._laeuft,
                "welcher": self._welcher,
                "takt": self._takt,
                "breite": self._breite,
                "qualitaet": self._qualitaet,
                "seit": round(time.time() - self._seit, 1) if self._seit else 0.0,
                "zuschauer": self._zuschauer,
                "telegram": sorted(self._ziele.keys()),
                "monitore": [
                    {k: v for k, v in m.items() if k != "feld"} for m in monitore()
                ],
            }

    def starten(
        self,
        welcher: str = "alle",
        takt: float = 2.0,
        breite: int = BREITE_VORGABE,
        qualitaet: int = QUALITAET_VORGABE,
    ) -> dict:
        probe = bild(welcher, breite, qualitaet)
        with self._lock:
            self._welcher = welcher or "alle"
            self._takt = max(TAKT_MIN, min(TAKT_MAX, float(takt or 2.0)))
            self._breite = max(320, min(2560, int(breite or BREITE_VORGABE)))
            self._qualitaet = max(20, min(95, int(qualitaet or QUALITAET_VORGABE)))
            self._letztes = probe
            self._letzte_zeit = time.time()
            if not self._laeuft:
                self._laeuft = True
                self._seit = time.time()
        _log.info("Uebertragung laeuft: %s", self._welcher)
        return self.stand()

    def stoppen(self) -> dict:
        with self._lock:
            self._laeuft = False
            self._seit = 0.0
            self._ziele = {}
            self._letztes = b""
        _log.info("Uebertragung beendet")
        return self.stand()

    def aktuell(self) -> bytes:
        with self._lock:
            laeuft = self._laeuft
            welcher = self._welcher
            breite = self._breite
            qualitaet = self._qualitaet
            letztes = self._letztes
            alter = time.time() - self._letzte_zeit
        if not laeuft:
            return bild(welcher, breite, qualitaet)
        if letztes and alter < TAKT_MIN:
            return letztes
        frisch = bild(welcher, breite, qualitaet)
        with self._lock:
            self._letztes = frisch
            self._letzte_zeit = time.time()
        return frisch

    def zuschauer_an(self) -> None:
        with self._lock:
            self._zuschauer += 1

    def zuschauer_ab(self) -> None:
        with self._lock:
            self._zuschauer = max(0, self._zuschauer - 1)

    def telegram_ziel(self, chat_id: str, nachricht_id: int) -> None:
        with self._lock:
            self._ziele[str(chat_id)] = {
                "nachricht": int(nachricht_id),
                "fehler": 0,
            }

    def telegram_los(self, chat_id: str) -> None:
        with self._lock:
            self._ziele.pop(str(chat_id), None)

    def telegram_ziele(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._ziele.items()}

    def takt(self) -> float:
        with self._lock:
            return self._takt

    def laeuft(self) -> bool:
        with self._lock:
            return self._laeuft

    async def schleife(self) -> None:
        while True:
            try:
                if not self.laeuft():
                    await asyncio.sleep(1.0)
                    continue
                ziele = self.telegram_ziele()
                if not ziele:
                    await asyncio.sleep(0.5)
                    continue
                daten = await asyncio.to_thread(self.aktuell)
                from app.services.telegram_service import get_telegram_service

                dienst = get_telegram_service()
                for chat_id, eintrag in ziele.items():
                    ok = await dienst.live_bild_ersetzen(
                        chat_id, int(eintrag["nachricht"]), daten
                    )
                    if not ok:
                        with self._lock:
                            ziel = self._ziele.get(chat_id)
                            if ziel is not None:
                                ziel["fehler"] = int(ziel.get("fehler", 0)) + 1
                                if ziel["fehler"] > 5:
                                    self._ziele.pop(chat_id, None)
                    else:
                        with self._lock:
                            ziel = self._ziele.get(chat_id)
                            if ziel is not None:
                                ziel["fehler"] = 0
                await asyncio.sleep(max(1.0, self.takt()))
            except Exception as fehler:
                _log.warning("Uebertragung gestolpert: %s", fehler)
                await asyncio.sleep(2.0)


_dienst: LiveService | None = None


def get_live_service() -> LiveService:
    global _dienst
    if _dienst is None:
        _dienst = LiveService()
    return _dienst
