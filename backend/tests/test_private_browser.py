from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services import private_proxy_service as psvc

client = TestClient(app)


class _FakeResp:
    def __init__(self, content, headers, url, status=200, encoding="utf-8"):
        self.content = content
        self.headers = headers
        self.url = url
        self.status_code = status
        self.encoding = encoding


class _FakeClient:
    payload = b""
    ctype = "text/html; charset=utf-8"

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        return _FakeResp(
            _FakeClient.payload, {"content-type": _FakeClient.ctype}, url
        )


def test_routen_registriert():
    paths = set(app.openapi()["paths"])
    assert "/api/private/proxy" in paths


def test_privat_seite_wird_ausgeliefert():
    res = client.get("/privat")
    assert res.status_code == 200
    assert "Privater Browser" in res.text
    assert "/api/private/proxy" in res.text


def test_normalize_und_target():
    assert psvc.normalize("heise.de") == "https://heise.de"
    assert psvc.normalize("http://x.de") == "http://x.de"
    assert psvc.normalize("//x.de") == "https://x.de"
    assert psvc.proxy_target("https://a.de/x y").endswith("a.de%2Fx%20y")


def test_ssrf_schutz():
    assert psvc._blocked("127.0.0.1")
    assert psvc._blocked("localhost")
    assert psvc._blocked("169.254.169.254")
    assert psvc._blocked("")


def test_proxy_injiziert_und_entfernt_frame_header(monkeypatch):
    _FakeClient.payload = (
        b"<html><head><title>Testseite</title></head>"
        b'<body><base href="http://alt/"><a href="/x">x</a></body></html>'
    )
    monkeypatch.setattr(psvc, "_blocked", lambda host: False)
    monkeypatch.setattr(psvc.httpx, "AsyncClient", _FakeClient)
    res = client.get("/api/private/proxy", params={"url": "http://x.test/seite"})
    assert res.status_code == 200
    body = res.text
    assert '<base href="http://x.test/seite">' in body
    assert "jonNav" in body
    assert body.count("<base") == 1
    assert "x-frame-options" not in {k.lower() for k in res.headers}
    assert "content-security-policy" not in {k.lower() for k in res.headers}
    assert res.headers.get("cache-control", "").startswith("no-store")


def test_proxy_reicht_nicht_html_durch(monkeypatch):
    _FakeClient.payload = b"\x89PNG\r\n\x1a\n"
    _FakeClient.ctype = "image/png"
    monkeypatch.setattr(psvc, "_blocked", lambda host: False)
    monkeypatch.setattr(psvc.httpx, "AsyncClient", _FakeClient)
    res = client.get("/api/private/proxy", params={"url": "http://x.test/bild.png"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/png")
    assert res.content == b"\x89PNG\r\n\x1a\n"
    _FakeClient.ctype = "text/html; charset=utf-8"


def test_proxy_blockt_loopback():
    res = client.get(
        "/api/private/proxy", params={"url": "http://127.0.0.1:8756/api/health"}
    )
    assert res.status_code == 403


def test_proxy_lehnt_fremdes_schema_ab():
    res = client.get("/api/private/proxy", params={"url": "ftp://x.de/"})
    assert res.status_code == 400
