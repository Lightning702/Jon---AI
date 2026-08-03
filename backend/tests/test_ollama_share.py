from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.api.p2p_routes import create_chat_app
from app.main import app
from app.providers.base import ChatMessage, ChatRequest, ProviderError
from app.providers.ollama_provider import OllamaProvider
from app.services import ollama_share_service as share_mod
from app.services import ollama_service as os_mod
from app.services.ollama_share_service import (
    OllamaShareService,
    ShareError,
    parse_invite,
)

client = TestClient(app)


@pytest.fixture
def shares(tmp_path, monkeypatch):
    monkeypatch.setattr(share_mod, "SHARE_FILE", tmp_path / "ollama_share.json")
    made = OllamaShareService()
    monkeypatch.setattr(share_mod, "_service", made)
    return made


@pytest.fixture
def ollama(tmp_path, monkeypatch):
    monkeypatch.setattr(os_mod, "OLLAMA_FILE", tmp_path / "ollama.json")
    made = os_mod.OllamaService()
    monkeypatch.setattr(os_mod, "_service", made)
    return made


@pytest.fixture
def host(shares):
    return TestClient(create_chat_app())


def _patch_client(monkeypatch, handler):
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def _ndjson(lines: list[dict]) -> bytes:
    return "".join(json.dumps(line) + "\n" for line in lines).encode("utf-8")


def test_freigabe_ist_zuerst_aus(shares):
    share = shares.share()
    assert share["enabled"] is False
    assert share["visibility"] == "private"
    assert len(share["code"]) == 8
    assert share["link"].startswith("jon://ollama/")


def test_einladungslink_wird_zerlegt():
    assert parse_invite("AB39KD12") == ("AB39KD12", "", 0)
    assert parse_invite("ab39kd12@192.168.1.50:8758") == (
        "AB39KD12",
        "192.168.1.50",
        8758,
    )
    assert parse_invite("jon://ollama/AB39KD12@10.0.0.5:9000") == (
        "AB39KD12",
        "10.0.0.5",
        9000,
    )
    with pytest.raises(ShareError):
        parse_invite("nein danke!")


def test_privat_laesst_niemanden_herein(shares):
    shares.update_share({"enabled": True, "visibility": "private"})
    assert shares.info() == {"available": False}
    with pytest.raises(ShareError):
        shares.join({"code": shares.share()["code"], "name": "Anna"}, "10.0.0.9")


def test_ausgeschaltete_freigabe_laesst_niemanden_herein(shares):
    shares.update_share({"visibility": "public"})
    with pytest.raises(ShareError):
        shares.join({"code": shares.share()["code"], "name": "Anna"}, "10.0.0.9")


def test_oeffentlich_gibt_token_und_zeigt_benutzer(shares):
    shares.update_share({"enabled": True, "visibility": "public", "name": "Felix PC"})
    result = shares.join(
        {"code": shares.share()["code"], "name": "Anna", "user_id": "abc"}, "10.0.0.9"
    )
    assert result["token"]
    assert result["name"] == "Felix PC"
    users = shares.users()
    assert len(users) == 1
    assert users[0]["user"] == "Anna"
    assert users[0]["address"] == "10.0.0.9"
    assert shares.authorize(result["token"])["id"] == result["grant_id"]


