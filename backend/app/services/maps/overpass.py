from __future__ import annotations

from app.core.config import get_settings

from .base import Place
from .http import post_json
from .nominatim import haversine_m

CATEGORIES: dict[str, dict[str, object]] = {
    "restaurant": {
        "label": "Restaurants",
        "icon": "🍽️",
        "filters": ['["amenity"~"^(restaurant|fast_food|food_court)$"]'],
    },
    "cafe": {
        "label": "Cafés",
        "icon": "☕",
        "filters": ['["amenity"~"^(cafe|ice_cream)$"]'],
    },
    "bar": {"label": "Bars", "icon": "🍸", "filters": ['["amenity"~"^(bar|pub)$"]']},
    "hotel": {
        "label": "Hotels",
        "icon": "🏨",
        "filters": ['["tourism"~"^(hotel|hostel|guest_house|motel|apartment)$"]'],
    },
    "supermarkt": {
        "label": "Supermärkte",
        "icon": "🛒",
        "filters": ['["shop"~"^(supermarket|convenience|greengrocer)$"]'],
    },
    "geschaeft": {"label": "Geschäfte", "icon": "🛍️", "filters": ['["shop"]']},
    "tankstelle": {
        "label": "Tankstellen",
        "icon": "⛽",
        "filters": ['["amenity"="fuel"]'],
    },
    "ladesaeule": {
        "label": "Ladesäulen",
        "icon": "🔌",
        "filters": ['["amenity"="charging_station"]'],
    },
    "apotheke": {
        "label": "Apotheken",
        "icon": "💊",
        "filters": ['["amenity"="pharmacy"]'],
    },
    "arzt": {
        "label": "Ärzte & Kliniken",
        "icon": "🏥",
        "filters": ['["amenity"~"^(doctors|hospital|clinic)$"]'],
    },
    "bank": {
        "label": "Banken & Geldautomaten",
        "icon": "🏧",
        "filters": ['["amenity"~"^(bank|atm)$"]'],
    },
    "bahnhof": {
        "label": "Bahnhöfe",
        "icon": "🚉",
        "filters": [
            '["railway"~"^(station|halt)$"]',
            '["public_transport"="station"]',
        ],
    },
    "haltestelle": {
        "label": "Haltestellen",
        "icon": "🚌",
        "filters": ['["highway"="bus_stop"]', '["railway"="tram_stop"]'],
    },
    "flughafen": {
        "label": "Flughäfen",
        "icon": "✈️",
        "filters": ['["aeroway"="aerodrome"]'],
    },
    "park": {
        "label": "Parks & Grün",
        "icon": "🌳",
        "filters": ['["leisure"~"^(park|garden|nature_reserve)$"]'],
    },
    "sehenswuerdigkeit": {
        "label": "Sehenswürdigkeiten",
        "icon": "📸",
        "filters": [
            '["tourism"~"^(attraction|museum|viewpoint|artwork|gallery|zoo)$"]',
            '["historic"~"^(castle|monument|memorial|ruins|church)$"]',
        ],
    },
    "parken": {
        "label": "Parkplätze",
        "icon": "🅿️",
        "filters": ['["amenity"="parking"]'],
    },
    "toilette": {
        "label": "Toiletten",
        "icon": "🚻",
        "filters": ['["amenity"="toilets"]'],
    },
    "sport": {
        "label": "Sport & Fitness",
        "icon": "🏋️",
        "filters": [
            '["leisure"~"^(fitness_centre|sports_centre|swimming_pool)$"]',
        ],
    },
}

