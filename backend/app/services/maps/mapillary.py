from __future__ import annotations

import math

from app.core.config import get_settings

from .base import StreetImage
from .nominatim import haversine_m

FIELDS = (
    "id,computed_geometry,geometry,compass_angle,computed_compass_angle,"
    "captured_at,is_pano,sequence,thumb_1024_url,thumb_2048_url"
)


def _bbox(lat: float, lon: float, radius_m: int) -> str:
    dlat = radius_m / 111320.0
    dlon = radius_m / max(1.0, 111320.0 * math.cos(math.radians(lat)))
    return f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"


class MapillaryProvider:
    name = "mapillary"

    def __init__(self) -> None:
        self._token = (get_settings().mapillary_token or "").strip()
        self._base = "https://graph.mapillary.com"

    def available(self) -> bool:
        return bool(self._token)

    def _image(self, raw: dict) -> StreetImage | None:
        geometry = raw.get("computed_geometry") or raw.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if len(coords) != 2:
            return None
        thumb = str(raw.get("thumb_1024_url") or "")
        full = str(raw.get("thumb_2048_url") or thumb)
        if not full:
            return None
        captured = raw.get("captured_at")
        stamp = ""
        if isinstance(captured, (int, float)) and captured > 0:
            from datetime import datetime

            stamp = datetime.fromtimestamp(captured / 1000.0).strftime("%m/%Y")
        sequence = raw.get("sequence")
        return StreetImage(
            id=str(raw.get("id", "")),
            lat=float(coords[1]),
            lon=float(coords[0]),
            bearing=float(
                raw.get("computed_compass_angle")
                if raw.get("computed_compass_angle") is not None
                else raw.get("compass_angle") or 0.0
            ),
            url=full,
            thumb=thumb or full,
            spherical=bool(raw.get("is_pano")),
            captured_at=stamp,
            sequence=str(sequence) if sequence else "",
            source=self.name,
        )

    async def near(
        self, lat: float, lon: float, radius_m: int = 120, limit: int = 24
    ) -> list[StreetImage]:
        if not self.available():
            return []
        from .http import get_json

        data = await get_json(
            f"{self._base}/images",
            params={
                "access_token": self._token,
                "fields": FIELDS,
                "bbox": _bbox(lat, lon, max(30, min(int(radius_m), 600))),
                "limit": max(1, min(int(limit) * 3, 100)),
            },
            ttl=900.0,
            bucket="mapillary",
            min_interval=0.2,
        )
        raw_items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_items, list):
            return []
        images = [
            image
            for image in (self._image(item) for item in raw_items if isinstance(item, dict))
            if image is not None
        ]
        images.sort(key=lambda i: haversine_m(lat, lon, i.lat, i.lon))
        return images[: max(1, int(limit))]

    async def sequence(self, sequence_id: str, limit: int = 60) -> list[StreetImage]:
        if not self.available() or not sequence_id:
            return []
        from .http import get_json

        data = await get_json(
            f"{self._base}/image_ids",
            params={"access_token": self._token, "sequence_id": sequence_id},
            ttl=3600.0,
            bucket="mapillary",
            min_interval=0.2,
        )
        ids = [
            str(item.get("id"))
            for item in (data.get("data") or [])
            if isinstance(item, dict) and item.get("id")
        ][: max(1, min(int(limit), 120))]
        images: list[StreetImage] = []
        for image_id in ids:
            raw = await get_json(
                f"{self._base}/{image_id}",
                params={"access_token": self._token, "fields": FIELDS},
                ttl=3600.0,
                bucket="mapillary",
                min_interval=0.05,
            )
            if isinstance(raw, dict):
                image = self._image(raw)
                if image is not None:
                    images.append(image)
        return images
