from __future__ import annotations

import asyncio
import socket
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from app.services.phone import g711, sipmsg
from app.services.phone.audio import RATE_NET, SAMPLES_PER_FRAME, VoiceGate, resample
from app.services.phone.conversation import (
    _phone_style,
    split_sentences,
    wants_goodbye,
    wants_pause,
)
from app.services.phone.rtp import RtpSession, open_port, tone
from app.services.phone.sipmsg import (
    authorization_header,
    build_sdp,
    digest_response,
    parse_auth,
    parse_sdp,
    parse_uri,
)
from app.services.phone.stack import SipStack
from app.services.phone_service import PhoneService, next_occurrence, parse_when

VIENNA = ZoneInfo("Europe/Vienna")
CRLF = chr(13) + chr(10)


@pytest.fixture()
def service(tmp_path, monkeypatch):
    import app.services.phone_service as ps

    monkeypatch.setattr(ps, "CALLS_FILE", tmp_path / "phone_calls.json")
    monkeypatch.setattr(ps, "LOG_FILE", tmp_path / "phone_log.json")
    return ps.PhoneService()


def test_ulaw_roundtrip_bleibt_nah_am_original():
    original = tone(440, 0.05)
    decoded = g711.ulaw_decode(g711.ulaw_encode(original))
    assert decoded.size == original.size
    error = np.abs(decoded.astype(np.int32) - original.astype(np.int32))
    assert error.max() < 400


def test_alaw_und_ulaw_sind_unterschiedlich():
    original = tone(440, 0.02)
    assert g711.ulaw_encode(original) != g711.alaw_encode(original)
    assert g711.decode(g711.encode(original, 8), 8).size == original.size


def test_resample_haelt_die_laenge_ein():
    samples = tone(300, 0.1)
    up = resample(samples, RATE_NET, 16000)
    assert abs(up.size - samples.size * 2) <= 2
    down = resample(up, 16000, RATE_NET)
    assert abs(down.size - samples.size) <= 2


def test_sip_uri_parsen():
    uri = parse_uri('"Felix" <sip:jon-phone@192.168.0.5:5062;transport=udp>')
    assert uri.user == "jon-phone"
    assert uri.host == "192.168.0.5"
    assert uri.port == 5062
    assert uri.address == ("192.168.0.5", 5062)


def test_sip_nachricht_bauen_und_parsen():
    headers = [("Via", "SIP/2.0/UDP 10.0.0.1:5060;branch=z9hG4bKabc"), ("CSeq", "1 INVITE")]
    request = sipmsg.build_request("INVITE", "sip:a@b", headers, b"x", "application/sdp")
    parsed = sipmsg.parse(request.encode())
    assert parsed is not None
    assert parsed.method == "INVITE"
    assert parsed.cseq_method() == "INVITE"
    assert parsed.cseq_number() == 1
    assert parsed.body == b"x"


def test_digest_entspricht_rfc2617_beispiel():
    result = digest_response(
        "Mufasa",
        "Circle Of Life",
        "testrealm@host.com",
        "dcd98b7102dd2f0e8b11d0f600bfb0c093",
        "GET",
        "/dir/index.html",
        qop="auth",
        cnonce="0a4f113b",
        nc="00000001",
    )
    assert result == "6629fae49393a05397450978507c4ef1"


def test_authorization_header_ist_vollstaendig():
    challenge = parse_auth('Digest realm="jon", nonce="abc", algorithm=MD5, qop="auth"')
    header = authorization_header("jon-phone", "geheim", challenge, "REGISTER", "sip:jon")
    assert header.startswith("Digest ")
    for part in ("username=", "realm=", "nonce=", "response=", "qop=auth", "cnonce="):
        assert part in header


def test_sdp_bauen_und_wieder_lesen():
    body = build_sdp("192.168.0.10", 16400, [0, 8], 12345)
    parsed = parse_sdp(body)
    assert parsed["host"] == "192.168.0.10"
    assert parsed["port"] == 16400
    assert 0 in parsed["payloads"]
    assert 101 in parsed["payloads"]