_ALIASES = {
    "restaurants": "restaurant",
    "essen": "restaurant",
    "mittagessen": "restaurant",
    "abendessen": "restaurant",
    "imbiss": "restaurant",
    "pizza": "restaurant",
    "cafes": "cafe",
    "kaffee": "cafe",
    "bars": "bar",
    "kneipe": "bar",
    "hotels": "hotel",
    "uebernachtung": "hotel",
    "übernachtung": "hotel",
    "supermarket": "supermarkt",
    "einkaufen": "supermarkt",
    "laden": "geschaeft",
    "shops": "geschaeft",
    "tanken": "tankstelle",
    "benzin": "tankstelle",
    "strom": "ladesaeule",
    "apotheken": "apotheke",
    "krankenhaus": "arzt",
    "klinik": "arzt",
    "geldautomat": "bank",
    "bahn": "bahnhof",
    "zug": "bahnhof",
    "bus": "haltestelle",
    "tram": "haltestelle",
    "airport": "flughafen",
    "gruen": "park",
    "grün": "park",
    "museum": "sehenswuerdigkeit",
    "attraktion": "sehenswuerdigkeit",
    "parkplatz": "parken",
    "wc": "toilette",
    "fitness": "sport",
}


_NEARBY_PHRASES = (
    "in der nähe",
    "in der naehe",
    "in meiner nähe",
    "in meiner naehe",
    "in der umgebung",
    "um mich herum",
    "um mich",
    "hier in der nähe",
    "nearby",
    "near me",
    "hier",
    "nahe",
    "gute",
    "guter",
    "gutes",
    "ein",
    "eine",
    "einen",
)


def _normalise(value: str) -> str:
    text = value.strip().lower()
    for phrase in _NEARBY_PHRASES:
        text = text.replace(phrase, " ")
    text = " ".join(text.split())
    return text.replace(" ", "_")


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


def category_list() -> list[dict[str, str]]:
    return [
        {"id": key, "label": str(value["label"]), "icon": str(value["icon"])}
        for key, value in CATEGORIES.items()
    ]


class OverpassProvider:
    name = "overpass"

    def __init__(self) -> None:
        self._base = get_settings().overpass_base_url

    def _query(self, category: str, lat: float, lon: float, radius_m: int) -> str:
        spec = CATEGORIES[category]
        filters = [str(item) for item in spec["filters"]]
        parts = []
        for element in ("node", "way"):
            for filt in filters:
                parts.append(f"{element}{filt}(around:{radius_m},{lat},{lon});")
        return f"[out:json][timeout:25];({''.join(parts)});out center tags 60;"

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
        radius = max(100, min(int(radius_m), 20000))
        data = await post_json(
            self._base,
            data=self._query(key, lat, lon, radius),
            ttl=600.0,
            bucket="overpass",
            min_interval=1.0,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        elements = data.get("elements") if isinstance(data, dict) else None
        if not isinstance(elements, list):
            return []
        spec = CATEGORIES[key]
        places: list[Place] = []
        seen: set[str] = set()
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = element.get("tags") or {}
            name = str(tags.get("name") or "").strip()
            if not name:
                continue
            center = element.get("center") or {}
            plat = float(element.get("lat") or center.get("lat") or 0.0)
            plon = float(element.get("lon") or center.get("lon") or 0.0)
            if not plat and not plon:
                continue
            marker = f"{name.lower()}|{round(plat, 4)}|{round(plon, 4)}"
            if marker in seen:
                continue
            seen.add(marker)
            street = str(tags.get("addr:street") or "")
            number = str(tags.get("addr:housenumber") or "")
            city = str(tags.get("addr:city") or "")
            label = ", ".join(
                part for part in [f"{street} {number}".strip(), city] if part
            )
            places.append(
                Place(
                    id=f"osm:{element.get('type', 'n')}:{element.get('id', '')}",
                    name=name,
                    label=label or str(spec["label"]),
                    lat=plat,
                    lon=plon,
                    kind="poi",
                    category=str(spec["label"]),
                    address={
                        k.removeprefix("addr:"): str(v)
                        for k, v in tags.items()
                        if k.startswith("addr:")
                    },
                    distance_m=haversine_m(lat, lon, plat, plon),
                    source=self.name,
                    extra={
                        "icon": str(spec["icon"]),
                        "kategorie": key,
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
