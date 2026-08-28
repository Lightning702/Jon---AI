from __future__ import annotations

import re

from app.core.config import get_settings

from .base import Place
from .http import post_json
from .nominatim import haversine_m

CATEGORIES: dict[str, dict[str, object]] = {
    "restaurant": {
        "label": "Restaurants",
        "icon": "🍽️",
        "match": {"amenity": ("restaurant", "fast_food", "food_court")},
    },
    "cafe": {
        "label": "Cafés",
        "icon": "☕",
        "match": {"amenity": ("cafe", "ice_cream")},
    },
    "bar": {"label": "Bars", "icon": "🍸", "match": {"amenity": ("bar", "pub")}},
    "hotel": {
        "label": "Hotels",
        "icon": "🏨",
        "match": {
            "tourism": ("hotel", "hostel", "guest_house", "motel", "apartment")
        },
    },
    "supermarkt": {
        "label": "Supermärkte",
        "icon": "🛒",
        "match": {"shop": ("supermarket", "convenience", "greengrocer")},
    },
    "baeckerei": {
        "label": "Bäckereien",
        "icon": "🥐",
        "match": {"shop": ("bakery", "pastry")},
    },
    "drogerie": {
        "label": "Drogerien",
        "icon": "🧴",
        "match": {"shop": ("chemist", "cosmetics", "perfumery")},
    },
    "geschaeft": {"label": "Geschäfte", "icon": "🛍️", "match": {"shop": ()}},
    "tankstelle": {
        "label": "Tankstellen",
        "icon": "⛽",
        "match": {"amenity": ("fuel",)},
    },
    "ladesaeule": {
        "label": "Ladesäulen",
        "icon": "🔌",
        "match": {"amenity": ("charging_station",)},
    },
    "apotheke": {
        "label": "Apotheken",
        "icon": "💊",
        "match": {"amenity": ("pharmacy",)},
    },
    "arzt": {
        "label": "Ärzte & Kliniken",
        "icon": "🏥",
        "match": {"amenity": ("doctors", "hospital", "clinic")},
    },
    "bank": {
        "label": "Banken & Geldautomaten",
        "icon": "🏧",
        "match": {"amenity": ("bank", "atm")},
    },
    "post": {
        "label": "Post & Paket",
        "icon": "📮",
        "match": {"amenity": ("post_office",), "shop": ("kiosk",)},
    },
    "bahnhof": {
        "label": "Bahnhöfe",
        "icon": "🚉",
        "match": {
            "railway": ("station", "halt"),
            "public_transport": ("station",),
        },
    },
    "haltestelle": {
        "label": "Haltestellen",
        "icon": "🚌",
        "match": {"highway": ("bus_stop",), "railway": ("tram_stop",)},
    },
    "flughafen": {
        "label": "Flughäfen",
        "icon": "✈️",
        "match": {"aeroway": ("aerodrome",)},
    },
    "park": {
        "label": "Parks & Grün",
        "icon": "🌳",
        "match": {"leisure": ("park", "garden", "nature_reserve")},
    },
    "sehenswuerdigkeit": {
        "label": "Sehenswürdigkeiten",
        "icon": "📸",
        "match": {
            "tourism": (
                "attraction",
                "museum",
                "viewpoint",
                "artwork",
                "gallery",
                "zoo",
            ),
            "historic": ("castle", "monument", "memorial", "ruins", "church"),
        },
    },
    "parken": {
        "label": "Parkplätze",
        "icon": "🅿️",
        "match": {"amenity": ("parking",)},
    },
    "toilette": {
        "label": "Toiletten",
        "icon": "🚻",
        "match": {"amenity": ("toilets",)},
    },
    "sport": {
        "label": "Sport & Fitness",
        "icon": "🏋️",
        "match": {
            "leisure": ("fitness_centre", "sports_centre", "swimming_pool")
        },
    },
}