def test_voice_gate_erkennt_sprache_und_pause():
    gate = VoiceGate(start_frames=2, end_frames=3)
    quiet = np.zeros(SAMPLES_PER_FRAME, dtype=np.int16)
    loud = (tone(400, 0.02, amplitude=0.5))[:SAMPLES_PER_FRAME]
    for _ in range(5):
        assert gate.feed(quiet) is None
    assert gate.feed(loud) is None
    assert gate.feed(loud) is None
    assert gate.talking
    result = None
    for _ in range(4):
        result = gate.feed(quiet)
        if result is not None:
            break
    assert result is not None
    assert result.size > 0
    assert not gate.talking


def test_voice_gate_ignoriert_dauerhafte_stille():
    gate = VoiceGate(start_frames=2, end_frames=3)
    quiet = np.zeros(SAMPLES_PER_FRAME, dtype=np.int16)
    for _ in range(50):
        assert gate.feed(quiet) is None
    assert gate.flush() is None


def test_parse_when_relative():
    base = datetime(2026, 8, 8, 12, 0, tzinfo=VIENNA)
    assert parse_when("in 20 Minuten", base) == base + timedelta(minutes=20)
    assert parse_when("in 2 Stunden", base) == base + timedelta(hours=2)
    assert parse_when("in einer minute", base) == base + timedelta(minutes=1)
    assert parse_when("jetzt", base) <= base + timedelta(seconds=10)


def test_parse_when_uhrzeit_und_tag():
    base = datetime(2026, 8, 8, 12, 0, tzinfo=VIENNA)
    heute = parse_when("heute um 18 Uhr", base)
    assert (heute.hour, heute.minute, heute.day) == (18, 0, 8)
    morgen = parse_when("morgen um 9 Uhr", base)
    assert (morgen.hour, morgen.day) == (9, 9)
    genau = parse_when("morgen um 15:30", base)
    assert (genau.hour, genau.minute, genau.day) == (15, 30, 9)


def test_parse_when_wochentag_ist_in_der_zukunft():
    base = datetime(2026, 8, 8, 12, 0, tzinfo=VIENNA)
    montag = parse_when("nächsten Montag um 17 Uhr", base)
    assert montag.weekday() == 0
    assert montag > base
    assert montag.hour == 17


def test_parse_when_iso_behaelt_zeitzone():
    result = parse_when("2026-08-09T18:00:00+02:00")
    assert result.hour == 18
    assert result.utcoffset() == timedelta(hours=2)


def test_parse_when_meldet_unsinn():
    with pytest.raises(ValueError):
        parse_when("irgendwann mal")
    with pytest.raises(ValueError):
        parse_when("")


def test_parse_when_lehnt_ungueltige_uhrzeit_ab():
    with pytest.raises(ValueError):
        parse_when("heute um 25:00")


def test_wiederholung_rechnet_weiter():
    base = datetime(2026, 8, 8, 18, 0, tzinfo=VIENNA)
    assert next_occurrence("täglich", base) == base + timedelta(days=1)
    assert next_occurrence("wöchentlich", base) == base + timedelta(days=7)
    montag = next_occurrence("jeden Montag", base)
    assert montag is not None and montag.weekday() == 0
    assert next_occurrence("", base) is None
    assert next_occurrence("einmal", base) is None


def test_planen_auflisten_aendern_absagen(service):
    call = service.schedule("morgen um 9 Uhr", message="Aufstehen", reason="Wecker")
    assert call["status"] == "scheduled"
    assert service.list()[0]["id"] == call["id"]
    geaendert = service.update(call["id"], when="morgen um 10 Uhr")
    assert geaendert is not None
    assert datetime.fromisoformat(geaendert["scheduled_at"]).hour == 10
    assert service.cancel(call["id"]) is True
    assert service.list() == []
    assert service.cancel(call["id"]) is False


