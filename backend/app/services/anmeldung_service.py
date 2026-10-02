from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime

from app.core.config import DATA_DIR
from app.core.logbook import logger as logbook_logger
from app.core.store import atomic_write_json, read_json

_log = logbook_logger("anmeldung")

DATEI = DATA_DIR / "anmeldung.json"
SUPPORT_URL = "https://felworks-impressum.netlify.app/support"
ITERATIONEN = 390_000
MIN_NAME = 2
MIN_PASSWORT = 6
MAX_LAENGE = 128
VERSUCHE = 5
SPERRE = 60.0


class AnmeldeFehler(Exception):
    def __init__(self, text: str, status: int = 400, **extra) -> None:
        super().__init__(text)
        self.status = status
        self.extra = extra


def _name(wert: str) -> str:
    return " ".join(str(wert or "").split()).casefold()


def _hash(wert: str, salz: bytes, iterationen: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", wert.encode("utf-8"), salz, iterationen)


def _eintrag(benutzername: str, passwort: str) -> dict:
    from app.core.krypto import passwort_hash

    return {
        "version": 2,
        "verfahren": "argon2id",
        "benutzer": passwort_hash(_name(benutzername)),
        "passwort": passwort_hash(passwort),
        "geaendert": datetime.now().isoformat(timespec="seconds"),
    }


def _alt_eintrag(benutzername: str, passwort: str) -> dict:
    benutzer_salz = secrets.token_bytes(16)
    passwort_salz = secrets.token_bytes(16)
    return {
        "version": 1,
        "verfahren": "pbkdf2-sha256",
        "iterationen": ITERATIONEN,
        "benutzer_salz": benutzer_salz.hex(),
        "benutzer_hash": _hash(_name(benutzername), benutzer_salz, ITERATIONEN).hex(),
        "passwort_salz": passwort_salz.hex(),
        "passwort_hash": _hash(passwort, passwort_salz, ITERATIONEN).hex(),
        "geaendert": datetime.now().isoformat(timespec="seconds"),
    }


def pruefe_neu(benutzername: str, passwort: str) -> None:
    name = _name(benutzername)
    if len(name) < MIN_NAME:
        raise AnmeldeFehler(f"Der Benutzername braucht mindestens {MIN_NAME} Zeichen.")
    if len(passwort or "") < MIN_PASSWORT:
        raise AnmeldeFehler(f"Das Passwort braucht mindestens {MIN_PASSWORT} Zeichen.")
    if len(name) > MAX_LAENGE or len(passwort) > MAX_LAENGE:
        raise AnmeldeFehler(f"Hoechstens {MAX_LAENGE} Zeichen, bitte.")


class AnmeldungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fehlversuche = 0
        self._gesperrt_bis = 0.0

    def _laden(self) -> dict | None:
        daten = read_json(DATEI, None)
        if not isinstance(daten, dict):
            return None
        if daten.get("verfahren") == "argon2id":
            noetig = ("benutzer", "passwort")
        else:
            noetig = ("benutzer_salz", "benutzer_hash", "passwort_salz", "passwort_hash")
        if not all(isinstance(daten.get(k), str) and daten.get(k) for k in noetig):
            return None
        return daten

    def eingerichtet(self) -> bool:
        return self._laden() is not None

    def gesperrt_sekunden(self) -> int:
        rest = self._gesperrt_bis - time.monotonic()
        return int(rest + 0.999) if rest > 0 else 0

    def stand(self) -> dict:
        return {
            "eingerichtet": self.eingerichtet(),
            "gesperrt_sekunden": self.gesperrt_sekunden(),
            "support": SUPPORT_URL,
            "mindestens": {"benutzername": MIN_NAME, "passwort": MIN_PASSWORT},
        }

    def einrichten(self, benutzername: str, passwort: str) -> dict:
        with self._lock:
            if self.eingerichtet():
                raise AnmeldeFehler("Der Zugang ist schon eingerichtet.", 409)
            pruefe_neu(benutzername, passwort)
            atomic_write_json(DATEI, _eintrag(benutzername, passwort))
            self._fehlversuche = 0
        _log.info("Zugang eingerichtet")
        return {"ok": True}

    def _vergleichen(self, daten: dict, benutzername: str, passwort: str) -> bool:
        if daten.get("verfahren") == "argon2id":
            from app.core.krypto import passwort_pruefen

            name_ok = passwort_pruefen(daten["benutzer"], _name(benutzername))
            passwort_ok = passwort_pruefen(daten["passwort"], str(passwort or ""))
            return name_ok and passwort_ok
        iterationen = int(daten.get("iterationen") or ITERATIONEN)
        name_ok = hmac.compare_digest(
            _hash(_name(benutzername), bytes.fromhex(daten["benutzer_salz"]), iterationen).hex(),
            daten["benutzer_hash"],
        )
        passwort_ok = hmac.compare_digest(
            _hash(str(passwort or ""), bytes.fromhex(daten["passwort_salz"]), iterationen).hex(),
            daten["passwort_hash"],
        )
        return name_ok and passwort_ok

    @staticmethod
    def _veraltet(daten: dict) -> bool:
        if daten.get("verfahren") != "argon2id":
            return True
        from app.core.krypto import passwort_veraltet

        return passwort_veraltet(daten["passwort"]) or passwort_veraltet(daten["benutzer"])

    def pruefen(self, benutzername: str, passwort: str) -> dict:
        with self._lock:
            warten = self.gesperrt_sekunden()
            if warten:
                raise AnmeldeFehler(
                    f"Zu viele Fehlversuche. Warte noch {warten} Sekunden.",
                    429,
                    sekunden=warten,
                )
            daten = self._laden()
            if daten is None:
                raise AnmeldeFehler("Es ist noch kein Zugang eingerichtet.", 409)
            if self._vergleichen(daten, benutzername, passwort):
                self._fehlversuche = 0
                if self._veraltet(daten):
                    atomic_write_json(DATEI, _eintrag(benutzername, passwort))
                    _log.info("Zugang auf Argon2id umgestellt")
                return {"ok": True}
            self._fehlversuche += 1
            uebrig = max(0, VERSUCHE - self._fehlversuche)
            if uebrig == 0:
                self._fehlversuche = 0
                self._gesperrt_bis = time.monotonic() + SPERRE
                _log.warning("Anmeldung nach %s Fehlversuchen gesperrt", VERSUCHE)
                raise AnmeldeFehler(
                    f"Zu viele Fehlversuche. Warte {int(SPERRE)} Sekunden.",
                    429,
                    sekunden=int(SPERRE),
                    versuche_uebrig=0,
                )
            raise AnmeldeFehler(
                "Benutzername oder Passwort stimmt nicht.",
                401,
                versuche_uebrig=uebrig,
            )

    def aendern(
        self,
        benutzername: str,
        passwort: str,
        neuer_benutzername: str = "",
        neues_passwort: str = "",
    ) -> dict:
        self.pruefen(benutzername, passwort)
        ziel_name = neuer_benutzername.strip() or benutzername
        ziel_passwort = neues_passwort or passwort
        if not neuer_benutzername.strip() and not neues_passwort:
            raise AnmeldeFehler("Gib einen neuen Benutzernamen oder ein neues Passwort ein.")
        pruefe_neu(ziel_name, ziel_passwort)
        with self._lock:
            atomic_write_json(DATEI, _eintrag(ziel_name, ziel_passwort))
        _log.info("Zugangsdaten geaendert")
        return {"ok": True}


_service: AnmeldungService | None = None


def get_anmeldung_service() -> AnmeldungService:
    global _service
    if _service is None:
        _service = AnmeldungService()
    return _service
