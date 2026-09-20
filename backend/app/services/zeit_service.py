from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_json, read_json

STORE = DATA_DIR / "zeiten.json"
ARTEN = ("stoppuhr", "timer", "wecker")
EIGENE_QUELLEN = {"", "app", "desktop", "mini-jon"}
MAX_UHREN = 12
KLINGELDAUER = 60.0
ALTLAST = 3600.0
TAKT = 0.5


class ZeitFehler(Exception):
    pass


def stumm() -> bool:
    return bool(os.environ.get("JON_ZEIT_STUMM"))


def _weckdatei() -> Path:
    return Path(os.environ.get("WINDIR", "C:\\Windows")) / "Media" / "Alarm01.wav"


def ton_an() -> bool:
    if stumm() or os.name != "nt":
        return False
    try:
        import winsound

        datei = _weckdatei()
        if datei.exists():
            winsound.PlaySound(
                str(datei),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
            )
        else:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        return True
    except Exception as fehler:
        leise(fehler, "services/zeit")
        return False


def ton_aus() -> None:
    if os.name != "nt":
        return
    try:
        import winsound

        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception as fehler:
        leise(fehler, "services/zeit")


def uhrzeit_lesen(text: str) -> float:
    roh = str(text or "").strip().lower().replace("uhr", "").strip()
    roh = roh.replace(".", ":").replace(",", ":")
    if not roh:
        raise ZeitFehler("Fuer einen Wecker brauche ich eine Uhrzeit.")
    teile = [t for t in roh.split(":") if t != ""]
    try:
        stunde = int(teile[0])
        minute = int(teile[1]) if len(teile) > 1 else 0
    except (IndexError, ValueError):
        raise ZeitFehler("Die Uhrzeit muss so aussehen: 07:30.")
    if not 0 <= stunde <= 23 or not 0 <= minute <= 59:
        raise ZeitFehler("Die Uhrzeit muss zwischen 00:00 und 23:59 liegen.")
    jetzt = datetime.now()
    ziel = jetzt.replace(hour=stunde, minute=minute, second=0, microsecond=0)
    if ziel <= jetzt:
        ziel += timedelta(days=1)
    return ziel.timestamp()


