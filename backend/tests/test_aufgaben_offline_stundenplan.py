from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest

from app.services.settings_service import get_settings_service


@pytest.fixture(autouse=True)
def _saubere_einstellungen():
    dienst = get_settings_service()
    alt = {k: dienst.get().get(k) for k in ("offline_modus", "modell_je_aufgabe", "aufgabenmodelle", "lokaler_server_url", "telegram_morning", "telegram_morgen_stundenplan", "telegram_morgen_zusaetze", "telegram_morning_time")}
    yield
    dienst.update(alt)
    from app.services.stundenplan_service import get_stundenplan_service

    get_stundenplan_service().loeschen()


def test_aufgaben_einordnen_waehlt_passende_modelle():
    from app.services.aufgaben_modelle import einordnen

    vorschlag = einordnen([
        ("lokalserver", "gpt-oss-120b"),
        ("lokalserver", "qwen2.5-coder-32b"),
        ("lokalserver", "z-image-turbo"),
        ("lokalserver", "qwen2.5-vl-7b"),
        ("lokalserver", "nomic-embed-text"),
    ])
    assert vorschlag["bild"]["model"] == "z-image-turbo"
    assert vorschlag["text"]["model"] == "gpt-oss-120b"
    assert vorschlag["code"]["model"] == "qwen2.5-coder-32b"
    assert vorschlag["sehen"]["model"] == "qwen2.5-vl-7b"


def test_aufgabenmodell_ersetzt_chatwahl_und_laesst_sich_abschalten():
    from app.services.aufgaben_modelle import fuer_chat, speichern

    speichern({"text": {"provider": "lokalserver", "model": "gpt-oss-120b"}})
    get_settings_service().update({"modell_je_aufgabe": True})
    assert fuer_chat("text", "nvidia", "x") == ("lokalserver", "gpt-oss-120b")
    assert fuer_chat("code", "nvidia", "x") == ("lokalserver", "gpt-oss-120b")
    get_settings_service().update({"modell_je_aufgabe": False})
    assert fuer_chat("text", "nvidia", "x") == ("nvidia", "x")


def test_offline_modus_erzwingt_lokales_modell_und_sperrt_netz():
    from app.services import offline

    get_settings_service().update({"offline_modus": False, "aufgabenmodelle": {}})
    assert offline.lokal_erzwingen("nvidia", "m") == ("nvidia", "m")
    assert not offline.gesperrt("web_search")
    get_settings_service().update({"offline_modus": True, "aufgabenmodelle": {"text": {"provider": "ollama", "model": "llama3.2"}}})
    assert offline.lokal_erzwingen("nvidia", "m") == ("ollama", "llama3.2")
    assert offline.lokal_erzwingen("ollama", "qwen3") == ("ollama", "qwen3")
    assert offline.gesperrt("web_search")
    assert offline.gesperrt("browser_goto")
    assert not offline.gesperrt("read_file")


def test_offline_werkzeug_wird_blockiert(tmp_path):
    from app.services.tools import ToolBox

    get_settings_service().update({"offline_modus": True})
    ergebnis = json.loads(asyncio.run(ToolBox(str(tmp_path)).execute("web_search", {"query": "wetter"})))
    assert ergebnis.get("offline") is True


def test_router_bleibt_offline_lokal():
    from app.services.modell_router import ModelRouter

    get_settings_service().update({"offline_modus": True})
    async def namen(provider, model):
        return [provider]

    async def planen(provider, namen, model):
        return [("nvidia", "m"), ("ollama", "qwen3")]

    route = asyncio.run(ModelRouter().plan("nvidia", "m", anbieter=namen, planen=planen, ollama=False))
    assert route == [("ollama", "qwen3")]
    assert all(p in ("ollama", "lmstudio", "lokalserver") or str(m).startswith("share:") for p, m in route)


def test_stundenplan_speichern_und_tag():
    from app.services.stundenplan_service import StundenplanService

    dienst = StundenplanService()
    dienst.setzen({"Mo": [{"fach": "Deutsch", "von": "9.40", "bis": "10:30"}, {"fach": "Mathe", "von": "8:00", "bis": "8:50", "raum": "2B"}]})
    name, stunden = dienst.fuer(date(2026, 10, 5))
    assert name == "montag"
    assert [s["fach"] for s in stunden] == ["Mathe", "Deutsch"]
    assert stunden[1]["von"] == "09:40"
    assert "Mathe (2B)" in dienst.text("montag")
    with pytest.raises(ValueError):
        dienst.setzen({"montag": []})


