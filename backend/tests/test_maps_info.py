from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.maps import insights

client = TestClient(app)

BING_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:News="http://news"><channel>
<item><title>Regierung beschliesst Entlastungspaket</title>
<link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3a%2f%2fwww.derstandard.at%2fstory%2f1&amp;c=1</link>
<pubDate>Sat, 29 Aug 2026 17:12:00 GMT</pubDate>
<News:Source>Der Standard</News:Source>
<News:Image>http://www.bing.com/th?id=ONUT.abc&amp;pid=News</News:Image></item>
<item><title>OeBB investieren in die Weststrecke</title>
<link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3a%2f%2forf.at%2fstory%2f2&amp;c=2</link>
<pubDate>Sat, 29 Aug 2026 15:00:00 GMT</pubDate>
<News:Source>ORF</News:Source></item>
<item><title>Ohne echte Adresse</title><link>news.google.com/nix</link></item>
</channel></rss>"""

GOOGLE_RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Rekord bei Naechtigungen - Die Presse</title>
<link>https://news.google.com/rss/articles/XYZ</link>
<pubDate>Sat, 29 Aug 2026 12:00:00 GMT</pubDate>
<source url="https://www.diepresse.com">Die Presse</source></item>
</channel></rss>"""


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        raise ValueError("kein json")


class FakeClient:
    def __init__(self, pages: dict[str, str], fehler: set[str] | None = None) -> None:
        self.pages = pages
        self.fehler = fehler or set()
        self.calls: list[str] = []

    async def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append(url)
        for key, body in self.pages.items():
            if key in url:
                if key in self.fehler:
                    raise RuntimeError("Netz weg")
                return FakeResponse(body)
        raise RuntimeError(f"unerwartet: {url}")


def _install(monkeypatch, client_obj: FakeClient) -> None:
    async def fake_client():
        return client_obj

    async def no_cache(key, ttl):
        return None

    async def no_store(key, value):
        return None

    monkeypatch.setattr(insights, "get_client", fake_client)
    monkeypatch.setattr(insights, "cached", no_cache)
    monkeypatch.setattr(insights, "store", no_store)


def test_bing_link_zeigt_auf_originalquelle():
    link = "http://www.bing.com/news/apiclick.aspx?ref=FexRss&url=https%3a%2f%2fwww.orf.at%2fa&c=1"
    assert insights._bing_target(link) == "https://www.orf.at/a"


def test_weiterleitungsdomains_werden_nicht_als_quelle_gezeigt():
    assert insights._article("Titel", "https://news.google.com/x", "", "", "lokal") is None
    echt = insights._article("Titel", "https://orf.at/a", "", "", "lokal")
    assert echt["quelle"] == "Orf"


def test_doppelte_meldungen_fallen_weg():
    a = {"titel": "Gleiche Meldung", "url": "https://a.at/1", "bereich": "lokal"}
    b = {"titel": "Gleiche  Meldung!", "url": "https://b.at/2", "bereich": "national"}
    c = {"titel": "Andere Meldung", "url": "https://c.at/3", "bereich": "national"}
    merged = insights._merge([[a], [b, c]], 5)
    assert [item["titel"] for item in merged] == ["Gleiche Meldung", "Andere Meldung"]


def test_bilder_werden_von_direkten_quellen_uebernommen():
    ziel = [{"titel": "Wien baut um", "url": "https://a.at/1", "bild": ""}]
    quelle = [{"titel": "Wien baut um", "url": "https://b.at/2", "bild": "https://bild/1.jpg"}]
    assert insights._enrich(ziel, quelle)[0]["bild"] == "https://bild/1.jpg"


def test_news_liefert_bild_quelle_zeit_und_link(monkeypatch):
    fake = FakeClient({"bing.com": BING_RSS, "news.google.com": GOOGLE_RSS, "gdelt": "{}"})
    _install(monkeypatch, fake)
    treffer = asyncio.run(insights.news("Wien", "Österreich", "at", "stadt", 5))
    assert treffer
    erste = treffer[0]
    assert erste["url"].startswith("https://www.derstandard.at")
    assert erste["quelle"] == "Der Standard"
    assert erste["bild"].startswith("https://www.bing.com/th")
    assert erste["zeit"].startswith("2026-08-29")
    assert all(not item["url"].startswith("news.google.com") for item in treffer)


