from __future__ import annotations

import asyncio
import base64
import html
import re
import urllib.parse
from datetime import datetime

import httpx

from app.core.kinderschutz import KINDER_ALTER, kindgerecht
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

JUNK_DOMAINS = ("duckduckgo.com", "lite.duckduckgo.com", "html.duckduckgo.com", "r.search.yahoo.com")

BING_BLOCK = re.compile(r'<li class="b_algo"')
BING_LINK = re.compile(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
BING_SNIPPET = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
BING_BALLAST = re.compile(r"<link[^>]*>|<style.*?</style>|<script.*?</script>", re.S)
YAHOO_BLOCK = re.compile(r'<div class="dd [^"]*algo[ "]')
YAHOO_LINK = re.compile(r'href="(https?://r\.search\.yahoo\.com/[^"]+|https?://(?!r\.search)[^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>', re.S)
YAHOO_SNIPPET = re.compile(r'<div class="compText[^"]*"[^>]*>\s*<p[^>]*>(.*?)</p>', re.S)

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


FUELLWOERTER = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem", "einer", "eines", "und", "oder", "aber",
    "wie", "was", "wer", "wem", "wen", "wo", "wann", "warum", "wieso", "welche", "welcher", "welches", "ist", "sind",
    "war", "waren", "wird", "werden", "hat", "haben", "von", "vom", "zum", "zur", "fuer", "mit", "bei", "aus", "nach",
    "ueber", "unter", "auf", "an", "am", "im", "in", "es", "ich", "du", "er", "sie", "wir", "ihr", "mir", "mich", "dir",
    "dich", "mein", "dein", "sein", "kann", "man", "gibt", "bitte", "mal", "auch", "noch", "nicht", "the", "and", "for",
    "what", "how", "why", "when", "where", "who", "with", "from", "are", "was", "does", "can",
}


def _normal(text: str) -> str:
    klein = str(text or "").casefold()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        klein = klein.replace(alt, neu)
    return re.sub(r"[^a-z0-9]+", " ", klein)


def kurzfassung(frage: str, anzahl: int = 4) -> str:
    woerter = [w.strip("\"„“”'()[]") for w in str(frage or "").split()]
    kern = [w for w in woerter if w and _normal(w).strip() and _normal(w).strip() not in FUELLWOERTER and not re.fullmatch(r"(?:19|20)\d\d", w)]
    return " ".join(kern[:anzahl])


def vereinfacht(frage: str) -> str:
    woerter = [w for w in str(frage or "").split() if _normal(w).strip() and _normal(w).strip() not in FUELLWOERTER]
    return " ".join(woerter[:6])


def passt_zur_frage(frage: str, eintrag: dict) -> bool:
    woerter = [w for w in _normal(frage).split() if len(w) > 2 and w not in FUELLWOERTER]
    if not woerter:
        return True
    text = _normal(" ".join(str(eintrag.get(f, "")) for f in ("title", "snippet", "url")))
    treffer = sum(1 for w in woerter if (w[:6] if len(w) > 6 else w) in text)
    return treffer >= (len(woerter) + 1) // 2


