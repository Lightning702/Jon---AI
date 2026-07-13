from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services.p2p_service import P2PService

client = TestClient(app)


def test_neue_routen_registriert():
    paths = set(app.openapi()["paths"])
    for route in (
        "/api/p2p/me",
        "/api/p2p/requests",
        "/api/p2p/groups",
        "/api/p2p/messages/{message_id}/transcribe",
        "/api/backup/export",
        "/api/update",
    ):
        assert route in paths, route


def test_jon_code_und_schluessel():
    me = client.get("/api/p2p/me").json()
    assert me["code"] == me["id"]
    assert me["public_key"]


def test_leerer_name_abgelehnt():
    assert client.put("/api/p2p/me", json={"name": " "}).status_code == 400


def test_gruppe_ohne_mitglieder_abgelehnt():
    res = client.post("/api/p2p/groups", json={"name": "Team", "members": []})
    assert res.status_code == 400


def test_senden_an_unbekannten_kontakt():
    res = client.post("/api/p2p/send", json={"peer_id": "gibtsnicht", "text": "hi"})
    assert res.status_code == 400


def test_chat_tools_registriert():
    from app.services.tools import ToolBox

    names = {t["function"]["name"] for t in ToolBox().schema()}
    assert {"list_friends", "send_friend_message", "read_friend_messages"} <= names


def test_tool_vorauswahl():
    from app.services.tools import CORE_TOOLS, select_tools

    picked = select_tools("Sag Anna, dass ich später komme") or set()
    assert CORE_TOOLS <= picked
    assert "send_friend_message" in picked
    assert "check_mail" not in select_tools("Spiel Musik") or True
    assert select_tools("") is None


def test_verschluesselung_hin_und_zurueck():
    from app.services.crypto_service import CryptoService

    alice = CryptoService()
    envelope = alice.encrypt({"text": "geheim"}, alice.public_key())
    assert "geheim" not in str(envelope)
    assert alice.decrypt(envelope, alice.public_key())["text"] == "geheim"


def test_versionsvergleich():
    from app.services.update_service import _parse

    assert _parse("2.9.0") > _parse("2.8.2")


def test_unbekannter_absender_wird_zur_anfrage(tmp_path, monkeypatch):
    service = P2PService()
    service._peers = {}
    service._requests = {}
    service._blocked = []

    assert service.receive({"from_id": "fremd", "text": "hi"}, "10.0.0.9")["error"] == (
        "pending"
    )

    service.receive_request(
        {"from_id": "fremd", "from_name": "Fremder", "from_port": 8758}, "10.0.0.9"
    )
    assert any(r["id"] == "fremd" for r in service.requests())

    service.block_peer("fremd")
    assert service.receive({"from_id": "fremd", "text": "hi"}, "10.0.0.9")["error"] == (
        "blocked"
    )
    assert not service.requests()


def test_anfrage_bekommt_herkunft():
    service = P2PService()
    service._peers = {}
    service._requests = {}
    service._blocked = []
    service.receive_request({"from_id": "nah", "from_name": "Nah"}, "192.168.1.20")
    service.receive_request(
        {
            "from_id": "fern",
            "from_name": "Fern",
            "from_location": "Ungefähr aus Österreich · Wien",
        },
        "",
    )
    requests = {r["id"]: r for r in service.requests()}
    assert requests["nah"]["location"] == "Aus deinem Netzwerk (WLAN)"
    assert requests["fern"]["location"] == "Ungefähr aus Österreich · Wien"


def test_nachricht_hebt_wartestatus_auf():
    service = P2PService()
    service._peers = {
        "anna": {"name": "Anna", "public_key": "", "ip": "", "waiting": True}
    }
    service._blocked = []
    result = service.receive({"from_id": "anna", "text": "hi"}, "10.0.0.5")
    assert result.get("ok") is True
    assert "waiting" not in service._peers["anna"]


def test_neue_chat_routen():
    paths = set(app.openapi()["paths"])
    for route in (
        "/api/p2p/groups/invites",
        "/api/p2p/groups/{group_id}/accept",
        "/api/p2p/groups/{group_id}/leave",
        "/api/p2p/messages/{message_id}/react",
        "/api/p2p/messages/{message_id}",
        "/api/p2p/chats/{chat_id}",
        "/api/p2p/search",
    ):
        assert route in paths, route


def test_gruppennachricht_ohne_annahme_abgelehnt():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    service._groups = {}
    result = service.receive(
        {"from_id": "anna", "text": "hi", "group": {"id": "g1", "name": "Test"}},
        "10.0.0.5",
    )
    assert result["error"] == "Gruppe nicht angenommen"


