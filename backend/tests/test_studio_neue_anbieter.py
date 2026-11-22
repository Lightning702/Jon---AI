from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest

from app.services import studio_service
from app.services.studio_service import PNG_MAGIC, StudioError, StudioService

BILD = PNG_MAGIC + b"\r\n\x1a\n" + b"\0" * 64
B64 = base64.b64encode(BILD).decode()


@pytest.fixture()
def dienst(monkeypatch, tmp_path):
    monkeypatch.setattr(studio_service, "CONFIG_FILE", tmp_path / "studio.json")
    monkeypatch.setattr(studio_service, "GALLERY_FILE", tmp_path / "galerie.json")
    monkeypatch.setattr(studio_service, "STUDIO_DIR", tmp_path / "studio")
    monkeypatch.setattr("app.services.aufgaben_modelle.fuer", lambda art: None)
    monkeypatch.setattr("app.services.offline.aktiv", lambda: False)
    monkeypatch.setattr(studio_service.asyncio, "sleep", _sofort)
    service = StudioService()
    service._config = {}
    monkeypatch.setattr(service, "_inherited", lambda anbieter: "")
    return service


async def _sofort(_sekunden):
    return None


def _mit_server(monkeypatch, behandeln):
    anfragen: list[httpx.Request] = []

    def weiter(anfrage: httpx.Request) -> httpx.Response:
        anfragen.append(anfrage)
        return behandeln(anfrage)

    transport = httpx.MockTransport(weiter)
    monkeypatch.setattr(
        StudioService,
        "_client",
        staticmethod(lambda timeout=180.0: httpx.AsyncClient(transport=transport, follow_redirects=True)),
    )
    return anfragen


def _bild(dienst, anbieter, **mehr):
    return asyncio.run(dienst.generate("Ein roter Apfel", provider=anbieter, **mehr))


def test_alle_anbieter_haben_eine_methode():
    for name in studio_service.PROVIDERS:
        assert hasattr(StudioService, f"_{name}"), name
    assert set(studio_service.AUSWEICHEN) <= set(studio_service.PROVIDERS)
    assert "aihorde" not in studio_service.AUSWEICHEN


def test_xai_schickt_bearer_und_liest_b64(dienst, monkeypatch):
    dienst._config = {"schluessel": {"xai": "xai-test"}}
    anfragen = _mit_server(monkeypatch, lambda a: httpx.Response(200, json={"data": [{"b64_json": B64}]}))
    werk = _bild(dienst, "xai")
    assert werk["anbieter"] == "xai" and werk["mime"] == "image/png"
    assert str(anfragen[0].url) == "https://api.x.ai/v1/images/generations"
    assert anfragen[0].headers["authorization"] == "Bearer xai-test"
    assert json.loads(anfragen[0].content)["model"] == "grok-2-image-1212"


def test_recraft_waehlt_erlaubte_groesse(dienst, monkeypatch):
    dienst._config = {"schluessel": {"recraft": "rc"}}
    anfragen = _mit_server(monkeypatch, lambda a: httpx.Response(200, json={"data": [{"b64_json": B64}]}))
    _bild(dienst, "recraft", size="1280x720")
    koerper = json.loads(anfragen[0].content)
    assert koerper["size"] == "1820x1024" and koerper["model"] == "recraftv3"


def test_deepinfra_rundet_auf_raster(dienst, monkeypatch):
    dienst._config = {"schluessel": {"deepinfra": "di"}}
    anfragen = _mit_server(monkeypatch, lambda a: httpx.Response(200, json={"data": [{"b64_json": B64}]}))
    _bild(dienst, "deepinfra", size="1280x720")
    assert json.loads(anfragen[0].content)["size"] == "1280x704"
    assert "api.deepinfra.com/v1/openai/images/generations" in str(anfragen[0].url)


def test_huggingface_wartet_auf_ladendes_modell(dienst, monkeypatch):
    dienst._config = {"schluessel": {"huggingface": "hf_test"}}
    antworten = [httpx.Response(503, json={"error": "loading"}), httpx.Response(200, content=BILD, headers={"content-type": "image/png"})]
    anfragen = _mit_server(monkeypatch, lambda a: antworten.pop(0))
    werk = _bild(dienst, "huggingface")
    assert len(anfragen) == 2 and werk["anbieter"] == "huggingface"
    assert str(anfragen[0].url).endswith("/hf-inference/models/black-forest-labs/FLUX.1-schnell")


def test_bfl_fragt_nach_bis_fertig(dienst, monkeypatch):
    dienst._config = {"schluessel": {"bfl": "bfl-key"}}
    staende = [{"status": "Pending"}, {"status": "Ready", "result": {"sample": "https://bild.example/x.png"}}]

    def antwort(anfrage: httpx.Request) -> httpx.Response:
        if anfrage.method == "POST":
            return httpx.Response(200, json={"id": "a1", "polling_url": "https://api.bfl.ai/v1/get_result?id=a1"})
        if "get_result" in str(anfrage.url):
            return httpx.Response(200, json=staende.pop(0))
        return httpx.Response(200, content=BILD, headers={"content-type": "image/png"})

    anfragen = _mit_server(monkeypatch, antwort)
    werk = _bild(dienst, "bfl", size="1536x1024")
    koerper = json.loads(anfragen[0].content)
    assert koerper["width"] == 1440 and koerper["height"] == 1024
    assert anfragen[0].headers["x-key"] == "bfl-key"
    assert werk["anbieter"] == "bfl"


