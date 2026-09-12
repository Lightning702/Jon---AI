from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from app.core.fehler import leise


@dataclass
class Fall:
    kennung: str
    bereich: str
    beschreibung: str
    pruefung: Callable[[], bool]
    gewicht: float = 1.0


@dataclass
class Ergebnis:
    kennung: str
    bereich: str
    beschreibung: str
    bestanden: bool
    fehler: str = ""
    dauer: float = 0.0

    def als_dict(self) -> dict:
        return {
            "kennung": self.kennung,
            "bereich": self.bereich,
            "beschreibung": self.beschreibung,
            "bestanden": self.bestanden,
            "fehler": self.fehler,
            "dauer": round(self.dauer, 3),
        }


def _werkzeug_da(text: str, name: str) -> bool:
    from app.services.tools import select_tools

    namen = select_tools(text)
    return namen is None or name in namen


def _risiko(name: str, args: dict) -> str:
    from app.services.risiko import bewerten

    return bewerten(name, args).risiko


def _browser_risiko(ziel: str, url: str = "") -> str:
    from app.services.browser.sicherheit import get_guard

    return get_guard().bewerten("click", {}, url=url, ziel=ziel).risiko


def _zeit(text: str) -> str:
    from app.services.zeitraum import verstehen

    return verstehen(text).beschreibung


def _plan(text: str) -> bool:
    from app.services.browser.planer import braucht_plan

    return braucht_plan(text)[0]


def _zutrauen(werkzeug: str) -> float:
    from app.services.erwartung_service import get_erwartung_service

    return float(get_erwartung_service().schaetzen(werkzeug)["zutrauen"])


def _ueberraschung(zutrauen: float, ok: bool) -> float:
    from app.services.erwartung_service import ErwartungService

    return ErwartungService._ueberraschung(zutrauen, ok, 0.0, 0.0)


def _aufwand(text: str) -> str:
    from app.services.metakognition_service import get_metakognition_service

    return get_metakognition_service().einschaetzen(text, False)["stufe"]


def _budget_haelt(text: str, budget: int) -> bool:
    from app.services.aufmerksamkeit_service import get_aufmerksamkeit_service

    return get_aufmerksamkeit_service().waehlen(text, budget)["verbraucht"] <= budget


def _planschritte(daten: dict) -> list[dict]:
    from app.services.planer_service import PlanerService
    from app.services.tools import werkzeugnamen

    return PlanerService._saeubern(daten, werkzeugnamen() | {"denken"})


