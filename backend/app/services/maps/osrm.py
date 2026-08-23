from __future__ import annotations

import uuid

from app.core.config import get_settings

from .base import RouteOption, RouteStep

PROFILES = {"auto": "driving", "fahrrad": "bike", "fuss": "foot"}

_MODIFIER_TEXT = {
    "left": "links",
    "right": "rechts",
    "sharp left": "scharf links",
    "sharp right": "scharf rechts",
    "slight left": "leicht links",
    "slight right": "leicht rechts",
    "straight": "geradeaus",
    "uturn": "wenden",
}

_MANEUVER_TEXT = {
    "depart": "Start",
    "arrive": "Ziel erreicht",
    "turn": "Abbiegen",
    "new name": "Weiter",
    "continue": "Weiter",
    "merge": "Einfädeln",
    "on ramp": "Auffahrt",
    "off ramp": "Abfahrt",
    "fork": "Gabelung",
    "end of road": "Straßenende",
    "roundabout": "Kreisverkehr",
    "rotary": "Kreisverkehr",
    "roundabout turn": "Im Kreisverkehr abbiegen",
    "notification": "Hinweis",
}


def _step_text(step: dict) -> str:
    maneuver = step.get("maneuver") or {}
    typ = str(maneuver.get("type", ""))
    modifier = str(maneuver.get("modifier", ""))
    road = str(step.get("name") or "").strip()
    base = _MANEUVER_TEXT.get(typ, typ.replace("_", " ").capitalize() or "Weiter")
    direction = _MODIFIER_TEXT.get(modifier, "")
    if typ == "depart":
        return f"Start{f' auf {road}' if road else ''}"
    if typ == "arrive":
        return "Ziel erreicht"
    if typ in ("roundabout", "rotary"):
        exit_no = maneuver.get("exit")
        suffix = f", {exit_no}. Ausfahrt" if exit_no else ""
        return f"Kreisverkehr{suffix}{f' auf {road}' if road else ''}"
    parts = [base]
    if direction:
        parts.append(direction)
    if road:
        parts.append(f"auf {road}")
    return " ".join(parts)


class OsrmProvider:
    name = "osrm"

    def __init__(self) -> None:
        settings = get_settings()
        self._base = settings.osrm_base_url.rstrip("/")
        wanted = [
            item.strip().lower()
            for item in settings.osrm_profiles.split(",")
            if item.strip()
        ]
        self.modes = tuple(mode for mode in wanted if mode in PROFILES) or ("auto",)

    async def route(
        self,
        points: list[tuple[float, float]],
        mode: str,
        alternatives: bool = True,
    ) -> list[RouteOption]:
        profile = PROFILES.get(mode)
        if profile is None or len(points) < 2:
            return []
        from .http import get_json

        coords = ";".join(f"{lon},{lat}" for lat, lon in points)
        data = await get_json(
            f"{self._base}/route/v1/{profile}/{coords}",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true",
                "alternatives": "3" if alternatives and len(points) == 2 else "false",
                "annotations": "false",
            },
            ttl=300.0,
            bucket="osrm",
            min_interval=0.3,
        )
        if not isinstance(data, dict) or data.get("code") != "Ok":
            return []
        options: list[RouteOption] = []
        for index, raw in enumerate(data.get("routes") or []):
            geometry = (raw.get("geometry") or {}).get("coordinates") or []
            steps: list[RouteStep] = []
            legs: list[dict] = []
            for leg in raw.get("legs") or []:
                legs.append(
                    {
                        "distanz_m": float(leg.get("distance") or 0.0),
                        "dauer_s": float(leg.get("duration") or 0.0),
                        "zusammenfassung": str(leg.get("summary") or ""),
                    }
                )
                for step in leg.get("steps") or []:
                    location = (step.get("maneuver") or {}).get("location") or []
                    steps.append(
                        RouteStep(
                            text=_step_text(step),
                            distance_m=float(step.get("distance") or 0.0),
                            duration_s=float(step.get("duration") or 0.0),
                            modifier=str(
                                (step.get("maneuver") or {}).get("modifier", "")
                            ),
                            road=str(step.get("name") or ""),
                            mode=mode,
                            lon=float(location[0]) if len(location) == 2 else None,
                            lat=float(location[1]) if len(location) == 2 else None,
                        )
                    )
            names = [
                leg["zusammenfassung"] for leg in legs if leg["zusammenfassung"]
            ]
            options.append(
                RouteOption(
                    id=uuid.uuid4().hex[:10],
                    mode=mode,
                    distance_m=float(raw.get("distance") or 0.0),
                    duration_s=float(raw.get("duration") or 0.0),
                    geometry=[[float(c[0]), float(c[1])] for c in geometry],
                    steps=steps,
                    summary=" · ".join(names[:3])
                    or ("Hauptroute" if index == 0 else f"Alternative {index}"),
                    source=self.name,
                    legs=legs,
                )
            )
        return options
