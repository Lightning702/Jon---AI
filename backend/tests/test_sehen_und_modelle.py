from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from app.core.config import NVIDIA_SEHEN_MODELL, NVIDIA_SEHEN_RESERVE, NVIDIA_VIDEO_MODELL
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.services import modell_info, sehen, unzensiert
from app.services.settings_service import get_settings_service


@pytest.fixture
def einstellungen():
    dienst = get_settings_service()
    alt = dict(dienst.get())
    yield dienst
    dienst.update({k: alt.get(k) for k in ("provider", "model", "vision_model", "video_model", "unzensiert_modus", "offline_modus", "modell_je_aufgabe") if alt.get(k) is not None})


def _jpeg(farbe: str = "red") -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (64, 48), farbe).save(puffer, "JPEG")
    return puffer.getvalue()


class Sicht(OpenAICompatibleProvider):
    def __init__(self, name: str, antworten: dict[str, str]):
        super().__init__(name=name, base_url="http://127.0.0.1:9", api_key="x")
        self.antworten = antworten
        self.aufrufe: list[tuple[str, int, str]] = []

    async def describe_images(self, model, data_urls, prompt, max_tokens=300, slot="jon", system=""):
        self.aufrufe.append((model, len(data_urls), system))
        antwort = self.antworten.get(model, "")
        if antwort == "!":
            raise RuntimeError("kaputt")
        return antwort


def _registry(monkeypatch, **anbieter):
    monkeypatch.setattr(sehen, "_anbieter", lambda: anbieter)


def test_bilder_gehen_an_glimmer_videos_an_diffusiongemma(einstellungen):
    einstellungen.update({"provider": "nvidia", "model": "nvidia/nemotron-3-ultra-550b-a55b", "vision_model": "", "video_model": "", "offline_modus": False, "modell_je_aufgabe": False})
    bild = [m for a, m in sehen.kette("bild") if a == "nvidia"]
    video = [m for a, m in sehen.kette("video") if a == "nvidia"]
    assert bild[:3] == [NVIDIA_SEHEN_MODELL, NVIDIA_VIDEO_MODELL, NVIDIA_SEHEN_RESERVE]
    assert video[:3] == [NVIDIA_VIDEO_MODELL, NVIDIA_SEHEN_MODELL, NVIDIA_SEHEN_RESERVE]
    assert NVIDIA_SEHEN_MODELL == "meta/muse-glimmer-30b"
    assert NVIDIA_VIDEO_MODELL == "google/diffusiongemma-26b-a4b-it"


def test_leere_antwort_faellt_auf_das_naechste_modell(einstellungen, monkeypatch):
    einstellungen.update({"provider": "nvidia", "vision_model": "", "offline_modus": False, "modell_je_aufgabe": False})
    nvidia = Sicht("nvidia", {NVIDIA_SEHEN_MODELL: "", NVIDIA_VIDEO_MODELL: "Ein roter Kreis."})
    _registry(monkeypatch, nvidia=nvidia)
    ergebnis = asyncio.run(sehen.beschreiben([_jpeg()], "Was ist zu sehen?", "bild", "nvidia"))
    assert ergebnis["text"] == "Ein roter Kreis."
    assert ergebnis["modell"] == NVIDIA_VIDEO_MODELL
    assert [a[0] for a in nvidia.aufrufe] == [NVIDIA_SEHEN_MODELL, NVIDIA_VIDEO_MODELL]


def test_video_schickt_mehrere_bilder_oder_ein_raster(einstellungen, monkeypatch):
    einstellungen.update({"provider": "nvidia", "video_model": "", "offline_modus": False, "modell_je_aufgabe": False})
    nvidia = Sicht("nvidia", {NVIDIA_VIDEO_MODELL: "!", NVIDIA_SEHEN_MODELL: "Erst rot, dann blau."})
    _registry(monkeypatch, nvidia=nvidia)
    bilder = [_jpeg("red"), _jpeg("blue"), _jpeg("green")]
    ergebnis = asyncio.run(sehen.beschreiben(bilder, "Ablauf?", "video", "nvidia", zeiten=[0.5, 1.5, 2.5], dauer=3.0))
    assert ergebnis["text"] == "Erst rot, dann blau."
    assert nvidia.aufrufe[0][:2] == (NVIDIA_VIDEO_MODELL, 3)
    assert nvidia.aufrufe[1][:2] == (NVIDIA_SEHEN_MODELL, 1)