_ALIASES = {
    "restaurants": "restaurant",
    "essen": "restaurant",
    "mittagessen": "restaurant",
    "abendessen": "restaurant",
    "imbiss": "restaurant",
    "pizza": "restaurant",
    "pizzeria": "restaurant",
    "gasthaus": "restaurant",
    "wirtshaus": "restaurant",
    "cafes": "cafe",
    "kaffee": "cafe",
    "konditorei": "cafe",
    "bars": "bar",
    "kneipe": "bar",
    "pub": "bar",
    "hotels": "hotel",
    "uebernachtung": "hotel",
    "übernachtung": "hotel",
    "pension": "hotel",
    "supermarket": "supermarkt",
    "supermaerkte": "supermarkt",
    "supermärkte": "supermarkt",
    "lebensmittel": "supermarkt",
    "lebensmittelgeschaeft": "supermarkt",
    "lebensmittelgeschäft": "supermarkt",
    "einkaufen": "supermarkt",
    "einkauf": "supermarkt",
    "baecker": "baeckerei",
    "bäcker": "baeckerei",
    "bäckerei": "baeckerei",
    "baeckereien": "baeckerei",
    "bäckereien": "baeckerei",
    "brot": "baeckerei",
    "drogerien": "drogerie",
    "drogeriemarkt": "drogerie",
    "parfuemerie": "drogerie",
    "parfümerie": "drogerie",
    "laden": "geschaeft",
    "geschaefte": "geschaeft",
    "geschäft": "geschaeft",
    "geschäfte": "geschaeft",
    "shops": "geschaeft",
    "shop": "geschaeft",
    "shopping": "geschaeft",
    "tanken": "tankstelle",
    "tankstellen": "tankstelle",
    "benzin": "tankstelle",
    "diesel": "tankstelle",
    "sprit": "tankstelle",
    "strom": "ladesaeule",
    "ladestation": "ladesaeule",
    "ladesaeulen": "ladesaeule",
    "ladesäule": "ladesaeule",
    "ladesäulen": "ladesaeule",
    "apotheken": "apotheke",
    "medikamente": "apotheke",
    "notapotheke": "apotheke",
    "krankenhaus": "arzt",
    "spital": "arzt",
    "klinik": "arzt",
    "aerzte": "arzt",
    "ärzte": "arzt",
    "arztpraxis": "arzt",
    "doktor": "arzt",
    "banken": "bank",
    "geldautomat": "bank",
    "bankomat": "bank",
    "atm": "bank",
    "postamt": "post",
    "postfiliale": "post",
    "paketshop": "post",
    "bahn": "bahnhof",
    "zug": "bahnhof",
    "bahnhoefe": "bahnhof",
    "bahnhöfe": "bahnhof",
    "hauptbahnhof": "bahnhof",
    "bus": "haltestelle",
    "bushaltestelle": "haltestelle",
    "haltestellen": "haltestelle",
    "tram": "haltestelle",
    "strassenbahn": "haltestelle",
    "straßenbahn": "haltestelle",
    "airport": "flughafen",
    "flughaefen": "flughafen",
    "flughäfen": "flughafen",
    "gruen": "park",
    "grün": "park",
    "parks": "park",
    "museum": "sehenswuerdigkeit",
    "museen": "sehenswuerdigkeit",
    "attraktion": "sehenswuerdigkeit",
    "sehenswuerdigkeiten": "sehenswuerdigkeit",
    "sehenswürdigkeit": "sehenswuerdigkeit",
    "sehenswürdigkeiten": "sehenswuerdigkeit",
    "burg": "sehenswuerdigkeit",
    "schloss": "sehenswuerdigkeit",
    "parkplatz": "parken",
    "parkplaetze": "parken",
    "parkplätze": "parken",
    "parkhaus": "parken",
    "wc": "toilette",
    "toiletten": "toilette",
    "klo": "toilette",
    "fitness": "sport",
    "fitnessstudio": "sport",
    "gym": "sport",
    "schwimmbad": "sport",
    "hallenbad": "sport",
}

