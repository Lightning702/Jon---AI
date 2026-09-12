from __future__ import annotations

import asyncio
import json

import pytest

from app.services.aufmerksamkeit_service import get_aufmerksamkeit_service
from app.services.erwartung_service import get_erwartung_service
from app.services.fertigkeit_service import get_fertigkeit_service
from app.services.metakognition_service import GRUENDLICH, SCHNELL
from app.services.metakognition_service import get_metakognition_service
from app.services.neugier_service import BEANTWORTET, get_neugier_service
from app.services.planer_service import get_planer_service


def _frisch():
    dienst = get_erwartung_service()
    dienst._quoten = {}
    dienst._quoten_zeit = 0.0
    dienst._dauern = {}
    dienst._dauern_zeit = 0.0
    return dienst


def test_erwartung_wird_notiert_und_verglichen():
    dienst = _frisch()
    kennung = dienst.vorhersagen("list_dir", {"path": "C:/"})
    assert kennung
    ergebnis = dienst.abgleichen(kennung, True, '{"eintraege": []}', 0.2)
    assert ergebnis["gelungen"] is True
    assert 0.0 <= ergebnis["ueberraschung"] <= 1.0
    assert dienst.abgleichen(kennung, True, "", 0.1) == {}


def test_fehlschlag_bei_hohem_zutrauen_ueberrascht_und_lehrt():
    dienst = _frisch()
    kennung = dienst.vorhersagen("open_url", {"url": "https://example.com"})
    ergebnis = dienst.abgleichen(kennung, False, '{"error": "kein Netz"}', 0.4)
    assert ergebnis["ueberraschung"] >= 0.45

    from app.services.erfahrung_service import KLAPPT_NICHT, get_erfahrung_service

    eintraege = get_erfahrung_service().fuer("werkzeug:open_url", 10)
    assert any(e["art"] == KLAPPT_NICHT for e in eintraege)


def test_kalibrierung_rechnet_brier():
    dienst = _frisch()
    for _ in range(4):
        kennung = dienst.vorhersagen("netz_status", {})
        dienst.abgleichen(kennung, True, "{}", 0.05)
    kalib = dienst.kalibrierung(30)
    assert kalib["anzahl"] >= 4
    assert 0.0 <= kalib["brier"] <= 1.0
    assert kalib["text"]


def test_neugier_merkt_unsicherheit_und_dedupliziert():
    dienst = get_neugier_service()
    erste = dienst.aus_antwort(
        "Wie heisst der hoechste Berg in Vorarlberg",
        "Das weiss ich nicht genau, vermutlich irgendwas mit Piz.",
    )
    assert erste.get("id")
    zweite = dienst.fragen("Wie heisst der hoechste Berg in Vorarlberg?")
    assert zweite["id"] == erste["id"]
    assert any(f["id"] == erste["id"] for f in dienst.offene(50))


def test_neugier_sichere_antwort_erzeugt_keine_frage():
    dienst = get_neugier_service()
    vorher = len(dienst.offene(80))
    dienst.aus_antwort("Was ist 2+2", "Das sind 4.")
    assert len(dienst.offene(80)) == vorher


def test_neugier_antwort_landet_im_gedaechtnis(monkeypatch):
    dienst = get_neugier_service()
    frage = dienst.fragen("Welchen Kaffee mag Felix am Morgen?", dringlichkeit=0.9)

    async def _suche(query, limit=6, read=False):
        return {"treffer": [{"title": "Notiz", "snippet": "Felix trinkt Espresso."}]}

    async def _complete(system, user, *args, **kwargs):
        assert "Espresso" in user
        return "Felix trinkt morgens Espresso."

    monkeypatch.setattr("app.services.websearch_service.search_web", _suche)
    monkeypatch.setattr("app.services.llm.complete", _complete)
    ergebnis = asyncio.run(dienst.beantworten(frage["id"]))
    assert ergebnis["zustand"] == BEANTWORTET
    assert "Espresso" in ergebnis["antwort"]

    from app.services.memory_service import MemoryService

    assert MemoryService().search("Espresso", 10)


def test_neugier_unklare_antwort_zaehlt_als_versuch(monkeypatch):
    dienst = get_neugier_service()
    frage = dienst.fragen("Wie viele Blaetter hat der Baum vor dem Fenster?")

    async def _suche(query, limit=6, read=False):
        return {"treffer": []}

    async def _complete(system, user, *args, **kwargs):
        return "UNKLAR"

    monkeypatch.setattr("app.services.websearch_service.search_web", _suche)
    monkeypatch.setattr("app.services.llm.complete", _complete)
    ergebnis = asyncio.run(dienst.beantworten(frage["id"]))
    assert ergebnis["zustand"] != BEANTWORTET
    assert ergebnis["versuche"] == 1