def test_werkzeuge_stundenplan_und_morgen_nachricht(tmp_path):
    from app.services.tools import ToolBox

    box = ToolBox(str(tmp_path))
    gespeichert = json.loads(asyncio.run(box.execute("stundenplan", {"aktion": "setzen", "tage": {"dienstag": [{"fach": "Englisch", "von": "08:00"}]}})))
    assert gespeichert["ok"] and gespeichert["gespeichert"] == {"dienstag": 1}
    get_settings_service().update({"telegram_morning": False})
    stand = json.loads(asyncio.run(box.execute("morgen_nachricht", {"stundenplan": True, "zeit": "6.45", "hinzufuegen": "Wetter für Wien"})))
    assert stand["an"] and stand["stundenplan"] and stand["uhrzeit"] == "06:45"
    assert "Wetter für Wien" in stand["zusaetze"]
    weg = json.loads(asyncio.run(box.execute("morgen_nachricht", {"entfernen": "wetter"})))
    assert weg["zusaetze"] == []


def test_morgen_nachricht_haengt_stundenplan_an():
    from app.services.stundenplan_service import get_stundenplan_service
    from app.services.telegram_service import TelegramService

    heute = ("montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag")[date.today().weekday()]
    get_stundenplan_service().setzen({heute: [{"fach": "Physik", "von": "08:00", "bis": "08:50", "raum": "Labor"}]})
    get_settings_service().update({"telegram_morgen_stundenplan": True, "telegram_morgen_zusaetze": ["Motivationsspruch"]})
    dienst = TelegramService()
    liste = dienst._stundenplan_liste()
    assert "Physik (Labor)" in liste and "08:00–08:50" in liste
    zusaetze = dienst._morgen_zusaetze()
    assert zusaetze["zusaetze"] == ["Motivationsspruch"]
    assert "Physik" in zusaetze["stundenplan_heute"]
    get_settings_service().update({"telegram_morgen_stundenplan": False})
    assert dienst._stundenplan_liste() == ""


def test_video_wunsch_liest_bildschirm_und_sekunden(monkeypatch):
    from app.services.telegram_service import TelegramService

    monkeypatch.setattr(TelegramService, "_bildschirmzahl", staticmethod(lambda: 2))
    dienst = TelegramService()
    assert dienst._videowunsch(["2"]) == (15, "2", "")
    assert dienst._videowunsch(["bildschirm", "1", "30s"]) == (30, "1", "")
    assert dienst._videowunsch(["alle"])[1] == "alle"
    assert dienst._videowunsch(["20"]) == (20, "", "")
    assert dienst._videowunsch(["monitor", "3"])[2]


def test_fenster_punkte_findet_claude():
    from app.services.fenster_wechsel import _punkte

    claude = {"titel": "Claude", "programm": "claude.exe"}
    anderes = {"titel": "Explorer - Dokumente", "programm": "explorer.exe"}
    assert _punkte("Claude", claude) > _punkte("Claude", anderes)


def test_risiko_neue_werkzeuge():
    from app.services.browser.sicherheit import NIEDRIG
    from app.services.risiko import bewerten

    assert bewerten("was_laeuft").risiko == NIEDRIG
    assert bewerten("wechseln", {"ziel": "Claude"}).risiko == NIEDRIG
    assert bewerten("stundenplan", {"aktion": "heute"}).risiko == NIEDRIG


def test_cloudmodelle_zaehlen_nicht_als_lokal():
    from app.services.aufgaben_modelle import einordnen
    from app.services.offline import lokal

    assert not lokal("ollama", "gemini-3-flash-preview:cloud")
    assert lokal("ollama", "gemma4:e2b")
    vorschlag = einordnen([("ollama", "gemini-3-flash-preview:cloud"), ("ollama", "gemma4:e2b"), ("ollama", "x/z-image-turbo:latest")])
    assert vorschlag["text"]["model"] == "gemma4:e2b"
    assert "bild" not in vorschlag