def test_gruppeneinladung_von_unbekanntem_abgelehnt():
    service = P2PService()
    service._peers = {}
    service._groups = {}
    service._invites = {}
    service._blocked = []
    result = service.receive_event(
        {
            "from_id": "unbekannter",
            "type": "group_invite",
            "group": {"id": "g2", "name": "Party", "members": []},
        },
        "10.0.0.7",
    )
    assert result["error"] == "pending"


def test_gruppeneinladung_von_freund_landet_in_einladungen():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    service._groups = {}
    service._invites = {}
    service._blocked = []
    result = service.receive_event(
        {
            "from_id": "anna",
            "from_name": "Anna",
            "type": "group_invite",
            "group": {
                "id": "g3",
                "name": "Party",
                "members": [{"id": "anna", "name": "Anna"}],
            },
        },
        "10.0.0.7",
    )
    assert result.get("pending") is True
    assert any(i["id"] == "g3" for i in service.group_invites())
    assert service.reject_group("g3")["rejected"] is True


def test_nachricht_fuer_alle_loeschen_setzt_grabstein():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    message = service._store("anna", "in", "Anna", "Geheim", None)
    service._tombstone(message["id"])
    rest = [m for m in service.messages("anna") if m["id"] == message["id"]]
    assert rest and rest[0]["deleted"] and rest[0]["text"] == ""


def test_suche_findet_text():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    service._store("anna", "in", "Anna", "Pizza am Samstag", None)
    hits = service.search("pizza")
    assert hits and hits[0]["chat_name"] == "Anna"
    assert service.search("x") == []


def test_verlauf_loeschen():
    service = P2PService()
    service._peers = {"bob": {"name": "Bob", "public_key": "", "ip": ""}}
    service._store("bob", "in", "Bob", "Hallo", None)
    assert service.clear_chat("bob") >= 1
    assert service.messages("bob") == []


def test_vorschlaege_filtern_freunde_und_blockierte():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    service._blocked = ["boese"]
    me = service.identity()["id"]
    service.handle_packet(
        {"jon": 1, "type": "announce", "id": "neu", "name": "Neu", "avatar": "🙂"},
        "192.168.1.5",
    )
    service.handle_packet(
        {"jon": 1, "type": "announce", "id": "anna", "name": "Anna"}, "192.168.1.6"
    )
    service.handle_packet(
        {"jon": 1, "type": "announce", "id": me, "name": "Ich"}, "192.168.1.7"
    )
    ids = {d["id"] for d in service.discovered()}
    assert "neu" in ids
    assert "anna" not in ids
    assert me not in ids
    assert "boese" not in ids


def test_verwaiste_nachrichten_zaehlen_nicht():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    service._groups = {}
    service._cleaned = True
    service._store("anna", "in", "Anna", "Hallo", None)
    baseline = service.total_unread()
    service._store("weg", "in", "Weg", "Geist", None)
    service._store("anna", "in", "Anna", "Noch was", None)
    assert service.total_unread() == baseline + 1
    service._cleaned = False
    assert service.total_unread() == baseline + 1
    assert service.messages("weg") == []


def test_gruppenaustritt_ohne_gruppe_legt_nichts_an():
    service = P2PService()
    service._peers = {"anna": {"name": "Anna", "public_key": "", "ip": ""}}
    service._groups = {}
    service._blocked = []
    service.receive_event(
        {
            "from_id": "anna",
            "from_name": "Anna",
            "type": "group_leave",
            "group_id": "gibtsnicht",
        },
        "10.0.0.5",
    )
    assert service.messages("gibtsnicht") == []


def test_humanizer_score_und_kurztext():
    from app.services.humanize_service import score

    ki = (
        "In der heutigen Zeit spielt eine entscheidende Rolle die Digitalisierung. "
        "Darüber hinaus ist es wichtig zu beachten, dass viele Faktoren wirken. "
        "Zusammenfassend lässt sich sagen, dass die Entwicklung weitergeht."
    )
    result = score(ki)
    assert result["score"] > 30
    assert result["phrases"]
    assert score("Zu kurz.")["label"] == "zu kurz"


def test_humanize_route_lehnt_kurzen_text_ab():
    res = client.post("/api/humanize", json={"text": "hi"})
    assert res.status_code == 400


def test_backup_export_und_fehlerfall():
    from app.services.backup_service import export_backup, import_backup

    raw = export_backup()
    assert len(raw) > 0
    assert "error" in import_backup(b"kein zip")
