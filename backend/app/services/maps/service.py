from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import get_settings

from .base import (
    MODE_LABELS,
    TRAVEL_MODES,
    MapsError,
    Place,
    RouteOption,
    StreetImage,
    format_distance,
    format_duration,
)
from . import device
from .kartaview import KartaViewProvider
from .mapillary import MapillaryProvider
from .nominatim import NominatimProvider, haversine_m
from .osrm import OsrmProvider
from .overpass import OverpassProvider, category_list, resolve_category
from .styles import THEMES, build_style, palette_for
from .transitous import TransitousProvider
from .valhalla import ValhallaProvider

GEOCODERS = {"nominatim": NominatimProvider}
PLACE_PROVIDERS = {"overpass": OverpassProvider}
ROUTERS = {"osrm": OsrmProvider, "valhalla": ValhallaProvider}
TRANSIT_ROUTERS = {"transitous": TransitousProvider}
STREET_PROVIDERS = {
    "kartaview": KartaViewProvider,
    "mapillary": MapillaryProvider,
}


class MapsService:
    def __init__(self) -> None:
        settings = get_settings()
        self._geocoder = GEOCODERS.get(
            settings.maps_geocoder, NominatimProvider
        )()
        self._places = PLACE_PROVIDERS.get(
            settings.maps_places, OverpassProvider
        )()
        primary = ROUTERS.get(settings.maps_router, OsrmProvider)()
        fallback_name = "valhalla" if settings.maps_router != "valhalla" else "osrm"
        fallback = ROUTERS[fallback_name]()
        self._routers = [primary, fallback]
        self._transit = TRANSIT_ROUTERS.get(
            settings.maps_transit, TransitousProvider
        )()
        street_cls = STREET_PROVIDERS.get(settings.maps_street, KartaViewProvider)
        self._street = street_cls()
        if not self._street.available():
            self._street = KartaViewProvider()
        self._home: tuple[float, float] | None = None
        self._home_source = "voreinstellung"
        self._home_lock = asyncio.Lock()

    def config(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "anbieter": {
                "geocoding": self._geocoder.name,
                "orte": self._places.name,
                "routing": [router.name for router in self._routers],
                "oepnv": self._transit.name,
                "street": self._street.name,
            },
            "themes": list(THEMES),
            "start": {
                "lat": settings.maps_home_lat,
                "lon": settings.maps_home_lon,
                "zoom": settings.maps_home_zoom,
            },
            "modi": [
                {"id": mode, "label": MODE_LABELS[mode]} for mode in TRAVEL_MODES
            ],
            "kategorien": category_list(),
            "ebenen": {
                "satellit": bool(settings.maps_tiles_satellite),
                "gelaende": bool(settings.maps_terrain_tiles),
                "gebaeude3d": True,
                "verkehr": bool(settings.maps_traffic_tiles),
                "oepnv": bool(settings.maps_transit_tiles),
                "fahrrad": bool(settings.maps_bike_tiles),
                "fusswege": True,
            },
            "faehigkeiten": {
                "globus": True,
                "neigen": True,
                "drehen": True,
                "street_fotos": self._street.available(),
                "street_render": True,
                "geraeteortung": device.available(),
                "oepnv_routing": True,
            },
            "attribution": "© OpenStreetMap-Mitwirkende · Jon Maps",
        }

    async def style(self, theme: str) -> dict[str, Any]:
        name = theme if theme in THEMES else "dark"
        return await build_style(name)

    def palette(self, theme: str) -> dict[str, str]:
        return palette_for(theme if theme in THEMES else "dark")

    @staticmethod
    def _place_label(place: Place) -> str:
        address = place.address or {}
        street = str(address.get("road") or address.get("pedestrian") or "").strip()
        number = str(address.get("house_number") or "").strip()
        town = str(
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("suburb")
            or ""
        ).strip()
        line = " ".join(part for part in (street, number) if part)
        readable = ", ".join(part for part in (line, town) if part)
        if readable:
            return readable
        if place.name and not place.name.isdigit():
            return place.name
        return place.label.split(",")[0].strip() or place.name

    @staticmethod
    def _stored_home() -> tuple[tuple[float, float], str, str] | None:
        try:
            from app.services.settings_service import get_settings_service

            data = get_settings_service().get()
        except Exception:
            return None
        lat = float(data.get("maps_home_lat") or 0.0)
        lon = float(data.get("maps_home_lon") or 0.0)
        if not lat and not lon:
            return None
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None
        return (
            (lat, lon),
            str(data.get("maps_home_label") or ""),
            str(data.get("maps_home_source") or "gespeichert"),
        )

    async def set_home(
        self, lat: float, lon: float, source: str = "geraet"
    ) -> dict[str, Any]:
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise MapsError("Diese Koordinaten gibt es nicht.")
        label = ""
        try:
            place = await self.reverse(lat, lon)
            if place is not None:
                label = self._place_label(place)
        except Exception:
            label = ""
        try:
            from app.services.settings_service import get_settings_service

            get_settings_service().update(
                {
                    "maps_home_lat": float(lat),
                    "maps_home_lon": float(lon),
                    "maps_home_label": label,
                    "maps_home_source": source,
                }
            )
        except Exception as exc:
            raise MapsError(f"Standort konnte nicht gespeichert werden: {exc}")
        self._home = (float(lat), float(lon))
        return {"lat": float(lat), "lon": float(lon), "name": label, "quelle": source}

    async def home_details(self) -> dict[str, Any]:
        stored = self._stored_home()
        if stored is not None:
            (lat, lon), label, source = stored
            return {"lat": lat, "lon": lon, "name": label, "quelle": source}
        lat, lon = await self.home()
        return {"lat": lat, "lon": lon, "name": "", "quelle": self._home_source}

    async def locate_device(self, force: bool = False) -> dict | None:
        return await device.locate(force)

    async def home(self) -> tuple[float, float]:
        settings = get_settings()
        stored = self._stored_home()
        if stored is not None:
            self._home = stored[0]
            self._home_source = stored[2]
            return self._home
        if self._home is not None:
            return self._home
        async with self._home_lock:
            if self._home is not None:
                return self._home
            fix = await device.locate()
            if fix is not None:
                self._home_source = "geraet"
                self._home = (fix["lat"], fix["lon"])
                return self._home
            located: tuple[float, float] | None = None
            try:
                from .http import get_json

                data = await get_json(
                    "http://ip-api.com/json/",
                    params={"fields": "status,lat,lon,city"},
                    ttl=3600.0,
                )
                if isinstance(data, dict) and data.get("status") == "success":
                    located = (float(data["lat"]), float(data["lon"]))
            except Exception:
                located = None
            self._home_source = "ip" if located else "voreinstellung"
            self._home = located or (settings.maps_home_lat, settings.maps_home_lon)
            return self._home

    async def search(
        self,
        query: str,
        near: tuple[float, float] | None = None,
        limit: int = 8,
    ) -> list[Place]:
        text = query.strip()
        if not text:
            return []
        category = resolve_category(text)
        origin = near or await self.home()
        if category:
            nearby = await self.places(category, origin[0], origin[1], 2500, limit)
            if nearby:
                return nearby
        return await self._geocoder.search(text, origin, limit)

    async def places(
        self,
        category: str,
        lat: float,
        lon: float,
        radius_m: int = 1500,
        limit: int = 20,
    ) -> list[Place]:
        return await self._places.nearby(category, lat, lon, radius_m, limit)

    async def reverse(self, lat: float, lon: float) -> Place | None:
        return await self._geocoder.reverse(lat, lon)

    async def resolve_point(
        self, value: str | dict[str, Any], near: tuple[float, float] | None = None
    ) -> Place:
        if isinstance(value, dict):
            lat = value.get("lat")
            lon = value.get("lon")
            if lat is not None and lon is not None:
                place = await self.reverse(float(lat), float(lon))
                if place is not None:
                    return place
                return Place(
                    id=f"punkt:{lat},{lon}",
                    name=str(value.get("name") or "Punkt"),
                    label=f"{float(lat):.5f}, {float(lon):.5f}",
                    lat=float(lat),
                    lon=float(lon),
                    kind="punkt",
                    source="koordinate",
                )
            value = str(value.get("name") or value.get("query") or "")
        text = str(value).strip()
        if not text:
            raise MapsError("Kein Ort angegeben")
        lowered = text.lower()
        if lowered in ("hier", "mein standort", "aktueller standort", "standort"):
            lat, lon = near or await self.home()
            place = await self.reverse(lat, lon)
            if place is not None:
                return place
        parts = text.replace(";", ",").split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return await self.resolve_point({"lat": lat, "lon": lon})
            except ValueError:
                pass
        found = await self.search(text, near, 1)
        if not found:
            raise MapsError(f"Ort nicht gefunden: {text}")
        return found[0]

    async def route(
        self,
        points: list[tuple[float, float]],
        mode: str = "auto",
        alternatives: bool = True,
    ) -> list[RouteOption]:
        if len(points) < 2:
            raise MapsError("Für eine Route braucht Jon Start und Ziel")
        if mode == "oepnv":
            try:
                transit = await self._transit.route(points, mode, alternatives)
            except Exception:
                transit = []
            if transit:
                return transit
            walking = await self.route(points, "fuss", False)
            for option in walking:
                option.extra["hinweis"] = (
                    "Für diese Strecke liefert der ÖPNV-Anbieter keine Verbindung — "
                    "Jon zeigt den Fußweg."
                )
            return walking
        errors: list[str] = []
        for router in self._chain(mode):
            try:
                options = await router.route(points, mode, alternatives)
            except Exception as exc:
                errors.append(self._route_error(router.name, exc))
                continue
            if options:
                return options
        label = MODE_LABELS.get(mode, mode)
        if errors:
            raise MapsError(
                f"Für {label} findet Jon hier keine Route: {errors[0]}"
            )
        raise MapsError(f"Für {label} findet Jon auf dieser Strecke keine Route.")

    @staticmethod
    def _route_error(provider: str, exc: Exception) -> str:
        status = getattr(getattr(exc, "response", None), "status_code", 0)
        if status == 400:
            return (
                "Die Strecke ist für dieses Verkehrsmittel zu weit oder nicht "
                "durchgehend befahrbar."
            )
        if status == 429:
            return f"Der Anbieter {provider} ist gerade überlastet."
        if status:
            return f"Der Anbieter {provider} antwortet mit Fehler {status}."
        return f"Der Anbieter {provider} ist nicht erreichbar."

    def _chain(self, mode: str) -> list[Any]:
        able = [router for router in self._routers if mode in router.modes]
        if mode == "auto":
            return able
        able.sort(key=lambda router: 0 if router.name == "valhalla" else 1)
        return able

    async def street_images(
        self, lat: float, lon: float, radius_m: int = 150, limit: int = 24
    ) -> dict[str, Any]:
        images: list[StreetImage] = []
        if self._street.available():
            try:
                images = await self._street.near(lat, lon, radius_m, limit)
            except Exception:
                images = []
        return {
            "modus": "fotos" if images else "render",
            "anbieter": self._street.name if images else "jon-render",
            "bilder": [image.to_dict() for image in images],
            "hinweis": ""
            if images
            else (
                "Keine echten Straßenfotos verfügbar — Jon erkundet die Straße in "
                "seiner eigenen 3D-Ansicht."
            ),
        }

    async def street_sequence(self, sequence_id: str, limit: int = 60) -> list[dict]:
        if not self._street.available():
            return []
        try:
            images = await self._street.sequence(sequence_id, limit)
        except Exception:
            return []
        return [image.to_dict() for image in images]

    async def answer(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        near_raw = args.get("near")
        near: tuple[float, float] | None = None
        if isinstance(near_raw, dict) and near_raw.get("lat") is not None:
            near = (float(near_raw["lat"]), float(near_raw["lon"]))
        if action == "suche":
            query = str(args.get("query") or "")
            found = await self.search(query, near, int(args.get("limit") or 6))
            center = (
                {"lat": found[0].lat, "lon": found[0].lon} if found else None
            )
            return {
                "aktion": "suche",
                "anfrage": query,
                "treffer": [place.to_dict() for place in found],
                "karte": {
                    "center": center,
                    "zoom": 14 if found else 5,
                    "marker": [place.to_dict() for place in found],
                },
                "text": self._search_text(query, found),
            }
        if action == "umgebung":
            category = str(args.get("category") or args.get("query") or "")
            origin = near or await self.home()
            if args.get("around"):
                anchor = await self.resolve_point(str(args["around"]), near)
                origin = (anchor.lat, anchor.lon)
            found = await self.places(
                category,
                origin[0],
                origin[1],
                int(args.get("radius") or 1500),
                int(args.get("limit") or 12),
            )
            return {
                "aktion": "umgebung",
                "kategorie": category,
                "mittelpunkt": {"lat": origin[0], "lon": origin[1]},
                "treffer": [place.to_dict() for place in found],
                "karte": {
                    "center": {"lat": origin[0], "lon": origin[1]},
                    "zoom": 14,
                    "marker": [place.to_dict() for place in found],
                },
                "text": self._nearby_text(category, found),
            }
        if action == "route":
            mode = str(args.get("mode") or "auto").lower()
            if mode not in TRAVEL_MODES:
                mode = "auto"
            start = await self.resolve_point(args.get("from") or "hier", near)
            ziel = await self.resolve_point(args.get("to") or "", near)
            stops: list[Place] = []
            for stop in args.get("via") or []:
                stops.append(await self.resolve_point(stop, near))
            points = [(start.lat, start.lon)]
            points.extend((stop.lat, stop.lon) for stop in stops)
            points.append((ziel.lat, ziel.lon))
            options = await self.route(points, mode, True)
            return {
                "aktion": "route",
                "modus": mode,
                "modus_label": MODE_LABELS[mode],
                "start": start.to_dict(),
                "ziel": ziel.to_dict(),
                "zwischenstopps": [stop.to_dict() for stop in stops],
                "routen": [option.to_dict() for option in options],
                "karte": {
                    "center": {
                        "lat": (start.lat + ziel.lat) / 2,
                        "lon": (start.lon + ziel.lon) / 2,
                    },
                    "marker": [start.to_dict(), ziel.to_dict()],
                    "route": options[0].geometry if options else [],
                },
                "text": self._route_text(start, ziel, mode, options),
            }
        if action == "erkunden":
            target = await self.resolve_point(args.get("query") or "hier", near)
            street = await self.street_images(target.lat, target.lon, 180, 12)
            return {
                "aktion": "erkunden",
                "ort": target.to_dict(),
                "street": street,
                "karte": {
                    "center": {"lat": target.lat, "lon": target.lon},
                    "zoom": 17,
                    "marker": [target.to_dict()],
                    "modus": "street",
                },
                "text": (
                    f"Ich habe {target.name} geöffnet — du kannst dort auf "
                    "Straßenebene wechseln oder als Mensch, Auto oder Flugzeug "
                    "losziehen."
                ),
            }
        raise MapsError(f"Unbekannte Maps-Aktion: {action}")

    def _search_text(self, query: str, found: list[Place]) -> str:
        if not found:
            return f"Zu „{query}“ habe ich nichts gefunden."
        head = found[0]
        rest = len(found) - 1
        suffix = f" (und {rest} weitere Treffer)" if rest > 0 else ""
        return f"„{query}“ → {head.name}, {head.label}{suffix}."

    def _nearby_text(self, category: str, found: list[Place]) -> str:
        if not found:
            return f"In der Nähe finde ich nichts zu „{category}“."
        lines = [
            f"{index + 1}. {place.name}"
            + (
                f" · {format_distance(place.distance_m)}"
                if place.distance_m is not None
                else ""
            )
            for index, place in enumerate(found[:5])
        ]
        return "In der Nähe:\n" + "\n".join(lines)

    def _route_text(
        self,
        start: Place,
        ziel: Place,
        mode: str,
        options: list[RouteOption],
    ) -> str:
        if not options:
            return f"Für {MODE_LABELS[mode]} finde ich keine Route zu {ziel.name}."
        best = options[0]
        text = (
            f"{MODE_LABELS[mode]} von {start.name} nach {ziel.name}: "
            f"{format_duration(best.duration_s)} · "
            f"{format_distance(best.distance_m)}"
        )
        if len(options) > 1:
            alt = options[1]
            text += f". Alternative: {format_duration(alt.duration_s)}"
        return text + "."

    @staticmethod
    def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_m(lat1, lon1, lat2, lon2)


_service: MapsService | None = None


def get_maps_service() -> MapsService:
    global _service
    if _service is None:
        _service = MapsService()
    return _service
