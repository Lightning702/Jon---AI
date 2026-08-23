from __future__ import annotations

import math

from app.core.config import get_settings

from .base import Place
from .http import get_json

_KIND_BY_CLASS = {
    "amenity": "poi",
    "shop": "geschaeft",
    "tourism": "sehenswuerdigkeit",
    "leisure": "freizeit",
    "highway": "strasse",
    "railway": "bahn",
    "aeroway": "flughafen",
    "boundary": "gebiet",
    "place": "ort",
    "building": "gebaeude",
    "natural": "natur",
    "waterway": "gewaesser",
}

_LABEL_BY_TYPE = {
    "restaurant": "Restaurant",
    "cafe": "Café",
    "fast_food": "Imbiss",
    "bar": "Bar",
    "hotel": "Hotel",
    "hostel": "Hostel",
    "guest_house": "Pension",
    "fuel": "Tankstelle",
    "charging_station": "Ladesäule",
    "pharmacy": "Apotheke",
    "hospital": "Krankenhaus",
    "supermarket": "Supermarkt",
    "bakery": "Bäckerei",
    "station": "Bahnhof",
    "bus_stop": "Bushaltestelle",
    "aerodrome": "Flughafen",
    "park": "Park",
    "museum": "Museum",
    "attraction": "Sehenswürdigkeit",
    "viewpoint": "Aussichtspunkt",
    "city": "Stadt",
    "town": "Stadt",
    "village": "Dorf",
    "suburb": "Stadtteil",
    "country": "Land",
    "state": "Bundesland",
}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _viewbox(lat: float, lon: float, span_km: float) -> str:
    dlat = span_km / 111.0
    dlon = span_km / max(1.0, 111.0 * math.cos(math.radians(lat)))
    return f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}"


class NominatimProvider:
    name = "nominatim"

    def __init__(self) -> None:
        self._base = get_settings().nominatim_base_url.rstrip("/")

    def _place(self, raw: dict, near: tuple[float, float] | None) -> Place:
        lat = float(raw.get("lat", 0.0))
        lon = float(raw.get("lon", 0.0))
        address = {
            str(k): str(v) for k, v in (raw.get("address") or {}).items() if v is not None
        }
        display = str(raw.get("display_name", ""))
        name = (
            str(raw.get("name") or "").strip()
            or display.split(",")[0].strip()
            or "Ort"
        )
        klass = str(raw.get("class", ""))
        typ = str(raw.get("type", ""))
        bbox = None
        raw_box = raw.get("boundingbox")
        if isinstance(raw_box, list) and len(raw_box) == 4:
            south, north, west, east = (float(v) for v in raw_box)
            bbox = [west, south, east, north]
        distance = (
            haversine_m(near[0], near[1], lat, lon) if near is not None else None
        )
        return Place(
            id=f"osm:{raw.get('osm_type', 'n')}:{raw.get('osm_id', '')}",
            name=name,
            label=display,
            lat=lat,
            lon=lon,
            kind=_KIND_BY_CLASS.get(klass, "ort"),
            category=_LABEL_BY_TYPE.get(typ, typ.replace("_", " ").strip().title()),
            address=address,
            bbox=bbox,
            distance_m=distance,
            source=self.name,
            extra={"osm_class": klass, "osm_type": typ},
        )

    async def search(
        self,
        query: str,
        near: tuple[float, float] | None = None,
        limit: int = 8,
    ) -> list[Place]:
        text = query.strip()
        if not text:
            return []
        params: dict[str, object] = {
            "q": text,
            "format": "jsonv2",
            "addressdetails": 1,
            "namedetails": 0,
            "limit": max(1, min(int(limit), 25)),
            "accept-language": "de",
        }
        if near is not None:
            params["viewbox"] = _viewbox(near[0], near[1], 40.0)
            params["bounded"] = 0
        data = await get_json(
            f"{self._base}/search",
            params=params,
            ttl=900.0,
            bucket="nominatim",
            min_interval=1.1,
        )
        if not isinstance(data, list):
            return []
        return [self._place(item, near) for item in data if isinstance(item, dict)]

    async def reverse(self, lat: float, lon: float) -> Place | None:
        data = await get_json(
            f"{self._base}/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": 18,
                "accept-language": "de",
            },
            ttl=1800.0,
            bucket="nominatim",
            min_interval=1.1,
        )
        if not isinstance(data, dict) or "lat" not in data:
            return None
        return self._place(data, None)