def test_bfl_meldet_inhaltsfilter(dienst, monkeypatch):
    dienst._config = {"schluessel": {"bfl": "bfl-key"}}

    def antwort(anfrage: httpx.Request) -> httpx.Response:
        if anfrage.method == "POST":
            return httpx.Response(200, json={"id": "a1", "polling_url": "https://api.bfl.ai/v1/get_result?id=a1"})
        return httpx.Response(200, json={"status": "Content Moderated"})

    _mit_server(monkeypatch, antwort)
    with pytest.raises(StudioError) as fehler:
        asyncio.run(dienst._bfl("x", "bild", "flux-pro-1.1", 1024, 1024, "", "k", None))
    assert "Inhaltsfilter" in str(fehler.value)


def test_ideogram_schickt_multipart(dienst, monkeypatch):
    dienst._config = {"schluessel": {"ideogram": "ig"}}

    def antwort(anfrage: httpx.Request) -> httpx.Response:
        if "ideogram-v3" in str(anfrage.url):
            return httpx.Response(200, json={"data": [{"url": "https://ideogram.example/b.png"}]})
        return httpx.Response(200, content=BILD, headers={"content-type": "image/png"})

    anfragen = _mit_server(monkeypatch, antwort)
    _bild(dienst, "ideogram", size="1280x720")
    erste = anfragen[0]
    assert erste.headers["content-type"].startswith("multipart/form-data")
    assert erste.headers["api-key"] == "ig"
    inhalt = erste.content.decode()
    assert 'name="aspect_ratio"' in inhalt and "16x9" in inhalt and "TURBO" in inhalt


def test_aihorde_ohne_schluessel_und_mit_filter(dienst, monkeypatch):
    checks = [{"done": False, "is_possible": True}, {"done": True}]

    def antwort(anfrage: httpx.Request) -> httpx.Response:
        adresse = str(anfrage.url)
        if adresse.endswith("/generate/async"):
            return httpx.Response(202, json={"id": "h1"})
        if "/generate/check/" in adresse:
            return httpx.Response(200, json=checks.pop(0))
        if "/generate/status/" in adresse:
            return httpx.Response(200, json={"generations": [{"img": "https://r2.example/h1.webp"}]})
        return httpx.Response(200, content=b"RIFF\0\0\0\0WEBPVP8 ", headers={"content-type": "image/webp"})

    anfragen = _mit_server(monkeypatch, antwort)
    werk = _bild(dienst, "aihorde", size="1536x1024")
    koerper = json.loads(anfragen[0].content)
    assert anfragen[0].headers["apikey"] == "0000000000"
    assert anfragen[0].headers["client-agent"].startswith("Jon:")
    assert koerper["nsfw"] is False and koerper["censor_nsfw"] is True
    assert koerper["params"]["width"] * koerper["params"]["height"] <= 576 * 576
    assert koerper["models"] == ["Deliberate"]
    assert werk["mime"] == "image/webp"


def test_comfyui_baut_workflow_mit_erstem_checkpoint(dienst, monkeypatch):
    dienst._config = {"anbieter": "comfyui", "basis": {"comfyui": "http://127.0.0.1:8188"}}
    verlauf = [{}, {"p1": {"status": {"status_str": "success", "completed": True}, "outputs": {"9": {"images": [{"filename": "Jon_0001.png", "subfolder": "", "type": "output"}]}}}}]

    def antwort(anfrage: httpx.Request) -> httpx.Response:
        adresse = str(anfrage.url)
        if "object_info" in adresse:
            return httpx.Response(200, json={"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": ["COMBO", {"options": ["sdxl_lightning.safetensors", "b.ckpt"]}]}}}})
        if adresse.endswith("/prompt"):
            return httpx.Response(200, json={"prompt_id": "p1", "node_errors": {}})
        if "/history/" in adresse:
            return httpx.Response(200, json=verlauf.pop(0))
        return httpx.Response(200, content=BILD, headers={"content-type": "image/png"})

    anfragen = _mit_server(monkeypatch, antwort)
    werk = _bild(dienst, "comfyui")
    workflow = json.loads(next(a for a in anfragen if str(a.url).endswith("/prompt")).content)["prompt"]
    assert workflow["4"]["inputs"]["ckpt_name"] == "sdxl_lightning.safetensors"
    assert workflow["3"]["inputs"]["steps"] == 4
    assert "filename=Jon_0001.png" in str(anfragen[-1].url)
    assert werk["anbieter"] == "comfyui"


def test_offline_nimmt_comfyui_nur_wenn_eingerichtet(dienst, monkeypatch):
    monkeypatch.setattr("app.services.offline.aktiv", lambda: True)
    monkeypatch.setattr("app.providers.lokal_server.einstellung", lambda: ("", ""))
    assert dienst.pick() == "lokal"
    dienst._config = {"basis": {"comfyui": "http://127.0.0.1:8188"}}
    assert dienst.pick() == "comfyui"
