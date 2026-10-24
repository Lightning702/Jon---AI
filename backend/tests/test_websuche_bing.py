from __future__ import annotations

import asyncio
import base64

import httpx

from app.services.websearch_service import WebSearch, _real_url


def _bing_link(ziel: str) -> str:
    kodiert = base64.urlsafe_b64encode(ziel.encode()).decode().rstrip("=")
    return f"https://www.bing.com/ck/a?!&amp;&amp;p=abc&amp;u=a1{kodiert}&amp;ntb=1"


SEITE = (
    "<html><body><ol>"
    f'<li class="b_algo" data-id=1><link rel="stylesheet" href="https://r.bing.com/x.css"/><h2><a href="{_bing_link("https://www.bsi.bund.de/backup")}">Datensicherung beim <strong>BSI</strong></a></h2>'
    '<div class="b_caption"><p class="b_lineclamp2">Die 3-2-1-Regel: drei Kopien, zwei Medien, eine außer Haus.</p></div></li>'
    f'<li class="b_algo" data-id=2><h2><a href="{_bing_link("https://de.wikipedia.org/wiki/Datensicherung")}">Datensicherung – Wikipedia</a></h2><p>Grundlage der Datensicherheit.</p></li>'
    "</ol></body></html>"
)


def test_bing_ziel_wird_entschluesselt():
    assert _real_url(_bing_link("https://example.org/a?b=1")) == "https://example.org/a?b=1"
    assert _real_url("https://www.bing.com/ck/a?u=kaputt") == ""


def test_bing_treffer_werden_gelesen():
    def antwort(anfrage):
        assert anfrage.url.host == "www.bing.com"
        return httpx.Response(200, text=SEITE)

    async def lauf():
        async with httpx.AsyncClient(transport=httpx.MockTransport(antwort)) as client:
            return await WebSearch()._bing(client, "Datensicherung", 6)

    treffer = asyncio.run(lauf())
    assert [t["url"] for t in treffer] == ["https://www.bsi.bund.de/backup", "https://de.wikipedia.org/wiki/Datensicherung"]
    assert treffer[0]["title"] == "Datensicherung beim BSI"
    assert "3-2-1-Regel" in treffer[0]["snippet"]
    assert treffer[0]["engine"] == "bing"


def test_zufallstreffer_von_bing_werden_aussortiert():
    from app.services.websearch_service import passt_zur_frage

    assert not passt_zur_frage("Hauptstadt von Australien", {"title": "Socks | Adult Forum", "snippet": "annoyed when watching", "url": "https://forum.example/socks"})
    assert not passt_zur_frage("nemotron 3 ultra nvidia", {"title": "Grüner Leguan – Wikipedia", "snippet": "Der Grüne Leguan", "url": "https://de.wikipedia.org/wiki/Gruener_Leguan"})
    assert passt_zur_frage("Hauptstadt von Australien", {"title": "Canberra", "snippet": "Canberra ist die Hauptstadt Australiens", "url": "https://de.wikipedia.org/wiki/Canberra"})
    assert passt_zur_frage("Öffnungszeiten Schönbrunn", {"title": "Schloss Schönbrunn Öffnungszeiten", "snippet": "", "url": "https://oeffnungszeitenbuch.at"})
    assert passt_zur_frage("wie ist das", {"title": "Irgendwas", "snippet": "", "url": "https://x.example"})


def test_suche_wiederholt_einmal_mit_kernwoertern(monkeypatch):
    from app.services import websearch_service as ws

    fragen = []

    async def suchen(self, query, limit=6, read=False):
        fragen.append(query)
        if len(fragen) == 1:
            return {"frage": query, "treffer": [], "fehler": "Keine Suchmaschine hat geantwortet."}
        return {"frage": query, "treffer": [{"url": "https://de.wikipedia.org/wiki/Canberra", "engine": "wikipedia-de"}]}

    monkeypatch.setattr(ws.WebSearch, "_suchen", suchen)
    monkeypatch.setattr(ws, "WIEDERHOL_PAUSE", 0)
    ergebnis = asyncio.run(ws.WebSearch().search("Was ist die Hauptstadt von Australien?"))
    assert fragen == ["Was ist die Hauptstadt von Australien?", "Hauptstadt Australien?"]
    assert ergebnis["treffer"] and ergebnis["wiederholt"] is True
    assert ergebnis["frage"] == "Was ist die Hauptstadt von Australien?"


def test_erfolgreiche_suche_wird_nicht_wiederholt(monkeypatch):
    from app.services import websearch_service as ws

    fragen = []

    async def suchen(self, query, limit=6, read=False):
        fragen.append(query)
        return {"frage": query, "treffer": [{"url": "https://x.example", "engine": "bing"}]}

    monkeypatch.setattr(ws.WebSearch, "_suchen", suchen)
    assert asyncio.run(ws.WebSearch().search("Wetter Wien"))["treffer"]
    assert fragen == ["Wetter Wien"]


def test_kurzfassung_laesst_jahreszahlen_und_fuellwoerter_weg():
    from app.services.websearch_service import kurzfassung

    assert kurzfassung('"run LLM locally" guide hardware GPU 2024') == "run LLM locally guide"
    assert kurzfassung("Was ist die Hauptstadt von Australien?", 3) == "Hauptstadt Australien?"


def test_hackernews_liefert_nur_passende_geschichten():
    def antwort(anfrage):
        assert anfrage.url.host == "hn.algolia.com"
        assert anfrage.url.params["query"] == "llama.cpp VRAM guide"
        return httpx.Response(200, json={"hits": [
            {"title": "A llama.cpp guide for VRAM", "url": "https://example.org/llama-guide"},
            {"title": "Show HN: My cat", "url": "https://example.org/cat"},
            {"title": "Ohne Adresse", "url": None},
        ]})

    async def lauf():
        async with httpx.AsyncClient(transport=httpx.MockTransport(antwort)) as client:
            return await WebSearch()._hackernews(client, "llama.cpp VRAM guide 2025", 6)

    treffer = asyncio.run(lauf())
    assert [t["url"] for t in treffer] == ["https://example.org/llama-guide"]
    assert treffer[0]["engine"] == "hackernews"
