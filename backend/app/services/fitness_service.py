from __future__ import annotations

import re
import secrets
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any

from app.core.config import DATA_DIR
from app.core.logbook import logger as logbook_logger

_log = logbook_logger("fitness")

STORE = DATA_DIR / "fitness.json"
ARTEN = ("gym", "laufen", "rad", "schwimmen", "yoga", "wandern", "sonstiges")
ART_NAMEN = {
    "gym": "Gym",
    "laufen": "Laufen",
    "rad": "Radfahren",
    "schwimmen": "Schwimmen",
    "yoga": "Yoga",
    "wandern": "Wandern",
    "sonstiges": "Training",
}
TAGE_MAX = 400
TRAININGS_MAX = 2000
SCHRITTZIEL = 8000
WOCHENZIEL = 3

_ZAHL = r"\d+(?:[.,]\d+)?"
_SAETZE = re.compile(rf"(\d+)\s*[x×\*]\s*(\d+)(?:\s*(?:mit|à|a|@|je)?\s*({_ZAHL})\s*(?:kg|kilo))?", re.I)
_GEWICHT = re.compile(rf"({_ZAHL})\s*(?:kg|kilo)", re.I)
_WDH = re.compile(r"(\d+)\s*(?:wdh|wiederholungen|mal|stück|stueck)?", re.I)
_TRENNER = re.compile(r"\s*(?:[;\n]|(?<!\d),|,(?!\d)|\bund\b|\bdann\b)\s*", re.I)


class FitnessFehler(Exception):
    pass


def _zahl(text: str) -> float:
    return float(text.replace(",", "."))


def uebungen_lesen(text: str) -> list[dict]:
    uebungen: list[dict] = []
    for teil in _TRENNER.split(text or ""):
        teil = teil.strip(" .:-")
        if not teil:
            continue
        saetze: list[dict] = []
        rest = teil
        treffer = _SAETZE.search(teil)
        if treffer:
            anzahl = max(1, min(20, int(treffer.group(1))))
            wdh = max(1, min(500, int(treffer.group(2))))
            gewicht_text = treffer.group(3)
            if gewicht_text is None:
                weiteres = _GEWICHT.search(teil)
                gewicht_text = weiteres.group(1) if weiteres else None
            gewicht = _zahl(gewicht_text) if gewicht_text else 0.0
            saetze = [{"wdh": wdh, "gewicht": gewicht} for _ in range(anzahl)]
            rest = _SAETZE.sub(" ", teil)
            rest = _GEWICHT.sub(" ", rest)
        else:
            gewicht_treffer = _GEWICHT.search(teil)
            gewicht = _zahl(gewicht_treffer.group(1)) if gewicht_treffer else 0.0
            ohne_gewicht = _GEWICHT.sub(" ", teil)
            wdh_treffer = _WDH.search(ohne_gewicht)
            if wdh_treffer:
                saetze = [{"wdh": max(1, min(500, int(wdh_treffer.group(1)))), "gewicht": gewicht}]
                rest = _WDH.sub(" ", ohne_gewicht, count=1)
            else:
                rest = ohne_gewicht
        name = re.sub(r"\b(?:mit|à|je|sätze|saetze|satz|wdh|wiederholungen|mal|kg|kilo)\b", " ", rest, flags=re.I)
        name = re.sub(r"[^\wÄÖÜäöüß\- ]", " ", name)
        name = re.sub(r"\s+", " ", name).strip(" -")
        if not name:
            continue
        uebungen.append({"name": name[:60].capitalize() if name.islower() else name[:60], "saetze": saetze})
    return uebungen[:30]


def datum_lesen(wert: Any) -> str:
    text = str(wert or "").strip().lower()
    heute = date.today()
    if not text or text == "heute":
        return heute.isoformat()
    if text == "gestern":
        return (heute - timedelta(days=1)).isoformat()
    if text == "vorgestern":
        return (heute - timedelta(days=2)).isoformat()
    for muster in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, muster).date().isoformat()
        except ValueError:
            continue
    kurz = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.?", text)
    if kurz:
        try:
            return date(heute.year, int(kurz.group(2)), int(kurz.group(1))).isoformat()
        except ValueError:
            pass
    raise FitnessFehler("Das Datum verstehe ich nicht. Nimm heute, gestern oder TT.MM.JJJJ.")