def test_raster_ist_ein_jpeg_mit_allen_bildern():
    roh = sehen.raster([_jpeg("red"), _jpeg("blue"), _jpeg("green"), _jpeg("white"), _jpeg("black"), _jpeg("yellow")], [0, 1, 2, 3, 4, 5])
    with Image.open(io.BytesIO(roh)) as bild:
        assert bild.format == "JPEG"
        assert bild.width == 3 * sehen.RASTER_KANTE


def test_video_bilder_aus_echter_datei(tmp_path):
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    pfad = tmp_path / "probe.avi"
    schreiber = cv2.VideoWriter(str(pfad), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for i in range(40):
        rahmen = np.zeros((48, 64, 3), dtype=np.uint8)
        rahmen[:, :, 2] = 255 if i < 20 else 0
        rahmen[:, :, 0] = 0 if i < 20 else 255
        schreiber.write(rahmen)
    schreiber.release()
    bilder, zeiten, dauer = sehen.video_bilder(pfad, 6)
    assert len(bilder) == 6
    assert 3.5 <= dauer <= 4.5
    assert zeiten == sorted(zeiten)


def test_unzensiert_nur_lokal_und_nie_fuer_kinder(einstellungen):
    from app.core.kinderschutz import KINDER_ALTER

    einstellungen.update({"unzensiert_modus": False})
    assert unzensiert.anweisung("ollama", "dolphin-mistral") == ""
    einstellungen.update({"unzensiert_modus": True})
    assert "UNZENSIERT-MODUS" in unzensiert.anweisung("ollama", "dolphin-mistral")
    assert "UNZENSIERT-MODUS" in unzensiert.anweisung("lmstudio", "x", "code")
    assert unzensiert.anweisung("nvidia", "meta/muse-glimmer-30b") == ""
    assert unzensiert.anweisung("ollama", "gpt-oss:120b-cloud") == ""
    assert "Minderjaehrigen" in unzensiert.anweisung("ollama", "x")
    marke = KINDER_ALTER.set(10)
    try:
        assert unzensiert.anweisung("ollama", "x") == ""
    finally:
        KINDER_ALTER.reset(marke)


def test_unzensiert_bleibt_lokal_ohne_cloud_ausweichen(einstellungen):
    einstellungen.update({"unzensiert_modus": True})
    versuche = [("ollama", "dolphin"), ("nvidia", "x"), ("ollama", "llama3")]
    assert unzensiert.nur_lokal(versuche) == [("ollama", "dolphin"), ("ollama", "llama3")]
    assert unzensiert.fuer_versuche(unzensiert.nur_lokal(versuche))
    assert unzensiert.nur_lokal([("nvidia", "x"), ("ollama", "y")]) == [("nvidia", "x"), ("ollama", "y")]
    assert unzensiert.fuer_versuche([("nvidia", "x"), ("ollama", "y")]) == ""
    einstellungen.update({"unzensiert_modus": False})
    assert unzensiert.nur_lokal(versuche) == versuche


def test_fachteam_bekommt_die_anweisung(einstellungen):
    from app.services.agenten_service import AgentenService

    einstellungen.update({"unzensiert_modus": True})
    gesehen: list[str] = []

    async def complete(system, user, **_):
        gesehen.append(system)
        return "fertig"

    dienst = AgentenService(complete=complete)
    asyncio.run(dienst._model("Du bist ein Fachagent.", {"a": 1}, {"provider": "ollama", "model": "dolphin", "slot": "jon"}))
    asyncio.run(dienst._model("Du bist ein Fachagent.", {"a": 1}, {"provider": "nvidia", "model": "x", "slot": "jon"}))
    assert "UNZENSIERT-MODUS" in gesehen[0]
    assert "UNZENSIERT-MODUS" not in gesehen[1]


def test_sehen_gibt_lokalen_modellen_die_anweisung(einstellungen, monkeypatch):
    einstellungen.update({"unzensiert_modus": True, "provider": "ollama", "model": "llava", "vision_model": "", "offline_modus": False, "modell_je_aufgabe": False})
    ollama = Sicht("ollama", {"llava": "Alles beschrieben."})
    _registry(monkeypatch, ollama=ollama)
    ergebnis = asyncio.run(sehen.beschreiben([_jpeg()], "Was ist zu sehen?", "bild", "ollama"))
    assert ergebnis["text"] == "Alles beschrieben."
    assert "UNZENSIERT-MODUS" in ollama.aufrufe[0][2]


@pytest.mark.parametrize(
    "modell,gesamt,aktiv,moe",
    [
        ("google/diffusiongemma-26b-a4b-it", 26, 4, True),
        ("nvidia/nemotron-3-ultra-550b-a55b", 550, 55, True),
        ("meta/muse-glimmer-30b", 30, 30, False),
        ("ibm/granite-3.0-3b-a800m-instruct", 3, 0.8, True),
        ("mistralai/mixtral-8x22b-v0.1", 176, 176, False),
        ("google/gemma-4-31b-it", 31, 31, False),
    ],
)
def test_parameter_aus_dem_namen(modell, gesamt, aktiv, moe):
    werte = modell_info.parameter(modell)
    assert werte["gesamt_mrd"] == gesamt
    assert werte["aktiv_mrd"] == aktiv
    assert werte["moe"] is moe


def test_glimmer_ist_sichtbar_und_hat_messwerte():
    from app.core.config import lebendes_modell
    from app.services.modell_messungen import MESSUNGEN

    assert lebendes_modell("meta/muse-glimmer-30b") == "meta/muse-glimmer-30b"
    nvidia = MESSUNGEN["nvidia"]
    assert len(nvidia) >= 80
    info = modell_info.zusammenfassen("nvidia", "meta/muse-glimmer-30b", nvidia["meta/muse-glimmer-30b"])
    assert info["zustand"] == "bereit"
    assert "bild_zu_text" in info["faehigkeiten"]
    assert "Video zu Text" in info["faehigkeit_namen"]
    assert info["kurz_s"] and info["lang_s"]
    assert info["hersteller"] == "Meta"
    gemma = modell_info.zusammenfassen("nvidia", "google/diffusiongemma-26b-a4b-it", nvidia["google/diffusiongemma-26b-a4b-it"])
    assert gemma["video_s"] is not None
    gesperrt = [m for m, e in nvidia.items() if "fehler" in (e.get("hallo") or {}) and "404" in e["hallo"]["fehler"]]
    assert gesperrt and modell_info.zusammenfassen("nvidia", gesperrt[0], nvidia[gesperrt[0]])["zustand"] == "gesperrt"
    einbettung = modell_info.zusammenfassen("nvidia", "nvidia/nv-embedqa-mistral-7b-v2", nvidia["nvidia/nv-embedqa-mistral-7b-v2"])
    assert einbettung["faehigkeiten"] == ["einbettung"]


def test_modelle_info_endpunkt_und_eigene_messung(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.main import app

    async def modelle(dienst, timeout):
        return ["meta/muse-glimmer-30b", "nvidia/neu-1b"]

    monkeypatch.setattr(routes, "_models_for", modelle)
    monkeypatch.setattr(routes, "get_registry", lambda: SimpleNamespace(all=lambda: {"nvidia": object()}))
    modell_info.get_modell_info().merken("nvidia", "nvidia/neu-1b", {"zeit": 1, "hallo": {"s": 0.5, "erstes": 0.2}})
    try:
        with TestClient(app) as client:
            antwort = client.get("/api/modelle/info", params={"anbieter": "nvidia"})
        assert antwort.status_code == 200
        daten = antwort.json()["modelle"]
        assert daten["meta/muse-glimmer-30b"]["zustand"] == "bereit"
        assert daten["nvidia/neu-1b"]["kurz_s"] == 0.5
        assert daten["nvidia/neu-1b"]["parameter"]["gesamt_mrd"] == 1
    finally:
        modell_info.DATEI.unlink(missing_ok=True)


def test_registry_listet_glimmer_und_gemma():
    from app.providers.registry import get_registry

    standard = get_registry().all()["nvidia"]._default_models
    assert "meta/muse-glimmer-30b" in standard
    assert "google/diffusiongemma-26b-a4b-it" in standard