def test_planen_lehnt_vergangenheit_ab(service):
    with pytest.raises(ValueError):
        service.schedule("2020-01-01T10:00:00+01:00")


def test_faellige_anrufe_werden_erkannt(service):
    faellig = service.schedule("in 1 minute", message="jetzt")
    service.schedule((datetime.now(VIENNA) + timedelta(hours=5)).isoformat(), message="spaeter")
    assert service.due() == []
    service.update(
        faellig["id"], when=(datetime.now(VIENNA) - timedelta(minutes=1)).isoformat()
    )
    due = service.due()
    assert len(due) == 1
    assert due[0]["message"] == "jetzt"


def test_finden_ueber_uhrzeit_und_stichwort(service):
    service.schedule("morgen um 9 Uhr", reason="Zahnarzt")
    service.schedule("morgen um 17 Uhr", reason="Projekt")
    assert service.find("zahnarzt")["reason"] == "Zahnarzt"
    assert service.find("17:00")["reason"] == "Projekt"
    assert service.find("gibt es nicht") is None


def test_wiederkehrender_anruf_legt_folgetermin_an(service):
    call = service.schedule("morgen um 8 Uhr", reason="Wecker", recurrence="täglich")
    service._finish(call["id"], "completed", "fertig", 30)
    offen = service.list()
    assert len(offen) == 1
    neu = datetime.fromisoformat(offen[0]["scheduled_at"])
    alt = datetime.fromisoformat(call["scheduled_at"])
    assert neu == alt + timedelta(days=1)


def test_einmaliger_anruf_legt_keinen_folgetermin_an(service):
    call = service.schedule("morgen um 8 Uhr", reason="einmalig")
    service._finish(call["id"], "completed", "fertig", 12)
    assert service.list() == []


def test_verlauf_wird_begrenzt_und_loeschbar(service):
    for index in range(5):
        service.record({"id": str(index), "status": "completed"})
    assert len(service.history()) == 5
    assert service.history(limit=2) == service.history()[:2]
    service.clear_history()
    assert service.history() == []


def test_status_meldet_fehlende_teile(service, monkeypatch):
    monkeypatch.setattr(
        service, "settings", lambda: {"phone_enabled": False, "phone_sip_port": 5060}
    )
    status = service.status()
    assert status["enabled"] is False
    assert status["running"] is False
    assert status["device"]["registered"] is False


def test_diagnose_listet_alle_pruefungen(service, monkeypatch):
    monkeypatch.setattr(
        service, "settings", lambda: {"phone_enabled": True, "phone_sip_port": 5060}
    )
    report = service.diagnostics()
    namen = [check["name"] for check in report["checks"]]
    assert "SIP-Dienst" in namen
    assert "Telefon angemeldet" in namen
    assert "Spracherkennung" in namen
    assert report["ready"] is False


def test_anruf_ohne_angemeldetes_geraet_scheitert_verstaendlich(service, monkeypatch):
    monkeypatch.setattr(
        service,
        "settings",
        lambda: {"phone_enabled": True, "phone_sip_port": 5060, "phone_sip_user": "x"},
    )
    monkeypatch.setattr(service, "start", _noop)
    with pytest.raises(RuntimeError) as exc:
        asyncio.run(service.place_call(message="Hallo"))
    assert "SIP" in str(exc.value) or "nicht" in str(exc.value)


async def _noop() -> None:
    return None


def test_registrierung_verlangt_authentifizierung():
    asyncio.run(_registrierung_verlangt_authentifizierung())