def test_fertigkeit_anlegen_pruefen_und_ausfuehren(monkeypatch):
    dienst = get_fertigkeit_service()
    dienst.loeschen("Morgenlage")
    fehler = dienst.anlegen("Leer", [])
    assert fehler.get("error")

    fertigkeit = dienst.anlegen(
        "Morgenlage",
        [
            {"werkzeug": "netz_status", "args": {}},
            {"werkzeug": "list_dir", "args": {"path": "{{ordner}}"}},
        ],
        beschreibung="Zeit ansehen und einen Ordner pruefen",
        ausloeser="morgens den Stand pruefen",
    )
    assert fertigkeit["schritte"][0]["bekannt"] is True
    assert dienst.platzhalter("Morgenlage") == ["ordner"]

    ohne_werte = asyncio.run(dienst.ausfuehren("Morgenlage"))
    assert ohne_werte["platzhalter"] == ["ordner"]

    gelaufen: list[tuple[str, dict]] = []

    async def _execute(self, name, args, source=None):
        gelaufen.append((name, args))
        return json.dumps({"ok": True}, ensure_ascii=False)

    monkeypatch.setattr("app.services.tools.ToolBox.execute", _execute)
    ergebnis = asyncio.run(
        dienst.ausfuehren("Morgenlage", {"ordner": "C:/Temp"})
    )
    assert ergebnis["ok"] is True
    assert gelaufen[1][1]["path"] == "C:/Temp"
    assert dienst.holen("Morgenlage")["erfolge"] == 1


def test_fertigkeit_bricht_bei_fehler_ab_und_zaehlt(monkeypatch):
    dienst = get_fertigkeit_service()
    dienst.loeschen("Kettenbruch")
    dienst.anlegen(
        "Kettenbruch",
        [
            {"werkzeug": "netz_status", "args": {}},
            {"werkzeug": "list_dir", "args": {"path": "C:/"}},
        ],
    )
    laeufe: list[str] = []

    async def _execute(self, name, args, source=None):
        laeufe.append(name)
        return json.dumps({"error": "geht nicht"}, ensure_ascii=False)

    monkeypatch.setattr("app.services.tools.ToolBox.execute", _execute)
    ergebnis = asyncio.run(dienst.ausfuehren("Kettenbruch"))
    assert ergebnis["ok"] is False
    assert len(laeufe) == 1
    eintrag = dienst.holen("Kettenbruch")
    assert eintrag["versuche"] == 1 and eintrag["erfolge"] == 0


def test_fertigkeit_entdeckt_wiederkehrende_ketten():
    from app.services.action_log_service import log_action

    for _ in range(4):
        log_action("test", "clipboard_get", {}, "{}", True)
        log_action("test", "clipboard_set", {"text": "x"}, "{}", True)
    vorschlaege = get_fertigkeit_service().entdecken(tage=1, mindest=3)
    assert any("clipboard_set" in v["name"] for v in vorschlaege)


def test_planer_baut_dag_und_fuehrt_der_reihe_nach_aus(monkeypatch):
    dienst = get_planer_service()
    plan_json = json.dumps(
        {
            "schritte": [
                {"id": "s1", "titel": "Netz pruefen", "werkzeug": "netz_status", "args": {}},
                {
                    "id": "s2",
                    "titel": "Zusammenfassen",
                    "werkzeug": "denken",
                    "args": {"frage": "Fasse zusammen"},
                    "haengt_von": ["s1"],
                },
                {
                    "id": "s3",
                    "titel": "Erfundenes Werkzeug",
                    "werkzeug": "gibt_es_nicht",
                    "args": {},
                },
            ],
            "ergebnis": "Ein Ueberblick",
        }
    )

    async def _complete(system, user, *args, **kwargs):
        if "Planer" in system:
            return plan_json
        return "Alles ruhig."

    monkeypatch.setattr("app.services.llm.complete", _complete)
    plan = asyncio.run(dienst.entwerfen("Mach mir einen Ueberblick"))
    assert plan["anzahl"] == 3
    assert plan["schritte"][2]["werkzeug"] == "denken"

    reihenfolge: list[str] = []

    async def _execute(self, name, args, source=None):
        reihenfolge.append(name)
        return json.dumps({"ok": True}, ensure_ascii=False)

    monkeypatch.setattr("app.services.tools.ToolBox.execute", _execute)
    ereignisse = []

    async def _lauf():
        async for eintrag in dienst.ausfuehren(plan["id"]):
            ereignisse.append(eintrag)

    asyncio.run(_lauf())
    assert ereignisse[-1]["art"] == "ende" and ereignisse[-1]["ok"] is True
    assert reihenfolge == ["netz_status"]
    fertig = dienst.holen(plan["id"])
    assert fertig["zustand"] == "fertig"
    assert all(s["zustand"] == "erledigt" for s in fertig["schritte"])