_BRANDS = {
    "interspar": "supermarkt",
    "spar": "supermarkt",
    "eurospar": "supermarkt",
    "billa": "supermarkt",
    "hofer": "supermarkt",
    "lidl": "supermarkt",
    "aldi": "supermarkt",
    "penny": "supermarkt",
    "rewe": "supermarkt",
    "edeka": "supermarkt",
    "netto": "supermarkt",
    "merkur": "supermarkt",
    "mpreis": "supermarkt",
    "adeg": "supermarkt",
    "unimarkt": "supermarkt",
    "kaufland": "supermarkt",
    "norma": "supermarkt",
    "denns": "supermarkt",
    "dm": "drogerie",
    "bipa": "drogerie",
    "rossmann": "drogerie",
    "douglas": "drogerie",
    "anker": "baeckerei",
    "stroeck": "baeckerei",
    "ströck": "baeckerei",
    "backwerk": "baeckerei",
    "omv": "tankstelle",
    "shell": "tankstelle",
    "aral": "tankstelle",
    "jet": "tankstelle",
    "eni": "tankstelle",
    "esso": "tankstelle",
    "turmoel": "tankstelle",
    "turmöl": "tankstelle",
    "avanti": "tankstelle",
    "mcdonalds": "restaurant",
    "mc_donalds": "restaurant",
    "burger_king": "restaurant",
    "kfc": "restaurant",
    "subway": "restaurant",
    "vapiano": "restaurant",
    "nordsee": "restaurant",
    "starbucks": "cafe",
    "aida": "cafe",
    "hervis": "sport",
    "intersport": "sport",
    "decathlon": "sport",
    "mediamarkt": "geschaeft",
    "media_markt": "geschaeft",
    "saturn": "geschaeft",
    "hornbach": "geschaeft",
    "obi": "geschaeft",
    "bauhaus": "geschaeft",
    "ikea": "geschaeft",
}

_FILLER = re.compile(
    r"\b(?:"
    r"in\s+(?:der|meiner|meinem|unserer)\s+(?:n[aä]he|naehe|umgebung|gegend)"
    r"|hier\s+in\s+der\s+(?:n[aä]he|naehe)"
    r"|ganz\s+in\s+der\s+(?:n[aä]he|naehe)"
    r"|um\s+mich(?:\s+herum)?"
    r"|bei\s+mir"
    r"|near\s+me|nearby|around\s+me|close\s+by"
    r")\b",
    re.IGNORECASE,
)

_NEAR_WORD = re.compile(
    r"\b(?:n[aä]chst\w*|naechst\w*|n[aä]he|naehe|umgebung|nearest|closest|hier)\b",
    re.IGNORECASE,
)

_STOPWORDS = {
    "der",
    "die",
    "das",
    "den",
    "dem",
    "des",
    "ein",
    "eine",
    "einen",
    "einem",
    "einer",
    "eines",
    "zum",
    "zur",
    "zu",
    "nach",
    "beim",
    "bei",
    "am",
    "an",
    "im",
    "in",
    "von",
    "vom",
    "gute",
    "guter",
    "gutes",
    "guten",
    "beste",
    "bester",
    "bestes",
    "besten",
    "irgendein",
    "irgendeine",
    "irgendeinen",
    "the",
    "a",
    "any",
    "mir",
    "mich",
    "me",
}

_WORDS = re.compile(r"[^0-9a-zA-ZäöüÄÖÜßéèêáàâíìîóòôúùû]+")


def wants_nearby(value: str) -> bool:
    text = value or ""
    return bool(_FILLER.search(text) or _NEAR_WORD.search(text))


def strip_nearby(value: str) -> str:
    text = _FILLER.sub(" ", value or "")
    text = _NEAR_WORD.sub(" ", text)
    return " ".join(text.split()).strip(" ,-·")