async def _registrierung_verlangt_authentifizierung():
    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    await stack.start()
    sock = _client_socket()
    try:
        first = await _exchange(sock, _register_message(stack.port), stack.port)
        assert first is not None
        assert first.status == 401
        challenge = parse_auth(first.header("www-authenticate"))
        assert challenge["realm"] == "jon"

        auth = authorization_header(
            "jon-phone", "geheim", challenge, "REGISTER", f"sip:127.0.0.1:{stack.port}"
        )
        second = await _exchange(sock, _register_message(stack.port, auth), stack.port)
        assert second is not None
        assert second.status == 200
        assert stack.binding is not None
        assert stack.binding.contact.user == "jon-phone"
        assert stack.binding.user_agent == "Linphone"
    finally:
        sock.close()
        await stack.stop()


def test_falsches_passwort_wird_abgelehnt():
    asyncio.run(_falsches_passwort_wird_abgelehnt())


async def _falsches_passwort_wird_abgelehnt():
    stack = SipStack("jon-phone", "richtig", host="127.0.0.1", port=_free_port())
    await stack.start()
    sock = _client_socket()
    try:
        first = await _exchange(sock, _register_message(stack.port), stack.port)
        challenge = parse_auth(first.header("www-authenticate"))
        auth = authorization_header(
            "jon-phone", "falsch", challenge, "REGISTER", f"sip:127.0.0.1:{stack.port}"
        )
        second = await _exchange(sock, _register_message(stack.port, auth), stack.port)
        assert second.status == 401
        assert stack.binding is None
    finally:
        sock.close()
        await stack.stop()


def test_anruf_ohne_registrierung_meldet_klartext():
    asyncio.run(_anruf_ohne_registrierung_meldet_klartext())


async def _anruf_ohne_registrierung_meldet_klartext():
    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    await stack.start()
    try:
        with pytest.raises(RuntimeError) as exc:
            await stack.call()
        assert "angemeldet" in str(exc.value)
    finally:
        await stack.stop()


def test_options_wird_beantwortet():
    asyncio.run(_options_wird_beantwortet())


async def _options_wird_beantwortet():
    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    await stack.start()
    sock = _client_socket()
    try:
        lines = [
            f"OPTIONS sip:jon-phone@127.0.0.1:{stack.port} SIP/2.0",
            "Via: SIP/2.0/UDP 127.0.0.1:6000;branch=z9hG4bKopt",
            "From: <sip:test@127.0.0.1>;tag=t1",
            f"To: <sip:jon-phone@127.0.0.1:{stack.port}>",
            "Call-ID: opt-1",
            "CSeq: 1 OPTIONS",
            "Content-Length: 0",
        ]
        message = (CRLF.join(lines) + CRLF + CRLF).encode()
        response = await _exchange(sock, message, stack.port)
        assert response.status == 200
    finally:
        sock.close()
        await stack.stop()


def test_rtp_uebertraegt_audio_zwischen_zwei_sitzungen():
    asyncio.run(_rtp_uebertraegt_audio())


async def _rtp_uebertraegt_audio():
    sock_a, port_a = open_port("127.0.0.1")
    sock_b, port_b = open_port("127.0.0.1")
    left = RtpSession(sock_a, port_a)
    right = RtpSession(sock_b, port_b)
    left.set_remote("127.0.0.1", port_b)
    right.set_remote("127.0.0.1", port_a)
    left.start()
    right.start()
    try:
        payload = tone(440, 0.06)
        await left.play(payload)
        frames = []
        for _ in range(3):
            frame = await right.read_frame(timeout=1.0)
            if frame is None:
                break
            frames.append(frame)
        assert frames
        assert right.packets_received >= len(frames)
        received = np.concatenate(frames)
        assert float(np.abs(received.astype(np.float64)).mean()) > 500
    finally:
        await left.stop()
        await right.stop()


def test_telefonstil_entfernt_markdown():
    text = "**Hallo** Felix\n- Punkt eins\n```code```\n# Titel"
    clean = _phone_style(text)
    assert "*" not in clean
    assert "```" not in clean
    assert "#" not in clean
    assert "\n" not in clean
    assert "Hallo" in clean


def test_telefonstil_kuerzt_lange_antworten():
    long_text = " ".join(f"Satz nummer {i}." for i in range(20))
    assert len(split_sentences(_phone_style(long_text))) <= 4


