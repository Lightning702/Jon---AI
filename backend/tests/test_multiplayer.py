from __future__ import annotations

import asyncio
import json

import pytest

from app.services import multiplayer_service as mp


class FakeTransport(mp.Transport):
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False

    async def send(self, payload: dict) -> None:
        self.sent.append(json.loads(json.dumps(payload)))

    async def close(self) -> None:
        self.closed = True

    def last(self, kind: str) -> dict | None:
        for entry in reversed(self.sent):
            if entry.get("t") == kind:
                return entry
        return None

    def all_of(self, kind: str) -> list[dict]:
        return [e for e in self.sent if e.get("t") == kind]


@pytest.fixture()
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "MP_DIR", tmp_path / "multiplayer")
    return mp.MultiplayerService()


async def _pair(service: mp.MultiplayerService, game: str = "blockwelt"):
    host_transport = FakeTransport()
    guest_transport = FakeTransport()
    lobby, host = service.create_lobby(game, "Host", "gold", seed=42, max_players=2)
    await service.attach(lobby, host, host_transport)
    _, guest = service.join_lobby(lobby.code, "Gast", "blau")
    await service.attach(lobby, guest, guest_transport)
    return lobby, host, guest, host_transport, guest_transport


def test_code_format_und_eindeutigkeit(service):
    codes = set()
    for _ in range(60):
        lobby, _ = service.create_lobby("blockwelt", "A")
        assert len(lobby.code) == mp.CODE_LENGTH
        assert all(c in mp.CODE_ALPHABET for c in lobby.code)
        assert "O" not in lobby.code and "0" not in lobby.code
        codes.add(lobby.code)
    assert len(codes) == 60


def test_join_mit_code_und_volle_lobby(service):
    lobby, _ = service.create_lobby("blockwelt", "Host", max_players=2)
    _, guest = service.join_lobby(lobby.code.lower(), "Gast")
    assert guest.slot == 1
    assert not guest.host
    with pytest.raises(ValueError):
        service.join_lobby(lobby.code, "Dritter")
    with pytest.raises(ValueError):
        service.join_lobby("XXXXXX", "Niemand")


