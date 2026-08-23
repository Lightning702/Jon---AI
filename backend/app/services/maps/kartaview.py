from __future__ import annotations

from app.core.config import get_settings

from .base import StreetImage
from .nominatim import haversine_m


def _image_url(name: str) -> str:
    cleaned = str(name or "").lstrip("/")
    if not cleaned:
        return ""
    return f"https://api.openstreetcam.org/{cleaned}"


def _to_image(raw: dict, source: str) -> StreetImage | None:
    try:
        lat = float(raw.get("lat") or raw.get("match_lat") or 0.0)
        lon = float(raw.get("lng") or raw.get("match_lng") or 0.0)
    except (TypeError, ValueError):
        return None
    if not lat and not lon:
        return None
    full = _image_url(str(raw.get("lth_name") or raw.get("name") or ""))
    thumb = _image_url(str(raw.get("th_name") or raw.get("lth_name") or ""))
    if not full:
        return None
    try:
        bearing = float(raw.get("heading") or 0.0)
    except (TypeError, ValueError):
        bearing = 0.0
    captured = str(raw.get("shot_date") or raw.get("date_added") or "")[:10]
    try:
        index = int(raw.get("sequence_index") or 0)
    except (TypeError, ValueError):
        index = 0
    return StreetImage(
        id=str(raw.get("id", "")),
        lat=lat,
        lon=lon,
        bearing=bearing if bearing >= 0 else 0.0,
        url=full,
        thumb=thumb or full,
        spherical=str(raw.get("projection", "")).upper() in ("SPHERE", "EQUIRECTANGULAR"),
        captured_at=captured,
        sequence=str(raw.get("sequence_id") or ""),
        index=index,
        source=source,
    )


class KartaViewProvider:
    name = "kartaview"

    def __init__(self) -> None:
        self._base = get_settings().kartaview_base_url.rstrip("/")

    def available(self) -> bool:
        return True

    async def near(
        self, lat: float, lon: float, radius_m: int = 150, limit: int = 24
    ) -> list[StreetImage]:
        from .http import post_json

        radius = max(30, min(int(radius_m), 2000))
        data = await post_json(
            f"{self._base}/1.0/list/nearby-photos/",
            data=f"lat={lat}&lng={lon}&radius={radius}",
            ttl=900.0,
            bucket="kartaview",
            min_interval=0.25,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        items = data.get("currentPageItems") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        images = [
            image
            for image in (
                _to_image(item, self.name) for item in items if isinstance(item, dict)
            )
            if image is not None
        ]
        images.sort(key=lambda i: haversine_m(lat, lon, i.lat, i.lon))
        return images[: max(1, int(limit))]

    async def sequence(self, sequence_id: str, limit: int = 200) -> list[StreetImage]:
        if not sequence_id:
            return []
        from .http import post_json

        data = await post_json(
            f"{self._base}/1.0/sequence/photo-list/",
            data=f"sequenceId={sequence_id}",
            ttl=3600.0,
            bucket="kartaview",
            min_interval=0.25,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        payload = data.get("osv") if isinstance(data, dict) else None
        photos = payload.get("photos") if isinstance(payload, dict) else None
        if not isinstance(photos, list):
            return []
        images = [
            image
            for image in (
                _to_image(item, self.name) for item in photos if isinstance(item, dict)
            )
            if image is not None
        ]
        images.sort(key=lambda i: i.index)
        return images[: max(1, min(int(limit), 400))]