def test_abschied_und_unterbrechung_erkannt():
    assert wants_goodbye("okay tschüss dann")
    assert wants_goodbye("Auf Wiederhören Jon")
    assert not wants_goodbye("erzähl mir mehr")
    assert wants_pause("warte kurz")
    assert wants_pause("stopp mal")
    assert not wants_pause("erzähl weiter")


def _client_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.setblocking(False)
    return sock


async def _exchange(sock: socket.socket, payload: bytes, port: int):
    loop = asyncio.get_running_loop()
    await loop.sock_sendto(sock, payload, ("127.0.0.1", port))
    data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), timeout=3.0)
    return sipmsg.parse(data)


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _register_message(port: int, auth: str = "") -> bytes:
    lines = [
        f"REGISTER sip:127.0.0.1:{port} SIP/2.0",
        "Via: SIP/2.0/UDP 127.0.0.1:6000;branch=z9hG4bKreg",
        "From: <sip:jon-phone@127.0.0.1>;tag=abc",
        f"To: <sip:jon-phone@127.0.0.1:{port}>",
        "Call-ID: reg-1",
        "CSeq: 1 REGISTER",
        "Contact: <sip:jon-phone@127.0.0.1:6000>",
        "Expires: 600",
        "User-Agent: Linphone",
    ]
    if auth:
        lines.append(f"Authorization: {auth}")
    lines.append("Content-Length: 0")
    return ("\r\n".join(lines) + "\r\n\r\n").encode()


def test_registrierung_ueber_tcp():
    asyncio.run(_registrierung_ueber_tcp())


async def _registrierung_ueber_tcp():
    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    await stack.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", stack.port)
        writer.write(_register_message(stack.port))
        await writer.drain()
        first = sipmsg.parse(await asyncio.wait_for(reader.read(4096), timeout=3.0))
        assert first is not None
        assert first.status == 401
        challenge = parse_auth(first.header("www-authenticate"))
        auth = authorization_header(
            "jon-phone", "geheim", challenge, "REGISTER", f"sip:127.0.0.1:{stack.port}"
        )
        writer.write(_register_message(stack.port, auth))
        await writer.drain()
        second = sipmsg.parse(await asyncio.wait_for(reader.read(4096), timeout=3.0))
        assert second is not None
        assert second.status == 200
        assert stack.binding is not None
        assert stack.binding.transport == "tcp"
        writer.close()
    finally:
        await stack.stop()


def test_versuche_werden_protokolliert():
    asyncio.run(_versuche_werden_protokolliert())


async def _versuche_werden_protokolliert():
    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    await stack.start()
    sock = _client_socket()
    try:
        await _exchange(sock, _register_message(stack.port), stack.port)
        eintraege = stack.attempts()
        assert eintraege
        assert eintraege[0]["transport"] == "udp"
        assert "Anmeldung begonnen" in eintraege[0]["detail"]
        assert "Linphone" in eintraege[0]["detail"]
    finally:
        sock.close()
        await stack.stop()


def test_falscher_benutzername_wird_protokolliert():
    asyncio.run(_falscher_benutzername_wird_protokolliert())


async def _falscher_benutzername_wird_protokolliert():
    stack = SipStack("jon-neu", "geheim", host="127.0.0.1", port=_free_port())
    await stack.start()
    sock = _client_socket()
    try:
        antwort = await _exchange(sock, _register_message(stack.port), stack.port)
        assert antwort.status == 404
        eintraege = stack.attempts()
        assert "falscher Benutzername" in eintraege[0]["detail"]
        assert "jon-neu" in eintraege[0]["detail"]
    finally:
        sock.close()
        await stack.stop()


def test_eingehender_anruf_wird_angenommen():
    asyncio.run(_eingehender_anruf())


