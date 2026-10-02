from __future__ import annotations

import asyncio

import pytest

from app.services.handy_service import RECHTE_VORGABE, HandyFehler, HandyService, zeitanfrage_text


def _dienst(monkeypatch, tmp_path):
    import app.services.handy_service as modul

    monkeypatch.setattr(modul, "STORE", tmp_path / "handy.json")

    async def still(*args, **kwargs):
        return None

    monkeypatch.setattr(modul, "_telegram_melden", still)
    dienst = HandyService()
    dienst._data["geraete"].append({
        "id": "geraet-1", "name": "Mias Handy", "token": "t", "schluessel": "", "rechte": dict(RECHTE_VORGABE),
        "faehigkeiten": ["status", "apps", "durchsage", "klingeln", "regeln"], "zustand": {}, "gesehen": 0,
    })
    return dienst


def test_zeitanfrage_erlauben(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    auftraege = []

    async def auftrag(geraete_id, op, daten=None, wartezeit=45.0):
        auftraege.append((op, dict(daten or {})))
        return {"ok": True, "daten": {"limits": {}}}

    monkeypatch.setattr(dienst, "auftrag", auftrag)
    antwort = asyncio.run(dienst.meldung_annehmen("geraet-1", {"art": "zeitanfrage", "daten": {"app": "tiktok", "name": "TikTok", "minuten": 30, "text": "Hausaufgaben fertig"}}))
    kennung = antwort["id"]
    assert [m["id"] for m in dienst.offene_zeitanfragen()] == [kennung]
    ergebnis = asyncio.run(dienst.zeitanfrage_beantworten("geraet-1", kennung, True))
    assert ergebnis["erlaubt"] is True and ergebnis["minuten"] == 30
    ops = [op for op, _ in auftraege]
    assert ops == ["regeln", "zeitantwort"]
    assert "tiktok" in auftraege[0][1]["ausnahmen"]
    assert auftraege[1][1]["erlaubt"] is True
    assert dienst.offene_zeitanfragen() == []
    with pytest.raises(HandyFehler, match="schon beantwortet"):
        asyncio.run(dienst.zeitanfrage_beantworten("geraet-1", kennung, False))


def test_zeitanfrage_ablehnen(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    auftraege = []

    async def auftrag(geraete_id, op, daten=None, wartezeit=45.0):
        auftraege.append(op)
        return {"ok": True, "daten": {}}

    monkeypatch.setattr(dienst, "auftrag", auftrag)
    kennung = asyncio.run(dienst.meldung_annehmen("geraet-1", {"art": "zeitanfrage", "daten": {"app": "tiktok", "minuten": 15}}))["id"]
    ergebnis = asyncio.run(dienst.zeitanfrage_beantworten("geraet-1", kennung, False))
    assert ergebnis["erlaubt"] is False
    assert auftraege == ["zeitantwort"]


def test_zeitanfrage_text_enthaelt_code():
    text = zeitanfrage_text("Mias Handy", {"name": "TikTok", "minuten": 30, "text": "bitte"}, "abcd1234")
    assert "30 Minuten mehr TikTok" in text and "/ja abcd" in text and "„bitte“" in text
