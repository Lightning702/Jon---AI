from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.connectors import get_connector_manager
from app.services.handy_service import (
    RECHTE_VORGABE,
    _entschluesseln,
    _unb64,
    _verschluesseln,
    get_handy_service,
    schluessel_fuer_code,
    thema_fuer,
)
from app.services.tools import ToolBox

client = TestClient(app)


def _umschlag(schluessel: bytes, art: str, kennung: str, klartext: dict) -> dict:
    zusatz = f"{art}:{kennung}".encode("utf-8")
    return {"v": 2, "k": art, "i": kennung, **_verschluesseln(schluessel, zusatz, klartext)}


def _auspacken(schluessel: bytes, art: str, kennung: str, umschlag: dict) -> dict:
    zusatz = f"{art}:{kennung}".encode("utf-8")
    return _entschluesseln(schluessel, zusatz, umschlag)


@pytest.fixture()
def handy():
    dienst = get_handy_service()
    for eintrag in dienst.geraete():
        dienst.geraet_entfernen(eintrag["id"])
    dienst.kopplung_abbrechen()
    nutzlast = json.loads(client.post("/api/handy/pairing/start").json()["nutzlast"])
    code = nutzlast["c"]
    thema = thema_fuer(code)
    paarschluessel = schluessel_fuer_code(code)
    client.post(
        "/api/handy/gate",
        json=_umschlag(
            paarschluessel,
            "pair",
            thema,
            {"op": "pair", "rid": 1, "name": "Testpixel", "plattform": "Android 15"},
        ),
    )
    client.post("/api/handy/pairing/answer", json={"angenommen": True})
    fertig = client.post(
        "/api/handy/gate",
        json=_umschlag(paarschluessel, "pair", thema, {"op": "pair-status", "rid": 2}),
    )
    zugang = _auspacken(paarschluessel, "pair", thema, fertig.json())
    yield zugang["geraet"], _unb64(zugang["schluessel"])
    dienst.geraet_entfernen(zugang["geraet"])
    dienst.kopplung_abbrechen()


def _antworten(geraet: str, schluessel: bytes, antworten: dict[str, dict]):
    dienst = get_handy_service()

    async def lauschen(fertig: asyncio.Event) -> None:
        strom = dienst.umschlag_strom(
            _umschlag(schluessel, "dev", geraet, {"op": "events", "rid": 90})
        )
        async for stueck in strom:
            paket = _auspacken(schluessel, "dev", geraet, stueck)
            if paket.get("bereit"):
                fertig.set()
            ereignis = paket.get("ereignis")
            if not isinstance(ereignis, dict) or ereignis.get("art") != "auftrag":
                continue
            daten = ereignis.get("daten") or {}
            vorlage = antworten.get(str(daten.get("op")))
            if vorlage is None:
                antwort = {"ok": False, "fehler": "Nicht unterstuetzt."}
            elif callable(vorlage):
                antwort = vorlage(daten)
            else:
                antwort = {"ok": True, "daten": vorlage}
            await dienst.umschlag(
                _umschlag(
                    schluessel,
                    "dev",
                    geraet,
                    {
                        "op": "antwort",
                        "rid": 91,
                        "auftrag": daten.get("auftrag"),
                        **antwort,
                    },
                )
            )

    return lauschen


def _mit_handy(geraet: str, schluessel: bytes, antworten: dict, aufgabe):
    async def lauf():
        bereit = asyncio.Event()
        lauscher = asyncio.create_task(_antworten(geraet, schluessel, antworten)(bereit))
        try:
            await asyncio.wait_for(bereit.wait(), timeout=5)
            return await aufgabe()
        finally:
            lauscher.cancel()

    return asyncio.run(lauf())


def test_neues_geraet_hat_nur_standardrechte(handy):
    geraet, _ = handy
    daten = client.get("/api/handy/devices").json()["geraete"]
    eintrag = next(g for g in daten if g["id"] == geraet)
    assert eintrag["rechte"] == RECHTE_VORGABE
    assert eintrag["rechte"]["kamera"] is False
    assert eintrag["rechte"]["standort"] is False
    assert eintrag["stufen"]["kamera"] == "sensibel"


def _beschreibung(kasten: ToolBox, name: str) -> str:
    for eintrag in kasten.schema("Wo ist mein Handy?"):
        if eintrag["function"]["name"] == name:
            return eintrag["function"]["description"]
    return ""


