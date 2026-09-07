from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import unicodedata
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text

DIM = 384
NGRAM = 4
CACHE_DATEI = DATA_DIR / "semantik_cache.json"
MAX_CACHE = 4000

_UMLAUTE = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "à": "a",
    "á": "a",
    "â": "a",
    "è": "e",
    "é": "e",
    "ê": "e",
    "í": "i",
    "ó": "o",
    "ô": "o",
    "ú": "u",
    "ñ": "n",
    "ç": "c",
}

_WORT_RE = re.compile(r"[a-z0-9_]+")

STOPP = {
    "der",
    "die",
    "das",
    "den",
    "dem",
    "des",
    "ein",
    "eine",
    "einen",
    "einem",
    "einer",
    "und",
    "oder",
    "aber",
    "ist",
    "sind",
    "war",
    "bin",
    "bist",
    "hat",
    "habe",
    "haben",
    "wird",
    "werden",
    "kann",
    "koennen",
    "soll",
    "sollen",
    "will",
    "wollen",
    "mir",
    "mich",
    "dir",
    "dich",
    "ich",
    "du",
    "er",
    "sie",
    "es",
    "wir",
    "ihr",
    "mit",
    "von",
    "fuer",
    "auf",
    "aus",
    "bei",
    "nach",
    "zum",
    "zur",
    "zu",
    "im",
    "in",
    "am",
    "an",
    "als",
    "auch",
    "noch",
    "nur",
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "please",
    "bitte",
    "mal",
    "jon",
}

SYNONYME: dict[str, str] = {
    "homepage": "webseite internet browser",
    "netzseite": "webseite internet browser",
    "internetseite": "webseite internet browser",
    "webpage": "webseite internet browser",
    "website": "webseite internet browser",
    "onlineshop": "webseite shop kaufen browser",
    "surfen": "webseite browser",
    "netz": "internet webseite",
    "internet": "webseite browser netz online",
    "browser": "webseite internet netz",
    "seite": "webseite browser",
    "online": "internet webseite",
    "raussuchen": "suchen finden",
    "nachschauen": "suchen lesen",
    "nachsehen": "suchen lesen",
    "gucken": "sehen lesen",
    "schauen": "sehen lesen",
    "checken": "pruefen",
    "besorgen": "kaufen bestellen",
    "ordern": "bestellen kaufen",
    "warenkorb": "kaufen bestellen shop",
    "doktor": "arzt termin kalender",
    "praxis": "arzt termin kalender",
    "verabredung": "termin kalender",
    "meeting": "termin kalender",
    "besprechung": "termin kalender",
    "date": "termin kalender",
    "vormerken": "termin kalender erinnerung",
    "notieren": "notiz kalender erinnerung",
    "merken": "erinnerung gedaechtnis speichern",
    "vergessen": "gedaechtnis loeschen",
    "entspannen": "musik ruhig spielen",
    "chillen": "musik ruhig spielen",
    "abspielen": "musik spielen",
    "lied": "musik song spielen",
    "song": "musik spielen",
    "playlist": "musik spielen",
    "radio": "musik spielen",
    "laut": "lautstaerke musik",
    "leise": "lautstaerke musik",
    "wetter": "wetter temperatur regen",
    "regnen": "wetter regen",
    "warm": "wetter temperatur",
    "kalt": "wetter temperatur",
    "sonne": "wetter",
    "weg": "route navigation karte",
    "fahren": "route navigation karte",
    "hinkommen": "route navigation karte",
    "adresse": "karte ort navigation",
    "umgebung": "karte ort naehe",
    "naehe": "karte ort umgebung",
    "restaurant": "karte ort essen",
    "apotheke": "karte ort geschaeft",
    "supermarkt": "karte ort geschaeft",
    "bildschirm": "screenshot bildschirm fenster",
    "monitor": "screenshot bildschirm fenster",
    "foto": "bild screenshot kamera",
    "bild": "bild grafik zeichnung",
    "zeichnen": "bild grafik erstellen",
    "malen": "bild grafik erstellen",
    "ordner": "datei verzeichnis dateien",
    "verzeichnis": "datei ordner dateien",
    "dokument": "datei dokument lesen",
    "papierkorb": "loeschen datei",
    "aufraeumen": "ordner dateien sortieren",
    "post": "mail email nachricht",
    "email": "mail nachricht",
    "schreiben": "nachricht senden text",
    "anrufen": "telefon anruf",
    "telefonieren": "telefon anruf",
    "handy": "handy telefon geraet",
    "smartphone": "handy telefon geraet",
    "licht": "smarthome lampe schalten",
    "lampe": "smarthome licht schalten",
    "heizung": "smarthome schalten",
    "steckdose": "smarthome schalten",
    "rechner": "system computer pc",
    "computer": "system pc",
    "programm": "programm app starten",
    "app": "programm starten",
    "starten": "programm oeffnen starten",
    "beenden": "programm schliessen",
    "neustart": "system neustart",
    "speicher": "system festplatte",
    "festplatte": "system speicher",
    "internetverbindung": "netzwerk internet",
    "wlan": "netzwerk internet",
    "drucken": "drucker ausdruck",
    "ausdruck": "drucker drucken",
    "uebersetzen": "text uebersetzung",
    "zusammenfassen": "text zusammenfassung",
    "rechnen": "berechnung zahlen",
    "lernen": "wissen lernen dokument",
    "recherche": "suchen wissen internet",
    "forschen": "suchen wissen internet",
    "gestern": "verlauf zeit protokoll",
    "vorhin": "verlauf zeit protokoll",
    "damals": "verlauf zeit protokoll",
    "letzte": "verlauf zeit",
    "wecker": "alarm wecker zeit",
    "timer": "timer zeit stoppuhr",
    "erinnere": "erinnerung kalender",
}

