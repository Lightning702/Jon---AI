from __future__ import annotations

import asyncio

from app.core.kinderschutz import KINDER_ALTER, alter_pruefen, kinder_prompt, kindgerecht, werkzeuge_fuer_kinder
from app.services.handy_service import RECHTE_VORGABE, HandyService


def _werkzeug(name: str) -> dict:
    return {"type": "function", "function": {"name": name, "parameters": {}}}


def test_alter_wird_geprueft():
    assert alter_pruefen(9) == 9
    assert alter_pruefen("12") == 12
    assert alter_pruefen(2) == 0
    assert alter_pruefen(18) == 0
    assert alter_pruefen("abc") == 0
    assert alter_pruefen(None) == 0


def test_prompt_passt_sich_dem_alter_an():
    klein, gross = kinder_prompt(6), kinder_prompt(15)
    assert "147" in klein and "116 111" in klein
    assert "Volksschule" in klein and "Teenager" in gross
    assert "HAUSAUFGABEN" in gross


def test_nur_sichere_werkzeuge():
    alle = [_werkzeug(n) for n in ("web_search", "run_powershell", "delete_path", "maps", "android_screen_time", "android_app_open")]
    namen = [t["function"]["name"] for t in werkzeuge_fuer_kinder(alle)]
    assert namen == ["web_search", "maps", "android_app_open"]


def test_treffer_filter():
    assert kindgerecht({"url": "https://kinder.wiki/dinosaurier", "title": "Dinosaurier"})
    assert not kindgerecht({"url": "https://example.com/casino-bonus", "title": "Bonus"})
    assert not kindgerecht({"url": "https://example.com", "snippet": "XXX Videos"})


def test_geraet_meldet_kindermodus(monkeypatch, tmp_path):
    import app.services.handy_service as modul

    monkeypatch.setattr(modul, "STORE", tmp_path / "handy.json")
    dienst = HandyService()
    dienst._data["geraete"].append({
        "id": "kind", "name": "Mias Handy", "token": "t", "schluessel": "", "rechte": dict(RECHTE_VORGABE),
        "faehigkeiten": [], "zustand": {}, "gesehen": 0,
    })
    assert dienst.kinder_alter("kind") == 0
    dienst._data["geraete"][0]["zustand"] = {"kinder": {"an": True, "alter": 8}}
    assert dienst.kinder_alter("kind") == 8
    dienst._data["geraete"][0]["zustand"] = {"kinder": {"an": False, "alter": 8}}
    assert dienst.kinder_alter("kind") == 0


def test_chat_nimmt_alter_vom_geraet(monkeypatch):
    from app.schemas import ChatIn
    from app.services.chat_service import ChatService
    from app.services.geraete_funktionen import HANDY_KONTEXT
    import app.services.handy_service as modul

    class Attrappe:
        def kinder_alter(self, geraete_id):
            return 7 if geraete_id == "kind" else 0

    monkeypatch.setattr(modul, "get_handy_service", lambda: Attrappe())
    dienst = ChatService.__new__(ChatService)
    anfrage = ChatIn(messages=[{"role": "user", "content": "Hallo"}], kinder=12)
    assert dienst._kinder_alter(anfrage) == 12
    marke = HANDY_KONTEXT.set("kind")
    try:
        assert dienst._kinder_alter(anfrage) == 7
        assert dienst._kinder_alter(ChatIn(messages=[{"role": "user", "content": "Hallo"}])) == 7
    finally:
        HANDY_KONTEXT.reset(marke)
    assert dienst._kinder_alter(ChatIn(messages=[{"role": "user", "content": "Hallo"}])) == 0


def test_bild_im_kindermodus_gesperrt():
    from app.services.tools import ToolBox

    box = ToolBox.__new__(ToolBox)

    async def ablauf():
        marke = KINDER_ALTER.set(9)
        try:
            return await box._create_image({"prompt": "casino mit poker", "kind": "bild"})
        finally:
            KINDER_ALTER.reset(marke)

    assert "Kindermodus" in asyncio.run(ablauf())
