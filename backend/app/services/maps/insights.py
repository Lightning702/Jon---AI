from __future__ import annotations

import asyncio
import html
import re
import urllib.parse
from datetime import datetime, timezone

from app.services.system_service import WEATHER_CODES

import httpx

from .http import cached, get_client, get_json, store

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_NEWS_URL = "https://news.google.com/rss/search"
BING_NEWS_URL = "https://www.bing.com/news/search"

WEATHER_TTL = 600.0
NEWS_TTL = 900.0
GDELT_TIMEOUT = 6.0
GDELT_CONNECT = 2.5
MAX_AGE_DAYS = 14

COUNTRY_NAMES = {
    "at": "austria",
    "de": "germany",
    "ch": "switzerland",
    "li": "liechtenstein",
    "lu": "luxembourg",
    "fr": "france",
    "it": "italy",
    "es": "spain",
    "pt": "portugal",
    "nl": "netherlands",
    "be": "belgium",
    "dk": "denmark",
    "se": "sweden",
    "no": "norway",
    "fi": "finland",
    "is": "iceland",
    "ie": "ireland",
    "gb": "unitedkingdom",
    "uk": "unitedkingdom",
    "pl": "poland",
    "cz": "czechrepublic",
    "sk": "slovakia",
    "hu": "hungary",
    "si": "slovenia",
    "hr": "croatia",
    "ba": "bosniaandherzegovina",
    "rs": "serbia",
    "me": "montenegro",
    "mk": "macedonia",
    "al": "albania",
    "gr": "greece",
    "bg": "bulgaria",
    "ro": "romania",
    "md": "moldova",
    "ua": "ukraine",
    "by": "belarus",
    "ru": "russia",
    "lt": "lithuania",
    "lv": "latvia",
    "ee": "estonia",
    "tr": "turkey",
    "cy": "cyprus",
    "mt": "malta",
    "us": "unitedstates",
    "ca": "canada",
    "mx": "mexico",
    "br": "brazil",
    "ar": "argentina",
    "cl": "chile",
    "co": "colombia",
    "pe": "peru",
    "uy": "uruguay",
    "au": "australia",
    "nz": "newzealand",
    "jp": "japan",
    "cn": "china",
    "kr": "southkorea",
    "in": "india",
    "id": "indonesia",
    "th": "thailand",
    "vn": "vietnam",
    "ph": "philippines",
    "my": "malaysia",
    "sg": "singapore",
    "il": "israel",
    "ae": "unitedarabemirates",
    "sa": "saudiarabia",
    "eg": "egypt",
    "ma": "morocco",
    "tn": "tunisia",
    "za": "southafrica",
    "ng": "nigeria",
    "ke": "kenya",
}

COUNTRY_LANGS = {
    "at": ("german", "de", "AT"),
    "de": ("german", "de", "DE"),
    "ch": ("german", "de", "CH"),
    "li": ("german", "de", "AT"),
    "lu": ("french", "fr", "FR"),
    "fr": ("french", "fr", "FR"),
    "be": ("dutch", "nl", "BE"),
    "nl": ("dutch", "nl", "NL"),
    "it": ("italian", "it", "IT"),
    "es": ("spanish", "es", "ES"),
    "pt": ("portuguese", "pt", "PT"),
    "br": ("portuguese", "pt", "BR"),
    "mx": ("spanish", "es", "MX"),
    "ar": ("spanish", "es", "AR"),
    "cl": ("spanish", "es", "CL"),
    "co": ("spanish", "es", "CO"),
    "pe": ("spanish", "es", "PE"),
    "dk": ("danish", "da", "DK"),
    "se": ("swedish", "sv", "SE"),
    "no": ("norwegian", "no", "NO"),
    "fi": ("finnish", "fi", "FI"),
    "is": ("icelandic", "is", "IS"),
    "pl": ("polish", "pl", "PL"),
    "cz": ("czech", "cs", "CZ"),
    "sk": ("slovak", "sk", "SK"),
    "hu": ("hungarian", "hu", "HU"),
    "si": ("slovenian", "sl", "SI"),
    "hr": ("croatian", "hr", "HR"),
    "rs": ("serbian", "sr", "RS"),
    "gr": ("greek", "el", "GR"),
    "bg": ("bulgarian", "bg", "BG"),
    "ro": ("romanian", "ro", "RO"),
    "ua": ("ukrainian", "uk", "UA"),
    "ru": ("russian", "ru", "RU"),
    "tr": ("turkish", "tr", "TR"),
    "jp": ("japanese", "ja", "JP"),
    "cn": ("chinese", "zh-CN", "CN"),
    "kr": ("korean", "ko", "KR"),
    "th": ("thai", "th", "TH"),
    "vn": ("vietnamese", "vi", "VN"),
    "id": ("indonesian", "id", "ID"),
    "il": ("hebrew", "he", "IL"),
    "sa": ("arabic", "ar", "SA"),
    "ae": ("arabic", "ar", "AE"),
    "eg": ("arabic", "ar", "EG"),
    "ma": ("arabic", "ar", "MA"),
}

