from __future__ import annotations

import asyncio
import html
import re
import urllib.parse
from datetime import datetime

import httpx

from app.services.research.web import (
    UnsafeUrl,
    check_url,
    domain_of,
    extract_text,
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

AD_MARKERS = ("/y.js", "ad_domain=", "ad_provider=", "duckduckgo.com/y.js")

JUNK_DOMAINS = ("duckduckgo.com", "lite.duckduckgo.com", "html.duckduckgo.com")

LITE_LINK = re.compile(
    r"""<a[^>]+href=["']([^"']+)["'][^>]*class=["']result-link["'][^>]*>(.*?)</a>""",
    re.S,
)
LITE_SNIPPET = re.compile(
    r"""<td[^>]*class=["']result-snippet["'][^>]*>(.*?)</td>""", re.S
)
HTML_LINK = re.compile(
    r"""<a[^>]+class=["']result__a["'][^>]+href=["']([^"']+)["'][^>]*>(.*?)</a>""",
    re.S,
)
HTML_SNIPPET = re.compile(
    r"""class=["']result__snippet["'][^>]*>(.*?)</a>""", re.S
)

READ_CHARS = 2600
MAX_READ = 3


def _clean(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")


def _tidy(text: str) -> str:
    return re.sub(r"\s+", " ", _clean(text)).strip()


def _real_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    if "uddg=" in href:
        query = urllib.parse.urlparse(href).query
        found = urllib.parse.parse_qs(query).get("uddg")
        if found:
            href = found[0]
    return href


def _is_ad(href: str) -> bool:
    low = href.lower()
    return any(marker in low for marker in AD_MARKERS)


class WebSearch:
    @staticmethod
    def _client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=7.0),
            follow_redirects=True,
            max_redirects=4,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
            },
        )

    async def search(
        self, query: str, limit: int = 6, read: bool = False
    ) -> dict:
        frage = query.strip()
        if not frage:
            return {"frage": "", "treffer": [], "fehler": "Kein Suchbegriff."}
        limit = max(1, min(int(limit), 12))
        engines = (
            self._duckduckgo_lite,
            self._duckduckgo_html,
            self._wikipedia,
        )
        treffer: list[dict] = []
        gesehen: set[str] = set()
        quellen: list[str] = []
        fehler: list[str] = []
        async with self._client() as client:
            for engine in engines:
                try:
                    gefunden = await engine(client, frage, limit)
                except Exception as exc:
                    fehler.append(f"{engine.__name__.strip('_')}: {exc}")
                    continue
                if gefunden:
                    quellen.append(gefunden[0]["engine"])
                for hit in gefunden:
                    schluessel = hit["url"].rstrip("/").lower()
                    if schluessel in gesehen:
                        continue
                    gesehen.add(schluessel)
                    treffer.append(hit)
                if len(treffer) >= limit:
                    break
            treffer = treffer[:limit]
            if read and treffer:
                await self._read_pages(client, treffer)
        ergebnis = {
            "frage": frage,
            "stand": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "suchmaschinen": quellen,
            "treffer": treffer,
        }
        if not treffer:
            ergebnis["fehler"] = (
                "Keine Suchmaschine hat geantwortet. Das heisst NICHT, dass es die "
                "Sache nicht gibt - sag dem Nutzer, dass die Suche gerade nicht "
                "durchkam, und versuche es mit anderen Suchwoertern."
            )
            if fehler:
                ergebnis["details"] = fehler[:3]
        return ergebnis

    async def _read_pages(
        self, client: httpx.AsyncClient, treffer: list[dict]
    ) -> None:
        ziele = [hit for hit in treffer if not hit["url"].lower().endswith(".pdf")]
        aufgaben = [self._read_one(client, hit) for hit in ziele[:MAX_READ]]
        if aufgaben:
            await asyncio.gather(*aufgaben, return_exceptions=True)

    async def _read_one(self, client: httpx.AsyncClient, hit: dict) -> None:
        try:
            safe = check_url(hit["url"])
        except UnsafeUrl:
            return
        try:
            response = await client.get(safe)
            response.raise_for_status()
            if "text/html" not in response.headers.get("content-type", "").lower():
                return
            titel, text = extract_text(response.text)
        except Exception:
            return
        if text.strip():
            hit["auszug"] = text[:READ_CHARS]
            if titel and not hit.get("title"):
                hit["title"] = titel

    def _pack(self, title: str, href: str, snippet: str, engine: str) -> dict | None:
        url = _real_url(href.strip())
        if not url.startswith("http") or _is_ad(url):
            return None
        if domain_of(url) in JUNK_DOMAINS:
            return None
        try:
            url = check_url(url)
        except UnsafeUrl:
            return None
        titel = _tidy(title)
        if not titel:
            return None
        return {
            "title": titel[:180],
            "url": url,
            "domain": domain_of(url),
            "snippet": _tidy(snippet)[:400],
            "engine": engine,
        }

    async def _duckduckgo_lite(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        response = await client.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query, "kl": "de-de"},
        )
        response.raise_for_status()
        seite = response.text
        treffer: list[dict] = []
        offen: dict | None = None
        for block in re.split(r"<tr[^>]*>", seite):
            link = LITE_LINK.search(block)
            if link:
                offen = self._pack(link.group(2), link.group(1), "", "duckduckgo")
                if offen:
                    treffer.append(offen)
                continue
            text = LITE_SNIPPET.search(block)
            if text and offen is not None:
                offen["snippet"] = _tidy(text.group(1))[:400]
                offen = None
            if len(treffer) >= limit:
                break
        return treffer[:limit]

    async def _duckduckgo_html(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        response = await client.get(
            "https://html.duckduckgo.com/html/", params={"q": query, "kl": "de-de"}
        )
        response.raise_for_status()
        seite = response.text
        treffer: list[dict] = []
        for block in re.split(r'class="result results_links', seite)[1:]:
            link = HTML_LINK.search(block)
            if not link:
                continue
            text = HTML_SNIPPET.search(block)
            eintrag = self._pack(
                link.group(2), link.group(1), text.group(1) if text else "", "duckduckgo"
            )
            if eintrag:
                treffer.append(eintrag)
            if len(treffer) >= limit:
                break
        return treffer[:limit]

    async def _wikipedia(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        treffer: list[dict] = []
        for sprache in ("de", "en"):
            response = await client.get(
                f"https://{sprache}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": min(limit, 5),
                },
            )
            response.raise_for_status()
            for item in (response.json().get("query") or {}).get("search") or []:
                titel = str(item.get("title") or "")
                if not titel:
                    continue
                slug = urllib.parse.quote(titel.replace(" ", "_"))
                eintrag = self._pack(
                    titel,
                    f"https://{sprache}.wikipedia.org/wiki/{slug}",
                    str(item.get("snippet") or ""),
                    f"wikipedia-{sprache}",
                )
                if eintrag:
                    treffer.append(eintrag)
            if treffer:
                break
        return treffer[:limit]


def get_web_search() -> WebSearch:
    return WebSearch()


async def search_web(query: str, limit: int = 6, read: bool = False) -> dict:
    return await WebSearch().search(query, limit, read)


def search_web_sync(query: str, limit: int = 6, read: bool = False) -> dict:
    return asyncio.run(WebSearch().search(query, limit, read))