def _normalise(value: str) -> str:
    words = [
        word
        for word in _WORDS.split(strip_nearby(value).lower())
        if word and word not in _STOPWORDS
    ]
    return "_".join(words)


def resolve_category(value: str) -> str:
    key = _normalise(value)
    if not key:
        return ""
    if key in CATEGORIES:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    singular = key.rstrip("s") if key.endswith("s") else key
    if singular in CATEGORIES:
        return singular
    if singular in _ALIASES:
        return _ALIASES[singular]
    return ""


def resolve_brand(value: str) -> str:
    key = _normalise(value)
    if not key:
        return ""
    if key in _BRANDS:
        return _BRANDS[key]
    for word in key.split("_"):
        if word in _BRANDS:
            return _BRANDS[word]
    return ""


def split_query(value: str) -> tuple[str, str]:
    cleaned = strip_nearby(value)
    if not cleaned:
        return "", ""
    direct = resolve_category(cleaned)
    if direct:
        return direct, ""
    brand = resolve_brand(cleaned)
    if brand:
        rest = " ".join(
            word for word in cleaned.split() if not resolve_category(word)
        ).strip(" ,-·")
        return brand, rest or cleaned
    words = cleaned.split()
    for index, word in enumerate(words):
        found = resolve_category(word)
        if found:
            rest = " ".join(words[:index] + words[index + 1 :]).strip(" ,-·")
            return found, rest
    return "", cleaned


def category_list() -> list[dict[str, str]]:
    return [
        {"id": key, "label": str(value["label"]), "icon": str(value["icon"])}
        for key, value in CATEGORIES.items()
    ]


def category_label(key: str) -> str:
    spec = CATEGORIES.get(key)
    return str(spec["label"]) if spec else ""


def category_icon(key: str) -> str:
    spec = CATEGORIES.get(key)
    return str(spec["icon"]) if spec else "📍"


def _match(key: str) -> dict[str, tuple[str, ...]]:
    spec = CATEGORIES.get(key) or {}
    raw = dict(spec.get("match") or {})
    return {str(tag): tuple(values) for tag, values in raw.items()}


def category_filters(key: str) -> list[str]:
    parts: list[str] = []
    for tag, values in _match(key).items():
        if not values:
            parts.append(f'["{tag}"]')
        elif len(values) == 1:
            parts.append(f'["{tag}"="{values[0]}"]')
        else:
            parts.append(f'["{tag}"~"^({"|".join(values)})$"]')
    return parts


def detect_category(tags: dict[str, str]) -> str:
    for key in CATEGORIES:
        for tag, values in _match(key).items():
            value = str(tags.get(tag) or "")
            if not value:
                continue
            if not values or value in values:
                return key
    return ""


def name_regex(name: str) -> str:
    parts = [part for part in _WORDS.split(name or "") if part]
    return ".*".join(parts)


_NAME_KEYS = ("shop", "amenity", "tourism", "leisure", "office", "healthcare")

_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)