def test_falscher_code_wird_abgewiesen(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    with pytest.raises(ShareError):
        shares.join({"code": "ZZZZZZZZ", "name": "Anna"}, "10.0.0.9")


def test_nur_eingeladene_brauchen_eine_einladung(shares):
    shares.update_share({"enabled": True, "visibility": "invited"})
    with pytest.raises(ShareError):
        shares.join({"code": shares.share()["code"], "name": "Anna"}, "10.0.0.9")
    invite = shares.create_invite("Anna")
    assert invite["link"].startswith("jon://ollama/")
    result = shares.join({"code": invite["code"], "name": "Anna"}, "10.0.0.9")
    assert result["token"]
    with pytest.raises(ShareError):
        shares.join({"code": invite["code"], "name": "Bea"}, "10.0.0.10")


def test_widerruf_wirkt_sofort(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    token = shares.join({"code": shares.share()["code"], "name": "Anna"}, "10.0.0.9")[
        "token"
    ]
    assert shares.authorize(token)
    assert shares.revoke_all() == 1
    with pytest.raises(ShareError):
        shares.authorize(token)
    assert shares.users() == []


def test_widerruf_macht_alte_einladungen_nicht_wieder_gueltig(shares):
    shares.update_share({"enabled": True, "visibility": "invited"})
    invite = shares.create_invite("Anna")
    shares.join({"code": invite["code"], "name": "Anna"}, "10.0.0.9")
    shares.revoke_all()
    with pytest.raises(ShareError):
        shares.join({"code": invite["code"], "name": "Fremder"}, "10.0.0.11")


def test_einzelnen_benutzer_entfernen(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    code = shares.share()["code"]
    a = shares.join({"code": code, "name": "Anna"}, "10.0.0.9")
    b = shares.join({"code": code, "name": "Bea"}, "10.0.0.10")
    assert shares.remove_user(a["grant_id"]) is True
    with pytest.raises(ShareError):
        shares.authorize(a["token"])
    assert shares.authorize(b["token"])["user"] == "Bea"


def test_freigabe_abschalten_sperrt_alle_tokens(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    token = shares.join({"code": shares.share()["code"], "name": "Anna"}, "10.0.0.9")[
        "token"
    ]
    shares.update_share({"enabled": False})
    with pytest.raises(ShareError):
        shares.authorize(token)


def test_neuer_code_macht_den_alten_ungueltig(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    alt = shares.share()["code"]
    neu = shares.new_code()["code"]
    assert alt != neu
    with pytest.raises(ShareError):
        shares.join({"code": alt, "name": "Anna"}, "10.0.0.9")
    assert shares.join({"code": neu, "name": "Anna"}, "10.0.0.9")["token"]


def test_zu_viele_versuche_werden_gebremst(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    for _ in range(share_mod.JOIN_LIMIT):
        with pytest.raises(ShareError):
            shares.join({"code": "ZZZZZZZZ", "name": "Bot"}, "10.0.0.66")
    with pytest.raises(ShareError) as info:
        shares.join({"code": shares.share()["code"], "name": "Bot"}, "10.0.0.66")
    assert "Versuche" in str(info.value)


def test_sitzungen_und_letzte_aktivitaet(shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    grant = shares.join({"code": shares.share()["code"], "name": "Anna"}, "10.0.0.9")
    shares.touch(grant["grant_id"], "llama3.2", 1)
    user = shares.users()[0]
    assert user["model"] == "llama3.2"
    assert user["sessions"] == 1
    assert user["state"] == "aktiv"
    assert user["requests"] == 1
    assert user["last_activity"]
    shares.touch(grant["grant_id"], "llama3.2", -1)
    assert shares.users()[0]["state"] == "verbunden"


def test_endpunkt_ohne_token_gibt_401(host, shares):
    shares.update_share({"enabled": True, "visibility": "public"})
    assert host.get("/share/api/tags").status_code == 401
    assert host.get("/share/api/version").status_code == 401
    assert host.post("/share/api/chat", json={"model": "x"}).status_code == 401
    assert (
        host.get("/share/api/tags", headers={"Authorization": "Bearer falsch"}).status_code
        == 401
    )


def test_info_verraet_nichts_wenn_privat(host, shares):
    assert host.get("/share/info").json() == {"available": False}
    shares.update_share({"enabled": True, "visibility": "public", "name": "Felix PC"})
    info = host.get("/share/info").json()
    assert info["available"] is True
    assert info["name"] == "Felix PC"


def test_beitritt_und_modelle_ueber_http(host, shares, ollama, monkeypatch):
    shares.update_share({"enabled": True, "visibility": "public"})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})
        return httpx.Response(200, json={"version": "0.12.0"})

    _patch_client(monkeypatch, handler)
    joined = host.post(
        "/share/join", json={"code": shares.share()["code"], "name": "Anna"}
    )
    assert joined.status_code == 200
    token = joined.json()["token"]
    head = {"Authorization": f"Bearer {token}"}
    tags = host.get("/share/api/tags", headers=head)
    assert tags.status_code == 200
    assert tags.json()["models"] == [{"name": "llama3.2"}]
    assert host.get("/share/api/version", headers=head).json()["version"] == "0.12.0"


def test_chat_wird_an_den_lokalen_ollama_weitergereicht(
    host, shares, ollama, monkeypatch
):
    shares.update_share({"enabled": True, "visibility": "public"})
    gesehen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        gesehen["path"] = request.url.path
        gesehen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            content=_ndjson([{"message": {"content": "Hallo"}, "done": True}]),
        )

    _patch_client(monkeypatch, handler)
    token = host.post(
        "/share/join", json={"code": shares.share()["code"], "name": "Anna"}
    ).json()["token"]
    answer = host.post(
        "/share/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "llama3.2", "messages": [{"role": "user", "content": "Hi"}]},
    )
    assert answer.status_code == 200
    assert "Hallo" in answer.text
    assert gesehen["path"] == "/api/chat"
    assert gesehen["body"]["model"] == "llama3.2"
    assert shares.users()[0]["model"] == "llama3.2"


def test_gast_kann_den_speicher_des_gastgebers_nicht_sprengen(
    host, shares, ollama, monkeypatch
):
    shares.update_share({"enabled": True, "visibility": "public"})
    ollama.update({"context_length": 8192, "max_tokens": 4096, "keep_alive": "10m"})
    gesehen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        gesehen.update(json.loads(request.content))
        return httpx.Response(
            200, content=_ndjson([{"message": {"content": "ok"}, "done": True}])
        )

    _patch_client(monkeypatch, handler)
    token = host.post(
        "/share/join", json={"code": shares.share()["code"], "name": "Anna"}
    ).json()["token"]
    host.post(
        "/share/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Hi"}],
            "keep_alive": "-1",
            "options": {
                "num_ctx": 1000000,
                "num_predict": 999999,
                "temperature": 0.2,
                "top_k": 7,
            },
        },
    )
    assert gesehen["options"]["num_ctx"] == 8192
    assert gesehen["options"]["num_predict"] == 4096
    assert gesehen["options"]["temperature"] == 0.2
    assert gesehen["options"]["top_k"] == 7
    assert gesehen["keep_alive"] == "10m"


def test_unsinnige_anfrage_wird_abgewiesen(host, shares, ollama):
    shares.update_share({"enabled": True, "visibility": "public"})
    token = host.post(
        "/share/join", json={"code": shares.share()["code"], "name": "Anna"}
    ).json()["token"]
    answer = host.post(
        "/share/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"messages": []},
    )
    assert answer.status_code == 400


def test_widerrufener_zugriff_wird_beim_chat_geblockt(host, shares, ollama):
    shares.update_share({"enabled": True, "visibility": "public"})
    token = host.post(
        "/share/join", json={"code": shares.share()["code"], "name": "Anna"}
    ).json()["token"]
    shares.revoke_all()
    answer = host.post(
        "/share/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "llama3.2", "messages": []},
    )
    assert answer.status_code == 401


def _remote(shares, models=("llama3.2",)):
    return shares.store_remote(
        {
            "code": "AB39KD12",
            "host": "192.168.1.50",
            "port": 8758,
            "base": "http://192.168.1.50:8758",
            "token": "geheim",
            "grant_id": "g1",
            "name": "Felix PC",
            "description": "",
            "owner": "Felix",
            "added_at": "",
            "last_ok": "",
            "models": list(models),
            "error": "",
        }
    )


def test_fremdserver_erscheint_in_der_modellauswahl(shares, ollama, monkeypatch):
    _remote(shares)
    ollama.update({"enabled": False})
    provider = OllamaProvider()
    assert provider.available() is True
    assert asyncio.run(provider.list_models()) == ["share:AB39KD12/llama3.2"]


def test_chat_geht_authentifiziert_an_den_fremdserver(shares, ollama, monkeypatch):
    _remote(shares)
    gesehen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        gesehen["url"] = str(request.url)
        gesehen["auth"] = request.headers.get("authorization")
        gesehen["body"] = json.loads(request.content)
        return httpx.Response(
            200, content=_ndjson([{"message": {"content": "Moin"}, "done": True}])
        )

    _patch_client(monkeypatch, handler)
    provider = OllamaProvider()
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        model="share:AB39KD12/llama3.2",
        temperature=0.3,
        top_p=0.8,
    )

    async def run():
        return [chunk async for chunk in provider.stream(request)]

    chunks = asyncio.run(run())
    assert gesehen["url"] == "http://192.168.1.50:8758/share/api/chat"
    assert gesehen["auth"] == "Bearer geheim"
    assert gesehen["body"]["model"] == "llama3.2"
    assert gesehen["body"]["options"]["top_k"] == 40
    assert gesehen["body"]["options"]["temperature"] == 0.3
    assert "".join(c.delta for c in chunks if c.kind == "content") == "Moin"


