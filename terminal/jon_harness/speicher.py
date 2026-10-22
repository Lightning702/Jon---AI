from __future__ import annotations

import base64
import ctypes
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path


def ordner() -> Path:
    eigen = os.environ.get("JON_HARNESS_DIR")
    if eigen:
        pfad = Path(eigen)
    elif sys.platform == "win32":
        pfad = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Jon" / "Harness"
    else:
        pfad = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "jon-harness"
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def schreiben(pfad: Path, text: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    griff, temp = tempfile.mkstemp(dir=str(pfad.parent), prefix=pfad.name, suffix=".tmp")
    try:
        with os.fdopen(griff, "w", encoding="utf-8") as datei:
            datei.write(text)
        os.replace(temp, pfad)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    if sys.platform != "win32":
        try:
            os.chmod(pfad, 0o600)
        except OSError:
            pass


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(daten: bytes, verschluesseln: bool) -> bytes:
    crypt = ctypes.windll.crypt32
    kernel = ctypes.windll.kernel32
    puffer = ctypes.create_string_buffer(daten, len(daten))
    eingang = _Blob(len(daten), ctypes.cast(puffer, ctypes.POINTER(ctypes.c_char)))
    ausgang = _Blob()
    funktion = crypt.CryptProtectData if verschluesseln else crypt.CryptUnprotectData
    if verschluesseln:
        ok = funktion(ctypes.byref(eingang), "Jon Harness", None, None, None, 0, ctypes.byref(ausgang))
    else:
        ok = funktion(ctypes.byref(eingang), None, None, None, None, 0, ctypes.byref(ausgang))
    if not ok:
        raise OSError("Windows-Schluesselspeicher nicht verfuegbar")
    try:
        return ctypes.string_at(ausgang.pbData, ausgang.cbData)
    finally:
        kernel.LocalFree(ausgang.pbData)


def verbergen(text: str) -> str:
    if not text:
        return ""
    roh = text.encode("utf-8")
    if sys.platform == "win32":
        try:
            return "dp1:" + base64.b64encode(_dpapi(roh, True)).decode("ascii")
        except Exception:
            pass
    return "b64:" + base64.b64encode(roh).decode("ascii")


def aufdecken(text: str) -> str:
    if not text:
        return ""
    try:
        if text.startswith("dp1:"):
            return _dpapi(base64.b64decode(text[4:]), False).decode("utf-8")
        if text.startswith("b64:"):
            return base64.b64decode(text[4:]).decode("utf-8")
    except Exception:
        return ""
    return text


class Einstellungen:
    def __init__(self) -> None:
        self.pfad = ordner() / "einstellungen.json"
        self.daten: dict = {}
        self.laden()

    def laden(self) -> None:
        try:
            self.daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.daten = {}
        if not isinstance(self.daten, dict):
            self.daten = {}
        self.daten.setdefault("schluessel", {})
        self.daten.setdefault("modelle", {})
        if not self.daten.get("geraet"):
            self.daten["geraet"] = secrets.token_hex(10)
            self.speichern()

    def speichern(self) -> None:
        schreiben(self.pfad, json.dumps(self.daten, ensure_ascii=False, indent=2))

    def get(self, name: str, standard=None):
        return self.daten.get(name, standard)

    def setzen(self, **werte) -> None:
        self.daten.update(werte)
        self.speichern()

    def schluessel(self, anbieter: str) -> str:
        umgebung = os.environ.get(f"JON_{anbieter.upper()}_KEY") or os.environ.get(f"{anbieter.upper()}_API_KEY")
        if umgebung:
            return umgebung.strip()
        return aufdecken(str(self.daten["schluessel"].get(anbieter) or ""))

    def schluessel_setzen(self, anbieter: str, wert: str) -> None:
        if wert:
            self.daten["schluessel"][anbieter] = verbergen(wert.strip())
        else:
            self.daten["schluessel"].pop(anbieter, None)
        self.speichern()

    def modell(self, anbieter: str) -> str:
        return str(self.daten["modelle"].get(anbieter) or "")

    def modell_setzen(self, anbieter: str, modell: str) -> None:
        self.daten["modelle"][anbieter] = modell
        self.speichern()
