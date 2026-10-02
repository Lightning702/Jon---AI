from __future__ import annotations

import asyncio
import base64
import io
import json
import wave

import pytest

from app.services.geraete_funktionen import HANDY_KONTEXT, audio_ausfuehren
from app.services.handy_service import HandyFehler, HandyService


def test_geraeteprofil_ohne_relay(monkeypatch, tmp_path):
    import app.services.handy_service as module
    monkeypatch.setattr(module, "STORE", tmp_path / "handy.json")
    dienst = HandyService()
    monkeypatch.setattr(dienst, "_adressen", lambda: ["http://100.100.20.30:8756"])
    daten = dienst.kopplung_starten(direct_only=True)
    assert json.loads(daten["nutzlast"])["direct_only"] is True
    assert dienst.offenes_thema() == ""
    assert dienst.kopplung_status()["direct_only"] is True
    dienst.kopplung_starten()
    assert dienst.offenes_thema()


def test_abgelaufene_bestaetigung(monkeypatch, tmp_path):
    import app.services.handy_service as module
    monkeypatch.setattr(module, "STORE", tmp_path / "handy.json")
    dienst = HandyService()
    dienst.kopplung_starten(True)
    dienst._sitzung.update(status="wartet", ablauf=0)
    with pytest.raises(HandyFehler, match="abgelaufen"):
        dienst.kopplung_beantworten(True)


def test_antwort_von_falschem_handy(monkeypatch, tmp_path):
    import app.services.handy_service as module
    monkeypatch.setattr(module, "STORE", tmp_path / "handy.json")
    dienst = HandyService()

    async def pruefen():
        future = asyncio.get_running_loop().create_future()
        dienst._auftraege["auftrag"] = ("handy-a", future)
        assert not dienst.antwort_annehmen("handy-b", {"auftrag": "auftrag", "ok": True})["ok"]
        assert not future.done()
        assert dienst.antwort_annehmen("handy-a", {"auftrag": "auftrag", "ok": True})["ok"]
        assert (await future)["geraet"] == "handy-a"
        assert not dienst.antwort_annehmen("handy-a", {"auftrag": "auftrag", "ok": True})["ok"]

    asyncio.run(pruefen())


@pytest.mark.parametrize("daten", ["invalid!", "A" * 1_400_001, base64.b64encode(b"kein wav").decode()], ids=["invalid-base64", "too-large", "not-wav"])
def test_ungueltiges_audio(daten):
    assert not asyncio.run(audio_ausfuehren({"op": "audio-stt", "audio": daten}))["ok"]


def test_audio_roundtrip(monkeypatch):
    from app.services.voice_service import VoiceService
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 1600)
    daten = puffer.getvalue()
    def erkennen(self, empfangen, language):
        assert empfangen == daten
        assert language == "de-DE"
        return "Öffne WhatsApp"
    monkeypatch.setattr(VoiceService, "transcribe_wav", erkennen)
    result = asyncio.run(audio_ausfuehren({"op": "audio-stt", "audio": base64.urlsafe_b64encode(daten).decode().rstrip("=")}))
    assert result == {"ok": True, "text": "Öffne WhatsApp"}


def test_tts_limit():
    assert not asyncio.run(audio_ausfuehren({"op": "audio-tts", "text": "a" * 1201}))["ok"]


def test_app_auf_zugangsgeraet_gebunden(monkeypatch):
    from app.services.connectors.android import AndroidConnector
    connector = AndroidConnector()
    class Dienst:
        def faehig(self, id, recht):
            return True
        async def auftrag(self, id, op, daten):
            assert id == "dieses-handy"
            assert op == "app-oeffnen"
            assert daten == {"app": "whatsapp"}
            return {"ok": True}
    monkeypatch.setattr(connector, "_dienst", lambda: Dienst())
    monkeypatch.setattr(connector, "_waehlen", lambda args, recht: {"id": args["device"]})
    token = HANDY_KONTEXT.set("dieses-handy")
    try:
        assert asyncio.run(connector.ausfuehren("android_app_open", {"device": "anderes-handy", "app": "whatsapp"}))["ok"]
        assert "error" in asyncio.run(connector.ausfuehren("android_app_open", {"app": "com.android.settings"}))
    finally:
        HANDY_KONTEXT.reset(token)


def test_vpn_verweigert_oeffentliche_ziele(monkeypatch):
    import socket
    from app.services.geraete_vpn import private_adresse
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("8.8.8.8", 8756))])
    with pytest.raises(ValueError):
        private_adresse("http://example.com:8756")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("100.100.20.30", 8756))])
    assert private_adresse("pi.tailnet.ts.net") == "http://100.100.20.30:8756"
    with pytest.raises(ValueError):
        private_adresse("http://user:password@100.100.20.30")


def test_vpn_noch_nicht_angemeldet(monkeypatch):
    from types import SimpleNamespace
    import app.services.geraete_vpn as vpn
    monkeypatch.setattr(vpn.shutil, "which", lambda name: "tailscale")
    monkeypatch.setattr(vpn.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout='{"BackendState":"NeedsLogin","TailscaleIPs":null,"Peer":null}'))
    vpn._tailscale_status.cache_clear()
    result = vpn.tailscale_status()
    assert result["installiert"]
    assert not result["verbunden"]
    assert result["adressen"] == []
    vpn._tailscale_status.cache_clear()