def test_gesperrte_werkzeuge_sind_sichtbar_aber_markiert(handy):
    geraet, _ = handy
    kasten = ToolBox()
    assert _beschreibung(kasten, "android_device_status")
    assert "GESPERRT" not in _beschreibung(kasten, "android_device_status")
    assert "GESPERRT" in _beschreibung(kasten, "android_location_get")

    antwort = client.post(
        f"/api/handy/devices/{geraet}/rights",
        json={"recht": "standort", "wert": True},
    )
    assert antwort.status_code == 200
    assert antwort.json()["rechte"]["standort"] is True
    assert "GESPERRT" not in _beschreibung(kasten, "android_location_get")

    client.post(f"/api/handy/devices/{geraet}/rights", json={"recht": "standort", "wert": False})
    assert "GESPERRT" in _beschreibung(kasten, "android_location_get")


def test_unbekanntes_recht_wird_abgewiesen(handy):
    geraet, _ = handy
    antwort = client.post(
        f"/api/handy/devices/{geraet}/rights",
        json={"recht": "alles", "wert": True},
    )
    assert antwort.status_code == 400


def test_ohne_freigabe_kein_standort(handy):
    geraet, schluessel = handy

    async def frage():
        return await get_connector_manager().ausfuehren("android_location_get", {})

    ergebnis = _mit_handy(geraet, schluessel, {}, frage)
    assert "error" in ergebnis
    assert "Standort" in ergebnis["error"]
    assert "Werkzeuge" in ergebnis["error"]


def test_akku_kommt_vom_handy(handy):
    geraet, schluessel = handy
    zustand = {
        "akku": 74,
        "laedt": False,
        "netz": "WLAN",
        "android": "Android 15",
        "modell": "Pixel 8",
    }

    async def frage():
        return await get_connector_manager().ausfuehren("android_battery_status", {})

    ergebnis = _mit_handy(geraet, schluessel, {"zustand": zustand}, frage)
    assert ergebnis["akku"] == 74
    assert ergebnis["laedt"] is False
    assert ergebnis["online"] is True


def test_standort_nach_freigabe(handy):
    geraet, schluessel = handy
    client.post(f"/api/handy/devices/{geraet}/rights", json={"recht": "standort", "wert": True})
    ort = {"breite": 47.81, "laenge": 13.05, "genauigkeit": 12.0, "quelle": "gps"}

    async def frage():
        return await get_connector_manager().ausfuehren("android_location_get", {})

    ergebnis = _mit_handy(geraet, schluessel, {"ort": ort}, frage)
    assert ergebnis["breite"] == 47.81
    assert ergebnis["geraet"] == "Testpixel"


def test_hinweise_melden_fehlende_android_freigabe(handy):
    geraet, schluessel = handy
    client.post(f"/api/handy/devices/{geraet}/rights", json={"recht": "hinweise", "wert": True})

    def antwort(_daten: dict) -> dict:
        return {"ok": False, "fehler": "Der Zugriff auf Benachrichtigungen ist am Handy aus."}

    async def frage():
        return await get_connector_manager().ausfuehren("android_notifications_list", {})

    ergebnis = _mit_handy(geraet, schluessel, {"hinweise": antwort}, frage)
    assert "Benachrichtigungen" in ergebnis["error"]


def test_datei_geht_in_teilen_zum_handy(handy, tmp_path):
    geraet, schluessel = handy
    quelle: Path = tmp_path / "urlaub.pdf"
    inhalt = bytes(range(256)) * 400
    quelle.write_bytes(inhalt)
    dienst = get_handy_service()
    gesammelt: dict[str, bytes] = {}

    def holen(daten: dict) -> dict:
        marke = str(daten.get("marke"))
        teile = int(daten.get("teile"))
        stuecke = []
        for nummer in range(teile):
            block = dienst.datei_holen(geraet, {"marke": marke, "nr": nummer})
            assert block["ok"] is True
            stuecke.append(_unb64(block["daten"]))
        gesammelt[marke] = b"".join(stuecke)
        return {"ok": True, "daten": {"gespeichert": "/sdcard/Download/Jon/urlaub.pdf"}}

    async def frage():
        return await get_connector_manager().ausfuehren(
            "android_files_send", {"path": str(quelle)}
        )

    ergebnis = _mit_handy(geraet, schluessel, {"datei": holen}, frage)
    assert ergebnis["gespeichert"].endswith("urlaub.pdf")
    assert list(gesammelt.values())[0] == inhalt