DEFAULT_LANG = ("english", "en", "US")

BLOCKED_DOMAINS = {"news.google.com", "google.com", "youtube.com"}
REDIRECT_DOMAINS = BLOCKED_DOMAINS | {"bing.com", "news.search.yahoo.com"}

_TAG_RE = re.compile(r"<[^>]+>")
_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
_FIELD_RE = {
    "title": re.compile(r"<title>(.*?)</title>", re.S),
    "link": re.compile(r"<link>(.*?)</link>", re.S),
    "date": re.compile(r"<pubDate>(.*?)</pubDate>", re.S),
    "source": re.compile(r"<source[^>]*>(.*?)</source>", re.S),
    "source_url": re.compile(r"""<source[^>]+url=["']([^"']+)["']""", re.S),
    "bing_source": re.compile(r"<News:Source>(.*?)</News:Source>", re.S),
    "bing_image": re.compile(r"<News:Image>(.*?)</News:Image>", re.S),
}


def _clean(text: str) -> str:
    value = _TAG_RE.sub(" ", text)
    value = value.replace("<![CDATA[", "").replace("]]>", "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _lang_for(code: str) -> tuple[str, str, str]:
    return COUNTRY_LANGS.get(code.lower(), DEFAULT_LANG)


def _domain(url: str) -> str:
    match = re.match(r"https?://([^/]+)", url)
    if not match:
        return ""
    return match.group(1).lower().removeprefix("www.")


def _source_name(domain: str) -> str:
    if not domain:
        return "Quelle"
    parts = domain.split(".")
    if len(parts) > 2 and parts[0] in {"m", "amp", "news"}:
        parts = parts[1:]
    return parts[0].replace("-", " ").title()


def _gdelt_time(value: str) -> str:
    try:
        stamp = datetime.strptime(value.strip(), "%Y%m%dT%H%M%SZ")
        return stamp.replace(tzinfo=timezone.utc).isoformat()
    except Exception:
        return ""


def _rss_time(value: str) -> str:
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            stamp = datetime.strptime(value.strip(), fmt)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return stamp.astimezone(timezone.utc).isoformat()
        except Exception:
            continue
    return ""


def _article(
    title: str, url: str, image: str, published: str, scope: str
) -> dict | None:
    clean_title = _clean(title)
    if not clean_title or not url.startswith("http"):
        return None
    domain = _domain(url)
    if not domain or domain in BLOCKED_DOMAINS:
        return None
    return {
        "titel": clean_title[:180],
        "url": url,
        "quelle": _source_name(domain),
        "domain": domain,
        "bild": image if image.startswith("http") else "",
        "zeit": published,
        "bereich": scope,
    }


def _fresh(item: dict) -> bool:
    stamp = item.get("zeit") or ""
    if not stamp:
        return True
    try:
        published = datetime.fromisoformat(stamp)
    except ValueError:
        return True
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - published
    return age.days <= MAX_AGE_DAYS


def _merge(groups: list[list[dict]], limit: int) -> list[dict]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    merged: list[dict] = []
    for group in groups:
        for item in group:
            if not _fresh(item):
                continue
            key = item["url"].split("?")[0].rstrip("/").lower()
            title_key = re.sub(r"\W+", "", item["titel"].lower())[:60]
            if key in seen_urls or title_key in seen_titles:
                continue
            seen_urls.add(key)
            seen_titles.add(title_key)
            merged.append(item)
            if len(merged) >= limit:
                return merged
    return merged


async def _gdelt(query: str, country: str, lang: str, limit: int, scope: str) -> list[dict]:
    terms = [f'"{query}"' if " " in query else query]
    if country:
        terms.append(f"sourcecountry:{country}")
    if lang:
        terms.append(f"sourcelang:{lang}")
    params = {
        "query": " ".join(terms),
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max(5, min(limit * 3, 25)),
        "sort": "datedesc",
        "timespan": "5d",
    }
    key = f"gdelt:{params['query']}:{params['maxrecords']}"
    hit = await cached(key, NEWS_TTL)
    if hit is not None:
        return hit
    try:
        client = await get_client()
        response = await client.get(
            GDELT_URL,
            params=params,
            timeout=httpx.Timeout(GDELT_TIMEOUT, connect=GDELT_CONNECT),
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    found: list[dict] = []
    for raw in data.get("articles") or []:
        if not isinstance(raw, dict):
            continue
        item = _article(
            str(raw.get("title") or ""),
            str(raw.get("url") or ""),
            str(raw.get("socialimage") or ""),
            _gdelt_time(str(raw.get("seendate") or "")),
            scope,
        )
        if item:
            found.append(item)
    await store(key, found)
    return found


def _bing_market(code: str) -> tuple[str, str]:
    _, short, region = _lang_for(code)
    if "-" in short:
        return short, short.split("-")[0]
    return f"{short}-{region}", short


def _bing_target(link: str) -> str:
    value = html.unescape(link.strip())
    match = re.search(r"[?&]url=([^&]+)", value)
    if match:
        return urllib.parse.unquote(match.group(1))
    return value


def _bing_image(raw: str) -> str:
    value = html.unescape(raw.strip())
    if not value.startswith("http"):
        return ""
    value = value.replace("http://", "https://", 1)
    return value + "&w=320&h=220&c=14"


async def _bing_news(query: str, code: str, limit: int, scope: str) -> list[dict]:
    market, language = _bing_market(code)
    key = f"bing:{query}:{market}:{limit}"
    hit = await cached(key, NEWS_TTL)
    if hit is not None:
        return hit
    try:
        client = await get_client()
        response = await client.get(
            BING_NEWS_URL,
            params={
                "q": query,
                "format": "RSS",
                "setmkt": market,
                "setlang": language,
            },
        )
        response.raise_for_status()
        body = response.text
    except Exception:
        return []
    found: list[dict] = []
    for block in _ITEM_RE.findall(body)[: limit * 4]:
        title = _FIELD_RE["title"].search(block)
        link = _FIELD_RE["link"].search(block)
        if not title or not link:
            continue
        url = _bing_target(link.group(1))
        domain = _domain(url)
        if not url.startswith("http") or not domain or domain in REDIRECT_DOMAINS:
            continue
        headline = _clean(title.group(1))
        if not headline:
            continue
        source = _FIELD_RE["bing_source"].search(block)
        image = _FIELD_RE["bing_image"].search(block)
        date = _FIELD_RE["date"].search(block)
        found.append(
            {
                "titel": headline[:180],
                "url": url,
                "quelle": _clean(source.group(1)) if source else _source_name(domain),
                "domain": domain,
                "bild": _bing_image(image.group(1)) if image else "",
                "zeit": _rss_time(date.group(1)) if date else "",
                "bereich": scope,
            }
        )
        if len(found) >= limit * 2:
            break
    await store(key, found)
    return found


async def _google_news(query: str, code: str, limit: int, scope: str) -> list[dict]:
    _, short, region = _lang_for(code)
    key = f"gnews:{query}:{short}:{region}:{limit}"
    hit = await cached(key, NEWS_TTL)
    if hit is not None:
        return hit
    try:
        client = await get_client()
        response = await client.get(
            GOOGLE_NEWS_URL,
            params={
                "q": query,
                "hl": f"{short}-{region}",
                "gl": region,
                "ceid": f"{region}:{short}",
            },
        )
        response.raise_for_status()
        body = response.text
    except Exception:
        return []
    found: list[dict] = []
    for block in _ITEM_RE.findall(body)[: limit * 4]:
        title = _FIELD_RE["title"].search(block)
        link = _FIELD_RE["link"].search(block)
        if not title or not link:
            continue
        url = _clean(link.group(1))
        if not url.startswith("http"):
            continue
        source = _FIELD_RE["source"].search(block)
        source_url = _FIELD_RE["source_url"].search(block)
        date = _FIELD_RE["date"].search(block)
        headline = _clean(title.group(1))
        publisher = _clean(source.group(1)) if source else ""
        if publisher and headline.endswith(f"- {publisher}"):
            headline = headline[: -len(publisher) - 2].strip()
        if not headline:
            continue
        domain = _domain(source_url.group(1)) if source_url else ""
        found.append(
            {
                "titel": headline[:180],
                "url": url,
                "quelle": publisher or _source_name(domain),
                "domain": domain,
                "bild": "",
                "zeit": _rss_time(date.group(1)) if date else "",
                "bereich": scope,
            }
        )
        if len(found) >= limit * 2:
            break
    await store(key, found)
    return found


_OG_IMAGE_RE = re.compile(
    r"""<meta[^>]+(?:property|name)=["']og:image["'][^>]+content=["']([^"']+)""",
    re.I,
)

THUMB_TTL = 21600.0
THUMB_TIMEOUT = 5.0


async def _thumbnail(url: str) -> str:
    key = f"thumb:{url}"
    hit = await cached(key, THUMB_TTL)
    if hit is not None:
        return hit
    image = ""
    try:
        client = await get_client()
        response = await client.get(
            url, timeout=httpx.Timeout(THUMB_TIMEOUT, connect=3.0)
        )
        if response.status_code < 400:
            match = _OG_IMAGE_RE.search(response.text[:1500000])
            if match:
                found = html.unescape(match.group(1)).strip()
                if found.startswith("http"):
                    image = found
    except Exception:
        image = ""
    await store(key, image)
    return image


async def _add_thumbnails(items: list[dict]) -> list[dict]:
    offen = [
        item
        for item in items
        if not item.get("bild") and _domain(item["url"]) not in REDIRECT_DOMAINS
    ]
    if not offen:
        return items
    found = await asyncio.gather(
        *(_thumbnail(item["url"]) for item in offen), return_exceptions=True
    )
    for item, image in zip(offen, found):
        if isinstance(image, str) and image:
            item["bild"] = image
    return items


def _title_key(value: str) -> str:
    return re.sub(r"\W+", "", value.lower())[:48]


def _enrich(items: list[dict], donors: list[dict]) -> list[dict]:
    index: dict[str, str] = {}
    for donor in donors:
        if donor.get("bild"):
            index[_title_key(donor["titel"])] = donor["bild"]
    if not index:
        return items
    for item in items:
        if item.get("bild"):
            continue
        key = _title_key(item["titel"])
        image = index.get(key)
        if not image:
            for other, candidate in index.items():
                if key[:24] and (key[:24] in other or other[:24] in key):
                    image = candidate
                    break
        if image:
            item["bild"] = image
    return items


async def news(
    name: str,
    country: str = "",
    country_code: str = "",
    scope: str = "stadt",
    limit: int = 5,
) -> list[dict]:
    place = name.strip()
    nation = country.strip()
    code = country_code.strip().lower()
    if not place and not nation:
        return []
    limit = max(3, min(int(limit or 5), 8))
    gdelt_country = COUNTRY_NAMES.get(code, "")
    lang = _lang_for(code)[0] if code else ""
    is_city = scope == "stadt" and bool(place) and place.lower() != nation.lower()
    targets = [(place or nation, "lokal" if is_city else "national")]
    if is_city and nation:
        targets.append((nation, "national"))

    tasks = []
    for query, area in targets:
        tasks.append(("direkt", _bing_news(query, code, limit, area)))
        tasks.append(("direkt", _gdelt(query, gdelt_country, lang, limit, area)))
        tasks.append(("feed", _google_news(query, code, limit, area)))
    results = await asyncio.gather(
        *(task for _, task in tasks), return_exceptions=True
    )
    direct: list[list[dict]] = []
    feeds: list[list[dict]] = []
    for (art, _), result in zip(tasks, results):
        if isinstance(result, BaseException) or not result:
            continue
        if art == "direkt":
            direct.append(result)
        else:
            feeds.append(result)
    donors = [item for group in direct for item in group]
    merged = _merge(direct + feeds, limit)
    return await _add_thumbnails(_enrich(merged, donors))


async def weather(lat: float, lon: float, label: str = "") -> dict:
    data = await get_json(
        WEATHER_URL,
        params={
            "latitude": round(float(lat), 3),
            "longitude": round(float(lon), 3),
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
            "precipitation,weather_code,wind_speed_10m,is_day",
            "daily": "precipitation_probability_max,temperature_2m_max,"
            "temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 1,
        },
        ttl=WEATHER_TTL,
    )
    if not isinstance(data, dict):
        raise RuntimeError("Wetterdienst antwortet nicht")
    current = data.get("current") or {}
    daily = data.get("daily") or {}

    def first(key: str):
        values = daily.get(key) or []
        return values[0] if values else None

    code = current.get("weather_code")
    return {
        "ort": label,
        "temperatur": current.get("temperature_2m"),
        "gefuehlt": current.get("apparent_temperature"),
        "luftfeuchte": current.get("relative_humidity_2m"),
        "niederschlag": current.get("precipitation"),
        "regen_prozent": first("precipitation_probability_max"),
        "max": first("temperature_2m_max"),
        "min": first("temperature_2m_min"),
        "wind_kmh": current.get("wind_speed_10m"),
        "code": code,
        "zustand": WEATHER_CODES.get(code, "unbekannt"),
        "tag": bool(current.get("is_day", 1)),
        "stand": str(current.get("time") or ""),
    }


async def place_info(
    lat: float,
    lon: float,
    name: str = "",
    country: str = "",
    country_code: str = "",
    scope: str = "stadt",
    limit: int = 5,
) -> dict:
    label = name.strip() or country.strip()
    results = await asyncio.gather(
        news(name, country, country_code, scope, limit),
        weather(lat, lon, label),
        return_exceptions=True,
    )
    articles, forecast = results
    payload: dict = {
        "ort": label,
        "land": country.strip(),
        "bereich": scope,
        "news": [],
        "news_fehler": "",
        "wetter": None,
        "wetter_fehler": "",
    }
    if isinstance(articles, BaseException):
        payload["news_fehler"] = "Nachrichten sind gerade nicht erreichbar."
    elif not articles:
        payload["news_fehler"] = f"Zu {label} gibt es gerade keine Meldungen."
    else:
        payload["news"] = articles
    if isinstance(forecast, BaseException):
        payload["wetter_fehler"] = "Das Wetter ist gerade nicht erreichbar."
    else:
        payload["wetter"] = forecast
    return payload
