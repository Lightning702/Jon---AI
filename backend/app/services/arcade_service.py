from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from app.core.config import FROZEN, ROOT_DIR

MANIFEST_NAMEN = ("jon-spiele.json", "jon-games.json")
CACHE_SEKUNDEN = 5.0
START_PRUEFUNG = 0.6
BAU_TIMEOUT = 900

EINGEBAUTE_SPIELE: list[dict] = []


class SpielFehler(RuntimeError):
    pass


def _text(wert, fallback: str = "") -> str:
    return str(wert).strip() if isinstance(wert, (str, int, float)) else fallback


def _manifest_dateien(ordner: Path) -> Path | None:
    for name in MANIFEST_NAMEN:
        datei = ordner / name
        if datei.is_file():
            return datei
    return None


def _wurzeln() -> list[Path]:
    kandidaten = [ROOT_DIR, ROOT_DIR / "games", ROOT_DIR / "spiele"]
    if FROZEN:
        kandidaten.append(ROOT_DIR.parent)
    wurzeln: list[Path] = []
    gesehen: set[str] = set()
    for kandidat in kandidaten:
        try:
            if not kandidat.is_dir():
                continue
            schluessel = str(kandidat.resolve()).lower()
        except OSError:
            continue
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        wurzeln.append(kandidat)
    return wurzeln


def _spielordner() -> list[Path]:
    ordner: list[Path] = []
    gesehen: set[str] = set()
    for wurzel in _wurzeln():
        kandidaten = [wurzel]
        try:
            kandidaten += [p for p in wurzel.iterdir() if p.is_dir()]
        except OSError:
            continue
        for kandidat in kandidaten:
            if not _manifest_dateien(kandidat):
                continue
            try:
                schluessel = str(kandidat.resolve()).lower()
            except OSError:
                continue
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            ordner.append(kandidat)
    return ordner


def _eintrag(ordner: Path, manifest: dict, roh: dict) -> dict | None:
    spiel_id = _text(roh.get("id")).lower()
    titel = _text(roh.get("titel") or roh.get("title"))
    if not spiel_id or not titel:
        return None
    typ = _text(roh.get("typ") or roh.get("type"), "nativ").lower()
    exe = _text(roh.get("exe"))
    args = [str(a) for a in roh.get("args", []) if isinstance(a, (str, int, float))]
    bauen = _text(roh.get("bauen") or manifest.get("bauen"))
    vorschau = _text(roh.get("vorschau"))
    return {
        "id": spiel_id,
        "titel": titel,
        "genre": _text(roh.get("genre")),
        "icon": _text(roh.get("icon"), "🎮"),
        "kurz": _text(roh.get("kurz")),
        "beschreibung": _text(roh.get("beschreibung")),
        "steuerung": _text(roh.get("steuerung")),
        "version": _text(roh.get("version") or manifest.get("version")),
        "herausgeber": _text(roh.get("herausgeber") or manifest.get("herausgeber")),
        "sammlung": _text(manifest.get("sammlung")),
        "typ": "web" if typ == "web" else "nativ",
        "pfad": _text(roh.get("pfad")),
        "ordner": ordner,
        "exe": ordner / exe if exe else None,
        "args": args,
        "bauen": ordner / bauen if bauen else None,
        "vorschau": ordner / vorschau if vorschau else None,
    }


def _manifest_lesen(ordner: Path) -> list[dict]:
    datei = _manifest_dateien(ordner)
    if not datei:
        return []
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(daten, dict):
        return []
    rohe = daten.get("spiele") or daten.get("games") or []
    if not isinstance(rohe, list):
        return []
    eintraege = []
    for roh in rohe:
        if not isinstance(roh, dict):
            continue
        eintrag = _eintrag(ordner, daten, roh)
        if eintrag:
            eintraege.append(eintrag)
    return eintraege