def test_widerruf_meldet_sich_beim_gast_verstaendlich(shares, ollama, monkeypatch):
    _remote(shares)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Zugriff widerrufen"})

    _patch_client(monkeypatch, handler)
    provider = OllamaProvider()
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        model="share:AB39KD12/llama3.2",
    )

    async def run():
        return [chunk async for chunk in provider.stream(request)]

    with pytest.raises(ProviderError) as info:
        asyncio.run(run())
    assert "widerrufen" in str(info.value).lower()


def test_getrennter_server_gibt_klare_meldung(shares, ollama):
    provider = OllamaProvider()
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        model="share:WEGWEG12/llama3.2",
    )

    async def run():
        return [chunk async for chunk in provider.stream(request)]

    with pytest.raises(ProviderError) as info:
        asyncio.run(run())
    assert "nicht mehr verbunden" in str(info.value)


def test_verbindung_speichern_und_trennen(shares, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/share/join":
            return httpx.Response(
                200,
                json={
                    "token": "t1",
                    "grant_id": "g1",
                    "name": "Felix PC",
                    "description": "Grosse Grafikkarte",
                    "owner": "Felix",
                },
            )
        assert request.headers.get("authorization") == "Bearer t1"
        return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})

    _patch_client(monkeypatch, handler)
    entry = asyncio.run(shares.connect("AB39KD12@192.168.1.50:8758"))
    assert entry["name"] == "Felix PC"
    assert "token" not in entry
    assert shares.remote_models() == ["share:AB39KD12/llama3.2"]
    assert shares.forget_remote("AB39KD12") is True
    assert shares.remotes() == []


