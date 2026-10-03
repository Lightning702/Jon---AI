from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.api import support_routes


def test_support_nachricht_geht_an_netlify_forms_mit_systeminfo(monkeypatch):
    from app.main import create_app

    gesendet = []

    def antworten(anfrage: httpx.Request) -> httpx.Response:
        gesendet.append((str(anfrage.url), dict(httpx.QueryParams(anfrage.content.decode()))))
        return httpx.Response(303, headers={"location": "/support/danke.html"})

    echt = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: echt(transport=httpx.MockTransport(antworten), **kwargs))
    support_routes._gesendet.clear()
    client = TestClient(create_app())
    assert client.get("/api/support").json()["email"] == "felix.heinisch12@gmail.com"
    antwort = client.post("/api/support", json={"art": "premium", "betreff": "Mehr Spiele", "nachricht": "Bitte noch ein Rennspiel als Premium-Funktion.", "email": "test@example.com"})
    assert antwort.status_code == 200 and antwort.json()["ok"]
    url, felder = gesendet[0]
    assert url.endswith("/support/") and felder["form-name"] == "support" and felder["art"] == "Neue Premium-Funktion"
    assert felder["version"] and felder["stufe"] and felder["email"] == "test@example.com"
    assert client.post("/api/support", json={"art": "fehler", "betreff": "x", "nachricht": "zu kurz"}).status_code == 422
    for _ in range(4):
        client.post("/api/support", json={"art": "frage", "betreff": "Frage", "nachricht": "Wie installiere ich Jon auf dem Pi?", "infos": False})
    assert client.post("/api/support", json={"art": "frage", "betreff": "Frage", "nachricht": "Noch eine Nachricht hier."}).status_code == 429
    assert "version" not in gesendet[-1][1]
    support_routes._gesendet.clear()
