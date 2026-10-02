from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.logbook import logger as logbook_logger
from app.core.store import atomic_write_bytes, atomic_write_json, read_json

_log = logbook_logger("krypto")

PRAEFIX = "jv1:"
SCHLUESSEL_LAENGE = 32
NONCE_LAENGE = 12
HKDF_SALZ = b"jon-krypto-v1"
DIENST = "Jon Master Key"
STAND_DATEI = DATA_DIR / "krypto.json"
DATEI_SCHLUESSEL = DATA_DIR / "master.key"

ARGON_ZEIT = 3
ARGON_SPEICHER = 64 * 1024
ARGON_PARALLEL = 4


class KryptoFehler(Exception):
    pass


def zufall(anzahl: int = SCHLUESSEL_LAENGE) -> bytes:
    return secrets.token_bytes(anzahl)


def _b64(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _konto() -> str:
    return hashlib.sha256(str(DATA_DIR.resolve()).lower().encode("utf-8")).hexdigest()[:16]


def _ziel() -> str:
    return f"{DIENST} {_konto()}"


def _windows_lesen() -> bytes | None:
    import ctypes
    from ctypes import wintypes

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    zeiger = ctypes.POINTER(CREDENTIALW)()
    if not advapi.CredReadW(_ziel(), 1, 0, ctypes.byref(zeiger)):
        return None
    try:
        eintrag = zeiger.contents
        return bytes(ctypes.string_at(eintrag.CredentialBlob, eintrag.CredentialBlobSize))
    finally:
        advapi.CredFree(zeiger)


def _windows_schreiben(wert: bytes) -> bool:
    import ctypes
    from ctypes import wintypes

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    puffer = (ctypes.c_ubyte * len(wert)).from_buffer_copy(wert)
    eintrag = CREDENTIALW()
    eintrag.Type = 1
    eintrag.TargetName = _ziel()
    eintrag.Comment = "Hauptschluessel von Jon (FelWorks) - nicht loeschen"
    eintrag.CredentialBlobSize = len(wert)
    eintrag.CredentialBlob = ctypes.cast(puffer, ctypes.POINTER(ctypes.c_ubyte))
    eintrag.Persist = 2
    eintrag.UserName = "Jon"
    return bool(advapi.CredWriteW(ctypes.byref(eintrag), 0))


def _befehl(argumente: list[str], eingabe: str | None = None) -> str | None:
    try:
        lauf = subprocess.run(
            argumente,
            input=eingabe,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return None
    if lauf.returncode != 0:
        return None
    return lauf.stdout.strip()


def _macos_lesen() -> bytes | None:
    wert = _befehl(["security", "find-generic-password", "-a", _konto(), "-s", DIENST, "-w"])
    return wert.encode("ascii") if wert else None


def _macos_schreiben(wert: bytes) -> bool:
    return (
        _befehl(
            [
                "security",
                "add-generic-password",
                "-U",
                "-a",
                _konto(),
                "-s",
                DIENST,
                "-w",
                wert.decode("ascii"),
            ]
        )
        is not None
    )


def _linux_bereit() -> bool:
    return bool(shutil.which("secret-tool")) and bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS"))


def _linux_lesen() -> bytes | None:
    wert = _befehl(["secret-tool", "lookup", "dienst", "jon", "konto", _konto()])
    return wert.encode("ascii") if wert else None


def _linux_schreiben(wert: bytes) -> bool:
    return (
        _befehl(
            ["secret-tool", "store", f"--label={DIENST}", "dienst", "jon", "konto", _konto()],
            eingabe=wert.decode("ascii"),
        )
        is not None
    )


def _datei_lesen() -> bytes | None:
    try:
        return DATEI_SCHLUESSEL.read_bytes().strip() or None
    except OSError:
        return None


def _datei_schreiben(wert: bytes) -> bool:
    try:
        atomic_write_bytes(DATEI_SCHLUESSEL, wert)
        try:
            os.chmod(DATEI_SCHLUESSEL, 0o600)
        except OSError as fehler:
            leise(fehler, "core/krypto")
        return True
    except OSError as fehler:
        leise(fehler, "core/krypto")
        return False


SPEICHER = {
    "windows": (_windows_lesen, _windows_schreiben),
    "macos": (_macos_lesen, _macos_schreiben),
    "linux": (_linux_lesen, _linux_schreiben),
    "datei": (_datei_lesen, _datei_schreiben),
}


def _bevorzugt() -> list[str]:
    erzwungen = os.environ.get("JON_SCHLUESSELSPEICHER", "").strip().lower()
    if erzwungen in SPEICHER:
        return [erzwungen]
    if sys.platform == "win32":
        return ["windows", "datei"]
    if sys.platform == "darwin":
        return ["macos", "datei"]
    if _linux_bereit():
        return ["linux", "datei"]
    return ["datei"]


class Hauptschluessel:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._wert: bytes | None = None
        self._speicher = ""
        self._neu = False

    def _laden(self) -> None:
        stand = read_json(STAND_DATEI, {}) or {}
        gemerkt = str(stand.get("speicher") or "")
        reihenfolge = ([gemerkt] if gemerkt in SPEICHER else []) + [
            s for s in _bevorzugt() if s != gemerkt
        ]
        for name in reihenfolge:
            lesen, _ = SPEICHER[name]
            try:
                roh = lesen()
            except Exception as fehler:
                leise(fehler, "core/krypto")
                roh = None
            if roh:
                try:
                    wert = _unb64(roh.decode("ascii"))
                except Exception:
                    continue
                if len(wert) == SCHLUESSEL_LAENGE:
                    self._wert = wert
                    self._speicher = name
                    return
        if gemerkt:
            _log.warning(
                "Hauptschluessel aus %s nicht mehr lesbar - verschluesselte Daten "
                "muessen neu eingegeben werden",
                gemerkt,
            )
        wert = zufall(SCHLUESSEL_LAENGE)
        kodiert = _b64(wert).encode("ascii")
        for name in _bevorzugt():
            _, schreiben = SPEICHER[name]
            try:
                ok = schreiben(kodiert)
            except Exception as fehler:
                leise(fehler, "core/krypto")
                ok = False
            if ok:
                self._wert = wert
                self._speicher = name
                self._neu = True
                atomic_write_json(
                    STAND_DATEI,
                    {
                        "speicher": name,
                        "konto": _konto(),
                        "verfahren": "AES-256-GCM, HKDF-SHA256 pro Zweck",
                        "erstellt": datetime.now().isoformat(timespec="seconds"),
                    },
                )
                _log.info("Neuer Hauptschluessel im Speicher %s", name)
                return
        raise KryptoFehler("Der Hauptschluessel liess sich nirgends sicher ablegen.")

    def wert(self) -> bytes:
        with self._lock:
            if self._wert is None:
                self._laden()
            assert self._wert is not None
            return self._wert

    def speicher(self) -> str:
        self.wert()
        return self._speicher

    def vergessen(self) -> None:
        with self._lock:
            self._wert = None
            self._speicher = ""


_haupt = Hauptschluessel()


def hauptschluessel() -> Hauptschluessel:
    return _haupt


def _unterschluessel(zweck: str) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    return HKDF(
        algorithm=hashes.SHA256(),
        length=SCHLUESSEL_LAENGE,
        salt=HKDF_SALZ,
        info=f"jon:{zweck}".encode("utf-8"),
    ).derive(_haupt.wert())


def verschluesseln(klartext: bytes, zweck: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = zufall(NONCE_LAENGE)
    chiffre = AESGCM(_unterschluessel(zweck)).encrypt(nonce, klartext, zweck.encode("utf-8"))
    return PRAEFIX + _b64(nonce + chiffre)


def entschluesseln(text: str, zweck: str) -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not ist_verschluesselt(text):
        raise KryptoFehler("Kein verschluesselter Wert.")
    try:
        roh = _unb64(text[len(PRAEFIX):])
        return AESGCM(_unterschluessel(zweck)).decrypt(
            roh[:NONCE_LAENGE], roh[NONCE_LAENGE:], zweck.encode("utf-8")
        )
    except (InvalidTag, ValueError) as fehler:
        raise KryptoFehler("Der Wert laesst sich nicht entschluesseln.") from fehler


def ist_verschluesselt(wert: Any) -> bool:
    return isinstance(wert, str) and wert.startswith(PRAEFIX)


def text_verschluesseln(wert: str, zweck: str) -> str:
    if not wert or ist_verschluesselt(wert):
        return wert
    return verschluesseln(wert.encode("utf-8"), zweck)


def text_lesen(wert: Any, zweck: str) -> str:
    if not ist_verschluesselt(wert):
        return "" if wert is None else str(wert)
    try:
        return entschluesseln(wert, zweck).decode("utf-8")
    except KryptoFehler:
        _log.warning("Verschluesselter Wert (%s) nicht lesbar", zweck)
        return ""


def json_schreiben(pfad: Path, daten: Any, zweck: str) -> None:
    klartext = json.dumps(daten, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    atomic_write_json(
        pfad,
        {"jon_krypto": 1, "zweck": zweck, "daten": verschluesseln(klartext, zweck)},
    )


def json_lesen(pfad: Path, standard: Any, zweck: str) -> Any:
    roh = read_json(pfad, None)
    if roh is None:
        return standard
    if isinstance(roh, dict) and roh.get("jon_krypto") == 1 and ist_verschluesselt(roh.get("daten")):
        try:
            return json.loads(entschluesseln(roh["daten"], zweck).decode("utf-8"))
        except (KryptoFehler, ValueError):
            _log.warning("%s laesst sich nicht entschluesseln", Path(pfad).name)
            return standard
    return roh


def ist_klartext_datei(pfad: Path) -> bool:
    roh = read_json(pfad, None)
    return roh is not None and not (isinstance(roh, dict) and roh.get("jon_krypto") == 1)


def bytes_schreiben(pfad: Path, daten: bytes, zweck: str) -> None:
    atomic_write_bytes(pfad, verschluesseln(daten, zweck).encode("ascii"))


def bytes_lesen(pfad: Path, zweck: str) -> bytes | None:
    try:
        roh = Path(pfad).read_bytes()
    except OSError:
        return None
    try:
        text = roh.decode("ascii").strip()
    except UnicodeDecodeError:
        return roh
    if ist_verschluesselt(text):
        try:
            return entschluesseln(text, zweck)
        except KryptoFehler:
            _log.warning("%s laesst sich nicht entschluesseln", Path(pfad).name)
            return None
    return roh


def _argon():
    from argon2 import PasswordHasher

    return PasswordHasher(
        time_cost=ARGON_ZEIT,
        memory_cost=ARGON_SPEICHER,
        parallelism=ARGON_PARALLEL,
    )


def passwort_hash(passwort: str) -> str:
    return _argon().hash(passwort)


def passwort_pruefen(gespeichert: str, passwort: str) -> bool:
    from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

    try:
        return _argon().verify(gespeichert, passwort)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def passwort_veraltet(gespeichert: str) -> bool:
    try:
        return _argon().check_needs_rehash(gespeichert)
    except Exception:
        return True


def schluessel_aus_passwort(passwort: str, salz: bytes) -> bytes:
    from argon2.low_level import Type, hash_secret_raw

    return hash_secret_raw(
        secret=passwort.encode("utf-8"),
        salt=salz,
        time_cost=ARGON_ZEIT,
        memory_cost=ARGON_SPEICHER,
        parallelism=ARGON_PARALLEL,
        hash_len=SCHLUESSEL_LAENGE,
        type=Type.ID,
    )


def sha256_datei(pfad: Path) -> str:
    pruefer = hashlib.sha256()
    with open(pfad, "rb") as quelle:
        for block in iter(lambda: quelle.read(1_048_576), b""):
            pruefer.update(block)
    return pruefer.hexdigest()


def ed25519_pruefen(oeffentlich_b64: str, daten: bytes, signatur: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        schluessel = Ed25519PublicKey.from_public_bytes(base64.b64decode(oeffentlich_b64))
        schluessel.verify(signatur, daten)
        return True
    except (InvalidSignature, ValueError):
        return False


def stand() -> dict:
    return {
        "speicher": _haupt.speicher(),
        "verfahren": {
            "lokale_daten": "AES-256-GCM",
            "schluessel": "AES-256-GCM, Hauptschluessel im Schluesselspeicher des Systems",
            "passwoerter": "Argon2id",
            "schluesseltausch": "X25519",
            "updates": "Ed25519",
            "integritaet": "SHA-256",
            "transport": "TLS 1.3",
        },
    }
