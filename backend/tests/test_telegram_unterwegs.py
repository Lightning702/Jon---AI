from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import telegram_extras as te
from app.services import telegram_group_service as tgs
from app.services import telegram_service as ts


def _routenkarte() -> dict:
    return {
        "kind": "maps",
        "data": {
            "aktion": "route",
            "modus": "fuss",
            "filter": "supermarkt",
            "start": {"name": "Vogelweiderstraße", "lat": 47.8095, "lon": 13.055},
            "ziel": {
                "name": "Billa",
                "label": "Vogelweiderstraße 63",
                "lat": 47.8101,
                "lon": 13.0559,
            },
            "stationen": [
                {"name": "Vogelweiderstraße", "lat": 47.8095, "lon": 13.055},
                {"name": "Billa", "lat": 47.8101, "lon": 13.0559},
            ],
        },
    }


def _lernkarte() -> dict:
    return {"kind": "deep_learning", "data": {"id": "abc123", "task": {"id": "abc123"}}}


class _FakeResearch:
    def __init__(self):
        self.gestartet: list[str] = []
        self.gestoppt: list[str] = []
        self.tasks = {
            "abc123": {
                "id": "abc123",
                "titel": "Quantencomputer",
                "thema": "Quantencomputer",
                "status": "fertig",
                "minuten": 20,
                "fortschritt": 1.0,
                "dateien": ["README.md", "grundlagen.md"],
                "quellen": [{"url": "https://example.org"}],
                "zusammenfassung": "Kurzfassung der Recherche.",
                "ordner": "skills/quantencomputer",
                "fehler": "",
            }
        }

    async def start(self, topic, minutes=0, **kwargs):
        self.gestartet.append(topic)
        return {"id": "neu1", "titel": topic, "minuten": 25}

    def active(self):
        return []

    def list(self):
        return list(self.tasks.values())

    def get(self, task_id):
        return self.tasks[task_id]

    def stop(self, task_id):
        self.gestoppt.append(task_id)
        return self.tasks["abc123"]

    def status_text(self, task):
        return f"{task['titel']} · {task['status']}"

    def read_file(self, task_id, name):
        raise FileNotFoundError(name)


def _fake_research(monkeypatch) -> _FakeResearch:
    dienst = _FakeResearch()
    import app.services.research as research

    monkeypatch.setattr(research, "get_research_service", lambda: dienst)
    return dienst


def test_karte_wird_zu_pin_und_routenlink():
    karten = [_routenkarte()]
    punkte = te.map_points(karten)
    assert len(punkte) == 1
    assert punkte[0]["titel"] == "Billa"
    assert punkte[0]["label"] == "Vogelweiderstraße 63"
    link = te.map_links(karten)[0]
    assert "openstreetmap.org/directions" in link
    assert "fossgis_osrm_foot" in link
    assert "47.80950%2C13.05500%3B47.81010%2C13.05590" in link
    assert te.research_ids([_lernkarte(), _routenkarte()]) == ["abc123"]


def test_umgebungskarte_liefert_ersten_treffer():
    karte = {
        "kind": "maps",
        "data": {
            "aktion": "umgebung",
            "kategorie": "Apotheken",
            "treffer": [
                {"name": "Elisabeth-Apotheke", "label": "Salzburg", "lat": 47.81, "lon": 13.05}
            ],
        },
    }
    punkte = te.map_points([karte])
    assert punkte[0]["titel"] == "Elisabeth-Apotheke"
    assert te.map_links([karte]) == []


def test_lernbefehle_starten_und_stoppen(monkeypatch):
    dienst = _fake_research(monkeypatch)
    assert te.is_learn_command("/lernen Quantencomputer")
    assert te.is_learn_command("/lernstatus@JonBot")
    assert not te.is_learn_command("/stopp")

    antwort, task_id = asyncio.run(
        te.research_command("/lernen Quantencomputer 25 Minuten")
    )
    assert dienst.gestartet == ["Quantencomputer 25 Minuten"]
    assert task_id == "neu1" and "Quantencomputer" in antwort

    hinweis, leer = asyncio.run(te.research_command("/lernen"))
    assert leer == "" and "/lernen" in hinweis

    stand, _ = asyncio.run(te.research_command("/lernstatus"))
    assert "Quantencomputer" in stand

    stopp, _ = asyncio.run(te.research_command("/lernstop abc123"))
    assert dienst.gestoppt == ["abc123"] and "Abgebrochen" in stopp

    assert asyncio.run(te.research_command("/wetter")) is None


def test_lernbericht_fasst_ergebnis_zusammen(monkeypatch):
    _fake_research(monkeypatch)
    bericht = te.research_report("abc123")
    assert "Deep Learning fertig" in bericht
    assert "Quantencomputer" in bericht
    assert "2 Dateien · 1 Quellen" in bericht
    assert "Kurzfassung der Recherche." in bericht


def test_sicherer_werkzeugsatz_hat_maps_und_deep_learning():
    from app.services.chat_service import scoped_tools
    from app.services.tools import ToolBox

    alle = ToolBox().schema("Wo ist der nächste Supermarkt?")
    namen = {tool["function"]["name"] for tool in alle}
    assert "run_powershell" in namen
    gast = {tool["function"]["name"] for tool in scoped_tools(alle, "gast")}
    assert {"maps", "deep_learning", "web_search", "get_weather"} <= gast
    assert "run_powershell" not in gast
    assert "delete_path" not in gast
    assert "check_mail" not in gast
    assert "read_friend_messages" not in gast
    assert "clipboard_history" not in gast
    assert scoped_tools(alle, "voll") == alle
    assert scoped_tools(alle, "") == alle


