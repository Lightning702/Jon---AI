from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

from app.services.handy_service import RECHTE_VORGABE, HandyService, bericht_bauen, bericht_text, verlauf_merken


def _zustand(tag: str, genutzt: dict, schritte: int) -> dict:
    return {
        "bildschirmzeit": {"tag": tag, "genutzt": genutzt, "apps": [{"id": "tiktok", "name": "TikTok"}, {"id": "whatsapp", "name": "WhatsApp"}]},
        "schritte": schritte,
    }


def test_verlauf_nimmt_hoechststand_und_kuerzt():
    eintrag: dict = {}
    verlauf_merken(eintrag, _zustand("2026-09-20", {"tiktok": 30, "whatsapp": 10}, 2000))
    verlauf_merken(eintrag, _zustand("2026-09-20", {"tiktok": 12, "whatsapp": 25}, 1500))
    tag = eintrag["verlauf"]["2026-09-20"]
    assert tag["genutzt"] == {"tiktok": 30, "whatsapp": 25}
    assert tag["schritte"] == 2000
    assert tag["namen"]["tiktok"] == "TikTok"
    for i in range(60):
        verlauf_merken(eintrag, _zustand((date(2026, 1, 1) + timedelta(days=i)).isoformat(), {"tiktok": 1}, 1))
    assert len(eintrag["verlauf"]) == 42
    verlauf_merken(eintrag, {"bildschirmzeit": {"tag": "kaputt", "genutzt": {"tiktok": 5}}})
    assert "kaputt" not in eintrag["verlauf"]


def test_bericht_rechnet_woche_und_vorwoche():
    ende = date(2026, 9, 27)
    eintrag = {"id": "g1", "name": "Mias Handy", "meldungen": [], "verlauf": {}}
    for i in range(7):
        tag = (ende - timedelta(days=i)).isoformat()
        eintrag["verlauf"][tag] = {"genutzt": {"tiktok": 60, "whatsapp": 30}, "namen": {"tiktok": "TikTok", "whatsapp": "WhatsApp"}, "schritte": 5000}
    for i in range(7, 14):
        tag = (ende - timedelta(days=i)).isoformat()
        eintrag["verlauf"][tag] = {"genutzt": {"tiktok": 100}, "namen": {}, "schritte": 0}
    beginn = datetime.combine(ende, datetime.min.time()).timestamp() + 3600
    eintrag["meldungen"] = [
        {"art": "zeitanfrage", "zeit": beginn, "antwort": {"erlaubt": True}},
        {"art": "zeitanfrage", "zeit": beginn, "antwort": {"erlaubt": False}},
        {"art": "sos", "zeit": beginn},
        {"art": "zeitanfrage", "zeit": beginn - 30 * 86400},
    ]
    bericht = bericht_bauen(eintrag, ende.isoformat())
    assert bericht["von"] == "2026-09-21" and bericht["bis"] == "2026-09-27"
    assert bericht["gesamt"] == 7 * 90 and bericht["schnitt"] == 90
    assert bericht["vorwoche"] == 700
    assert [a["id"] for a in bericht["apps"]] == ["tiktok", "whatsapp"]
    assert bericht["schritte"] == 35000
    assert bericht["anfragen"] == 2 and bericht["erlaubt"] == 1 and bericht["sos"] == 1
    assert [t["wochentag"] for t in bericht["tage"]][-1] == "So"
    text = bericht_text(bericht)
    assert "Wochenbericht für Mias Handy (21.9. – 27.9.)" in text
    assert "10 h 30 min" in text and "Ø 1 h 30 min am Tag" in text and "−10 % zur Vorwoche" in text
    assert "TikTok 7 h" in text and "Schritte: 35.000 (Ø 5.000 am Tag)" in text
    assert "2 Anfragen, 1 erlaubt" in text and "SOS ausgelöst: 1×" in text


def test_bericht_wird_sonntags_einmal_gesendet(monkeypatch, tmp_path):
    import app.services.handy_service as modul

    monkeypatch.setattr(modul, "STORE", tmp_path / "handy.json")
    gesendet = []

    async def telegram(text, daten=None):
        gesendet.append(text)

    monkeypatch.setattr(modul, "_telegram_melden", telegram)
    dienst = HandyService()
    heute = date.today().isoformat()
    dienst._data["geraete"].append({
        "id": "g1", "name": "Mias Handy", "token": "t", "schluessel": "", "rechte": dict(RECHTE_VORGABE),
        "faehigkeiten": [], "zustand": {}, "gesehen": 0,
        "verlauf": {heute: {"genutzt": {"tiktok": 45}, "namen": {"tiktok": "TikTok"}, "schritte": 1234}},
    })
    sonntag = datetime(2026, 9, 27, 18, 5)
    assert dienst.bericht_faellig(datetime(2026, 9, 26, 19, 0)) == ""
    assert dienst.bericht_faellig(datetime(2026, 9, 27, 17, 59)) == ""
    woche = dienst.bericht_faellig(sonntag)
    assert woche == "2026-W39"
    assert asyncio.run(dienst.berichte_senden(woche)) == 1
    assert dienst.bericht_faellig(sonntag) == ""
    assert gesendet and "Mias Handy" in gesendet[0]
    neu = dienst.meldungen_neu()
    assert neu and neu[0]["art"] == "bericht" and neu[0]["geraet"] == "g1"
    assert HandyService()._data["bericht_woche"] == "2026-W39"
