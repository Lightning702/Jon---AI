from __future__ import annotations

import asyncio

from app.providers.openai_compatible import denk_extra


def test_standard_denkt_sichtbar_und_blitzmodus_schaltet_ab(monkeypatch):
    from app.services.settings_service import get_settings_service

    dienst = get_settings_service()
    monkeypatch.setattr(type(dienst), "get", lambda self: {"schnell_antworten": True})
    assert denk_extra("nvidia/nemotron-3-ultra-550b-a55b", None) == {"chat_template_kwargs": {"enable_thinking": True}}
    monkeypatch.setattr(type(dienst), "get", lambda self: {"blitzschnell": True})
    assert denk_extra("nvidia/nemotron-3-ultra-550b-a55b", None) == {"chat_template_kwargs": {"enable_thinking": False}}
    assert denk_extra("nvidia/nemotron-3-ultra-550b-a55b", True) == {"chat_template_kwargs": {"enable_thinking": True}}
    assert denk_extra("openai/gpt-4o", None) == {}


def test_neue_einstellungen_denken_sichtbar():
    from app.services.settings_service import DEFAULTS

    assert DEFAULTS["blitzschnell"] is False
    assert "schnell_antworten" not in DEFAULTS


def test_telegram_zeigt_die_gedanken_im_entwurf(monkeypatch):
    from app.services.telegram_service import TelegramService

    dienst = TelegramService()
    neu = []
    geaendert = []

    async def nachricht(chat_id, text, knoepfe=None):
        neu.append(text)
        return 7

    async def aendern(chat_id, nummer, text, knoepfe=None):
        geaendert.append(text)
        return True

    class Chat:
        def _system_prompt(self):
            return "Du bist Jon."

        async def stream(self, payload):
            for stueck in ("Der Nutzer fragt nach Backups. ", "Ich erkläre die 3-2-1-Regel kurz und klar."):
                yield {"type": "reasoning", "delta": stueck}
            yield {"type": "content", "delta": "Drei Kopien, zwei Medien, eine außer Haus."}

    monkeypatch.setattr(dienst, "_nachricht", nachricht)
    monkeypatch.setattr(dienst, "_aendern", aendern)
    monkeypatch.setattr(dienst, "_chat_service", Chat())
    monkeypatch.setattr("app.services.telegram_service.ENTWURF_TAKT", 0.0)
    antwort, _ = asyncio.run(dienst._answer("9", "Was ist die 3-2-1-Regel?"))
    assert neu and neu[0].startswith("Jon denkt nach")
    assert "3-2-1-Regel" in neu[0]
    assert antwort == "Drei Kopien, zwei Medien, eine außer Haus."


def test_harness_gibt_die_gedanken_weiter(monkeypatch):
    from app.services.harness import modell

    async def einmal(name, model, system, user, zugang):
        return '{"tool": "finish", "args": {"summary": "fertig"}}', "Ich prüfe zuerst die Dateien und baue dann die Seite."

    monkeypatch.setattr(modell, "_einmal", einmal)
    zugang = modell.Zugang("nvidia", "m")
    zugang.route = [("nvidia", "m")]
    antwort = asyncio.run(modell.anfragen(zugang, "s", "u"))
    assert antwort.gedanken == "Ich prüfe zuerst die Dateien und baue dann die Seite."
    assert antwort.text.startswith('{"tool"')


def test_harness_schreibt_gedanken_in_den_verlauf(tmp_path):
    from app.services.harness.service import HarnessService

    dienst = HarnessService(tmp_path / "harness", None)
    aufgabe = {"id": "t1", "sequence": 0, "log": []}
    dienst.emit(aufgabe, "gedanke", message="Ich lese zuerst die Aufgabe genau.")
    assert aufgabe["log"][-1]["type"] == "gedanke"
    assert aufgabe["log"][-1]["message"] == "Ich lese zuerst die Aufgabe genau."


def test_datei_erstellen_versteht_englische_felder(monkeypatch):
    from app.services import werkzeuge_kern
    from app.services.werkzeug_register import REGISTER

    erhalten = {}

    class Dienst:
        def erstellen(self, art, titel, inhalt, wunsch, dateiname, projekt, quelle="app", neue_datei=False):
            erhalten.update(art=art, inhalt=inhalt, wunsch=wunsch, dateiname=dateiname)
            return {"ok": True}

    monkeypatch.setattr("app.services.dokument_service.get_dokument_service", lambda: Dienst())
    assert werkzeuge_kern
    REGISTER["datei_erstellen"](None, {"path": "Notizen/hallo.txt", "content": "Hallo von Jon."})
    assert erhalten == {"art": "txt", "inhalt": "Hallo von Jon.", "wunsch": "Notizen", "dateiname": "hallo.txt"}


def test_harness_legt_dateien_im_arbeitsordner_an(tmp_path, monkeypatch):
    from app.services.dateiraum_service import get_dateiraum_service
    from app.services.harness.service import im_arbeitsordner

    dienst = get_dateiraum_service()
    monkeypatch.setattr(type(dienst), "frei", lambda self, pfad: (True, ""))
    assert im_arbeitsordner({"dateiname": "hallo.txt"}, tmp_path)["ort"] == str(tmp_path)
    assert "ort" not in im_arbeitsordner({"path": "a/hallo.txt"}, tmp_path)
    assert im_arbeitsordner({"ort": "Desktop"}, tmp_path)["ort"] == "Desktop"
    monkeypatch.setattr(type(dienst), "frei", lambda self, pfad: (False, "nein"))
    assert "ort" not in im_arbeitsordner({"dateiname": "hallo.txt"}, tmp_path)


def test_relative_pfade_landen_im_arbeitsordner(tmp_path):
    from app.services.harness.werkzeuge import im_ordner

    wurzel = str(tmp_path)
    assert im_ordner("write_file", {"path": "hallo.txt", "content": "x"}, wurzel)["path"] == str(tmp_path / "hallo.txt")
    assert im_ordner("write_file", {"path": str(tmp_path / "b.txt")}, wurzel)["path"] == str(tmp_path / "b.txt")
    assert im_ordner("copy_path", {"source": "a", "destination": "b"}, wurzel) == {"source": str(tmp_path / "a"), "destination": str(tmp_path / "b")}
    assert im_ordner("testumgebung", {"pfad": "main.py"}, wurzel) == {"pfad": "main.py"}
    assert im_ordner("write_file", {"path": "hallo.txt"}, "") == {"path": "hallo.txt"}
