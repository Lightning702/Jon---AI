from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.services import premium as modul
from app.services.premium import Premium

pytestmark = pytest.mark.standard


@pytest.fixture()
def standard(tmp_path, monkeypatch):
    dienst = Premium(tmp_path)
    monkeypatch.setattr(modul, "_premium", dienst)
    return dienst


@pytest.fixture()
def client(standard):
    from app.main import create_app

    yield TestClient(create_app())


def test_gesperrte_routen_antworten_mit_402_und_funktion(client):
    for methode, pfad, daten, feature in [
        ("post", "/api/studio/generate", {"prompt": "Ein Hund", "kind": "bild"}, "studio"),
        ("post", "/api/research/start", {"topic": "Quantencomputer"}, "recherche"),
        ("post", "/api/media/jobs", {"kind": "speech", "text": "Hallo"}, "stimmen"),
        ("post", "/api/games/starfall/start", None, "spiele"),
        ("post", "/api/inbox/analyze", {"items": []}, "automatik"),
    ]:
        antwort = getattr(client, methode)(pfad, json=daten) if daten is not None else getattr(client, methode)(pfad)
        assert antwort.status_code == 402, (pfad, antwort.status_code, antwort.text)
        assert antwort.json()["premium"] == feature


def test_mini_jon_aussehen_braucht_premium_aber_normale_einstellungen_nicht(client):
    assert client.put("/api/settings", json={"pet_3d": True}).status_code == 402
    assert client.put("/api/settings", json={"pet_companion": "cat"}).status_code == 402
    assert client.put("/api/settings", json={"pet_scale": 1.1}).status_code == 200


def test_chat_werkzeuge_melden_premium_statt_auszufuehren(standard):
    from app.services.tools import ToolBox

    box = ToolBox()

    async def lauf():
        return [json.loads(await box.execute(name, args)) for name, args in [("create_image", {"prompt": "x"}), ("browser_task", {"auftrag": "x"}), ("deep_learning", {"topic": "x"})]]

    for antwort in asyncio.run(lauf()):
        assert antwort["premium"] in {"studio", "browser", "recherche"} and "Premium" in antwort["error"]


def test_fachteam_und_harness_haben_tageskontingent(standard, tmp_path):
    from app.services.agenten_service import AgentenService
    from app.services.harness.service import HarnessService

    async def antwort(*args, **kwargs):
        return json.dumps({"tool": "finish", "args": {"summary": "ok"}})

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", antwort)
        projekt = tmp_path / "projekt"
        projekt.mkdir()
        for _ in range(3):
            task = service.start("Prüfe", str(projekt))
            await service.running[task["id"]]
        with pytest.raises(modul.PremiumNoetig, match="kostenlosen"):
            service.start("Noch einer", str(projekt))

    asyncio.run(ablauf())
    team = AgentenService()

    async def schnell(*args, **kwargs):
        return "ok"

    team.complete = schnell

    async def zweimal():
        team.start("Erkläre den AcI", persist=False)
        with pytest.raises(modul.PremiumNoetig):
            team.start("Noch einmal", persist=False)
        await team.close()

    asyncio.run(zweimal())


def test_handy_app_kennt_kein_premium(standard, client):
    from app.services.premium import FEATURES

    assert "funke" not in FEATURES and "Handy" not in FEATURES["fernsteuerung"][1]
    assert client.post("/api/mobile/befehl", json={"text": "/hilfe"}).status_code != 402
    assert client.post("/api/mobile/ausfuehren", json={"path": "gibt-es-nicht.txt"}).status_code != 402
