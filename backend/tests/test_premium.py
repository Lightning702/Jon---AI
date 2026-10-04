from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services import premium as modul
from app.services.premium import Premium, PremiumNoetig, b64url, lesen

pytestmark = pytest.mark.standard
SCHLUESSEL = Ed25519PrivateKey.generate()
OEFFENTLICH = base64.b64encode(SCHLUESSEL.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def token(inhalt: dict, schluessel=SCHLUESSEL) -> str:
    kopf = "JON1." + b64url(json.dumps(inhalt).encode())
    return kopf + "." + b64url(schluessel.sign(kopf.encode()))


@pytest.fixture()
def dienst(tmp_path, monkeypatch):
    monkeypatch.setattr(modul, "OEFFENTLICH", OEFFENTLICH)
    monkeypatch.setattr(modul, "_maschine", lambda: "test-maschine")
    return Premium(tmp_path)


def test_ohne_lizenz_ist_jon_standard(dienst):
    status = dienst.status()
    assert status["stufe"] == "standard" and status["name"] == "Standard"
    assert len(status["features"]) == 14 and not any(f["frei"] for f in status["features"])
    assert len(dienst.geraet()) == 20


def test_gueltige_lizenz_fuer_dieses_geraet_schaltet_premium_frei(dienst):
    dienst.speichern(token({"stufe": "premium", "geraete": [dienst.geraet()], "exp": time.time() + 3600, "abo": "sub_1"}))
    assert dienst.stufe() == "premium" and dienst.status()["name"] == "Premium"
    dienst.pruefen("studio")
    for _ in range(10):
        dienst.verbrauchen("harness")


def test_admin_lizenz_zeigt_admin(dienst):
    dienst.speichern(token({"stufe": "admin", "name": "Admin", "geraete": [dienst.geraet()], "exp": time.time() + 3600}))
    assert dienst.status()["name"] == "Admin"
    assert dienst.premium()


def test_gefaelschte_veraenderte_oder_fremde_lizenzen_bleiben_standard(dienst):
    with pytest.raises(ValueError, match="Signatur"):
        dienst.speichern(token({"stufe": "admin", "geraete": [dienst.geraet()], "exp": 0}, Ed25519PrivateKey.generate()))
    echt = token({"stufe": "premium", "geraete": [dienst.geraet()], "exp": time.time() + 3600})
    kopf, inhalt, signatur = echt.split(".")
    veraendert = b64url(json.dumps({"stufe": "admin", "geraete": [dienst.geraet()], "exp": 0}).encode())
    with pytest.raises(ValueError, match="Signatur"):
        dienst.speichern(f"{kopf}.{veraendert}.{signatur}")
    with pytest.raises(ValueError, match="anderes Gerät|nicht für dieses Gerät"):
        dienst.speichern(token({"stufe": "admin", "geraete": ["0" * 20], "exp": 0}))
    dienst.datei.write_text(json.dumps({"token": f"{kopf}.{veraendert}.{signatur}"}), encoding="utf-8")
    assert dienst.stufe() == "standard" and "Signatur" in dienst.status()["hinweis"]
    dienst.datei.write_text(json.dumps({"token": token({"stufe": "admin", "geraete": ["0" * 20], "exp": 0})}), encoding="utf-8")
    dienst._cache = None
    assert dienst.stufe() == "standard" and "anderes Gerät" in dienst.status()["hinweis"]


def test_abgelaufene_lizenz_faellt_auf_standard(dienst):
    dienst.speichern(token({"stufe": "premium", "geraete": [dienst.geraet()], "exp": time.time() + 1}))
    dienst._cache = None
    dienst.datei.write_text(json.dumps({"token": token({"stufe": "premium", "geraete": [dienst.geraet()], "exp": time.time() - 10})}), encoding="utf-8")
    assert dienst.stufe() == "standard" and "abgelaufen" in dienst.status()["hinweis"]
    assert dienst.braucht_erneuerung()


def test_standard_hat_tageskontingente_und_gesperrte_funktionen(dienst):
    for _ in range(3):
        dienst.verbrauchen("harness")
    with pytest.raises(PremiumNoetig, match="3 kostenlosen"):
        dienst.verbrauchen("harness")
    dienst.verbrauchen("fachteam")
    with pytest.raises(PremiumNoetig, match="1 kostenlose Fachteam"):
        dienst.verbrauchen("fachteam")
    with pytest.raises(PremiumNoetig) as fehler:
        dienst.pruefen("studio")
    assert fehler.value.feature == "studio"
    assert {f["key"]: f["verbraucht"] for f in dienst.status()["features"]}["harness"] == 3


def test_kauf_admin_und_eingabe_laufen_ueber_den_lizenzserver(dienst):
    aufrufe = []
    antworten = {"checkout": {"id": "cs_test_1", "url": "https://checkout.stripe.com/x"}}

    async def rufen(name, daten):
        aufrufe.append((name, daten))
        if name == "lizenz" and daten["aktion"] == "abholen":
            return {"offen": True} if len(aufrufe) < 3 else {"token": token({"stufe": "premium", "geraete": [daten["geraet"]], "exp": time.time() + 3600, "abo": "sub_1"})}
        if name == "lizenz" and daten["aktion"] == "geraet":
            return {"token": token({"stufe": "premium", "geraete": ["1" * 20, daten["geraet"]], "exp": time.time() + 3600, "abo": "sub_1"})}
        return antworten[name]

    async def codeserver(name, daten):
        aufrufe.append((name, daten))
        if name == "einloesen":
            if daten["code"] != "richtig":
                raise ValueError("Dieser Code ist ungültig.")
            return {"token": token({"stufe": "admin", "geraete": [daten["geraet"]], "exp": time.time() + 3600})}
        raise AssertionError(name)

    dienst.rufen = rufen
    dienst.codeserver = codeserver

    async def ablauf():
        assert (await dienst.kaufen("jahr"))["url"].startswith("https://checkout.stripe.com")
        assert aufrufe[0] == ("checkout", {"plan": "jahr", "geraet": dienst.geraet()})
        assert not (await dienst.abholen())["fertig"]
        fertig = await dienst.abholen()
        assert fertig["fertig"] and fertig["stufe"] == "premium" and not dienst.offen
        dienst.abmelden()
        status = await dienst.eingeben(token({"stufe": "premium", "geraete": ["1" * 20], "exp": time.time() + 3600, "abo": "sub_1"}))
        assert status["stufe"] == "premium" and aufrufe[-1][1]["aktion"] == "geraet"
        with pytest.raises(ValueError, match="ungültig"):
            await dienst.admin("falsch")
        assert (await dienst.admin("richtig"))["name"] == "Admin"

    asyncio.run(ablauf())


def test_premium_api_meldet_402_mit_funktion(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(modul, "_premium", Premium(tmp_path))
    app = create_app()

    @app.get("/api/test-premium")
    async def gesperrt():
        modul.get_premium().pruefen("browser")

    client = TestClient(app)
    antwort = client.get("/api/test-premium")
    assert antwort.status_code == 402
    assert antwort.json()["premium"] == "browser" and "Browser-Agent" in antwort.json()["detail"]
    assert client.get("/api/premium").json()["name"] == "Standard"


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js fehlt")
def test_vom_lizenzserver_signierte_lizenz_wird_in_jon_erkannt(tmp_path):
    privat = base64.b64encode(SCHLUESSEL.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).decode()
    basis = Path(__file__).resolve().parents[2] / "netlify" / "lib" / "basis.mjs"
    skript = f"import {{signieren}} from {json.dumps(basis.as_uri())}; process.stdout.write(signieren({{stufe: 'premium', geraete: ['{'a' * 20}'], exp: 0}}));"
    ausgabe = subprocess.run(["node", "--input-type=module", "-e", skript], capture_output=True, text=True, timeout=60, env={**os.environ, "JON_LIZENZ_SCHLUESSEL": privat})
    assert ausgabe.returncode == 0, ausgabe.stderr
    inhalt = lesen(ausgabe.stdout, OEFFENTLICH)
    assert inhalt["stufe"] == "premium" and inhalt["geraete"] == ["a" * 20] and inhalt["iat"] > 0


def test_lizenzserver_aufruf_folgt_weiterleitung_auf_die_hauptdomain(dienst, monkeypatch):
    import httpx

    gesehen = []

    def antworten(anfrage: httpx.Request) -> httpx.Response:
        gesehen.append((anfrage.method, str(anfrage.url), json.loads(anfrage.content)))
        if anfrage.url.host == "getjon.netlify.app":
            return httpx.Response(301, headers={"location": "https://getjon.info/.netlify/functions/premium-checkout"})
        return httpx.Response(200, json={"id": "cs_test_1", "url": "https://checkout.stripe.com/x"})

    echt = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: echt(transport=httpx.MockTransport(antworten), **kwargs))
    monkeypatch.setenv("JON_PREMIUM_URL", "https://getjon.netlify.app/.netlify/functions")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert asyncio.run(dienst.kaufen("monat"))["url"].startswith("https://checkout.stripe.com")
    finally:
        get_settings.cache_clear()
    assert [g[0] for g in gesehen] == ["POST", "POST"] and gesehen[1][2]["plan"] == "monat"


def test_ohne_netz_kommt_eine_klare_meldung(dienst, monkeypatch):
    import httpx

    def kaputt(anfrage):
        raise httpx.ConnectError("keine Verbindung")

    echt = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: echt(transport=httpx.MockTransport(kaputt), **kwargs))
    with pytest.raises(ConnectionError, match="nicht erreichbar"):
        asyncio.run(dienst.kaufen("monat"))