def test_offline_bringt_verstaendlichen_fehler(handy):
    geraet, _ = handy
    client.post(f"/api/handy/devices/{geraet}/rights", json={"recht": "kontakte", "wert": True})

    async def frage():
        return await get_connector_manager().ausfuehren(
            "android_contacts_search", {"query": "Mama"}
        )

    ergebnis = asyncio.run(frage())
    assert "offline" in ergebnis["error"]


def test_handy_darf_sperren_aber_nicht_freigeben(handy):
    geraet, schluessel = handy
    client.post(f"/api/handy/devices/{geraet}/rights", json={"recht": "kontakte", "wert": True})

    freigabe = _auspacken(
        schluessel,
        "dev",
        geraet,
        client.post(
            "/api/handy/gate",
            json=_umschlag(
                schluessel,
                "dev",
                geraet,
                {"op": "recht", "rid": 20, "recht": "kamera", "wert": True},
            ),
        ).json(),
    )
    assert freigabe["ok"] is False
    assert freigabe["rechte"]["kamera"] is False

    sperre = _auspacken(
        schluessel,
        "dev",
        geraet,
        client.post(
            "/api/handy/gate",
            json=_umschlag(
                schluessel,
                "dev",
                geraet,
                {"op": "recht", "rid": 21, "recht": "kontakte", "wert": False},
            ),
        ).json(),
    )
    assert sperre["ok"] is True
    assert sperre["rechte"]["kontakte"] is False


def test_datei_vom_handy_wird_angefordert(handy):
    geraet, schluessel = handy
    gefragt: list[str] = []

    def antwort(daten: dict) -> dict:
        gefragt.append(str(daten.get("pfad")))
        return {"ok": True, "daten": {"pfad": "C:/jon/handy/urlaub.jpg", "name": "urlaub.jpg"}}

    async def frage():
        return await get_connector_manager().ausfuehren(
            "android_files_receive",
            {"path": "content://media/external/images/media/42"},
        )

    ergebnis = _mit_handy(geraet, schluessel, {"datei-senden": antwort}, frage)
    assert gefragt == ["content://media/external/images/media/42"]
    assert ergebnis["name"] == "urlaub.jpg"


def test_zustandsmeldung_setzt_faehigkeiten(handy):
    geraet, schluessel = handy
    antwort = _auspacken(
        schluessel,
        "dev",
        geraet,
        client.post(
            "/api/handy/gate",
            json=_umschlag(
                schluessel,
                "dev",
                geraet,
                {
                    "op": "zustand",
                    "rid": 30,
                    "zustand": {"akku": 51, "netz": "Mobilfunk", "name": "Pixel 8"},
                    "faehigkeiten": ["status", "dateien"],
                },
            ),
        ).json(),
    )
    assert antwort["ok"] is True
    eintrag = next(
        g for g in client.get("/api/handy/devices").json()["geraete"] if g["id"] == geraet
    )
    assert eintrag["zustand"]["akku"] == 51
    assert eintrag["faehigkeiten"] == ["status", "dateien"]

    client.post(f"/api/handy/devices/{geraet}/rights", json={"recht": "kamera", "wert": True})
    kasten = ToolBox()
    foto = next(
        eintrag["function"]
        for eintrag in kasten.schema("Mach ein Foto mit dem Handy")
        if eintrag["function"]["name"] == "android_camera_request_photo"
    )
    assert "GESPERRT" in foto["description"]


def test_gerael_umbenennen_und_uebersicht(handy):
    geraet, _ = handy
    antwort = client.post(f"/api/handy/devices/{geraet}/name", json={"name": "Mein Handy"})
    assert antwort.status_code == 200
    assert antwort.json()["geraet"]["name"] == "Mein Handy"
    uebersicht = client.get("/api/handy/connectors").json()["connectoren"]
    android = next(c for c in uebersicht if c["id"] == "android")
    assert android["bereit"] is True
    assert any(g["name"] == "Mein Handy" for g in android["geraete"])