def test_stadt_holt_lokale_und_nationale_meldungen(monkeypatch):
    fake = FakeClient({"bing.com": BING_RSS, "news.google.com": GOOGLE_RSS, "gdelt": "{}"})
    _install(monkeypatch, fake)
    asyncio.run(insights.news("Wien", "Österreich", "at", "stadt", 5))
    abfragen = [call for call in fake.calls if "bing.com" in call]
    assert len(abfragen) == 2


def test_land_fragt_nur_einmal(monkeypatch):
    fake = FakeClient({"bing.com": BING_RSS, "news.google.com": GOOGLE_RSS, "gdelt": "{}"})
    _install(monkeypatch, fake)
    asyncio.run(insights.news("Österreich", "Österreich", "at", "land", 5))
    assert len([call for call in fake.calls if "bing.com" in call]) == 1


def test_wetter_faellt_nicht_mit_news_aus(monkeypatch):
    async def kaputte_news(*args, **kwargs):
        raise RuntimeError("News weg")

    async def gutes_wetter(lat, lon, label=""):
        return {"temperatur": 27, "zustand": "sonnig", "code": 0, "tag": True}

    monkeypatch.setattr(insights, "news", kaputte_news)
    monkeypatch.setattr(insights, "weather", gutes_wetter)
    data = asyncio.run(insights.place_info(48.2, 16.3, "Wien", "Österreich", "at"))
    assert data["wetter"]["temperatur"] == 27
    assert data["news"] == []
    assert data["news_fehler"]


def test_news_bleiben_ohne_wetter_nutzbar(monkeypatch):
    async def gute_news(*args, **kwargs):
        return [{"titel": "Etwas passiert", "url": "https://a.at/1", "bereich": "lokal"}]

    async def kaputtes_wetter(lat, lon, label=""):
        raise RuntimeError("Wetter weg")

    monkeypatch.setattr(insights, "news", gute_news)
    monkeypatch.setattr(insights, "weather", kaputtes_wetter)
    data = asyncio.run(insights.place_info(48.2, 16.3, "Wien", "Österreich", "at"))
    assert data["news"][0]["titel"] == "Etwas passiert"
    assert data["wetter"] is None
    assert data["wetter_fehler"]


def test_endpunkt_liefert_news_und_wetter(monkeypatch):
    async def gute_news(*args, **kwargs):
        return [
            {
                "titel": "Meldung",
                "url": "https://a.at/1",
                "quelle": "A",
                "domain": "a.at",
                "bild": "",
                "zeit": "",
                "bereich": "lokal",
            }
        ]

    async def gutes_wetter(lat, lon, label=""):
        return {"temperatur": 21, "zustand": "klar", "code": 0, "tag": True, "ort": label}

    monkeypatch.setattr(insights, "news", gute_news)
    monkeypatch.setattr(insights, "weather", gutes_wetter)
    antwort = client.get(
        "/api/maps/info",
        params={
            "lat": 48.2,
            "lon": 16.37,
            "name": "Wien",
            "country": "Österreich",
            "country_code": "at",
            "scope": "stadt",
        },
    )
    assert antwort.status_code == 200
    data = antwort.json()
    assert data["ort"] == "Wien"
    assert len(data["news"]) == 1
    assert data["wetter"]["temperatur"] == 21


def test_alte_meldungen_werden_aussortiert():
    frisch = {"titel": "Heute passiert", "url": "https://a.at/1", "zeit": ""}
    alt = {
        "titel": "Lang her",
        "url": "https://b.at/2",
        "zeit": "2019-01-01T10:00:00+00:00",
    }
    merged = insights._merge([[frisch, alt]], 5)
    assert [item["titel"] for item in merged] == ["Heute passiert"]
