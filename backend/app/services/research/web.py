from __future__ import annotations

import asyncio
import html
import ipaddress
import re
import urllib.parse

import httpx

from app.core.config import get_settings

ALLOWED_SCHEMES = ("http", "https")

BLOCKED_PATH_WORDS = (
    "/login",
    "/signin",
    "/sign-in",
    "/signup",
    "/sign-up",
    "/register",
    "/account",
    "/checkout",
    "/cart",
    "/basket",
    "/payment",
    "/bezahlen",
    "/warenkorb",
    "/anmelden",
    "/registrieren",
    "/logout",
    "/oauth",
    "/auth/",
    "/admin",
    "/upload",
    "/delete",
)

BLOCKED_SUFFIXES = (
    ".exe",
    ".msi",
    ".dmg",
    ".pkg",
    ".apk",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".jar",
    ".zip",
    ".rar",
    ".7z",
    ".iso",
    ".bin",
    ".dll",
    ".scr",
)

ALLOWED_TYPES = (
    "text/html",
    "text/plain",
    "application/xhtml",
    "application/json",
    "application/xml",
    "text/xml",
)

MAX_BYTES = 3_000_000

_SCRIPT_RE = re.compile(
    r"<(script|style|noscript|svg|canvas|iframe|form|nav|footer|aside)[^>]*>.*?</\1>",
    re.I | re.S,
)
_HEAD_RE = re.compile(r"<head[^>]*>.*?</head>", re.I | re.S)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_BLOCK_RE = re.compile(
    r"</?(p|div|section|article|br|li|tr|blockquote|pre|table)[^>]*>",
    re.I,
)
_HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.I | re.S)
_MAIN_RE = re.compile(r"<(main|article)[^>]*>(.*?)</\1>", re.I | re.S)
_HEADER_RE = re.compile(r"<header[^>]*>.*?</header>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")
_MIN_LINE = 45


class UnsafeUrl(RuntimeError):
    pass


def domain_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def check_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrl("Nur http und https sind erlaubt")
    host = parsed.hostname or ""
    if not host:
        raise UnsafeUrl("Keine gültige Adresse")
    if host in ("localhost", "127.0.0.1", "::1"):
        raise UnsafeUrl("Lokale Adressen sind für die Recherche gesperrt")
    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local:
            raise UnsafeUrl("Adressen im lokalen Netz sind gesperrt")
    except ValueError:
        pass
    lowered = parsed.path.lower()
    for word in BLOCKED_PATH_WORDS:
        if word in lowered:
            raise UnsafeUrl("Seiten mit Anmeldung oder Kauf werden nicht geöffnet")
    for suffix in BLOCKED_SUFFIXES:
        if lowered.endswith(suffix):
            raise UnsafeUrl("Ausführbare oder gepackte Dateien werden nicht geladen")
    return urllib.parse.urlunparse(parsed)


def extract_text(raw: str) -> tuple[str, str]:
    title_match = _TITLE_RE.search(raw)
    title = (
        html.unescape(_TAG_RE.sub("", title_match.group(1))).strip()
        if title_match
        else ""
    )
    body = _HEAD_RE.sub(" ", raw)
    body = _COMMENT_RE.sub(" ", body)
    body = _HEADER_RE.sub(" ", body)
    body = _SCRIPT_RE.sub(" ", body)
    candidates = [match.group(2) for match in _MAIN_RE.finditer(body)]
    if candidates:
        body = max(candidates, key=len)
    body = _HEADING_RE.sub(
        lambda match: "\n\n" + "#" * int(match.group(1)) + " " + match.group(2) + "\n",
        body,
    )
    body = _BLOCK_RE.sub("\n", body)
    body = _TAG_RE.sub(" ", body)
    body = html.unescape(body)
    body = _WS_RE.sub(" ", body)
    kept: list[str] = []
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                kept.append("## " + heading)
            continue
        if len(stripped) >= _MIN_LINE or (
            len(stripped) >= 20 and stripped[-1] in ".!?:)"
        ):
            kept.append(stripped)
    text = _NL_RE.sub("\n\n", "\n".join(kept))
    return title, text.strip()


class ResearchWeb:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(18.0, connect=8.0),
                        follow_redirects=True,
                        max_redirects=4,
                        headers={
                            "User-Agent": get_settings().maps_user_agent,
                            "Accept": "text/html,application/xhtml+xml,text/plain",
                            "Accept-Language": "de,en;q=0.8",
                        },
                    )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def search(self, query: str, limit: int = 8) -> list[dict]:
        results: list[dict] = []
        seen: set[str] = set()
        for hit in await self._wikipedia(query, 3):
            if hit["url"] not in seen:
                seen.add(hit["url"])
                results.append(hit)
        for hit in await self._duckduckgo(query, limit):
            if hit["url"] not in seen:
                seen.add(hit["url"])
                results.append(hit)
        return results[: max(1, limit + 3)]

    async def _duckduckgo(self, query: str, limit: int) -> list[dict]:
        from app.services.system_service import SystemService

        try:
            raw = await asyncio.to_thread(
                SystemService().web_search, query, max(1, min(limit, 10))
            )
        except Exception:
            return []
        hits: list[dict] = []
        for item in raw:
            url = str(item.get("url") or "")
            try:
                url = check_url(url)
            except UnsafeUrl:
                continue
            hits.append(
                {
                    "title": str(item.get("title") or url),
                    "url": url,
                    "snippet": str(item.get("snippet") or ""),
                    "engine": "duckduckgo",
                }
            )
        return hits

    async def _wikipedia(self, query: str, limit: int) -> list[dict]:
        client = await self._http()
        hits: list[dict] = []
        for language in ("de", "en"):
            try:
                response = await client.get(
                    f"https://{language}.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "srlimit": limit,
                    },
                )
                response.raise_for_status()
                data = response.json()
            except Exception:
                continue
            for item in (data.get("query") or {}).get("search") or []:
                title = str(item.get("title") or "")
                if not title:
                    continue
                slug = urllib.parse.quote(title.replace(" ", "_"))
                hits.append(
                    {
                        "title": title,
                        "url": f"https://{language}.wikipedia.org/wiki/{slug}",
                        "snippet": re.sub(
                            r"<[^>]+>", "", str(item.get("snippet") or "")
                        ),
                        "engine": f"wikipedia-{language}",
                    }
                )
            if hits:
                break
        return hits

    async def fetch(self, url: str, max_chars: int = 14000) -> dict:
        safe = check_url(url)
        client = await self._http()
        async with client.stream("GET", safe) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if not any(kind in content_type for kind in ALLOWED_TYPES):
                raise UnsafeUrl(f"Nicht lesbarer Inhaltstyp: {content_type or '?'}")
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_BYTES:
                    break
            body = b"".join(chunks)
            encoding = response.encoding or "utf-8"
        raw = body.decode(encoding, errors="replace")
        title, text = extract_text(raw)
        return {
            "url": safe,
            "domain": domain_of(safe),
            "title": title,
            "text": text[:max_chars],
            "chars": len(text),
        }


_web: ResearchWeb | None = None


def get_research_web() -> ResearchWeb:
    global _web
    if _web is None:
        _web = ResearchWeb()
    return _web
