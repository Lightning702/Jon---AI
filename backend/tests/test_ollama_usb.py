from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.services import ollama_usb
from app.services.ollama_usb import PRAEFIX, UsbFehler, UsbOllama, durchsuchen, modellname_aus_datei, modelle_lesen


def _speicher(wurzel: Path, modelle: dict[str, str], v2: bool = False, fehlend: bool = False) -> Path:
    speicher = wurzel / "ollama" / "models"
    (speicher / "blobs").mkdir(parents=True, exist_ok=True)
    ordner = "manifests-v2" if v2 else "manifests"
    host = "ollama.com" if v2 else "registry.ollama.ai"
    for nummer, (pfad, familie) in enumerate(modelle.items()):
        teile = pfad.split("/")
        if len(teile) == 2:
            teile = [host, "library", *teile]
        elif len(teile) == 3:
            teile = [host, *teile]
        konfig = json.dumps({"model_family": familie, "model_type": "3B", "file_type": "Q4_0"}).encode()
        (speicher / "blobs" / f"sha256-k{nummer}").write_bytes(konfig)
        if not fehlend:
            (speicher / "blobs" / f"sha256-m{nummer}").write_bytes(b"GGUF" + b"\0" * 32)
        manifest = {
            "config": {"digest": f"sha256:k{nummer}", "size": len(konfig)},
            "layers": [{"digest": f"sha256:m{nummer}", "size": 1_600_000_000}],
        }
        datei = speicher.joinpath(ordner, *teile)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(json.dumps(manifest), encoding="utf-8")
    return speicher


def test_modelle_werden_wie_bei_ollama_benannt(tmp_path):
    speicher = _speicher(tmp_path, {"dolphin-phi/latest": "phi2", "huihui/qwen3/8b": "qwen3", "hf.co/bartowski/llama-gguf/Q4_K_M": "llama"})
    namen = [m["name"] for m in modelle_lesen(speicher)]
    assert namen == ["dolphin-phi:latest", "hf.co/bartowski/llama-gguf:Q4_K_M", "huihui/qwen3:8b"]
    erstes = modelle_lesen(speicher)[0]
    assert erstes["id"] == PRAEFIX + "dolphin-phi:latest"
    assert erstes["familie"] == "phi2" and erstes["parameter"] == "3B" and erstes["vollstaendig"]


def test_neues_manifest_format_und_fehlende_dateien(tmp_path):
    speicher = _speicher(tmp_path, {"llama3.2/latest": "llama"}, v2=True, fehlend=True)
    modell = modelle_lesen(speicher)[0]
    assert modell["name"] == "llama3.2:latest" and modell["vollstaendig"] is False


def test_durchsuchen_findet_speicher_gguf_und_programm(tmp_path):
    _speicher(tmp_path / "Stick", {"mistral/7b": "llama"})
    gguf = tmp_path / "Stick" / "Downloads" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    gguf.parent.mkdir(parents=True)
    with open(gguf, "wb") as datei:
        datei.truncate(ollama_usb.GGUF_MIN + 1)
    (tmp_path / "Stick" / "Downloads" / "mmproj-model.gguf").write_bytes(b"x" * 10)
    (tmp_path / "Stick" / "ollama" / "ollama.exe").write_bytes(b"MZ")
    papierkorb = tmp_path / "Stick" / "$RECYCLE.BIN" / "ollama" / "models"
    _speicher(papierkorb.parent.parent, {"alt/latest": "llama"})
    fund = durchsuchen(str(tmp_path / "Stick"))
    assert [Path(s["pfad"]).name for s in fund["speicher"]] == ["models"]
    assert fund["speicher"][0]["modelle"][0]["name"] == "mistral:7b"
    assert [g["datei"] for g in fund["gguf"]] == ["Llama-3.2-3B-Instruct-Q4_K_M.gguf"]
    assert fund["gguf"][0]["vorschlag"] == "llama-3.2-3b-instruct-q4_k_m"
    assert any(p.endswith("ollama.exe") for p in fund["programme"])


def test_durchsuchen_meldet_fehlenden_pfad(tmp_path):
    with pytest.raises(UsbFehler):
        durchsuchen(str(tmp_path / "gibtsnicht"))
    with pytest.raises(UsbFehler):
        durchsuchen("")


def test_modellname_aus_datei():
    assert modellname_aus_datei("Qwen2.5 Coder (7B) Q5.gguf") == "qwen2.5-coder-7b-q5"
    assert modellname_aus_datei("....gguf") == "usb-modell"


@pytest.fixture()
def usb(monkeypatch, tmp_path):
    monkeypatch.setattr(ollama_usb, "DATEI", tmp_path / "ollama_usb.json")
    monkeypatch.setattr(ollama_usb, "PROTOKOLL", tmp_path / "ollama_usb.log")
    monkeypatch.setattr(ollama_usb.atexit, "register", lambda *a, **k: None)
    return UsbOllama()