def _real_url(href: str) -> str:
    href = html.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    if "r.search.yahoo.com" in href and "/RU=" in href:
        href = urllib.parse.unquote(href.split("/RU=", 1)[1].split("/RK=", 1)[0])
    if "bing.com/ck/a" in href:
        wert = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("u", [""])[0]
        if not wert.startswith("a1"):
            return ""
        try:
            return base64.urlsafe_b64decode(wert[2:] + "=" * (-len(wert[2:]) % 4)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return ""
    if "uddg=" in href:
        query = urllib.parse.urlparse(href).query
        found = urllib.parse.parse_qs(query).get("uddg")
        if found:
            href = found[0]
    return href


def _is_ad(href: str) -> bool:
    low = href.lower()
    return any(marker in low for marker in AD_MARKERS)


WIEDERHOL_PAUSE = 1.0


class WebSearch:
    @staticmethod
    def _client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(7.0, connect=3.5),
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
        ergebnis = await self._suchen(query, limit, read)
        if ergebnis.get("treffer") or not str(query or "").strip():
            return ergebnis
        await asyncio.sleep(WIEDERHOL_PAUSE)
        zweite = vereinfacht(query) or query.strip()
        neu = await self._suchen(zweite, limit, read)
        neu["wiederholt"] = True
        if zweite != query.strip():
            neu["frage"] = query.strip()
            neu["vereinfacht"] = zweite
        return neu

    async def _suchen(
        self, query: str, limit: int = 6, read: bool = False
    ) -> dict:
        frage = query.strip()
        if not frage:
            return {"frage": "", "treffer": [], "fehler": "Kein Suchbegriff."}
        limit = max(1, min(int(limit), 12))
        engines = (
            self._bing,
            self._hackernews,
            self._yahoo,
            self._duckduckgo_lite,
            self._duckduckgo_html,
            self._wikipedia,
        )
        treffer: list[dict] = []
        gesehen: set[str] = set()
        quellen: list[str] = []
        fehler: list[str] = []
        async with self._client() as client:
            laeufe = await asyncio.gather(
                *(engine(client, frage, limit) for engine in engines),
                return_exceptions=True,
            )
            for engine, ausgang in zip(engines, laeufe):
                if isinstance(ausgang, BaseException):
                    fehler.append(f"{engine.__name__.strip('_')}: {ausgang}")
                    continue
                if ausgang:
                    quellen.append(ausgang[0]["engine"])
                for hit in ausgang:
                    schluessel = hit["url"].rstrip("/").lower()
                    if schluessel in gesehen:
                        continue
                    gesehen.add(schluessel)
                    treffer.append(hit)
            if KINDER_ALTER.get():
                treffer = [h for h in treffer if kindgerecht(h)]
            treffer = treffer[:limit]
            if read and treffer:
                await self._read_pages(client, treffer)
        eigen = [h for h in treffer if not h["engine"].startswith("wikipedia")]
        ergebnis = {
            "frage": frage,
            "stand": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "suchmaschinen": quellen,
            "treffer": treffer,
            "mager": len(eigen) < 2,
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

    async def _bing(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        response = await client.get(
            "https://www.bing.com/search",
            params={"q": query, "setlang": "de", "cc": "AT", **({"adlt": "strict"} if KINDER_ALTER.get() else {})},
        )
        response.raise_for_status()
        treffer: list[dict] = []
        for block in BING_BLOCK.split(response.text)[1:]:
            block = BING_BALLAST.sub("", block[:12000])
            link = BING_LINK.search(block)
            if not link:
                continue
            rest = block[link.end():]
            text = BING_SNIPPET.search(rest)
            eintrag = self._pack(link.group(2), link.group(1), text.group(1) if text else "", "bing")
            if eintrag and passt_zur_frage(query, eintrag):
                treffer.append(eintrag)
            if len(treffer) >= limit:
                break
        return treffer

    async def _hackernews(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        kurz = kurzfassung(query, 3)
        if not kurz or KINDER_ALTER.get():
            return []
        response = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": kurz, "tags": "story", "hitsPerPage": min(limit * 2, 12)},
        )
        response.raise_for_status()
        treffer: list[dict] = []
        for item in response.json().get("hits") or []:
            adresse = str(item.get("url") or "")
            titel = str(item.get("title") or "")
            if not adresse or not titel:
                continue
            eintrag = self._pack(titel, adresse, "", "hackernews")
            if eintrag and passt_zur_frage(kurz, eintrag):
                treffer.append(eintrag)
            if len(treffer) >= limit:
                break
        return treffer

    async def _yahoo(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        response = await client.get(
            "https://search.yahoo.com/search",
            params={"p": query, "vm": "r" if KINDER_ALTER.get() else "p"},
        )
        response.raise_for_status()
        teile = YAHOO_BLOCK.split(response.text)[1:]
        treffer: list[dict] = []
        for block in teile:
            link = YAHOO_LINK.search(block[:6000])
            if not link:
                continue
            text = YAHOO_SNIPPET.search(block[:8000])
            eintrag = self._pack(link.group(2), link.group(1), text.group(1) if text else "", "yahoo")
            if eintrag:
                treffer.append(eintrag)
            if len(treffer) >= limit:
                break
        return treffer

    async def _duckduckgo_lite(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[dict]:
        response = await client.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query, "kl": "de-de", **({"kp": "1"} if KINDER_ALTER.get() else {})},
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
            "https://html.duckduckgo.com/html/", params={"q": query, "kl": "de-de", **({"kp": "1"} if KINDER_ALTER.get() else {})}
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
        kurz = kurzfassung(query)
        versuche = [(sprache, frage) for frage in dict.fromkeys(f for f in (query, kurz) if f) for sprache in ("de", "en")]
        for sprache, frage in versuche:
            response = await client.get(
                f"https://{sprache}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": frage,
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


async def texte_nachladen(treffer: list[dict], anzahl: int = MAX_READ) -> None:
    ziele = [
        eintrag
        for eintrag in treffer
        if eintrag.get("url") and not eintrag.get("auszug")
    ][:anzahl]
    if not ziele:
        return
    sucher = WebSearch()
    async with sucher._client() as client:
        await asyncio.gather(
            *(sucher._read_one(client, eintrag) for eintrag in ziele),
            return_exceptions=True,
        )