class OverpassProvider:
    name = "overpass"

    def __init__(self) -> None:
        base = get_settings().overpass_base_url
        self._base = base
        self._endpoints = [base] + [url for url in _MIRRORS if url != base]

    def _query(self, category: str, lat: float, lon: float, radius_m: int) -> str:
        parts = []
        for element in ("node", "way"):
            for filt in category_filters(category):
                parts.append(f"{element}{filt}(around:{radius_m},{lat},{lon});")
        return f"[out:json][timeout:25];({''.join(parts)});out center tags 60;"

    def _name_query(
        self, pattern: str, category: str, lat: float, lon: float, radius_m: int
    ) -> str:
        name = f'["name"~"{pattern}",i]'
        filters = (
            category_filters(category)
            if category
            else [f'["{key}"]' for key in _NAME_KEYS]
        )
        parts = []
        for element in ("node", "way"):
            for filt in filters:
                parts.append(
                    f"{element}{name}{filt}(around:{radius_m},{lat},{lon});"
                )
        return f"[out:json][timeout:25];({''.join(parts)});out center tags 60;"

    async def _post(self, query: str) -> dict:
        letzter: Exception | None = None
        for url in list(self._endpoints):
            try:
                data = await post_json(
                    url,
                    data=query,
                    ttl=600.0,
                    bucket="overpass",
                    min_interval=1.0,
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                )
            except Exception as exc:
                letzter = exc
                continue
            if url != self._endpoints[0]:
                self._endpoints.remove(url)
                self._endpoints.insert(0, url)
            return data if isinstance(data, dict) else {}
        if letzter is not None:
            raise letzter
        return {}

    async def _collect(
        self, query: str, category: str, lat: float, lon: float, limit: int
    ) -> list[Place]:
        data = await self._post(query)
        elements = data.get("elements") if isinstance(data, dict) else None
        if not isinstance(elements, list):
            return []
        places: list[Place] = []
        seen: set[str] = set()
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = element.get("tags") or {}
            title = str(tags.get("name") or "").strip()
            if not title:
                continue
            center = element.get("center") or {}
            plat = float(element.get("lat") or center.get("lat") or 0.0)
            plon = float(element.get("lon") or center.get("lon") or 0.0)
            if not plat and not plon:
                continue
            marker = f"{title.lower()}|{round(plat, 4)}|{round(plon, 4)}"
            if marker in seen:
                continue
            seen.add(marker)
            key = category or detect_category(tags)
            street = str(tags.get("addr:street") or "")
            number = str(tags.get("addr:housenumber") or "")
            city = str(tags.get("addr:city") or "")
            label = ", ".join(
                part for part in [f"{street} {number}".strip(), city] if part
            )
            places.append(
                Place(
                    id=f"osm:{element.get('type', 'n')}:{element.get('id', '')}",
                    name=title,
                    label=label or category_label(key) or "Ort",
                    lat=plat,
                    lon=plon,
                    kind="poi",
                    category=category_label(key),
                    address={
                        k.removeprefix("addr:"): str(v)
                        for k, v in tags.items()
                        if k.startswith("addr:")
                    },
                    distance_m=haversine_m(lat, lon, plat, plon),
                    source=self.name,
                    extra={
                        "icon": category_icon(key),
                        "kategorie": key,
                        "marke": str(tags.get("brand") or tags.get("operator") or ""),
                        "webseite": str(
                            tags.get("website") or tags.get("contact:website") or ""
                        ),
                        "telefon": str(
                            tags.get("phone") or tags.get("contact:phone") or ""
                        ),
                        "oeffnungszeiten": str(tags.get("opening_hours") or ""),
                        "kueche": str(tags.get("cuisine") or ""),
                    },
                )
            )
        places.sort(key=lambda p: p.distance_m or 0.0)
        return places[: max(1, min(int(limit), 60))]

    @staticmethod
    def _radius(radius_m: int) -> int:
        return max(100, min(int(radius_m), 25000))

    async def nearby(
        self,
        category: str,
        lat: float,
        lon: float,
        radius_m: int = 1500,
        limit: int = 20,
    ) -> list[Place]:
        key = resolve_category(category)
        if not key:
            return []
        query = self._query(key, lat, lon, self._radius(radius_m))
        return await self._collect(query, key, lat, lon, limit)

    async def named(
        self,
        name: str,
        lat: float,
        lon: float,
        radius_m: int = 5000,
        category: str = "",
        limit: int = 20,
    ) -> list[Place]:
        pattern = name_regex(name)
        if len(pattern.replace(".*", "")) < 2:
            return []
        key = resolve_category(category) if category else ""
        query = self._name_query(pattern, key, lat, lon, self._radius(radius_m))
        return await self._collect(query, key, lat, lon, limit)