class ZeitService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        roh = read_json(STORE, None)
        gelesen = (
            [self._auffrischen(e) for e in roh if isinstance(e, dict)]
            if isinstance(roh, list)
            else []
        )
        self._uhren: list[dict] = [u for u in gelesen if not self._altlast(u)]
        self._klingeln: list[str] = []
        self._ton = False
        self._wache: threading.Thread | None = None
        for uhr in self._uhren:
            if not uhr.get("geklingelt") and self._faellig(uhr):
                uhr["geklingelt"] = True
                uhr["fertig_seit"] = time.time() - KLINGELDAUER
        if self._uhren:
            self._wecken()

    def _sichern(self) -> None:
        atomic_write_json(STORE, self._uhren)

    @staticmethod
    def _auffrischen(eintrag: dict) -> dict:
        uhr = dict(eintrag)
        uhr["id"] = str(uhr.get("id") or uuid.uuid4().hex[:8])
        uhr["art"] = str(uhr.get("art") or "stoppuhr")
        uhr["titel"] = str(uhr.get("titel") or "")
        uhr["gestartet"] = float(uhr.get("gestartet") or time.time())
        uhr["dauer"] = float(uhr.get("dauer") or 0.0)
        uhr["pause_gesamt"] = float(uhr.get("pause_gesamt") or 0.0)
        uhr["pausiert_seit"] = float(uhr.get("pausiert_seit") or 0.0)
        uhr["quelle"] = str(uhr.get("quelle") or "app")
        uhr["gemeldet"] = bool(uhr.get("gemeldet", True))
        uhr["geklingelt"] = bool(uhr.get("geklingelt", False))
        uhr["fertig_seit"] = float(uhr.get("fertig_seit") or 0.0)
        uhr["aufgabe"] = str(uhr.get("aufgabe") or "")
        if uhr["art"] == "wecker":
            uhr["ziel"] = float(uhr.get("ziel") or uhr["gestartet"] + uhr["dauer"])
        return uhr

    @staticmethod
    def _altlast(uhr: dict) -> bool:
        jetzt = time.time()
        if uhr["art"] == "wecker":
            return jetzt - float(uhr.get("ziel") or 0.0) > ALTLAST
        if uhr["art"] == "timer" and uhr.get("geklingelt"):
            return jetzt - float(uhr.get("fertig_seit") or 0.0) > ALTLAST
        return False

    def _verstrichen(self, uhr: dict) -> float:
        pause = float(uhr.get("pause_gesamt", 0.0))
        if uhr.get("pausiert_seit"):
            pause += time.time() - float(uhr["pausiert_seit"])
        return max(0.0, time.time() - float(uhr["gestartet"]) - pause)

    def _faellig(self, uhr: dict) -> bool:
        if uhr["art"] == "wecker":
            return time.time() >= float(uhr.get("ziel") or 0.0)
        if uhr["art"] == "timer":
            return self._verstrichen(uhr) >= float(uhr.get("dauer") or 0.0)
        return False

    def _ansicht(self, uhr: dict) -> dict:
        verstrichen = self._verstrichen(uhr)
        klingelt = uhr["id"] in self._klingeln
        daten = {
            "id": uhr["id"],
            "art": uhr["art"],
            "titel": uhr.get("titel", ""),
            "gestartet": uhr["gestartet"],
            "gemessen": time.time(),
            "laeuft": not uhr.get("pausiert_seit"),
            "verstrichen": round(verstrichen, 1),
            "quelle": uhr.get("quelle", "app"),
            "klingelt": klingelt,
            "ton_pc": bool(uhr.get("aufgabe")) or (klingelt and self._ton),
        }
        if uhr["art"] == "timer":
            dauer = float(uhr.get("dauer") or 0.0)
            daten["dauer"] = dauer
            daten["rest"] = round(max(0.0, dauer - verstrichen), 1)
            daten["fertig"] = verstrichen >= dauer
        elif uhr["art"] == "wecker":
            ziel = float(uhr.get("ziel") or 0.0)
            daten["ziel"] = ziel
            daten["klingelt_um"] = datetime.fromtimestamp(ziel).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            daten["dauer"] = round(max(0.0, ziel - float(uhr["gestartet"])), 1)
            daten["rest"] = round(max(0.0, ziel - time.time()), 1)
            daten["fertig"] = time.time() >= ziel
            daten["laeuft"] = True
        else:
            daten["dauer"] = 0.0
            daten["fertig"] = False
        return daten

    def _wecken(self) -> None:
        if self._wache is not None and self._wache.is_alive():
            return
        self._wache = threading.Thread(
            target=self._wachen, name="jon-zeit", daemon=True
        )
        self._wache.start()

    def _wachen(self) -> None:
        while True:
            time.sleep(TAKT)
            try:
                if not self._runde():
                    return
            except Exception as fehler:
                leise(fehler, "services/zeit")
                return

    def _runde(self) -> bool:
        with self._lock:
            jetzt = time.time()
            geaendert = False
            for uhr in self._uhren:
                if uhr["art"] == "stoppuhr" or uhr.get("geklingelt"):
                    continue
                if not self._faellig(uhr):
                    continue
                uhr["geklingelt"] = True
                uhr["fertig_seit"] = jetzt
                geaendert = True
                self._klingeln.append(uhr["id"])
                if not uhr.get("aufgabe") and not self._ton:
                    self._ton = ton_an()
            for kennung in list(self._klingeln):
                uhr = self._suchen(kennung)
                gereicht = uhr is not None and (
                    jetzt - float(uhr.get("fertig_seit") or jetzt) > KLINGELDAUER
                )
                if uhr is None or gereicht:
                    self._klingeln.remove(kennung)
            if self._ton and not self._klingeln:
                ton_aus()
                self._ton = False
            if geaendert:
                self._sichern()
            offen = any(
                u["art"] != "stoppuhr" and not u.get("geklingelt") for u in self._uhren
            )
            return offen or bool(self._klingeln)

    def _suchen(self, uhr_id: str) -> dict | None:
        for uhr in self._uhren:
            if uhr["id"] == uhr_id:
                return uhr
        return None

    def _finden(self, uhr_id: str) -> dict:
        uhr = self._suchen(uhr_id)
        if uhr is None:
            raise ZeitFehler("Diese Uhr gibt es nicht.")
        return uhr

    def waehlen(self, kennung: str = "", art: str = "") -> dict:
        with self._lock:
            if not self._uhren:
                raise ZeitFehler("Es laeuft gerade keine Uhr.")
            gesucht = str(kennung or "").strip().lower()
            sorte = str(art or "").strip().lower()
            if gesucht in ARTEN and not sorte:
                sorte, gesucht = gesucht, ""
            if gesucht:
                for uhr in reversed(self._uhren):
                    if uhr["id"] == gesucht:
                        return uhr
                for uhr in reversed(self._uhren):
                    if gesucht in uhr.get("titel", "").lower():
                        return uhr
            passend = [u for u in self._uhren if not sorte or u["art"] == sorte]
            if not passend:
                raise ZeitFehler("Davon laeuft gerade keine Uhr.")
            offen = [u for u in passend if not u.get("geklingelt")]
            return (offen or passend)[-1]

    def starten(
        self,
        art: str,
        sekunden: int = 0,
        titel: str = "",
        quelle: str = "app",
        uhrzeit: str = "",
    ) -> dict:
        art = (art or "stoppuhr").strip().lower()
        if art not in ARTEN:
            raise ZeitFehler("Art muss stoppuhr, timer oder wecker sein.")
        if art == "timer" and sekunden <= 0:
            raise ZeitFehler("Ein Timer braucht eine Dauer.")
        jetzt = time.time()
        ziel = 0.0
        if art == "wecker":
            ziel = (
                uhrzeit_lesen(uhrzeit)
                if str(uhrzeit).strip()
                else jetzt + float(sekunden)
            )
            if ziel <= jetzt:
                raise ZeitFehler("Ein Wecker braucht eine Uhrzeit in der Zukunft.")
        quelle = str(quelle or "app").strip().lower()
        uhr = {
            "id": uuid.uuid4().hex[:8],
            "art": art,
            "titel": str(titel or "").strip(),
            "gestartet": jetzt,
            "dauer": float(sekunden if art != "wecker" else ziel - jetzt),
            "pause_gesamt": 0.0,
            "pausiert_seit": 0.0,
            "quelle": quelle,
            "gemeldet": quelle in EIGENE_QUELLEN,
            "geklingelt": False,
            "fertig_seit": 0.0,
            "aufgabe": "",
        }
        if art == "wecker":
            uhr["ziel"] = ziel
        with self._lock:
            self._uhren = self._uhren[-(MAX_UHREN - 1):] + [uhr]
            self._sichern()
        if art == "wecker":
            self._aufgabe_stellen(uhr)
        with self._lock:
            self._wecken()
            return self._ansicht(uhr)

    def _aufgabe_stellen(self, uhr: dict) -> None:
        if os.name != "nt" or stumm():
            return
        rest = float(uhr.get("ziel") or 0.0) - time.time()
        if rest <= 5:
            return
        try:
            from app.services.system_service import SystemService

            daten = SystemService().set_alarm(
                uhr.get("titel") or "Wecker", "", rest / 60.0
            )
            with self._lock:
                uhr["aufgabe"] = str(daten.get("task", ""))
                self._sichern()
        except Exception as fehler:
            leise(fehler, "services/zeit")

    def _aufgabe_loeschen(self, uhr: dict) -> None:
        name = str(uhr.get("aufgabe") or "")
        if not name:
            return
        uhr["aufgabe"] = ""
        if os.name != "nt":
            return
        try:
            from app.services.system_service import SystemService

            SystemService().delete_alarm(name)
        except Exception as fehler:
            leise(fehler, "services/zeit")

    def stand(self) -> dict:
        with self._lock:
            return {"uhren": [self._ansicht(uhr) for uhr in self._uhren]}

    def neue(self) -> dict:
        with self._lock:
            frisch = [uhr for uhr in self._uhren if not uhr.get("gemeldet")]
            for uhr in frisch:
                uhr["gemeldet"] = True
            if frisch:
                self._sichern()
            return {"uhren": [self._ansicht(uhr) for uhr in frisch]}

    def pausieren(self, uhr_id: str) -> dict:
        with self._lock:
            uhr = self._finden(uhr_id)
            if uhr["art"] == "wecker":
                raise ZeitFehler("Ein Wecker laesst sich nicht pausieren.")
            if not uhr.get("pausiert_seit"):
                uhr["pausiert_seit"] = time.time()
                self._sichern()
            return self._ansicht(uhr)

    def weiter(self, uhr_id: str) -> dict:
        with self._lock:
            uhr = self._finden(uhr_id)
            if uhr.get("pausiert_seit"):
                uhr["pause_gesamt"] = float(uhr.get("pause_gesamt", 0.0)) + (
                    time.time() - float(uhr["pausiert_seit"])
                )
                uhr["pausiert_seit"] = 0.0
                self._sichern()
            self._wecken()
            return self._ansicht(uhr)

    def anpassen(self, uhr_id: str, sekunden: float) -> dict:
        with self._lock:
            uhr = self._finden(uhr_id)
            if uhr["art"] == "stoppuhr":
                raise ZeitFehler("Eine Stoppuhr hat keine Dauer, die ich aendern kann.")
            versatz = float(sekunden)
            if uhr["art"] == "wecker":
                neu = float(uhr.get("ziel") or 0.0) + versatz
                if neu <= time.time():
                    raise ZeitFehler("So weit zurueck geht der Wecker nicht.")
                uhr["ziel"] = neu
                uhr["dauer"] = max(0.0, neu - float(uhr["gestartet"]))
            else:
                uhr["dauer"] = max(0.0, float(uhr.get("dauer") or 0.0) + versatz)
            self._beruhigen(uhr)
            if not self._faellig(uhr):
                uhr["geklingelt"] = False
                uhr["fertig_seit"] = 0.0
            self._sichern()
            self._wecken()
            ansicht = self._ansicht(uhr)
        if uhr["art"] == "wecker" and uhr.get("aufgabe"):
            self._aufgabe_loeschen(uhr)
            self._aufgabe_stellen(uhr)
        return ansicht

    def neustarten(self, uhr_id: str) -> dict:
        with self._lock:
            uhr = self._finden(uhr_id)
            jetzt = time.time()
            dauer = float(uhr.get("dauer") or 0.0)
            uhr["gestartet"] = jetzt
            uhr["pause_gesamt"] = 0.0
            uhr["pausiert_seit"] = 0.0
            uhr["geklingelt"] = False
            uhr["fertig_seit"] = 0.0
            if uhr["art"] == "wecker":
                uhr["ziel"] = jetzt + dauer
            self._beruhigen(uhr)
            self._sichern()
            self._wecken()
            ansicht = self._ansicht(uhr)
        if uhr["art"] == "wecker" and uhr.get("aufgabe"):
            self._aufgabe_loeschen(uhr)
            self._aufgabe_stellen(uhr)
        return ansicht

    def _beruhigen(self, uhr: dict) -> None:
        if uhr["id"] in self._klingeln:
            self._klingeln.remove(uhr["id"])
        if self._ton and not self._klingeln:
            ton_aus()
            self._ton = False

    def ruhe(self, uhr_id: str = "") -> dict:
        with self._lock:
            ziele = [self._finden(uhr_id)] if uhr_id else list(self._uhren)
            for uhr in ziele:
                self._beruhigen(uhr)
            return {"uhren": [self._ansicht(uhr) for uhr in self._uhren]}

    def stoppen(self, uhr_id: str = "") -> dict:
        with self._lock:
            weg = [self._finden(uhr_id)] if uhr_id else list(self._uhren)
            ansichten = [self._ansicht(uhr) for uhr in weg]
            for uhr in weg:
                self._beruhigen(uhr)
            kennungen = {uhr["id"] for uhr in weg}
            self._uhren = [e for e in self._uhren if e["id"] not in kennungen]
            self._sichern()
        for uhr in weg:
            if uhr.get("aufgabe"):
                self._aufgabe_loeschen(uhr)
        return {"gestoppt": ansichten}


_service: ZeitService | None = None


def get_zeit_service() -> ZeitService:
    global _service
    if _service is None:
        _service = ZeitService()
    return _service


def lesbar(sekunden: float) -> str:
    ganz = int(max(0, sekunden))
    stunden, rest = divmod(ganz, 3600)
    minuten, sek = divmod(rest, 60)
    if stunden:
        return f"{stunden}:{minuten:02d}:{sek:02d}"
    return f"{minuten}:{sek:02d}"


def beschreiben(uhr: dict) -> str:
    titel = str(uhr.get("titel") or "")
    anhang = f" ({titel})" if titel else ""
    if uhr.get("art") == "wecker":
        return f"Wecker um {str(uhr.get('klingelt_um') or '')[11:16]}{anhang}"
    if uhr.get("art") == "timer":
        return f"Timer {lesbar(float(uhr.get('rest') or 0.0))}{anhang}"
    return f"Stoppuhr {lesbar(float(uhr.get('verstrichen') or 0.0))}{anhang}"