def test_verbinden_startet_ollama_mit_stick_ordner(usb, monkeypatch, tmp_path):
    speicher = _speicher(tmp_path / "Stick", {"dolphin-phi/latest": "phi2"})
    programm = tmp_path / "Stick" / "ollama.exe"
    programm.write_bytes(b"MZ")
    gestartet = {}

    def starten(self, ordner, exe):
        gestartet.update(ordner=ordner, exe=exe)
        self._daten["port"] = 11436
        return 11436

    monkeypatch.setattr(UsbOllama, "_starten", starten)
    monkeypatch.setattr(UsbOllama, "laeuft", lambda self: True)
    monkeypatch.setattr(UsbOllama, "modelle", lambda self, frisch=False: [PRAEFIX + "dolphin-phi:latest"])
    stand = usb.verbinden(str(speicher), [str(programm)])
    assert gestartet == {"ordner": speicher, "exe": str(programm)}
    assert stand["aktiv"] and stand["speicher"] == str(speicher) and stand["port"] == 11436
    gespeichert = json.loads(ollama_usb.DATEI.read_text(encoding="utf-8"))
    assert gespeichert["aktiv"] is True and gespeichert["speicher"] == str(speicher)


def test_fremde_programme_werden_nicht_gestartet(usb, tmp_path, monkeypatch):
    speicher = _speicher(tmp_path / "Stick", {"a/latest": "llama"})
    boese = tmp_path / "boese.exe"
    boese.write_bytes(b"MZ")
    monkeypatch.setattr(ollama_usb.shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "leer"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "leer"))
    monkeypatch.setenv("ProgramW6432", str(tmp_path / "leer"))
    with pytest.raises(UsbFehler):
        usb._programm(speicher, [str(boese)])


def test_verbinden_lehnt_ordner_ohne_modelle_ab(usb, tmp_path):
    with pytest.raises(UsbFehler):
        usb.verbinden(str(tmp_path))


def test_abgezogener_stick_liefert_keine_modelle(usb, tmp_path):
    usb._daten.update({"aktiv": True, "speicher": str(tmp_path / "weg" / "models")})
    assert usb.modelle() == []
    with pytest.raises(UsbFehler):
        usb.sicherstellen()


def test_provider_listet_und_leitet_usb_modelle(monkeypatch):
    from app.providers.base import ChatMessage, ChatRequest
    from app.providers.ollama_provider import OllamaProvider

    class Attrappe:
        def aktiv(self):
            return True

        def modelle(self, frisch=False):
            return [PRAEFIX + "dolphin-phi:latest"]

        def sicherstellen(self):
            return "http://127.0.0.1:11435"

    monkeypatch.setattr(ollama_usb, "get_usb_ollama", lambda: Attrappe())
    provider = OllamaProvider()

    monkeypatch.setattr(provider._service, "enabled", lambda: False)
    assert asyncio.run(provider.list_models()) == [PRAEFIX + "dolphin-phi:latest"]

    gesehen = {}

    async def zeilen(self, client, url, payload, model, remote=None):
        gesehen.update(url=url, model=payload["model"], remote=remote)
        yield {"message": {"content": "Hallo vom Stick, alles bestens hier."}, "done": True}

    monkeypatch.setattr(OllamaProvider, "_lines", zeilen)

    async def lesen():
        text = ""
        anfrage = ChatRequest(messages=[ChatMessage(role="user", content="Hi")], model=PRAEFIX + "dolphin-phi:latest")
        async for stueck in provider.stream(anfrage):
            text += stueck.delta
        return text

    assert "Hallo vom Stick" in asyncio.run(lesen())
    assert gesehen["url"] == "http://127.0.0.1:11435/api/chat"
    assert gesehen["model"] == "dolphin-phi:latest" and gesehen["remote"]["usb"] is True


def test_routen_liefern_stand_und_suche(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    _speicher(tmp_path / "Stick", {"dolphin-phi/latest": "phi2"})
    monkeypatch.setattr("app.api.usb_routes.laufwerke", lambda: [{"pfad": "D:\\", "name": "STICK", "art": "usb", "frei": 1, "gesamt": 2, "system": False}])
    client = TestClient(create_app())
    stand = client.get("/api/ollama/usb").json()
    assert stand["laufwerke"][0]["name"] == "STICK" and "aktiv" in stand
    fund = client.post("/api/ollama/usb/suchen", json={"pfad": str(tmp_path / "Stick")}).json()
    assert fund["speicher"][0]["modelle"][0]["id"] == PRAEFIX + "dolphin-phi:latest"
    assert client.post("/api/ollama/usb/suchen", json={"pfad": str(tmp_path / "nix")}).status_code == 400
