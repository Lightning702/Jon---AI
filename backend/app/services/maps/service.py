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
    RouteStep,
    StreetImage,
    format_distance,
    format_duration,
)
from . import device
from .kartaview import KartaViewProvider
from .mapillary import MapillaryProvider
from .nominatim import NominatimProvider, haversine_m
from .osrm import OsrmProvider
from .overpass import (
    OverpassProvider,
    category_label,
    category_list,
    resolve_category,
    split_query,
    strip_nearby,
    wants_nearby,
)
from .styles import THEMES, build_style, palette_for
from .transitous import TransitousProvider
from .valhalla import ValhallaProvider

GEOCODERS = {"nominatim": NominatimProvider}
PLACE_PROVIDERS = {"overpass": OverpassProvider}
ROUTERS = {"osrm": OsrmProvider, "valhalla": ValhallaProvider}
TRANSIT_ROUTERS = {"transitous": TransitousProvider}
RADII = (2500, 10000, 25000)
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

    def _radii(self, radius: int, wide: bool) -> tuple[int, ...]:
        if radius:
            return (max(100, int(radius)),)
        return RADII if wide else RADII[:2]

    async def find(
        self,
        text: str,
        origin: tuple[float, float],
        limit: int = 12,
        radius: int = 0,
        wide: bool = True,
    ) -> tuple[str, list[Place]]:
        category, name = split_query(text)
        if not category and not name:
            return "", []
        for reach in self._radii(radius, wide):
            found = await self._lookup(name, category, origin, reach, limit)
            if found:
                return category, found
        if category and name:
            found = await self._lookup(name, "", origin, RADII[-1], limit)
            if found:
                return category, found
        return category, []

    async def _lookup(
        self,
        name: str,
        category: str,
        origin: tuple[float, float],
        radius: int,
        limit: int,
    ) -> list[Place]:
        try:
            if name:
                return await self._places.named(
                    name, origin[0], origin[1], radius, category, limit
                )
            return await self.places(category, origin[0], origin[1], radius, limit)
        except Exception:
            return []

    async def search(
        self,
        query: str,
        near: tuple[float, float] | None = None,
        limit: int = 8,
    ) -> list[Place]:
        text = query.strip()
        if not text:
            return []
        origin = near or await self.home()
        category, name = split_query(text)
        local = wants_nearby(text) or (bool(category) and not name)
        if category or (local and name):
            _, found = await self.find(text, origin, limit, wide=local)
            if found:
                return found
        found = await self._geocoder.search(strip_nearby(text) or text, origin, limit)
        if found:
            return found
        if name and not local:
            _, found = await self.find(text, origin, limit)
            return found
        return []

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
            if len(points) > 2:
                chained = await self._transit_chain(points)
                if chained:
                    return chained
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

    async def _transit_chain(
        self, points: list[tuple[float, float]]
    ) -> list[RouteOption]:
        parts: list[RouteOption] = []
        for index in range(len(points) - 1):
            try:
                options = await self.route(points[index : index + 2], "oepnv", False)
            except MapsError:
                return []
            if not options:
                return []
            parts.append(options[0])
        geometry: list[list[float]] = []
        steps: list[RouteStep] = []
        legs: list[dict[str, Any]] = []
        for part in parts:
            geometry.extend(part.geometry)
            steps.extend(part.steps)
            legs.append(
                {
                    "distanz_m": part.distance_m,
                    "dauer_s": part.duration_s,
                    "zusammenfassung": part.summary,
                }
            )
        changes = sum(int(part.extra.get("umstiege") or 0) for part in parts)
        return [
            RouteOption(
                id=parts[0].id,
                mode="oepnv",
                distance_m=sum(part.distance_m for part in parts),
                duration_s=sum(part.duration_s for part in parts),
                geometry=geometry,
                steps=steps,
                summary=f"{len(parts)} Etappen mit Bus und Bahn",
                source=parts[0].source,
                legs=legs,
                extra={"umstiege": changes + len(parts) - 1},
            )
        ]

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
                "filter": self._filter_key(query, found),
                "treffer": [place.to_dict() for place in found],
                "karte": {
                    "center": center,
                    "zoom": 14 if found else 5,
                    "marker": [place.to_dict() for place in found],
                },
                "text": self._search_text(query, found),
            }
        if action == "umgebung":
            wanted = str(args.get("category") or args.get("query") or "")
            origin = near or await self.home()
            if args.get("around"):
                anchor = await self.resolve_point(str(args["around"]), near)
                origin = (anchor.lat, anchor.lon)
            key, found = await self.find(
                wanted,
                origin,
                int(args.get("limit") or 12),
                int(args.get("radius") or 0),
            )
            if not found and not key:
                found = await self.search(wanted, origin, int(args.get("limit") or 12))
            category = category_label(key) or strip_nearby(wanted) or wanted
            return {
                "aktion": "umgebung",
                "kategorie": category,
                "filter": key,
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
            stations = await self._resolve_stations(args, near)
            points = [(place.lat, place.lon) for place in stations]
            options = await self.route(points, mode, len(points) == 2)
            legs = self._legs(stations, options[0] if options else None)
            lats = [place.lat for place in stations]
            lons = [place.lon for place in stations]
            filter_key, alternatives = await self._target_options(args, stations)
            return {
                "aktion": "route",
                "modus": mode,
                "modus_label": MODE_LABELS[mode],
                "filter": filter_key,
                "ziel_optionen": [place.to_dict() for place in alternatives],
                "start": stations[0].to_dict(),
                "ziel": stations[-1].to_dict(),
                "zwischenstopps": [place.to_dict() for place in stations[1:-1]],
                "stationen": [place.to_dict() for place in stations],
                "abschnitte": legs,
                "routen": [option.to_dict() for option in options],
                "karte": {
                    "center": {
                        "lat": (min(lats) + max(lats)) / 2,
                        "lon": (min(lons) + max(lons)) / 2,
                    },
                    "marker": [place.to_dict() for place in stations],
                    "route": options[0].geometry if options else [],
                },
                "text": self._trip_text(stations, mode, options, legs)
                + self._options_text(alternatives),
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
                    "Straßenebene wechseln oder im Flugzeug über die Gegend "
                    "fliegen."
                ),
            }
        raise MapsError(f"Unbekannte Maps-Aktion: {action}")

    @staticmethod
    def _filter_key(query: str, found: list[Place]) -> str:
        key, _ = split_query(query)
        if key:
            return key
        if found and str(found[0].extra.get("kategorie") or ""):
            return str(found[0].extra["kategorie"])
        return ""

    async def _target_options(
        self, args: dict[str, Any], stations: list[Place]
    ) -> tuple[str, list[Place]]:
        raw = self._station_inputs(args)
        target = raw[-1] if raw else ""
        if not isinstance(target, str) or not target.strip():
            return "", []
        key, name = split_query(target)
        if not key and not name:
            return "", []
        anchor = stations[-2] if len(stations) > 1 else stations[0]
        found: list[Place] = []
        try:
            key, found = await self.find(target, (anchor.lat, anchor.lon), 8)
        except Exception:
            found = []
        ziel = stations[-1]
        rest = [
            place
            for place in found
            if place.id != ziel.id
            and haversine_m(place.lat, place.lon, ziel.lat, ziel.lon) > 25.0
        ]
        return key, rest[:6]

    @staticmethod
    def _options_text(found: list[Place]) -> str:
        if not found:
            return ""
        lines = ", ".join(
            place.name
            + (
                f" ({format_distance(place.distance_m)})"
                if place.distance_m is not None
                else ""
            )
            for place in found[:3]
        )
        return f"\nAuch in der Nähe: {lines}."

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

    @staticmethod
    def _station_inputs(args: dict[str, Any]) -> list[Any]:
        def listed(value: Any) -> list[Any]:
            if value is None or value == "":
                return []
            if isinstance(value, (str, dict)):
                return [value]
            if isinstance(value, (list, tuple)):
                return [item for item in value if item not in (None, "")]
            return [value]

        raw: list[Any] = [args.get("from") or args.get("start") or "hier"]
        raw.extend(listed(args.get("via") or args.get("zwischenstopps")))
        raw.extend(listed(args.get("stops") or args.get("stationen")))
        raw.extend(listed(args.get("to") or args.get("ziel")))
        return raw

    async def _resolve_stations(
        self, args: dict[str, Any], near: tuple[float, float] | None
    ) -> list[Place]:
        stations: list[Place] = []
        for entry in self._station_inputs(args):
            anchor = (
                (stations[-1].lat, stations[-1].lon) if stations else near
            )
            place = await self.resolve_point(entry, anchor)
            if stations and haversine_m(
                stations[-1].lat, stations[-1].lon, place.lat, place.lon
            ) < 40.0:
                continue
            stations.append(place)
        if len(stations) < 2:
            raise MapsError(
                "Für einen Trip braucht Jon mindestens zwei verschiedene Orte."
            )
        return stations

    @staticmethod
    def _legs(
        stations: list[Place], option: RouteOption | None
    ) -> list[dict[str, Any]]:
        raw = list(option.legs) if option else []
        if len(raw) != len(stations) - 1:
            raw = []
        legs: list[dict[str, Any]] = []
        for index in range(len(stations) - 1):
            leg = raw[index] if index < len(raw) else {}
            legs.append(
                {
                    "von": stations[index].name,
                    "nach": stations[index + 1].name,
                    "distanz_m": float(leg.get("distanz_m") or 0.0),
                    "dauer_s": float(leg.get("dauer_s") or 0.0),
                    "zusammenfassung": str(leg.get("zusammenfassung") or ""),
                }
            )
        return legs

    def _trip_text(
        self,
        stations: list[Place],
        mode: str,
        options: list[RouteOption],
        legs: list[dict[str, Any]],
    ) -> str:
        chain = " → ".join(place.name for place in stations)
        if not options:
            return f"Für {MODE_LABELS[mode]} finde ich keine Route über {chain}."
        best = options[0]
        head = (
            f"{MODE_LABELS[mode]}: {chain} — "
            f"{format_duration(best.duration_s)} · "
            f"{format_distance(best.distance_m)}"
        )
        if len(stations) == 2:
            if len(options) > 1:
                head += f". Alternative: {format_duration(options[1].duration_s)}"
            return head + "."
        lines = [
            f"{index + 1}. {leg['von']} → {leg['nach']}: "
            f"{format_duration(leg['dauer_s'])} · "
            f"{format_distance(leg['distanz_m'])}"
            for index, leg in enumerate(legs)
        ]
        return head + "\n" + "\n".join(lines)

    @staticmethod
    def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_m(lat1, lon1, lat2, lon2)


_service: MapsService | None = None


def get_maps_service() -> MapsService:
    global _service
    if _service is None:
        _service = MapsService()
    return _service