class ArcadeService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._prozesse: dict[str, subprocess.Popen] = {}
        self._bauten: dict[str, dict] = {}
        self._cache: list[dict] = []
        self._cache_zeit = 0.0

    def _registry(self, frisch: bool = False) -> list[dict]:
        with self._lock:
            alt = time.time() - self._cache_zeit > CACHE_SEKUNDEN
            if frisch or alt or not self._cache:
                eintraege: list[dict] = []
                belegt: set[str] = set()
                for ordner in _spielordner():
                    for eintrag in _manifest_lesen(ordner):
                        if eintrag["id"] in belegt:
                            continue
                        belegt.add(eintrag["id"])
                        eintraege.append(eintrag)
                for eingebaut in EINGEBAUTE_SPIELE:
                    if eingebaut["id"] in belegt:
                        continue
                    eintrag = dict(eingebaut)
                    eintrag.setdefault("ordner", ROOT_DIR)
                    eintrag.setdefault("exe", None)
                    eintrag.setdefault("args", [])
                    eintrag.setdefault("bauen", None)
                    eintrag.setdefault("vorschau", None)
                    eintrag.setdefault("sammlung", "")
                    eintraege.append(eintrag)
                self._cache = eintraege
                self._cache_zeit = time.time()
            return list(self._cache)

    def _finden(self, spiel_id: str) -> dict:
        gesucht = _text(spiel_id).lower()
        for eintrag in self._registry():
            if eintrag["id"] == gesucht:
                return eintrag
        for eintrag in self._registry(frisch=True):
            if eintrag["id"] == gesucht:
                return eintrag
        raise SpielFehler(f"Das Spiel „{spiel_id}“ ist nicht installiert.")

    def _laeuft(self, spiel_id: str) -> bool:
        with self._lock:
            prozess = self._prozesse.get(spiel_id)
            if prozess is None:
                return False
            if prozess.poll() is None:
                return True
            self._prozesse.pop(spiel_id, None)
            return False

    def _bau_stand(self, spiel_id: str) -> dict:
        with self._lock:
            return dict(self._bauten.get(spiel_id) or {})

    def _status(self, eintrag: dict) -> tuple[str, str]:
        if eintrag["typ"] == "web":
            return "bereit", ""
        bau = self._bau_stand(eintrag["id"])
        if bau.get("status") == "baut":
            return "baut", "Wird gerade kompiliert — das dauert etwa eine Minute."
        if self._laeuft(eintrag["id"]):
            return "laeuft", "Läuft bereits in einem eigenen Fenster."
        exe = eintrag.get("exe")
        if exe and exe.exists():
            if os.name != "nt" and exe.suffix.lower() == ".exe":
                return "nicht_verfuegbar", "Dieses Spiel läuft nur unter Windows."
            return "bereit", ""
        if bau.get("status") == "fehler":
            return "fehler", bau.get("meldung", "Der letzte Bauversuch ist fehlgeschlagen.")
        if eintrag.get("bauen") and eintrag["bauen"].exists() and os.name == "nt":
            return "nicht_gebaut", "Noch nicht kompiliert — einmal „Bauen“ genügt."
        return "fehlt", "Die Spieldatei fehlt."

    def _oeffentlich(self, eintrag: dict) -> dict:
        status, hinweis = self._status(eintrag)
        exe = eintrag.get("exe")
        gebaut_am = ""
        if exe and exe.exists():
            gebaut_am = time.strftime("%d.%m.%Y", time.localtime(exe.stat().st_mtime))
        return {
            "id": eintrag["id"],
            "titel": eintrag["titel"],
            "genre": eintrag["genre"],
            "icon": eintrag["icon"],
            "kurz": eintrag["kurz"],
            "beschreibung": eintrag["beschreibung"],
            "steuerung": eintrag["steuerung"],
            "version": eintrag["version"],
            "herausgeber": eintrag["herausgeber"],
            "sammlung": eintrag["sammlung"],
            "typ": eintrag["typ"],
            "pfad": eintrag["pfad"],
            "status": status,
            "hinweis": hinweis,
            "vorschau": bool(eintrag.get("vorschau") and eintrag["vorschau"].exists()),
            "baubar": bool(eintrag.get("bauen") and eintrag["bauen"].exists() and os.name == "nt"),
            "gebaut_am": gebaut_am,
        }

    def spiele(self, frisch: bool = False) -> list[dict]:
        return [self._oeffentlich(e) for e in self._registry(frisch=frisch)]

    def vorschau(self, spiel_id: str) -> Path:
        eintrag = self._finden(spiel_id)
        bild = eintrag.get("vorschau")
        if not bild or not bild.exists():
            raise SpielFehler(f"Für „{eintrag['titel']}“ gibt es kein Vorschaubild.")
        return bild

    def starten(self, spiel_id: str) -> dict:
        eintrag = self._finden(spiel_id)
        if eintrag["typ"] == "web":
            return {"id": eintrag["id"], "typ": "web", "pfad": eintrag["pfad"], "status": "bereit"}

        if self._laeuft(eintrag["id"]):
            return {"id": eintrag["id"], "typ": "nativ", "status": "laeuft",
                    "hinweis": f"{eintrag['titel']} läuft bereits."}

        exe = eintrag.get("exe")
        if not exe or not exe.exists():
            if eintrag.get("bauen") and eintrag["bauen"].exists() and os.name == "nt":
                raise SpielFehler(
                    f"{eintrag['titel']} ist noch nicht kompiliert. "
                    "Klick auf „Bauen“ — dafür werden die Visual Studio Build Tools gebraucht."
                )
            raise SpielFehler(f"Die Spieldatei von {eintrag['titel']} fehlt: {exe}")
        if os.name != "nt" and exe.suffix.lower() == ".exe":
            raise SpielFehler(f"{eintrag['titel']} läuft nur unter Windows.")

        befehl = [str(exe), *eintrag["args"]]
        optionen: dict = {"cwd": str(eintrag["ordner"]), "close_fds": True}
        if os.name == "nt":
            optionen["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            optionen["start_new_session"] = True
        try:
            prozess = subprocess.Popen(
                befehl,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **optionen,
            )
        except OSError as fehler:
            raise SpielFehler(f"{eintrag['titel']} konnte nicht gestartet werden: {fehler}") from fehler

        time.sleep(START_PRUEFUNG)
        code = prozess.poll()
        if code not in (None, 0):
            raise SpielFehler(
                f"{eintrag['titel']} hat sich sofort wieder beendet (Code {code}). "
                "Details stehen in der Datei echo.log im Spielordner."
            )
        with self._lock:
            self._prozesse[eintrag["id"]] = prozess
        return {
            "id": eintrag["id"],
            "typ": "nativ",
            "status": "laeuft",
            "pid": prozess.pid,
            "hinweis": f"{eintrag['titel']} läuft jetzt in einem eigenen Fenster.",
        }

    def stoppen(self, spiel_id: str) -> dict:
        eintrag = self._finden(spiel_id)
        with self._lock:
            prozess = self._prozesse.pop(eintrag["id"], None)
        if prozess is None or prozess.poll() is not None:
            return {"id": eintrag["id"], "status": "bereit", "hinweis": "Das Spiel läuft nicht."}
        try:
            prozess.terminate()
            prozess.wait(timeout=5)
        except subprocess.TimeoutExpired:
            prozess.kill()
        except OSError as fehler:
            raise SpielFehler(f"{eintrag['titel']} ließ sich nicht beenden: {fehler}") from fehler
        return {"id": eintrag["id"], "status": "bereit", "hinweis": f"{eintrag['titel']} wurde beendet."}

    def bauen(self, spiel_id: str) -> dict:
        eintrag = self._finden(spiel_id)
        skript = eintrag.get("bauen")
        if not skript or not skript.exists():
            raise SpielFehler(f"Für {eintrag['titel']} gibt es kein Bau-Skript.")
        if os.name != "nt":
            raise SpielFehler(f"{eintrag['titel']} lässt sich nur unter Windows bauen.")
        with self._lock:
            if (self._bauten.get(eintrag["id"]) or {}).get("status") == "baut":
                return {"id": eintrag["id"], "status": "baut", "hinweis": "Der Bau läuft bereits."}
            self._bauten[eintrag["id"]] = {"status": "baut", "meldung": ""}
        threading.Thread(
            target=self._bau_lauf,
            args=(eintrag["id"], skript, eintrag["ordner"], eintrag["titel"]),
            daemon=True,
        ).start()
        return {
            "id": eintrag["id"],
            "status": "baut",
            "hinweis": f"{eintrag['titel']} wird kompiliert — das dauert etwa eine Minute.",
        }

    def _bau_lauf(self, spiel_id: str, skript: Path, ordner: Path, titel: str) -> None:
        try:
            ergebnis = subprocess.run(
                ["cmd", "/c", str(skript)],
                cwd=str(ordner),
                capture_output=True,
                text=True,
                errors="replace",
                timeout=BAU_TIMEOUT,
            )
            if ergebnis.returncode == 0:
                stand = {"status": "fertig", "meldung": ""}
            else:
                zeilen = [z.strip() for z in (ergebnis.stdout or "").splitlines() if z.strip()]
                stand = {
                    "status": "fehler",
                    "meldung": f"{titel} ließ sich nicht bauen: "
                    + (zeilen[-1] if zeilen else "Bitte die Visual Studio Build Tools installieren."),
                }
        except subprocess.TimeoutExpired:
            stand = {"status": "fehler", "meldung": f"Der Bau von {titel} hat zu lange gedauert."}
        except OSError as fehler:
            stand = {"status": "fehler", "meldung": f"Der Bau von {titel} schlug fehl: {fehler}"}
        with self._lock:
            self._bauten[spiel_id] = stand
            self._cache_zeit = 0.0

    def aufraeumen(self) -> None:
        with self._lock:
            for spiel_id in list(self._prozesse):
                self._laeuft(spiel_id)


_service: ArcadeService | None = None


def get_arcade_service() -> ArcadeService:
    global _service
    if _service is None:
        _service = ArcadeService()
    return _service
