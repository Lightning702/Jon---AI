from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.handy_service import (
    CODE_LAENGE,
    _b64,
    _entschluesseln,
    _unb64,
    _verschluesseln,
    code_saeubern,
    get_handy_service,
    schluessel_fuer_code,
    thema_fuer,
)

client = TestClient(app)


def _umschlag(schluessel: bytes, art: str, kennung: str, klartext: dict) -> dict:
    zusatz = f"{art}:{kennung}".encode("utf-8")
    return {"v": 1, "k": art, "i": kennung, **_verschluesseln(schluessel, zusatz, klartext)}


def _auspacken(schluessel: bytes, art: str, kennung: str, umschlag: dict) -> dict:
    zusatz = f"{art}:{kennung}".encode("utf-8")
    return _entschluesseln(schluessel, zusatz, umschlag)


@pytest.fixture()
def kopplung():
    get_handy_service().kopplung_abbrechen()
    antwort = client.post("/api/handy/pairing/start")
    assert antwort.status_code == 200
    nutzlast = json.loads(antwort.json()["nutzlast"])
    nutzlast["pc"] = thema_fuer(nutzlast["c"])
    schluessel = schluessel_fuer_code(nutzlast["c"])
    yield nutzlast, schluessel
    get_handy_service().kopplung_abbrechen()


def test_qr_nutzlast_enthaelt_code_und_broker(kopplung):
    nutzlast, _ = kopplung
    assert nutzlast["t"] == "jon-pair"
    assert nutzlast["u"] == "" or nutzlast["u"].startswith("http://")
    assert "127.0.0.1" not in nutzlast["u"]
    assert nutzlast["b"]
    assert len(nutzlast["c"]) == CODE_LAENGE
    assert code_saeubern(nutzlast["c"]) == nutzlast["c"]


def test_code_wird_gruppiert_angezeigt():
    get_handy_service().kopplung_abbrechen()
    daten = client.post("/api/handy/pairing/start").json()
    assert daten["code_gruppiert"].count("-") == 2
    assert daten["code_gruppiert"].replace("-", "") == daten["code"]
    stand = client.get("/api/handy/pairing/state").json()
    assert stand["code"] == daten["code"]
    get_handy_service().kopplung_abbrechen()


def test_getippter_code_ergibt_denselben_schluessel(kopplung):
    nutzlast, schluessel = kopplung
    getippt = "  " + "-".join(
        nutzlast["c"][i:i + 4] for i in range(0, CODE_LAENGE, 4)
    ).lower() + " "
    assert schluessel_fuer_code(code_saeubern(getippt)) == schluessel
    thema = thema_fuer(code_saeubern(getippt))
    antwort = client.post(
        "/api/handy/gate",
        json=_umschlag(schluessel, "pair", thema, {"op": "hello", "rid": 1}),
    )
    assert _auspacken(schluessel, "pair", thema, antwort.json())["ok"] is True


def test_falscher_code_wird_abgewiesen(kopplung):
    nutzlast, _ = kopplung
    fremd = schluessel_fuer_code("ZZZZZZZZZZZZ")
    umschlag = _umschlag(fremd, "pair", nutzlast["pc"], {"op": "hello"})
    antwort = client.post("/api/handy/gate", json=umschlag)
    assert antwort.status_code == 403


def test_zu_viele_fehlversuche_sperren_den_code(kopplung):
    nutzlast, schluessel = kopplung
    fremd = schluessel_fuer_code("YYYYYYYYYYYY")
    for _ in range(13):
        client.post(
            "/api/handy/gate",
            json=_umschlag(fremd, "pair", nutzlast["pc"], {"op": "hello"}),
        )
    gesperrt = client.post(
        "/api/handy/gate",
        json=_umschlag(schluessel, "pair", nutzlast["pc"], {"op": "hello"}),
    )
    assert gesperrt.status_code == 403


