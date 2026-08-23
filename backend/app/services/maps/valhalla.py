from __future__ import annotations

import uuid

from app.core.config import get_settings

from .base import RouteOption, RouteStep

COSTING = {"auto": "auto", "fahrrad": "bicycle", "fuss": "pedestrian"}

_MANEUVER_FALLBACK = "Weiter"


def decode_polyline6(encoded: str) -> list[list[float]]:
    coords: list[list[float]] = []
    index = 0
    lat = 0
    lon = 0
    length = len(encoded)
    while index < length:
        for target in ("lat", "lon"):
            shift = 0
            result = 0
            while index < length:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if target == "lat":
                lat += delta
            else:
                lon += delta
        coords.append([lon / 1e6, lat / 1e6])
    return coords


class ValhallaProvider:
    name = "valhalla"
    modes = ("auto", "fahrrad", "fuss")

    def __init__(self) -> None:
        self._base = get_settings().valhalla_base_url.rstrip("/")

    async def route(
        self,
        points: list[tuple[float, float]],
        mode: str,
        alternatives: bool = True,
    ) -> list[RouteOption]:
        costing = COSTING.get(mode)
        if costing is None or len(points) < 2:
            return []
        from .http import post_json

        payload = {
            "locations": [{"lat": lat, "lon": lon} for lat, lon in points],
            "costing": costing,
            "directions_options": {"units": "kilometers", "language": "de-DE"},
            "alternates": 2 if alternatives and len(points) == 2 else 0,
        }
        data = await post_json(
            f"{self._base}/route",
            payload=payload,
            ttl=300.0,
            bucket="valhalla",
            min_interval=0.4,
        )
        if not isinstance(data, dict):
            return []
        raw_trips = [data.get("trip")] + [
            alt.get("trip") for alt in data.get("alternates") or []
        ]
        options: list[RouteOption] = []
        for index, trip in enumerate(raw_trips):
            if not isinstance(trip, dict):
                continue
            geometry: list[list[float]] = []
            steps: list[RouteStep] = []
            legs: list[dict] = []
            for leg in trip.get("legs") or []:
                shape = decode_polyline6(str(leg.get("shape") or ""))
                geometry.extend(shape)
                leg_summary = leg.get("summary") or {}
                legs.append(
                    {
                        "distanz_m": float(leg_summary.get("length") or 0.0) * 1000.0,
                        "dauer_s": float(leg_summary.get("time") or 0.0),
                        "zusammenfassung": "",
                    }
                )
                for maneuver in leg.get("maneuvers") or []:
                    begin = int(maneuver.get("begin_shape_index") or 0)
                    point = shape[begin] if begin < len(shape) else None
                    names = maneuver.get("street_names") or []
                    steps.append(
                        RouteStep(
                            text=str(
                                maneuver.get("instruction") or _MANEUVER_FALLBACK
                            ),
                            distance_m=float(maneuver.get("length") or 0.0) * 1000.0,
                            duration_s=float(maneuver.get("time") or 0.0),
                            road=str(names[0]) if names else "",
                            mode=mode,
                            lon=point[0] if point else None,
                            lat=point[1] if point else None,
                        )
                    )
            summary = trip.get("summary") or {}
            options.append(
                RouteOption(
                    id=uuid.uuid4().hex[:10],
                    mode=mode,
                    distance_m=float(summary.get("length") or 0.0) * 1000.0,
                    duration_s=float(summary.get("time") or 0.0),
                    geometry=geometry,
                    steps=steps,
                    summary="Hauptroute" if index == 0 else f"Alternative {index}",
                    source=self.name,
                    legs=legs,
                )
            )
        return options