def test_systemtext_beschreibt_werkzeuge_je_nach_scope():
    ohne = tgs._system_text("junior", "MiniJonBot", "Anna", True, "", "")
    gast = tgs._system_text("junior", "MiniJonBot", "Anna", True, "", "gast")
    voll = tgs._system_text("junior", "MiniJonBot", "Anna", False, "", "voll")
    assert "KEINE Aktionen" in ohne and "maps" not in ohne
    assert "maps" in gast and "deep_learning" in gast
    assert "NICHT steuern" in gast
    assert "dieselben Werkzeuge wie am PC" in voll


def test_mini_jon_scope_haengt_am_gebundenen_chat():
    from app.services.settings_service import get_settings_service

    get_settings_service().update({"telegram_chat_id": "4242"})
    bot = tgs.MiniJonBot()
    assert bot.scope("-100200", True) == "gast"
    assert bot.scope("4242", False) == "voll"
    assert bot.scope("9999", False) == "gast"


def test_gruppenantwort_nutzt_werkzeuge(monkeypatch):
    gesehen: dict = {}

    async def fake_tool_answer(
        system, question, transcript, provider, model, slot, scope, source
    ):
        gesehen.update(
            {"system": system, "frage": question, "scope": scope, "quelle": source}
        )
        return {
            "text": "Der nächste Supermarkt ist der Billa.",
            "karten": [_routenkarte()],
            "aktionen": ["Route berechnet"],
        }

    monkeypatch.setattr(tgs, "tool_answer", fake_tool_answer)
    karten: list[dict] = []
    antwort = asyncio.run(
        tgs.group_answer(
            "junior",
            "MiniJonBot",
            "Anna",
            "wo ist der nächste Supermarkt?",
            transcript="Anna: hallo",
            group=True,
            scope="gast",
            source="telegram-mini_jon",
            cards=karten,
        )
    )
    assert antwort == "Der nächste Supermarkt ist der Billa."
    assert karten and karten[0]["kind"] == "maps"
    assert gesehen["scope"] == "gast"
    assert gesehen["quelle"] == "telegram-mini_jon"
    assert "maps" in gesehen["system"]


def test_bot_schickt_pin_link_und_lernwache(monkeypatch):
    gesendet: list[str] = []
    aufrufe: list[tuple] = []
    beobachtet: list[str] = []

    async def fake_api(self, method, payload=None, data=None, files=None):
        aufrufe.append((method, payload))
        return {"ok": True}

    async def fake_send(self, chat_id, text):
        gesendet.append(text)

    async def fake_watch(task_id, send):
        beobachtet.append(task_id)

    monkeypatch.setattr(tgs.GroupBot, "_api", fake_api)
    monkeypatch.setattr(tgs.GroupBot, "send", fake_send)
    monkeypatch.setattr(te, "watch_research", fake_watch)
    bot = tgs.MiniJonBot()

    async def lauf():
        await bot.send_cards("-100", [_routenkarte(), _lernkarte()])
        await asyncio.sleep(0)

    asyncio.run(lauf())
    assert aufrufe and aufrufe[0][0] == "sendVenue"
    assert aufrufe[0][1]["title"] == "Billa"
    assert gesendet and "openstreetmap.org/directions" in gesendet[0]
    assert beobachtet == ["abc123"]


def test_mini_jon_versteht_lernbefehl(monkeypatch):
    dienst = _fake_research(monkeypatch)
    gesendet: list[str] = []

    async def fake_api(self, method, payload=None, data=None, files=None):
        return {"ok": True}

    async def fake_send(self, chat_id, text):
        gesendet.append(text)

    async def fake_username(self):
        return "MiniJonBot"

    async def fake_watch(task_id, send):
        return None

    monkeypatch.setattr(tgs.GroupBot, "_api", fake_api)
    monkeypatch.setattr(tgs.GroupBot, "send", fake_send)
    monkeypatch.setattr(tgs.GroupBot, "username", fake_username)
    monkeypatch.setattr(te, "watch_research", fake_watch)
    bot = tgs.MiniJonBot()

    async def lauf():
        await bot.handle_message(
            {
                "chat": {"id": -700, "type": "group"},
                "from": {"first_name": "Anna"},
                "message_id": 5,
                "text": "/lernen Schwarze Löcher",
            }
        )
        await asyncio.sleep(0)

    asyncio.run(lauf())
    assert dienst.gestartet == ["Schwarze Löcher"]
    assert gesendet and "Schwarze Löcher" in gesendet[0]


def test_telegram_jon_merkt_sich_den_handystandort(monkeypatch):
    dienst = ts.get_telegram_service()
    gesetzt: list[tuple] = []

    class FakeMaps:
        async def home(self):
            return (48.0, 11.0)

        @staticmethod
        def distance(lat1, lon1, lat2, lon2):
            from app.services.maps.nominatim import haversine_m

            return haversine_m(lat1, lon1, lat2, lon2)

        async def set_home(self, lat, lon, quelle="geraet"):
            gesetzt.append((lat, lon, quelle))
            return {"lat": lat, "lon": lon}

    import app.services.maps as maps

    monkeypatch.setattr(maps, "get_maps_service", lambda: FakeMaps())
    dienst._last_home = 0.0
    asyncio.run(dienst._remember_position(47.8095, 13.055, False))
    assert gesetzt == [(47.8095, 13.055, "handy")]
    gesetzt.clear()
    asyncio.run(dienst._remember_position(48.0001, 11.0001, False))
    assert gesetzt == []