_lock = threading.Lock()
_cache: dict[str, list[float]] | None = None
_indizes: dict[str, "Index"] = {}


def normieren(text: str) -> str:
    roh = unicodedata.normalize("NFC", str(text or "")).lower()
    for zeichen, ersatz in _UMLAUTE.items():
        roh = roh.replace(zeichen, ersatz)
    return re.sub(r"[^a-z0-9_\s]+", " ", roh)


def _stamm(wort: str) -> str:
    for endung in ("ungen", "ung", "chen", "lein", "keit", "heit", "isch", "lich"):
        if len(wort) > len(endung) + 3 and wort.endswith(endung):
            return wort[: -len(endung)]
    for endung in ("nen", "en", "er", "es", "em", "st", "te", "n", "e", "s"):
        if len(wort) > len(endung) + 3 and wort.endswith(endung):
            return wort[: -len(endung)]
    return wort


def _erweitern(woerter: list[str]) -> list[str]:
    ausgabe = list(woerter)
    for wort in woerter:
        zusatz = SYNONYME.get(wort) or SYNONYME.get(_stamm(wort))
        if zusatz:
            ausgabe.extend(zusatz.split())
    return ausgabe


def merkmale(text: str) -> dict[str, float]:
    sauber = normieren(text)
    treffer: dict[str, float] = {}
    woerter = _erweitern(_WORT_RE.findall(sauber))
    for wort in woerter:
        if wort in STOPP:
            continue
        treffer[f"w:{wort}"] = treffer.get(f"w:{wort}", 0.0) + 1.0
        stamm = _stamm(wort)
        if stamm != wort:
            treffer[f"w:{stamm}"] = treffer.get(f"w:{stamm}", 0.0) + 0.7
        gepolstert = f" {wort} "
        for start in range(len(gepolstert) - NGRAM + 1):
            teil = gepolstert[start : start + NGRAM]
            treffer[f"g:{teil}"] = treffer.get(f"g:{teil}", 0.0) + 0.35
    return treffer


def _eimer(schluessel: str) -> tuple[int, float]:
    roh = hashlib.blake2b(schluessel.encode("utf-8"), digest_size=8).digest()
    zahl = int.from_bytes(roh, "big")
    return zahl % DIM, 1.0 if (zahl >> 63) & 1 else -1.0