def faelle() -> list[Fall]:
    from app.services.datenschutz_service import darf_raus, einstufen
    from app.services.fehlertext import verstaendlich
    from app.services.semantik import aehnlichkeit, vektor

    liste: list[Fall] = []

    werkzeug_proben = [
        ("w01", "Mach mir einen Screenshot vom Bildschirm", "screenshot"),
        ("w02", "Was laeuft gerade auf Spotify", "spotify_now_playing"),
        ("w03", "Trag mir Freitag 15 Uhr Zahnarzt ein", "calendar_add"),
        ("w04", "Wie wird das Wetter morgen in Wien", "get_weather"),
        ("w05", "Geh auf die Webseite und leg das Buch in den Warenkorb", "browser_task"),
        ("w06", "Kannst du auf einer homepage was raussuchen", "browser_read"),
        ("w07", "Wo ist die naechste Apotheke", "maps"),
        ("w08", "Zeig mir meinen Downloads-Ordner", "list_dir"),
        ("w09", "Was habe ich gestern gemacht", "was_war"),
        ("w10", "Was steht morgen an", "ziel"),
        ("w11", "Merk dir, dass ich Kaffee mag", "remember_about_user"),
        ("w12", "Mach das Licht im Wohnzimmer aus", "smarthome_control"),
        ("w13", "Lies mir das PDF vor", "read_pdf"),
        ("w14", "Schaffst du das ueberhaupt", "selbstbild"),
        ("w15", "Ist das Internet gerade da", "netz_status"),
    ]
    for kennung, text, werkzeug in werkzeug_proben:
        liste.append(
            Fall(
                kennung,
                "werkzeugauswahl",
                f"{text} -> {werkzeug}",
                lambda t=text, n=werkzeug: _werkzeug_da(t, n),
            )
        )

    risiko_proben = [
        ("r01", "read_file", {"path": "a.txt"}, "niedrig"),
        ("r02", "list_dir", {"path": "."}, "niedrig"),
        ("r03", "write_file", {"path": "a.txt"}, "mittel"),
        ("r04", "delete_path", {"path": "C:/Windows/System32"}, "hoch"),
        ("r05", "send_mail", {"to": "a@b.c"}, "hoch"),
        ("r06", "run_powershell", {"command": "Get-Date"}, "mittel"),
        ("r07", "run_powershell", {"command": "Remove-Item C: -Recurse -Force"}, "hoch"),
        ("r08", "write_file", {"path": "C:/Program Files/x.dll"}, "hoch"),
        ("r09", "browser_read", {}, "niedrig"),
        ("r10", "browser_confirm", {"token": "x"}, "hoch"),
    ]
    for kennung, name, args, erwartet in risiko_proben:
        liste.append(
            Fall(
                kennung,
                "risiko",
                f"{name} -> {erwartet}",
                lambda n=name, a=args, e=erwartet: _risiko(n, a) == e,
                1.5,
            )
        )

    browser_proben = [
        ("b01", "In den Warenkorb", "", "mittel"),
        ("b02", "Kostenpflichtig bestellen", "", "hoch"),
        ("b03", "Jetzt kaufen", "", "hoch"),
        ("b04", "Nachricht senden", "", "hoch"),
        ("b05", "Konto loeschen", "", "hoch"),
        ("b06", "Weiterlesen", "", "niedrig"),
        ("b07", "Absenden", "https://shop.test/kasse", "hoch"),
    ]
    for kennung, ziel, url, erwartet in browser_proben:
        liste.append(
            Fall(
                kennung,
                "browserwaechter",
                f"{ziel} -> {erwartet}",
                lambda z=ziel, u=url, e=erwartet: _browser_risiko(z, u) == e,
                1.5,
            )
        )

    zeit_proben = [
        ("z01", "gestern", "gestern"),
        ("z02", "morgen", "morgen"),
        ("z03", "letzte woche", "letzte Woche"),
        ("z04", "vor 3 tagen", "vor 3 Tagen"),
        ("z05", "24.12.", "24.12."),
        ("z06", "", "heute"),
    ]
    for kennung, text, erwartet in zeit_proben:
        liste.append(
            Fall(
                kennung,
                "zeit",
                f"{text or '(leer)'} -> {erwartet}",
                lambda t=text, e=erwartet: e in _zeit(t),
            )
        )

    plan_proben = [
        ("p01", "Oeffne Wikipedia", False),
        ("p02", "Vergleiche Hotels und buche das beste", True),
        ("p03", "Bestell mir eine Pizza", True),
        ("p04", "Lies mir die Seite vor", False),
    ]
    for kennung, text, erwartet in plan_proben:
        liste.append(
            Fall(
                kennung,
                "planer",
                f"{text} -> Plan {erwartet}",
                lambda t=text, e=erwartet: _plan(t) is e,
            )
        )

    datenschutz_proben = [
        ("d01", "Mein Passwort ist geheim123", "geheim"),
        ("d02", "Schreib an felix@example.com", "persoenlich"),
        ("d03", "Wie spaet ist es", "oeffentlich"),
    ]
    for kennung, text, erwartet in datenschutz_proben:
        liste.append(
            Fall(
                kennung,
                "datenschutz",
                f"{text[:30]} -> {erwartet}",
                lambda t=text, e=erwartet: einstufen(t).stufe == e,
                1.5,
            )
        )
    liste.append(
        Fall(
            "d04",
            "datenschutz",
            "Passwort geht nicht per Mail raus",
            lambda: darf_raus("send_mail", {"body": "passwort: abc123"})[0] is False,
            2.0,
        )
    )

    fehler_proben = [
        ("f01", "[WinError 5] Zugriff verweigert", "Rechte"),
        ("f02", "httpx.ConnectTimeout: timed out", "Zeitueberschreitung"),
        ("f03", "net::ERR_NAME_NOT_RESOLVED", "Adresse"),
        ("f04", "429 rate limit exceeded", "bremst"),
    ]
    for kennung, roh, erwartet in fehler_proben:
        liste.append(
            Fall(
                kennung,
                "fehlertexte",
                f"{roh[:24]} -> verstaendlich",
                lambda r=roh, e=erwartet: e.lower() in verstaendlich(r).lower(),
            )
        )

    liste.append(
        Fall(
            "s01",
            "semantik",
            "aehnliche Saetze werden erkannt",
            lambda: aehnlichkeit(
                vektor("Der Nutzer wohnt in Wien"), vektor("Der Nutzer wohnt in Graz")
            )
            > 0.6,
        )
    )
    liste.append(
        Fall(
            "s02",
            "semantik",
            "fremde Saetze bleiben getrennt",
            lambda: aehnlichkeit(
                vektor("Der Hund heisst Rex"), vektor("Die Rechnung ist bezahlt")
            )
            < 0.4,
        )
    )
    liste.append(
        Fall(
            "s03",
            "semantik",
            "Synonyme greifen",
            lambda: aehnlichkeit(vektor("homepage"), vektor("webseite")) > 0.3,
        )
    )

    aufwand_proben = [
        ("m01", "danke dir", "schnell"),
        ("m02", "wie spaet ist es", "schnell"),
        (
            "m03",
            "Recherchiere die drei guenstigsten Anbieter, vergleiche sie und "
            "erstelle mir danach eine Uebersicht mit Empfehlung, und dann schick "
            "sie mir per Mail. Warum ist der erste eigentlich so teuer?",
            "gruendlich",
        ),
    ]
    for kennung, text, stufe in aufwand_proben:
        liste.append(
            Fall(
                kennung,
                "metakognition",
                f"{text[:40]} -> {stufe}",
                lambda t=text, e=stufe: _aufwand(t) == e,
            )
        )

    liste.append(
        Fall(
            "e01",
            "erwartung",
            "Zutrauen liegt zwischen 0 und 1",
            lambda: 0.0 < _zutrauen("list_dir") <= 1.0,
        )
    )
    liste.append(
        Fall(
            "e02",
            "erwartung",
            "unsichere Werkzeuge bekommen weniger Vorschuss",
            lambda: _zutrauen("run_powershell") <= _zutrauen("list_dir"),
        )
    )
    liste.append(
        Fall(
            "e03",
            "erwartung",
            "ein Fehlschlag trotz hoher Erwartung ueberrascht",
            lambda: _ueberraschung(0.9, False) >= 0.45,
        )
    )
    liste.append(
        Fall(
            "e04",
            "erwartung",
            "ein Erfolg wie erwartet ueberrascht nicht",
            lambda: _ueberraschung(0.9, True) < 0.45,
        )
    )
    liste.append(
        Fall(
            "a01",
            "aufmerksamkeit",
            "das Denkbudget wird eingehalten",
            lambda: _budget_haelt("Was steht heute an?", 600),
        )
    )
    liste.append(
        Fall(
            "a02",
            "aufmerksamkeit",
            "mehr Budget bedeutet nie weniger Inhalt",
            lambda: _budget_haelt("Was steht heute an?", 4000),
        )
    )
    liste.append(
        Fall(
            "p01",
            "planer",
            "erfundene Werkzeuge werden zu Denkschritten",
            lambda: _planschritte(
                {
                    "schritte": [
                        {"id": "s1", "titel": "Zauberei", "werkzeug": "gibt_es_nicht"}
                    ]
                }
            )[0]["werkzeug"]
            == "denken",
        )
    )
    liste.append(
        Fall(
            "p02",
            "planer",
            "echte Werkzeuge bleiben erhalten",
            lambda: _planschritte(
                {
                    "schritte": [
                        {
                            "id": "s1",
                            "titel": "Ordner",
                            "werkzeug": "list_dir",
                            "args": {"path": "C:/"},
                        }
                    ]
                }
            )[0]["werkzeug"]
            == "list_dir",
        )
    )
    liste.append(
        Fall(
            "p03",
            "planer",
            "Abhaengigkeiten auf unbekannte Schritte fallen weg",
            lambda: _planschritte(
                {
                    "schritte": [
                        {
                            "id": "s1",
                            "titel": "Erst",
                            "werkzeug": "denken",
                            "haengt_von": ["gibtsnicht"],
                        }
                    ]
                }
            )[0]["haengt_von"]
            == [],
        )
    )

    return liste