def test_verbinden_ohne_adresse_und_ohne_fund_meldet_sich(shares, monkeypatch):
    async def nothing(code, timeout=2.0):
        return None

    monkeypatch.setattr(shares, "discover", nothing)
    with pytest.raises(ShareError) as info:
        asyncio.run(shares.connect("AB39KD12"))
    assert "im Netzwerk gefunden" in str(info.value)


def test_netzwerksuche_antwortet_nur_bei_passendem_code(shares):
    assert shares.answer_query("EGAL") is None
    shares.update_share({"enabled": True, "visibility": "public"})
    code = shares.share()["code"]
    assert shares.answer_query("ZZZZZZZZ") is None
    reply = shares.answer_query(code)
    assert reply is not None
    assert reply["code"] == code
    assert reply["port"] == shares._port()
    shares.update_share({"visibility": "private"})
    assert shares.answer_query(code) is None


def test_netzwerksuche_kennt_offene_einladungen(shares):
    shares.update_share({"enabled": True, "visibility": "invited"})
    invite = shares.create_invite("Anna")
    assert shares.answer_query(invite["code"]) is not None
    shares.join({"code": invite["code"], "name": "Anna"}, "10.0.0.9")
    assert shares.answer_query(invite["code"]) is None


def test_geteilter_server_wird_ein_eigener_anbieter(shares, ollama, monkeypatch):
    monkeypatch.setattr(share_mod, "_service", shares)
    _remote(shares, models=("llama3.2", "mistral"))
    shares.update_remote("AB39KD12", {"model": "llama3.2", "owner": "Felix"})
    eintraege = shares.providers()
    assert eintraege == [
        {
            "provider": "share:AB39KD12",
            "label": "Ollama von Felix",
            "owner": "Felix",
            "model": "llama3.2",
        }
    ]
    liste = client.get("/api/providers").json()
    geteilt = [p for p in liste if p["provider"] == "share:AB39KD12"]
    assert geteilt and geteilt[0]["label"] == "Ollama von Felix"
    assert geteilt[0]["models"] == ["llama3.2"]
    assert geteilt[0]["locked"] is True
    assert geteilt[0]["configured"] is True


def test_anbieter_der_freigabe_waehlt_das_geteilte_modell(shares, ollama, monkeypatch):
    monkeypatch.setattr(share_mod, "_service", shares)
    _remote(shares, models=("llama3.2", "mistral"))
    shares.update_remote("AB39KD12", {"model": "mistral"})
    from app.schemas import ChatIn, MessageIn
    from app.services.chat_service import ChatService

    payload = ChatIn(
        messages=[MessageIn(role="user", content="Hi")],
        provider="share:AB39KD12",
        model="egal",
        persist=False,
    )
    assert ChatService().resolve(payload) == ("ollama", "share:AB39KD12/mistral")


def test_gastgeber_nennt_sein_geteiltes_modell(host, shares, ollama, monkeypatch):
    shares.update_share({"enabled": True, "visibility": "public"})
    ollama.update({"model": "llama3.2"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})

    _patch_client(monkeypatch, handler)
    joined = host.post(
        "/share/join", json={"code": shares.share()["code"], "name": "Anna"}
    ).json()
    assert joined["model"] == "llama3.2"
    tags = host.get(
        "/share/api/tags", headers={"Authorization": f"Bearer {joined['token']}"}
    ).json()
    assert tags["model"] == "llama3.2"


def test_api_endpunkte_der_freigabe(shares):
    assert client.get("/api/ollama/share").status_code == 200
    res = client.put(
        "/api/ollama/share",
        json={"enabled": True, "visibility": "public", "name": "Mein PC"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Mein PC"
    assert client.put("/api/ollama/share", json={"visibility": "quatsch"}).status_code == 400
    invite = client.post("/api/ollama/share/invites", json={"label": "Anna"}).json()
    assert invite["code"]
    assert client.delete(f"/api/ollama/share/invites/{invite['code']}").json()["deleted"]
    assert client.get("/api/ollama/share/users").json() == []
    assert client.post("/api/ollama/share/revoke").json()["revoked"] == 0
    assert client.get("/api/ollama/remote").json() == []
    assert client.post("/api/ollama/remote", json={"code": "!!"}).status_code == 400
    alt = client.get("/api/ollama/share").json()["share"]["code"]
    assert client.post("/api/ollama/share/code").json()["code"] != alt