def _lokaler_vektor(text: str) -> list[float]:
    werte = [0.0] * DIM
    for schluessel, gewicht in merkmale(text).items():
        stelle, vorzeichen = _eimer(schluessel)
        werte[stelle] += vorzeichen * (1.0 + math.log(gewicht + 1.0))
    laenge = math.sqrt(sum(w * w for w in werte))
    if laenge <= 0.0:
        return werte
    return [w / laenge for w in werte]


def _modellname() -> str:
    try:
        from app.services.settings_service import get_settings_service

        return str(get_settings_service().get().get("semantik_modell", "")).strip()
    except Exception:
        return ""


def _ollama_vektor(text: str, modell: str) -> list[float] | None:
    try:
        import httpx

        from app.core.config import get_settings

        basis = get_settings().ollama_base_url.rstrip("/")
        if basis.endswith("/v1"):
            basis = basis[:-3].rstrip("/")
        antwort = httpx.post(
            f"{basis}/api/embeddings",
            json={"model": modell, "prompt": text[:4000]},
            timeout=8.0,
        )
        if antwort.status_code != 200:
            return None
        daten = antwort.json()
        werte = daten.get("embedding") or []
        if not isinstance(werte, list) or not werte:
            return None
        laenge = math.sqrt(sum(float(w) * float(w) for w in werte))
        if laenge <= 0:
            return None
        return [float(w) / laenge for w in werte]
    except Exception:
        return None


def _cache_laden() -> dict[str, list[float]]:
    global _cache
    if _cache is not None:
        return _cache
    daten: dict[str, list[float]] = {}
    if CACHE_DATEI.exists():
        try:
            roh = json.loads(CACHE_DATEI.read_text(encoding="utf-8"))
            if isinstance(roh, dict):
                daten = {k: list(v) for k, v in roh.items() if isinstance(v, list)}
        except Exception:
            daten = {}
    _cache = daten
    return _cache


def _cache_sichern() -> None:
    if _cache is None:
        return
    try:
        eintraege = list(_cache.items())[-MAX_CACHE:]
        atomic_write_text(
            CACHE_DATEI,
            json.dumps(dict(eintraege), ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        return


def vektor(text: str, merken: bool = True) -> list[float]:
    inhalt = str(text or "").strip()
    if not inhalt:
        return [0.0] * DIM
    modell = _modellname()
    if not modell:
        return _lokaler_vektor(inhalt)
    schluessel = hashlib.blake2b(
        f"{modell}|{inhalt}".encode("utf-8"), digest_size=12
    ).hexdigest()
    with _lock:
        speicher = _cache_laden()
        vorhanden = speicher.get(schluessel)
    if vorhanden:
        return vorhanden
    werte = _ollama_vektor(inhalt, modell)
    if werte is None:
        return _lokaler_vektor(inhalt)
    if merken:
        with _lock:
            speicher = _cache_laden()
            speicher[schluessel] = werte
            _cache_sichern()
    return werte


def aehnlichkeit(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))


class Index:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._eintraege: dict[str, list[float]] = {}
        self._texte: dict[str, str] = {}

    def setzen(self, name: str, text: str) -> None:
        with self._lock:
            if self._texte.get(name) == text:
                return
            self._texte[name] = text
            self._eintraege[name] = vektor(text)

    def entfernen(self, name: str) -> None:
        with self._lock:
            self._eintraege.pop(name, None)
            self._texte.pop(name, None)

    def leeren(self) -> None:
        with self._lock:
            self._eintraege.clear()
            self._texte.clear()

    def namen(self) -> list[str]:
        with self._lock:
            return list(self._eintraege)

    def suchen(
        self, text: str, top_k: int = 8, schwelle: float = 0.12
    ) -> list[tuple[str, float]]:
        frage = vektor(text)
        with self._lock:
            eintraege = list(self._eintraege.items())
        bewertet = [(name, aehnlichkeit(frage, werte)) for name, werte in eintraege]
        bewertet = [(n, w) for n, w in bewertet if w >= schwelle]
        bewertet.sort(key=lambda paar: paar[1], reverse=True)
        return bewertet[:top_k]


def get_index(name: str) -> Index:
    with _lock:
        if name not in _indizes:
            _indizes[name] = Index()
        return _indizes[name]
