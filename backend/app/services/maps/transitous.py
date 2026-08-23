from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.config import get_settings

from .base import RouteOption, RouteStep

MODE_TEXT = {
    "WALK": "Fußweg",
    "BIKE": "Fahrrad",
    "CAR": "Auto",
    "BUS": "Bus",
    "TRAM": "Tram",
    "SUBWAY": "U-Bahn",
    "METRO": "Metro",
    "RAIL": "Zug",
    "REGIONAL_RAIL": "Regionalzug",
    "REGIONAL_FAST_RAIL": "Regionalexpress",
    "LONG_DISTANCE": "Fernzug",
    "HIGHSPEED_RAIL": "Hochgeschwindigkeitszug",
    "NIGHT_RAIL": "Nachtzug",
    "COACH": "Fernbus",
    "FERRY": "Fähre",
    "AIRPLANE": "Flug",
    "OTHER": "Verbindung",
}


def decode_polyline(encoded: str, precision: int = 7) -> list[list[float]]:
    coords: list[list[float]] = []
    index = 0
    lat = 0
    lon = 0
    factor = float(10**precision)
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
        coords.append([lon / factor, lat / factor])
    return coords


def _clock(value: str) -> str:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return moment.astimezone().strftime("%H:%M")


class TransitousProvider:
    name = "transitous"
    modes = ("oepnv",)

    def __init__(self) -> None:
        self._base = get_settings().transitous_base_url.rstrip("/")

    async def route(
        self,
        points: list[tuple[float, float]],
        mode: str,
        alternatives: bool = True,
    ) -> list[RouteOption]:
        if mode != "oepnv" or len(points) < 2:
            return []
        from .http import get_json

        start, end = points[0], points[-1]
        data = await get_json(
            f"{self._base}/api/v1/plan",
            params={
                "fromPlace": f"{start[0]},{start[1]}",
                "toPlace": f"{end[0]},{end[1]}",
                "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "numItineraries": 3 if alternatives else 1,
                "transitModes": "TRANSIT",
                "preTransitModes": "WALK",
                "postTransitModes": "WALK",
            },
            ttl=180.0,
            bucket="transitous",
            min_interval=0.5,
        )
        if not isinstance(data, dict):
            return []
        options: list[RouteOption] = []
        for index, itinerary in enumerate(data.get("itineraries") or []):
            geometry: list[list[float]] = []
            steps: list[RouteStep] = []
            legs: list[dict] = []
            lines: list[str] = []
            for leg in itinerary.get("legs") or []:
                leg_mode = str(leg.get("mode") or "OTHER").upper()
                label = MODE_TEXT.get(leg_mode, leg_mode.title())
                shape = leg.get("legGeometry") or {}
                points_raw = str(shape.get("points") or "")
                precision = int(shape.get("precision") or 7)
                if points_raw:
                    geometry.extend(decode_polyline(points_raw, precision))
                origin = leg.get("from") or {}
                target = leg.get("to") or {}
                line = str(
                    leg.get("routeShortName") or leg.get("routeLongName") or ""
                ).strip()
                if line and leg_mode != "WALK":
                    lines.append(f"{label} {line}".strip())
                depart = _clock(str(leg.get("startTime") or ""))
                arrive = _clock(str(leg.get("endTime") or ""))
                headline = (
                    f"{label}{f' {line}' if line else ''} "
                    f"{origin.get('name', '')} → {target.get('name', '')}"
                ).strip()
                steps.append(
                    RouteStep(
                        text=f"{depart} {headline}".strip(),
                        distance_m=float(leg.get("distance") or 0.0),
                        duration_s=float(leg.get("duration") or 0.0),
                        road=line,
                        mode=leg_mode.lower(),
                        lat=float(origin.get("lat") or 0.0) or None,
                        lon=float(origin.get("lon") or 0.0) or None,
                    )
                )
                legs.append(
                    {
                        "modus": leg_mode.lower(),
                        "bezeichnung": label,
                        "linie": line,
                        "von": str(origin.get("name") or ""),
                        "nach": str(target.get("name") or ""),
                        "ab": depart,
                        "an": arrive,
                        "dauer_s": float(leg.get("duration") or 0.0),
                        "distanz_m": float(leg.get("distance") or 0.0),
                    }
                )
            total_distance = sum(float(leg["distanz_m"]) for leg in legs)
            options.append(
                RouteOption(
                    id=uuid.uuid4().hex[:10],
                    mode="oepnv",
                    distance_m=total_distance,
                    duration_s=float(itinerary.get("duration") or 0.0),
                    geometry=geometry,
                    steps=steps,
                    summary=" · ".join(lines[:3])
                    or ("Verbindung" if index == 0 else f"Alternative {index}"),
                    source=self.name,
                    legs=legs,
                    extra={
                        "umstiege": int(itinerary.get("transfers") or 0),
                        "abfahrt": _clock(str(itinerary.get("startTime") or "")),
                        "ankunft": _clock(str(itinerary.get("endTime") or "")),
                    },
                )
            )
        return options