def test_welcome_enthaelt_spawn_und_zustand(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        welcome = gt.last("welcome")
        assert welcome is not None
        assert welcome["player_id"] == guest.player_id
        assert welcome["lobby"]["code"] == lobby.code
        assert welcome["spawn"] != host.spawn
        assert welcome["protocol"] == mp.PROTOCOL_VERSION
        assert ht.last("lobby")["lobby"]["players"][1]["name"] == "Gast"

    asyncio.run(run())


def test_startablauf_wartet_auf_beide(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        await service.handle(lobby, host, {"t": "start"})
        assert ht.last("error")["code"] == "not_ready"
        await service.handle(lobby, guest, {"t": "ready", "value": True})
        await service.handle(lobby, host, {"t": "start"})
        assert lobby.phase == "loading"
        assert gt.last("start")["seed"] == 42
        await service.handle(lobby, host, {"t": "scene", "phase": "ready"})
        assert lobby.phase == "loading"
        assert gt.last("sync")["total"] == 2
        await service.handle(lobby, guest, {"t": "scene", "phase": "ready"})
        assert lobby.phase == "playing"
        assert ht.last("spawn") is not None
        assert gt.last("spawn") is not None

    asyncio.run(run())


def test_bewegung_wird_geprueft_und_korrigiert(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        base = dict(host.spawn)
        await service.handle(
            lobby, host, {"t": "input", "x": base["x"], "y": base["y"], "z": base["z"]}
        )
        await service.handle(
            lobby,
            host,
            {"t": "input", "x": base["x"] + 0.4, "y": base["y"], "z": base["z"], "anim": "walk"},
        )
        assert host.state["anim"] == "walk"
        assert ht.last("correct") is None
        await service.handle(
            lobby, host, {"t": "input", "x": base["x"] + 9000.0, "y": base["y"], "z": base["z"]}
        )
        assert ht.last("correct") is not None
        assert abs(host.state["x"] - (base["x"] + 0.4)) < 0.001

    asyncio.run(run())


def test_blockaenderung_nur_in_reichweite(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        host.state.update({"x": 10.0, "y": 40.0, "z": 10.0})
        ok = service._apply_act(
            lobby, host, {"kind": "block", "x": 11, "y": 40, "z": 10, "id": 3}
        )
        assert ok
        assert lobby.world["b:11,40,10"] == 3
        far = service._apply_act(
            lobby, host, {"kind": "block", "x": 900, "y": 40, "z": 10, "id": 3}
        )
        assert not far
        bad = service._apply_act(
            lobby, host, {"kind": "block", "x": 11, "y": 41, "z": 10, "id": 999}
        )
        assert not bad

    asyncio.run(run())


def test_interaktionen_landen_im_weltzustand(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service, "aetheria")
        lobby.phase = "playing"
        host.state.update({"x": 0.0, "y": 0.0, "z": 0.0})
        assert service._apply_act(lobby, host, {"kind": "door", "id": "12", "value": 1})
        assert service._apply_act(lobby, host, {"kind": "quest", "id": "2", "value": 3})
        assert service._apply_act(lobby, host, {"kind": "lever", "id": "a3", "value": True})
        assert lobby.world["door:12"] == 1
        assert lobby.world["quest:2"] == 3
        assert lobby.world["lever:a3"] is True
        assert not service._apply_act(lobby, host, {"kind": "door", "id": "12", "value": 1})
        assert not service._apply_act(lobby, host, {"kind": "unbekannt", "id": "1"})
        kinds = [e["kind"] for e in lobby.events]
        assert kinds.count("interact") == 3

    asyncio.run(run())


def test_snapshot_delta_und_ack(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        await service._tick_lobby(lobby)
        first = gt.last("snap")
        assert first["base"] == 0
        assert host.player_id in first["players"]
        await service.handle(lobby, guest, {"t": "ack", "snap": first["id"]})
        host.state["x"] = host.state["x"] + 1.0
        await service._tick_lobby(lobby)
        second = gt.last("snap")
        assert second["base"] == first["id"]
        assert list(second["players"]) == [host.player_id]
        assert set(second["players"][host.player_id]) == {"x"}
        assert "world" not in second

    asyncio.run(run())


def test_weltzustand_kommt_als_delta(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        await service._tick_lobby(lobby)
        snap = gt.last("snap")
        await service.handle(lobby, guest, {"t": "ack", "snap": snap["id"]})
        host.state.update({"x": 0.0, "y": 40.0, "z": 0.0})
        service._apply_act(lobby, host, {"kind": "block", "x": 1, "y": 40, "z": 0, "id": 9})
        await service._tick_lobby(lobby)
        delta = gt.last("snap")
        assert delta["world"] == {"b:1,40,0": 9}

    asyncio.run(run())


def test_ping_und_paketverlust(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        for _ in range(int(mp.TICK_HZ)):
            await service._tick_lobby(lobby)
        ping = ht.last("ping")
        assert ping is not None
        await service.handle(lobby, host, {"t": "pong", "s": ping["s"]})
        assert host.ping >= 0.0
        assert host.ping < 500.0
        assert 0.0 <= host.loss <= 100.0

    asyncio.run(run())


def test_reconnect_behaelt_spieler_und_welt(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        host.state.update({"x": 0.0, "y": 40.0, "z": 0.0})
        service._apply_act(lobby, host, {"kind": "block", "x": 1, "y": 40, "z": 0, "id": 12})
        token = guest.token
        await service.detach(lobby, guest)
        assert not guest.online
        assert guest.player_id in lobby.participants
        again = FakeTransport()
        pair = await service.handshake({"t": "hello", "token": token}, again)
        assert pair is not None
        assert pair[1].player_id == guest.player_id
        assert again.last("welcome")["state"]["world"]["b:1,40,0"] == 12

    asyncio.run(run())


def test_wiedereinstieg_im_laufenden_spiel_spawnt_sofort(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        guest.state.update({"x": 33.0, "y": 41.0, "z": -7.0, "yaw": 1.2})
        token = guest.token
        await service.detach(lobby, guest)
        again = FakeTransport()
        pair = await service.handshake({"t": "hello", "token": token}, again)
        assert pair is not None
        member = pair[1]
        assert again.last("welcome")["spawn"]["x"] == 33.0
        assert not member.loaded
        await service.handle(lobby, member, {"t": "scene", "phase": "ready"})
        spawn = again.last("spawn")
        assert spawn is not None
        assert spawn["resumed"] is True
        assert spawn["spawns"][member.player_id]["z"] == -7.0
        assert ht.last("spawn") is None

    asyncio.run(run())


def test_grace_zeit_entfernt_verlorene_spieler(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        await service.detach(lobby, guest)
        guest.dropped_at = mp._now() - mp.RECONNECT_GRACE - 1.0
        await service._tick_lobby(lobby)
        assert guest.player_id not in lobby.participants
        assert host.player_id in lobby.participants

    asyncio.run(run())


def test_host_wechselt_beim_verlassen(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        await service.handle(lobby, host, {"t": "leave"})
        assert guest.host
        assert lobby.owner == guest.player_id

    asyncio.run(run())


def test_szenenwechsel_ist_synchron(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        await service.handle(lobby, host, {"t": "scene", "phase": "request", "scene": "hoehle"})
        assert lobby.phase == "switching"
        assert gt.last("scene")["scene"] == "hoehle"
        await service.handle(lobby, host, {"t": "scene", "phase": "ready", "scene": "hoehle"})
        assert lobby.phase == "switching"
        await service.handle(lobby, guest, {"t": "scene", "phase": "ready", "scene": "hoehle"})
        assert lobby.phase == "playing"
        assert gt.last("spawn")["scene"] == "hoehle"

    asyncio.run(run())


def test_spielstand_wird_geteilt_und_gespeichert(service, tmp_path):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        ok = service._apply_act(
            lobby,
            host,
            {"kind": "checkpoint", "data": {"checkpoint": "bruecke", "quests": [1, 2]}},
        )
        assert ok
        assert lobby.save["checkpoint"] == "bruecke"
        stored = json.loads((mp.MP_DIR / f"{lobby.code}.json").read_text(encoding="utf-8"))
        assert stored["save"]["checkpoint"] == "bruecke"

    asyncio.run(run())


def test_neustart_stellt_sitzung_wieder_her(service, tmp_path, monkeypatch):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        host.state.update({"x": 5.0, "y": 40.0, "z": 5.0})
        service._apply_act(lobby, host, {"kind": "block", "x": 5, "y": 41, "z": 5, "id": 7})
        service._persist(lobby)
        code, token = lobby.code, guest.token
        fresh = mp.MultiplayerService()
        assert code in fresh._lobbies
        found = fresh.resume(token)
        assert found is not None
        assert found[0].world["b:5,41,5"] == 7
        assert len(found[0].participants) == 2

    asyncio.run(run())


def test_chat_hat_ratenbegrenzung(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        for i in range(12):
            await service.handle(lobby, host, {"t": "chat", "text": f"hallo {i}"})
        received = gt.all_of("chat")
        assert 0 < len(received) <= 6

    asyncio.run(run())


def test_zu_viele_verstoesse_werfen_raus(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        await service.handle(lobby, guest, {"t": "input", "x": 0.0, "y": 40.0, "z": 0.0})
        for _ in range(mp.MAX_VIOLATIONS + 4):
            await service.handle(
                lobby, guest, {"t": "input", "x": 5000.0, "y": 40.0, "z": 5000.0}
            )
        assert guest.player_id not in lobby.participants
        assert gt.last("kick") is not None

    asyncio.run(run())


def test_nur_host_darf_starten_und_schliessen(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        await service.handle(lobby, guest, {"t": "ready", "value": True})
        await service.handle(lobby, guest, {"t": "start"})
        assert lobby.phase == "lobby"
        await service.handle(lobby, guest, {"t": "close"})
        assert lobby.code in service._lobbies
        await service.handle(lobby, host, {"t": "close"})
        assert lobby.code not in service._lobbies
        assert ht.last("bye") is not None

    asyncio.run(run())


def test_handshake_erstellt_und_tritt_bei(service):
    async def run():
        first = FakeTransport()
        pair = await service.handshake(
            {"t": "create", "game": "aetheria", "name": "Felix", "seed": 7}, first
        )
        assert pair is not None
        lobby, host = pair
        assert lobby.game == "aetheria"
        code = first.last("welcome")["lobby"]["code"]
        second = FakeTransport()
        joined = await service.handshake({"t": "join", "code": code, "name": "Gast"}, second)
        assert joined is not None
        assert joined[0].code == code
        failed = FakeTransport()
        assert await service.handshake({"t": "join", "code": "ZZZZZZ"}, failed) is None
        assert failed.last("error")["code"] == "join"

    asyncio.run(run())


def test_lag_kompensation_nutzt_verlauf(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service, "aetheria")
        lobby.phase = "playing"
        host.ping = 120.0
        for step in range(6):
            await service.handle(
                lobby,
                host,
                {"t": "input", "x": float(step) * 0.5, "y": 0.0, "z": 0.0},
            )
            await asyncio.sleep(0.02)
        rewound = host.rewind(mp._now() - 0.12)
        assert rewound["x"] <= host.state["x"]
        assert service._apply_act(
            lobby, host, {"kind": "strike", "target": "wolf3", "damage": 40, "at": 1}
        )
        assert lobby.world["mob:wolf3"]["hp"] == 60.0
        assert lobby.events[-1]["kind"] == "strike"

    asyncio.run(run())


def test_emote_ueberlebt_bewegungspakete(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        base = dict(host.spawn)
        await service.handle(
            lobby, host, {"t": "input", "x": base["x"], "y": base["y"], "z": base["z"]}
        )
        await service.handle(lobby, host, {"t": "emote", "id": 4})
        assert host.state["emote"] == 4
        for step in range(5):
            await service.handle(
                lobby,
                host,
                {
                    "t": "input",
                    "x": base["x"] + 0.1 * step,
                    "y": base["y"],
                    "z": base["z"],
                    "anim": "walk",
                },
            )
        assert ht.last("correct") is None
        assert host.state["emote"] == 4
        assert host.state["hp"] == 100
        await service._tick_lobby(lobby)
        snap = gt.last("snap")
        assert snap["players"][host.player_id]["emote"] == 4
        await service.handle(
            lobby,
            host,
            {"t": "input", "x": base["x"] + 0.5, "y": base["y"], "z": base["z"], "emote": 0},
        )
        assert host.state["emote"] == 0
        await service.handle(lobby, host, {"t": "emote", "id": 9999})
        assert host.state["emote"] == 9999
        await service.handle(
            lobby,
            host,
            {"t": "input", "x": base["x"] + 0.6, "y": base["y"], "z": base["z"], "emote": 9999},
        )
        assert host.state["emote"] == 64

    asyncio.run(run())


def test_pause_erlaubt_keinen_sprung(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        await service.handle(lobby, host, {"t": "input", "x": 0.0, "y": 40.0, "z": 0.0})
        host.last_input = mp._now() - 30.0
        await service.handle(lobby, host, {"t": "input", "x": 4000.0, "y": 40.0, "z": 0.0})
        assert ht.last("correct") is not None
        assert host.state["x"] == 0.0
        host.last_input = mp._now() - 30.0
        await service.handle(lobby, host, {"t": "input", "x": 20.0, "y": 40.0, "z": 0.0})
        assert host.state["x"] == 20.0

    asyncio.run(run())


def test_blockstapel_wird_gebuendelt_uebernommen(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        host.state.update({"x": 0.0, "y": 40.0, "z": 0.0})
        cells = [[i, 40, 0, 9] for i in range(120)]
        assert service._apply_act(lobby, host, {"kind": "blocks", "cells": cells, "x": 0, "y": 40, "z": 0})
        assert lobby.world["b:119,40,0"] == 9
        assert len(lobby.world) == 120
        assert not service._apply_act(
            lobby, host, {"kind": "blocks", "cells": [[0, 0, 0, 1]] * (mp.MAX_BATCH_CELLS + 1)}
        )

    asyncio.run(run())


def test_effekte_gehen_nur_an_andere(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        await service.handle(
            lobby, host, {"t": "fx", "kind": "pearl", "data": {"x": 1, "y": 2, "z": 3}}
        )
        assert gt.last("fx")["data"]["z"] == 3
        assert gt.last("fx")["by"] == host.player_id
        assert ht.last("fx") is None
        await service.handle(lobby, host, {"t": "fx", "kind": "boese", "data": {}})
        assert len(gt.all_of("fx")) == 1

    asyncio.run(run())


def test_abgelehnte_aktion_meldet_koordinaten(service):
    async def run():
        lobby, host, guest, ht, gt = await _pair(service)
        lobby.phase = "playing"
        host.state.update({"x": 0.0, "y": 40.0, "z": 0.0})
        await service.handle(
            lobby, host, {"t": "act", "kind": "block", "x": 800, "y": 40, "z": 0, "id": 3}
        )
        reject = ht.last("reject")
        assert reject["kind"] == "block"
        assert reject["x"] == 800

    asyncio.run(run())


def test_rest_api_ist_in_der_echten_app_verdrahtet(monkeypatch, tmp_path):
    import httpx

    monkeypatch.setattr(mp, "MP_DIR", tmp_path / "multiplayer")
    monkeypatch.setattr(mp, "_service", None, raising=False)

    from app.main import create_app

    app = create_app()

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            info = await client.get("/api/mp/info")
            assert info.status_code == 200
            assert info.json()["tcp_port"] == 8759
            assert "blockwelt" in info.json()["games"]

            created = await client.post(
                "/api/mp/create", json={"game": "blockwelt", "name": "Felix"}
            )
            assert created.status_code == 200
            code = created.json()["code"]
            assert len(code) == mp.CODE_LENGTH
            assert created.json()["token"]

            joined = await client.post("/api/mp/join", json={"code": code, "name": "Jonas"})
            assert joined.status_code == 200

            lobby = await client.get(f"/api/mp/lobby/{code}")
            assert lobby.status_code == 200
            assert len(lobby.json()["players"]) == 2

            assert (await client.get("/api/mp/lobby/ZZZZZZ")).status_code == 404
            assert (
                await client.post("/api/mp/create", json={"game": "quake", "name": "X"})
            ).status_code == 400

            status = await client.get("/api/mp/status")
            assert status.status_code == 200
            assert status.json()["lobbies"] >= 1

    asyncio.run(run())


def test_koop_port_liefert_lobby_und_spielseite(monkeypatch, tmp_path):
    import httpx

    monkeypatch.setattr(mp, "MP_DIR", tmp_path / "multiplayer")
    monkeypatch.setattr(mp, "_service", None, raising=False)

    from app.api.multiplayer_routes import MP_WS_PORT, create_coop_app

    app = create_coop_app()

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://freund") as client:
            info = (await client.get("/api/mp/info")).json()
            assert info["ws_port"] == MP_WS_PORT
            assert info["invite_host"]

            created = await client.post("/api/mp/create", json={"game": "blockwelt", "name": "Host"})
            assert created.status_code == 200
            code = created.json()["code"]
            joined = await client.post("/api/mp/join", json={"code": code, "name": "Gast"})
            assert joined.status_code == 200
            assert len(joined.json()["lobby"]["players"]) == 2

            page = await client.get("/blockwelt")
            assert page.status_code == 200
            assert "MP_WS_PORT" in page.text

            assert (await client.get("/api/settings")).status_code == 404
            assert (await client.get("/api/chat")).status_code == 404

    asyncio.run(run())


def test_koop_port_ist_getrennt_vom_haupt_port():
    from app.api.multiplayer_routes import MP_TCP_PORT, MP_WS_PORT
    from app.core.config import get_settings

    ports = {get_settings().port, MP_TCP_PORT, MP_WS_PORT}
    assert len(ports) == 3


def test_fehlgeschlagener_handshake_nennt_den_grund(service):
    async def run():
        unknown = FakeTransport()
        assert await service.handshake({"t": "quatsch"}, unknown) is None
        assert unknown.last("error")["code"] == "handshake"

        stale = FakeTransport()
        assert await service.handshake({"t": "hello", "token": "weg"}, stale) is None
        assert stale.last("error")["code"] == "resume"

        wrong = FakeTransport()
        assert await service.handshake({"t": "create", "game": "quake"}, wrong) is None
        assert wrong.last("error")["code"] == "create"

    asyncio.run(run())


def test_zweiter_versuch_auf_derselben_leitung_klappt(service):
    async def run():
        transport = FakeTransport()
        lobby, _ = service.create_lobby("blockwelt", "Host", max_players=2)
        assert await service.handshake({"t": "join", "code": "ZZZZZZ"}, transport) is None
        assert transport.last("error")["code"] == "join"
        pair = await service.handshake({"t": "join", "code": lobby.code, "name": "Gast"}, transport)
        assert pair is not None
        assert transport.last("welcome")["lobby"]["code"] == lobby.code

    asyncio.run(run())


def _lan_module():
    from app.services import coop_lan_service as lan

    return lan


def _fake_cards(monkeypatch, cards):
    lan = _lan_module()
    monkeypatch.setattr(lan, "_cache", {"at": 0.0, "items": []})
    monkeypatch.setattr(lan, "_windows_interfaces", lambda: list(cards))
    monkeypatch.setattr(lan, "_fallback_interfaces", lambda: list(cards))
    return lan


def test_lan_adresse_bevorzugt_echte_netzwerkkarte(monkeypatch):
    cards = [
        {"ip": "192.168.56.1", "prefix": 24, "name": "Ethernet 3", "type": 6, "up": True,
         "gateway": "", "dhcp": False},
        {"ip": "10.2.0.2", "prefix": 32, "name": "ProTUN", "type": 53, "up": True,
         "gateway": "", "dhcp": False},
        {"ip": "10.0.0.253", "prefix": 24, "name": "WLAN", "type": 71, "up": True,
         "gateway": "10.0.0.138", "dhcp": True},
        {"ip": "192.168.176.1", "prefix": 20, "name": "vEthernet (Default Switch)", "type": 6,
         "up": True, "gateway": "", "dhcp": False},
    ]
    lan = _fake_cards(monkeypatch, cards)

    assert lan.invite_host() == "10.0.0.253"
    assert lan.local_addresses()[0] == "10.0.0.253"
    assert lan.address_for_peer("10.0.0.42") == "10.0.0.253"
    assert lan.address_for_peer("192.168.56.9") == "192.168.56.1"
    assert "10.0.0.255" in lan.broadcast_targets()
    assert "255.255.255.255" in lan.broadcast_targets()


def _freier_udp_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_beacon_findet_lobby_und_listet_offene_spiele(monkeypatch, tmp_path):
    lan = _lan_module()
    monkeypatch.setattr(lan, "DISCOVERY_PORT", _freier_udp_port())
    monkeypatch.setattr(lan, "broadcast_targets", lambda: ["127.0.0.1"])
    monkeypatch.setattr(lan, "address_for_peer", lambda peer: "127.0.0.1")
    monkeypatch.setattr(lan, "local_addresses", lambda: ["127.0.0.1"])
    monkeypatch.setattr(mp, "MP_DIR", tmp_path / "multiplayer")

    gastgeber = mp.MultiplayerService()
    gast = mp.MultiplayerService()
    lobby, _ = gastgeber.create_lobby("echo", "Felix", max_players=4)

    async def run():
        server = lan.CoopBeacon()
        client = lan.CoopBeacon()
        server.bind(gastgeber, 8759, 8760)
        client.bind(gast, 8759, 8760)
        tasks = [
            asyncio.create_task(server.serve(8759, 8760)),
            asyncio.create_task(client.serve(8759, 8760)),
        ]
        await asyncio.sleep(0.3)
        try:
            assert server.findable and client.online
            found = await client.find(lobby.code, timeout=3.0)
            assert found is not None
            assert found["code"] == lobby.code
            assert found["tcp_port"] == 8759
            assert found["ws_port"] == 8760
            assert found["origin"] == "http://127.0.0.1:8760"
            assert found["host_name"] == "Felix"

            assert await client.find("ZZZZZZ", timeout=0.8) is None

            offen = await client.scan(timeout=1.0)
            assert [entry["code"] for entry in offen] == [lobby.code]
        finally:
            for task in tasks:
                task.cancel()

    asyncio.run(run())


def test_join_wird_zum_gastgeber_im_netzwerk_weitergeleitet(service, monkeypatch):
    async def fake_find(code, timeout=1.8):
        assert code == "AB39KD"
        return {
            "code": "AB39KD",
            "host": "10.0.0.7",
            "tcp_port": 8759,
            "ws_port": 8760,
            "origin": "http://10.0.0.7:8760",
        }

    monkeypatch.setattr(service, "find_remote", fake_find)

    async def run():
        transport = FakeTransport()
        assert await service.handshake({"t": "join", "code": "AB39KD"}, transport) is None
        weiter = transport.last("redirect")
        assert weiter["host"] == "10.0.0.7"
        assert weiter["tcp_port"] == 8759
        assert weiter["ws_port"] == 8760
        assert transport.redirected is True
        assert transport.last("error") is None

    asyncio.run(run())


def test_ohne_netzwerkfund_bleibt_es_beim_fehler(service):
    async def run():
        transport = FakeTransport()
        assert await service.handshake({"t": "join", "code": "ZZZZZZ"}, transport) is None
        assert transport.last("redirect") is None
        assert transport.last("error")["code"] == "join"
        assert transport.redirected is False

    asyncio.run(run())


def test_welcome_nennt_einladung_mit_adresse(service, monkeypatch):
    lan = _lan_module()
    monkeypatch.setattr(lan, "invite_host", lambda: "10.0.0.253")
    monkeypatch.setattr(lan, "local_addresses", lambda: ["10.0.0.253"])

    async def run():
        transport = FakeTransport()
        lobby, host = service.create_lobby("blockwelt", "Host")
        await service.attach(lobby, host, transport)
        welcome = transport.last("welcome")
        assert welcome["invite"] == f"{lobby.code}@10.0.0.253:8760"
        assert welcome["invite_tcp"] == f"{lobby.code}@10.0.0.253:8759"
        assert welcome["addresses"] == ["10.0.0.253"]

    asyncio.run(run())


def test_such_und_netzwerk_endpunkte(monkeypatch, tmp_path):
    import httpx

    monkeypatch.setattr(mp, "MP_DIR", tmp_path / "multiplayer")
    monkeypatch.setattr(mp, "_service", None, raising=False)

    from app.api import multiplayer_routes as routes

    lan = _lan_module()
    monkeypatch.setattr(
        routes, "firewall_state", lambda refresh=False: {"supported": True, "ok": False, "rules": []}
    )
    for modul in (routes, lan):
        monkeypatch.setattr(modul, "local_addresses", lambda: ["10.0.0.253"])
        monkeypatch.setattr(modul, "invite_host", lambda: "10.0.0.253")

    app = routes.create_coop_app()

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/mp/create", json={"game": "echo", "name": "Host"})
            code = created.json()["code"]

            hier = await client.get(f"/api/mp/find/{code}")
            assert hier.status_code == 200
            assert hier.json()["where"] == "local"
            assert hier.json()["invite"].endswith("@10.0.0.253:8760")

            assert (await client.get("/api/mp/find/ZZZZZZ")).status_code == 404

            scan = (await client.get("/api/mp/scan")).json()["lobbies"]
            assert [entry["code"] for entry in scan] == [code]
            assert scan[0]["local"] is True

            netz = (await client.get("/api/mp/network")).json()
            assert netz["firewall"]["ok"] is False
            assert netz["udp_port"] == routes.MP_UDP_PORT
            assert netz["addresses"] == ["10.0.0.253"]

    asyncio.run(run())


def test_koop_ports_sind_alle_verschieden():
    from app.api.multiplayer_routes import MP_TCP_PORT, MP_UDP_PORT, MP_WS_PORT
    from app.core.config import get_settings

    assert len({get_settings().port, MP_TCP_PORT, MP_WS_PORT, MP_UDP_PORT}) == 4


def test_spielprofile_grenzen_sich_ab():
    assert set(mp.GAMES) == {"blockwelt", "aetheria", "echo"}
    assert mp.GAMES["blockwelt"].edit_range >= 8.0
    assert mp.GAMES["echo"].max_speed < mp.GAMES["aetheria"].max_speed
    assert 0 in mp.GAMES["blockwelt"].block_ids