async def _eingehender_anruf():
    from app.services.phone.rtp import open_port

    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    gefuehrt = asyncio.Event()
    gesehen = {}

    async def on_incoming(call):
        gesehen["state"] = call.state
        gesehen["direction"] = call.direction
        gefuehrt.set()

    stack.on_incoming = on_incoming
    await stack.start()
    sock = _client_socket()
    rtp_sock, rtp_port = open_port("127.0.0.1")
    try:
        first = await _exchange(sock, _invite_message(stack.port, rtp_port), stack.port)
        assert first.status == 401
        challenge = parse_auth(first.header("www-authenticate"))
        auth = authorization_header(
            "jon-phone", "geheim", challenge, "INVITE", f"sip:jon-phone@127.0.0.1:{stack.port}"
        )
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(
            sock, _invite_message(stack.port, rtp_port, auth), ("127.0.0.1", stack.port)
        )
        stati = []
        antwort = None
        for _ in range(4):
            data, _addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), 3.0)
            antwort = sipmsg.parse(data)
            stati.append(antwort.status)
            if antwort.status == 200:
                break
        assert 180 in stati
        assert antwort.status == 200
        sdp = parse_sdp(antwort.body)
        assert sdp["port"] > 0
        await loop.sock_sendto(
            sock, _ack_message(stack.port, antwort.to_tag()), ("127.0.0.1", stack.port)
        )
        await asyncio.wait_for(gefuehrt.wait(), 3.0)
        assert gesehen["state"] == "active"
        assert gesehen["direction"] == "in"
    finally:
        sock.close()
        rtp_sock.close()
        await stack.stop()


def test_eingehender_anruf_kann_abgeschaltet_werden():
    asyncio.run(_eingehender_anruf_abgeschaltet())


async def _eingehender_anruf_abgeschaltet():
    from app.services.phone.rtp import open_port

    stack = SipStack("jon-phone", "geheim", host="127.0.0.1", port=_free_port())
    stack.accept_incoming = False
    await stack.start()
    sock = _client_socket()
    rtp_sock, rtp_port = open_port("127.0.0.1")
    try:
        antwort = await _exchange(sock, _invite_message(stack.port, rtp_port), stack.port)
        assert antwort.status == 486
    finally:
        sock.close()
        rtp_sock.close()
        await stack.stop()


def _invite_message(port: int, rtp_port: int, auth: str = "") -> bytes:
    body = (
        "v=0\r\no=handy 1 1 IN IP4 127.0.0.1\r\ns=-\r\nc=IN IP4 127.0.0.1\r\n"
        f"t=0 0\r\nm=audio {rtp_port} RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\n"
    )
    lines = [
        f"INVITE sip:jon-phone@127.0.0.1:{port} SIP/2.0",
        "Via: SIP/2.0/UDP 127.0.0.1:6000;branch=z9hG4bKinv",
        "From: <sip:jon-phone@127.0.0.1>;tag=handy",
        f"To: <sip:jon-phone@127.0.0.1:{port}>",
        "Call-ID: incoming-1",
        "CSeq: 2 INVITE",
        "Contact: <sip:jon-phone@127.0.0.1:6000>",
        "User-Agent: Linphone",
    ]
    if auth:
        lines.append(f"Authorization: {auth}")
    lines.append("Content-Type: application/sdp")
    lines.append(f"Content-Length: {len(body)}")
    return (CRLF.join(lines) + CRLF + CRLF + body).encode()


def _ack_message(port: int, to_tag: str) -> bytes:
    lines = [
        f"ACK sip:jon-phone@127.0.0.1:{port} SIP/2.0",
        "Via: SIP/2.0/UDP 127.0.0.1:6000;branch=z9hG4bKack",
        "From: <sip:jon-phone@127.0.0.1>;tag=handy",
        f"To: <sip:jon-phone@127.0.0.1:{port}>;tag={to_tag}",
        "Call-ID: incoming-1",
        "CSeq: 2 ACK",
        "Content-Length: 0",
    ]
    return (CRLF.join(lines) + CRLF + CRLF).encode()