def _saetze_sauber(roh: Any) -> list[dict]:
    saetze = []
    for satz in roh if isinstance(roh, list) else []:
        if not isinstance(satz, dict):
            continue
        try:
            wdh = max(0, min(500, int(satz.get("wdh", satz.get("reps", 0)) or 0)))
            gewicht = max(0.0, min(1000.0, float(satz.get("gewicht", satz.get("weight", 0)) or 0)))
        except (TypeError, ValueError):
            continue
        if wdh or gewicht:
            saetze.append({"wdh": wdh, "gewicht": round(gewicht, 2)})
    return saetze[:20]


def _uebungen_sauber(roh: Any) -> list[dict]:
    uebungen = []
    for uebung in roh if isinstance(roh, list) else []:
        if not isinstance(uebung, dict):
            continue
        name = " ".join(str(uebung.get("name", "")).split())[:60]
        if not name:
            continue
        uebungen.append({"name": name, "saetze": _saetze_sauber(uebung.get("saetze", uebung.get("sets")))})
    return uebungen[:30]


def volumen(training: dict) -> float:
    return round(sum(s["wdh"] * s["gewicht"] for u in training.get("uebungen", []) for s in u.get("saetze", [])), 1)


class FitnessService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._daten = self._laden()

    def _laden(self) -> dict:
        from app.core.krypto import json_lesen

        roh = json_lesen(STORE, {}, "fitness")
        if not isinstance(roh, dict):
            roh = {}
        schritte = roh.get("schritte") if isinstance(roh.get("schritte"), dict) else {}
        trainings = roh.get("trainings") if isinstance(roh.get("trainings"), list) else []
        ziele = roh.get("ziele") if isinstance(roh.get("ziele"), dict) else {}
        gewicht = roh.get("gewicht") if isinstance(roh.get("gewicht"), list) else []
        return {"schritte": schritte, "trainings": trainings, "ziele": ziele, "gewicht": gewicht}

    def _sichern(self) -> None:
        from app.core.krypto import json_schreiben

        json_schreiben(STORE, self._daten, "fitness")

    def ziele(self) -> dict:
        with self._lock:
            ziele = dict(self._daten["ziele"])
        return {
            "schritte": int(ziele.get("schritte") or SCHRITTZIEL),
            "trainings_pro_woche": int(ziele.get("trainings_pro_woche") or WOCHENZIEL),
        }

    def ziel_setzen(self, schritte: Any = None, trainings_pro_woche: Any = None) -> dict:
        with self._lock:
            ziele = dict(self._daten["ziele"])
            if schritte is not None:
                try:
                    ziele["schritte"] = max(500, min(100_000, int(schritte)))
                except (TypeError, ValueError) as exc:
                    raise FitnessFehler("Das Schrittziel braucht eine Zahl.") from exc
            if trainings_pro_woche is not None:
                try:
                    ziele["trainings_pro_woche"] = max(1, min(21, int(trainings_pro_woche)))
                except (TypeError, ValueError) as exc:
                    raise FitnessFehler("Das Wochenziel braucht eine Zahl.") from exc
            self._daten["ziele"] = ziele
            self._sichern()
        return self.ziele()

    def schritte_melden(self, tage: dict, quelle: str = "handy") -> dict:
        if not isinstance(tage, dict):
            raise FitnessFehler("Schritte kommen als {datum: anzahl}.")
        grenze = (date.today() - timedelta(days=TAGE_MAX)).isoformat()
        morgen = (date.today() + timedelta(days=1)).isoformat()
        geaendert = 0
        with self._lock:
            speicher = self._daten["schritte"]
            for tag, anzahl in list(tage.items())[:60]:
                try:
                    tag_text = date.fromisoformat(str(tag)).isoformat()
                    zahl = max(0, min(200_000, int(anzahl)))
                except (TypeError, ValueError):
                    continue
                if tag_text < grenze or tag_text > morgen:
                    continue
                alt = speicher.get(tag_text) or {}
                if zahl >= int(alt.get("anzahl") or 0):
                    speicher[tag_text] = {"anzahl": zahl, "quelle": str(quelle)[:20], "zeit": time.time()}
                    geaendert += 1
            for alt_tag in [t for t in speicher if t < grenze]:
                speicher.pop(alt_tag, None)
            if geaendert:
                self._sichern()
        return {"gespeichert": geaendert}

    def training_eintragen(self, daten: dict) -> dict:
        art = str(daten.get("art") or "gym").strip().lower()
        if art not in ARTEN:
            art = "sonstiges"
        uebungen = _uebungen_sauber(daten.get("uebungen"))
        if not uebungen and daten.get("text"):
            uebungen = uebungen_lesen(str(daten.get("text")))
        try:
            dauer = max(0, min(24 * 60, int(float(daten.get("dauer_min") or 0))))
            distanz = max(0.0, min(1000.0, float(str(daten.get("distanz_km") or 0).replace(",", "."))))
        except (TypeError, ValueError) as exc:
            raise FitnessFehler("Dauer oder Distanz ist keine Zahl.") from exc
        titel = " ".join(str(daten.get("titel") or "").split())[:80] or ART_NAMEN[art]
        if not uebungen and not dauer and not distanz:
            raise FitnessFehler("Sag mir, was du gemacht hast: Übungen, Dauer oder Strecke.")
        training = {
            "id": secrets.token_hex(5),
            "datum": datum_lesen(daten.get("datum")),
            "zeit": time.time(),
            "art": art,
            "titel": titel,
            "dauer_min": dauer,
            "distanz_km": round(distanz, 2),
            "uebungen": uebungen,
            "notiz": " ".join(str(daten.get("notiz") or "").split())[:300],
        }
        with self._lock:
            liste = self._daten["trainings"]
            liste.append(training)
            self._daten["trainings"] = liste[-TRAININGS_MAX:]
            self._sichern()
        _log.info("Training eingetragen: %s am %s", titel, training["datum"])
        return {**training, "volumen": volumen(training), "rekorde": self._neue_rekorde(training)}

    def abgleichen(self, trainings: Any, geloescht: Any, schritte: Any, quelle: str = "handy") -> dict:
        if isinstance(schritte, dict):
            self.schritte_melden(schritte, quelle)
        weg = {str(k) for k in (geloescht if isinstance(geloescht, list) else [])}
        neu = 0
        with self._lock:
            liste = [t for t in self._daten["trainings"] if t.get("id") not in weg]
            bekannt = {t.get("id") for t in liste}
            for roh in trainings if isinstance(trainings, list) else []:
                if not isinstance(roh, dict):
                    continue
                kennung = str(roh.get("id", ""))[:40]
                if not kennung or kennung in bekannt:
                    continue
                try:
                    training = {
                        "id": kennung,
                        "datum": datum_lesen(roh.get("datum")),
                        "zeit": float(roh.get("zeit") or time.time()),
                        "art": str(roh.get("art") or "sonstiges") if str(roh.get("art") or "") in ARTEN else "sonstiges",
                        "titel": " ".join(str(roh.get("titel") or "Training").split())[:80],
                        "dauer_min": max(0, min(24 * 60, int(float(roh.get("dauer_min") or 0)))),
                        "distanz_km": max(0.0, min(1000.0, float(roh.get("distanz_km") or 0))),
                        "uebungen": _uebungen_sauber(roh.get("uebungen")),
                        "notiz": " ".join(str(roh.get("notiz") or "").split())[:300],
                    }
                except (FitnessFehler, TypeError, ValueError):
                    continue
                liste.append(training)
                bekannt.add(kennung)
                neu += 1
            self._daten["trainings"] = liste[-TRAININGS_MAX:]
            if neu or weg:
                self._sichern()
            alle = list(self._daten["trainings"])
        return {"neu": neu, "trainings": alle[-500:], "ziele": self.ziele()}

    def training_loeschen(self, kennung: str) -> bool:
        with self._lock:
            vorher = len(self._daten["trainings"])
            self._daten["trainings"] = [t for t in self._daten["trainings"] if t.get("id") != kennung]
            weg = len(self._daten["trainings"]) != vorher
            if weg:
                self._sichern()
        return weg

    def gewicht_eintragen(self, kg: Any, datum: Any = None) -> dict:
        try:
            wert = round(float(str(kg).replace(",", ".")), 1)
        except (TypeError, ValueError) as exc:
            raise FitnessFehler("Das Körpergewicht braucht eine Zahl.") from exc
        if not 20 <= wert <= 400:
            raise FitnessFehler("Das Körpergewicht wirkt unrealistisch.")
        tag = datum_lesen(datum)
        with self._lock:
            liste = [g for g in self._daten["gewicht"] if g.get("datum") != tag]
            liste.append({"datum": tag, "kg": wert})
            self._daten["gewicht"] = sorted(liste, key=lambda g: g["datum"])[-TAGE_MAX:]
            self._sichern()
        return {"datum": tag, "kg": wert}

    def _rekorde_aus(self, trainings: list[dict]) -> dict[str, dict]:
        rekorde: dict[str, dict] = {}
        for training in sorted(trainings, key=lambda t: (t.get("datum", ""), t.get("zeit", 0))):
            for uebung in training.get("uebungen", []):
                schluessel = uebung["name"].strip().lower()
                for satz in uebung.get("saetze", []):
                    bisher = rekorde.get(schluessel)
                    if satz["gewicht"] <= 0:
                        continue
                    if bisher is None or satz["gewicht"] > bisher["gewicht"] or (satz["gewicht"] == bisher["gewicht"] and satz["wdh"] > bisher["wdh"]):
                        rekorde[schluessel] = {"name": uebung["name"], "gewicht": satz["gewicht"], "wdh": satz["wdh"], "datum": training["datum"]}
        return rekorde

    def _neue_rekorde(self, training: dict) -> list[str]:
        with self._lock:
            vorher = [t for t in self._daten["trainings"] if t.get("id") != training["id"]]
        alte = self._rekorde_aus(vorher)
        neue = []
        for uebung in training.get("uebungen", []):
            schluessel = uebung["name"].strip().lower()
            bestes = max((s["gewicht"] for s in uebung.get("saetze", [])), default=0.0)
            if bestes > 0 and (schluessel not in alte or bestes > alte[schluessel]["gewicht"]):
                neue.append(f"{uebung['name']}: {bestes:g} kg")
        return neue

    def uebersicht(self, tage: int = 7) -> dict:
        tage = max(1, min(90, int(tage)))
        heute = date.today()
        with self._lock:
            schritte = dict(self._daten["schritte"])
            trainings = list(self._daten["trainings"])
            gewicht = list(self._daten["gewicht"])
        ziele = self.ziele()
        verlauf = []
        for versatz in range(tage - 1, -1, -1):
            tag = (heute - timedelta(days=versatz)).isoformat()
            verlauf.append({"datum": tag, "schritte": int((schritte.get(tag) or {}).get("anzahl") or 0)})
        wochenbeginn = heute - timedelta(days=heute.weekday())
        diese_woche = [t for t in trainings if t.get("datum", "") >= wochenbeginn.isoformat()]
        serie = 0
        tag = heute
        tage_mit = {t.get("datum") for t in trainings}
        if heute.isoformat() not in tage_mit:
            tag = heute - timedelta(days=1)
        while tag.isoformat() in tage_mit:
            serie += 1
            tag -= timedelta(days=1)
        letzte = sorted(trainings, key=lambda t: (t.get("datum", ""), t.get("zeit", 0)), reverse=True)[:15]
        rekorde = sorted(self._rekorde_aus(trainings).values(), key=lambda r: r["gewicht"], reverse=True)[:12]
        heute_schritte = verlauf[-1]["schritte"]
        return {
            "heute": {
                "datum": heute.isoformat(),
                "schritte": heute_schritte,
                "ziel": ziele["schritte"],
                "fortschritt": round(min(1.0, heute_schritte / max(1, ziele["schritte"])), 3),
            },
            "verlauf": verlauf,
            "schnitt": round(sum(v["schritte"] for v in verlauf) / len(verlauf)),
            "woche": {
                "trainings": len(diese_woche),
                "ziel": ziele["trainings_pro_woche"],
                "minuten": sum(int(t.get("dauer_min") or 0) for t in diese_woche),
                "volumen": round(sum(volumen(t) for t in diese_woche), 1),
            },
            "serie": serie,
            "trainings": [{**t, "volumen": volumen(t), "art_name": ART_NAMEN.get(t.get("art", ""), "Training")} for t in letzte],
            "rekorde": rekorde,
            "gewicht": gewicht[-30:],
            "ziele": ziele,
        }


_dienst: FitnessService | None = None
_dienst_lock = threading.Lock()


def get_fitness_service() -> FitnessService:
    global _dienst
    with _dienst_lock:
        if _dienst is None:
            _dienst = FitnessService()
        return _dienst