class BenchmarkService:
    def __init__(self) -> None:
        self._letzter: dict = {}

    def lauf(self, bereich: str = "") -> dict:
        ergebnisse: list[Ergebnis] = []
        start = time.time()
        for fall in faelle():
            if bereich and fall.bereich != bereich:
                continue
            begonnen = time.time()
            try:
                bestanden = bool(fall.pruefung())
                fehler = ""
            except Exception as exc:
                leise(exc, "services/benchmark_service")
                bestanden = False
                fehler = str(exc)[:200]
            ergebnisse.append(
                Ergebnis(
                    fall.kennung,
                    fall.bereich,
                    fall.beschreibung,
                    bestanden,
                    fehler,
                    time.time() - begonnen,
                )
            )
        gesamt = len(ergebnisse)
        bestanden = sum(1 for e in ergebnisse if e.bestanden)
        je_bereich: dict[str, dict] = {}
        for eintrag in ergebnisse:
            stand = je_bereich.setdefault(eintrag.bereich, {"gesamt": 0, "gut": 0})
            stand["gesamt"] += 1
            stand["gut"] += 1 if eintrag.bestanden else 0
        self._letzter = {
            "gesamt": gesamt,
            "bestanden": bestanden,
            "quote": round(bestanden / max(1, gesamt), 3),
            "dauer": round(time.time() - start, 2),
            "bereiche": je_bereich,
            "durchgefallen": [e.als_dict() for e in ergebnisse if not e.bestanden],
        }
        return self._letzter

    def letzter(self) -> dict:
        return dict(self._letzter)


_service: BenchmarkService | None = None


def get_benchmark_service() -> BenchmarkService:
    global _service
    if _service is None:
        _service = BenchmarkService()
    return _service
