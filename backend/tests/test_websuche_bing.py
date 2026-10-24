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