def test_planer_plant_nach_einem_fehler_um(monkeypatch):
    dienst = get_planer_service()
    erster = json.dumps(
        {
            "schritte": [
                {"id": "s1", "titel": "Ordner lesen", "werkzeug": "list_dir", "args": {"path": "C:/"}}
            ],
            "ergebnis": "Liste",
        }
    )
    zweiter = json.dumps(
        {
            "schritte": [
                {"id": "n1", "titel": "Anders denken", "werkzeug": "denken", "args": {"frage": "Was nun?"}}
            ],
            "ergebnis": "Umweg",
        }
    )
    aufrufe = {"plan": 0}

    async def _complete(system, user, *args, **kwargs):
        if "nachbesserst" in system or "gescheiterten" in system:
            return zweiter
        if "Planer" in system:
            aufrufe["plan"] += 1
            return erster
        return "Nachgedacht."

    monkeypatch.setattr("app.services.llm.complete", _complete)
    plan = asyncio.run(dienst.entwerfen("Lies den Ordner"))

    async def _execute(self, name, args, source=None):
        return json.dumps({"error": "Ordner weg"}, ensure_ascii=False)

    monkeypatch.setattr("app.services.tools.ToolBox.execute", _execute)
    arten = []

    async def _lauf():
        async for eintrag in dienst.ausfuehren(plan["id"]):
            arten.append(eintrag["art"])

    asyncio.run(_lauf())
    assert "umplanung" in arten
    fertig = dienst.holen(plan["id"])
    assert fertig["umplanungen"] == 1


def test_planer_haelt_bei_riskanten_schritten_an(monkeypatch):
    dienst = get_planer_service()
    plan_json = json.dumps(
        {
            "schritte": [
                {
                    "id": "s1",
                    "titel": "Alles loeschen",
                    "werkzeug": "delete_path",
                    "args": {"path": "C:/Windows"},
                }
            ],
            "ergebnis": "weg",
        }
    )

    async def _complete(system, user, *args, **kwargs):
        return plan_json

    monkeypatch.setattr("app.services.llm.complete", _complete)
    plan = asyncio.run(dienst.entwerfen("Loesch mal was"))
    ereignisse = []

    async def _lauf():
        async for eintrag in dienst.ausfuehren(plan["id"]):
            ereignisse.append(eintrag)

    asyncio.run(_lauf())
    assert ereignisse[0]["art"] == "freigabe"


def test_metakognition_trennt_plauderei_von_projekt():
    dienst = get_metakognition_service()
    leicht = dienst.einschaetzen("danke dir")
    schwer = dienst.einschaetzen(
        "Bitte recherchiere die drei guenstigsten Anbieter, vergleiche die Preise "
        "und erstelle mir danach eine Uebersicht mit Empfehlung, und dann schick "
        "sie mir per Mail. Warum ist der erste eigentlich so teuer?"
    )
    assert leicht["stufe"] == SCHNELL
    assert schwer["stufe"] == GRUENDLICH
    assert schwer["budget"] > leicht["budget"]
    assert schwer["plan_empfohlen"] is True
    assert dienst.stand()["anzahl"] >= 2


def test_aufmerksamkeit_haelt_das_budget_ein():
    dienst = get_aufmerksamkeit_service()
    gross = dienst.waehlen("Was steht heute an?", budget=4000)
    klein = dienst.waehlen("Was steht heute an?", budget=300)
    assert gross["verbraucht"] <= 4000
    assert klein["verbraucht"] <= 300
    assert len(klein["gewaehlt"]) <= len(gross["gewaehlt"])
    assert all(isinstance(b, str) and b for b in gross["bloecke"])


def test_chat_denkbloecke_nutzen_die_aufmerksamkeit():
    from app.services.chat_service import ChatService

    bloecke = ChatService._denkbloecke("Was steht heute an?", 1200)
    assert isinstance(bloecke, list)
    assert sum(len(b) for b in bloecke) <= 1200


@pytest.mark.parametrize(
    "werkzeug",
    [
        "selbsteinschaetzung",
        "ueberraschungen",
        "frage_merken",
        "offene_fragen",
        "frage_klaeren",
        "fertigkeiten",
        "fertigkeit_nutzen",
        "plan_machen",
        "plan_ausfuehren",
    ],
)
def test_neue_werkzeuge_sind_registriert_und_beschrieben(werkzeug):
    from app.services.tools import ToolBox, describe_tool
    from app.services.werkzeug_register import finden, finden_async, laden

    laden()
    assert finden(werkzeug) or finden_async(werkzeug)
    namen = {t["function"]["name"] for t in ToolBox()._eigene_tools()}
    assert werkzeug in namen
    assert describe_tool(werkzeug, {}) != werkzeug


def test_denken_gruppe_findet_die_neuen_werkzeuge():
    from app.services.tools import select_tools

    auswahl = select_tools("wie sicher bist du dir dabei eigentlich")
    assert auswahl is None or "selbsteinschaetzung" in auswahl
    plan = select_tools("zerleg das bitte schritt fuer schritt in einen plan")
    assert plan is None or "plan_machen" in plan