def test_kopplung_und_api_aufruf(kopplung):
    nutzlast, schluessel = kopplung
    pc = nutzlast["pc"]

    hallo = client.post(
        "/api/handy/gate",
        json=_umschlag(schluessel, "pair", pc, {"op": "hello", "rid": 1}),
    )
    assert hallo.status_code == 200
    assert _auspacken(schluessel, "pair", pc, hallo.json())["ok"] is True

    anfrage = client.post(
        "/api/handy/gate",
        json=_umschlag(
            schluessel,
            "pair",
            pc,
            {"op": "pair", "rid": 2, "name": "Testhandy", "plattform": "Android 15"},
        ),
    )
    assert _auspacken(schluessel, "pair", pc, anfrage.json())["status"] == "wartet"

    stand = client.get("/api/handy/pairing/state").json()
    assert stand["status"] == "wartet"
    assert stand["geraet"]["name"] == "Testhandy"

    bestaetigt = client.post("/api/handy/pairing/answer", json={"angenommen": True})
    assert bestaetigt.json()["status"] == "ok"

    fertig = client.post(
        "/api/handy/gate",
        json=_umschlag(schluessel, "pair", pc, {"op": "pair-status", "rid": 3}),
    )
    zugang = _auspacken(schluessel, "pair", pc, fertig.json())
    assert zugang["ok"] is True
    geraet = zugang["geraet"]
    geraeteschluessel = _unb64(zugang["schluessel"])

    ruf = client.post(
        "/api/handy/gate",
        json=_umschlag(
            geraeteschluessel,
            "dev",
            geraet,
            {"op": "call", "rid": 4, "method": "GET", "path": "/api/health"},
        ),
    )
    ergebnis = _auspacken(geraeteschluessel, "dev", geraet, ruf.json())
    assert ergebnis["ok"] is True
    assert json.loads(ergebnis["text"])["status"] == "ok"

    eigener = TestClient(app, headers={"X-Jon-Token": zugang["token"]})
    assert eigener.get("/api/projects").status_code == 200

    assert client.delete(f"/api/handy/devices/{geraet}").json()["entfernt"] is True
    verweigert = client.post(
        "/api/handy/gate",
        json=_umschlag(
            geraeteschluessel,
            "dev",
            geraet,
            {"op": "ping", "rid": 5},
        ),
    )
    assert verweigert.status_code == 403


def _koppeln(kopplung) -> tuple[str, bytes]:
    nutzlast, schluessel = kopplung
    pc = nutzlast["pc"]
    client.post(
        "/api/handy/gate",
        json=_umschlag(
            schluessel, "pair", pc, {"op": "pair", "rid": 1, "name": "Uploadhandy"}
        ),
    )
    client.post("/api/handy/pairing/answer", json={"angenommen": True})
    fertig = client.post(
        "/api/handy/gate",
        json=_umschlag(schluessel, "pair", pc, {"op": "pair-status", "rid": 2}),
    )
    zugang = _auspacken(schluessel, "pair", pc, fertig.json())
    return zugang["geraet"], _unb64(zugang["schluessel"])


def test_datei_kommt_in_teilen_an(kopplung):
    from pathlib import Path

    geraet, schluessel = _koppeln(kopplung)
    inhalt = bytes(range(256)) * 40
    start = _auspacken(
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
                    "op": "datei-start",
                    "rid": 3,
                    "name": "urlaub .jpg",
                    "art": "image/jpeg",
                    "groesse": len(inhalt),
                },
            ),
        ).json(),
    )
    assert start["ok"] is True
    kennung = start["id"]

    haelfte = len(inhalt) // 2
    teile = [inhalt[:haelfte], inhalt[haelfte:]]
    for nummer, stueck in enumerate(teile):
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
                        "op": "datei-teil",
                        "rid": 4 + nummer,
                        "id": kennung,
                        "nr": nummer,
                        "daten": _b64(stueck),
                    },
                ),
            ).json(),
        )
        assert antwort["ok"] is True

    ende = _auspacken(
        schluessel,
        "dev",
        geraet,
        client.post(
            "/api/handy/gate",
            json=_umschlag(
                schluessel,
                "dev",
                geraet,
                {"op": "datei-ende", "rid": 9, "id": kennung, "teile": 2},
            ),
        ).json(),
    )
    assert ende["ok"] is True
    ziel = Path(ende["pfad"])
    assert ziel.is_file()
    assert ziel.read_bytes() == inhalt
    assert ziel.name.endswith("urlaub .jpg")
    ziel.unlink()
    client.delete(f"/api/handy/devices/{geraet}")


def test_fehlende_teile_werden_gemeldet(kopplung):
    geraet, schluessel = _koppeln(kopplung)
    start = _auspacken(
        schluessel,
        "dev",
        geraet,
        client.post(
            "/api/handy/gate",
            json=_umschlag(
                schluessel,
                "dev",
                geraet,
                {"op": "datei-start", "rid": 3, "name": "clip.mp4", "groesse": 10},
            ),
        ).json(),
    )
    ende = _auspacken(
        schluessel,
        "dev",
        geraet,
        client.post(
            "/api/handy/gate",
            json=_umschlag(
                schluessel,
                "dev",
                geraet,
                {"op": "datei-ende", "rid": 4, "id": start["id"], "teile": 3},
            ),
        ).json(),
    )
    assert ende["ok"] is False
    assert ende["fehlend"] == [0, 1, 2]
    client.delete(f"/api/handy/devices/{geraet}")


def test_geraete_uebersicht_liefert_werte():
    antwort = client.get("/api/handy/system")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["ram"]["gesamt"] >= 0
    assert "system" in daten


def test_qr_bild_wird_erzeugt():
    antwort = client.get("/api/handy/pairing/qr", params={"text": "jon-test"})
    assert antwort.status_code == 200
    assert antwort.content[:4] == b"\x89PNG"
