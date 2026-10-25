from __future__ import annotations

import asyncio

import pytest

from app.services import studio_service
from app.services.studio_service import PNG_MAGIC, StudioError, StudioService

BILD = PNG_MAGIC + b"\r\n\x1a\n" + b"\0" * 64


@pytest.fixture()
def dienst(monkeypatch, tmp_path):
    monkeypatch.setattr(studio_service, "CONFIG_FILE", tmp_path / "studio.json")
    monkeypatch.setattr(studio_service, "GALLERY_FILE", tmp_path / "galerie.json")
    monkeypatch.setattr(studio_service, "STUDIO_DIR", tmp_path / "studio")
    monkeypatch.setattr("app.services.aufgaben_modelle.fuer", lambda art: None)
    monkeypatch.setattr("app.services.offline.aktiv", lambda: False)
    service = StudioService()
    service._config = {"anbieter": "lokal", "basis": {"lokal": "http://127.0.0.1:7860"}}
    monkeypatch.setattr(service, "_inherited", lambda anbieter: "nvapi-test" if anbieter == "nvidia" else "")
    return service


def _kaputt(meldung):
    async def handler(*args, **kwargs):
        raise StudioError(meldung)

    return handler


def test_nicht_erreichbarer_lokaler_server_weicht_auf_nvidia_aus(dienst, monkeypatch):
    aufrufe = []

    async def nvidia(prompt, kind, model, *rest):
        aufrufe.append(model)
        return BILD, "image/png", ""

    monkeypatch.setattr(dienst, "_lokal", _kaputt("Kein Bilder-Server unter http://127.0.0.1:7860 erreichbar"))
    monkeypatch.setattr(dienst, "_nvidia", nvidia)
    werk = asyncio.run(dienst.generate("Ein roter Apfel"))
    assert werk["anbieter"] == "nvidia"
    assert aufrufe == ["black-forest-labs/flux.2-klein-4b"]
    assert "Lokal auf deinem PC" in werk["ausweichen"] and "NVIDIA" in werk["ausweichen"]
    assert dienst.file(str(werk["datei"])).read_bytes() == BILD


def test_ueberlastetes_nvidia_modell_nimmt_das_standardmodell(dienst, monkeypatch):
    aufrufe = []

    async def nvidia(prompt, kind, model, *rest):
        aufrufe.append(model)
        if model == "black-forest-labs/flux.1-schnell":
            raise StudioError("NVIDIA bedient black-forest-labs/flux.1-schnell gerade nicht (Antwort 504).")
        return BILD, "image/png", ""

    monkeypatch.setattr(dienst, "_nvidia", nvidia)
    werk = asyncio.run(dienst.generate("Ein Hund", provider="nvidia", model="black-forest-labs/flux.1-schnell"))
    assert aufrufe == ["black-forest-labs/flux.1-schnell", "black-forest-labs/flux.2-klein-4b"]
    assert werk["modell"] == "black-forest-labs/flux.2-klein-4b"


def test_ohne_jeden_anbieter_nennt_jon_alle_gruende(dienst, monkeypatch):
    monkeypatch.setattr(dienst, "_inherited", lambda anbieter: "")
    monkeypatch.setattr(dienst, "_lokal", _kaputt("Kein Bilder-Server erreichbar"))
    monkeypatch.setattr(dienst, "_pollinations", _kaputt("Pollinations meldet 503: limit"))
    with pytest.raises(StudioError) as fehler:
        asyncio.run(dienst.generate("Ein Haus"))
    text = str(fehler.value)
    assert "Kein Bildanbieter hat geliefert" in text and "Bilder-Server" in text and "Pollinations" in text


def test_offline_bleibt_lokal(dienst, monkeypatch):
    monkeypatch.setattr("app.services.offline.aktiv", lambda: True)
    gerufen = []

    async def nvidia(*args, **kwargs):
        gerufen.append("nvidia")
        return BILD, "image/png", ""

    monkeypatch.setattr(dienst, "_lokal", _kaputt("Kein Bilder-Server erreichbar"))
    monkeypatch.setattr(dienst, "_nvidia", nvidia)
    with pytest.raises(StudioError):
        asyncio.run(dienst.generate("Ein Baum"))
    assert gerufen == []
