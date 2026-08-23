from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

TRAVEL_MODES = ("fuss", "auto", "fahrrad", "oepnv")

MODE_LABELS = {
    "fuss": "Zu Fuß",
    "auto": "Auto",
    "fahrrad": "Fahrrad",
    "oepnv": "Öffentliche Verkehrsmittel",
}


class MapsError(RuntimeError):
    pass


class ProviderUnavailable(MapsError):
    pass


@dataclass
class Place:
    id: str
    name: str
    label: str
    lat: float
    lon: float
    kind: str = "ort"
    category: str = ""
    address: dict[str, str] = field(default_factory=dict)
    bbox: list[float] | None = None
    distance_m: float | None = None
    source: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteStep:
    text: str
    distance_m: float
    duration_s: float
    modifier: str = ""
    road: str = ""
    mode: str = ""
    lat: float | None = None
    lon: float | None = None


@dataclass
class RouteOption:
    id: str
    mode: str
    distance_m: float
    duration_s: float
    geometry: list[list[float]]
    steps: list[RouteStep] = field(default_factory=list)
    summary: str = ""
    source: str = ""
    legs: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [asdict(s) for s in self.steps]
        return data


@dataclass
class StreetImage:
    id: str
    lat: float
    lon: float
    bearing: float
    url: str
    thumb: str
    spherical: bool
    captured_at: str = ""
    sequence: str = ""
    index: int = 0
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class GeocodingProvider(Protocol):
    name: str

    async def search(
        self, query: str, near: tuple[float, float] | None, limit: int
    ) -> list[Place]: ...

    async def reverse(self, lat: float, lon: float) -> Place | None: ...


@runtime_checkable
class PlacesProvider(Protocol):
    name: str

    async def nearby(
        self, category: str, lat: float, lon: float, radius_m: int, limit: int
    ) -> list[Place]: ...


@runtime_checkable
class RoutingProvider(Protocol):
    name: str
    modes: tuple[str, ...]

    async def route(
        self, points: list[tuple[float, float]], mode: str, alternatives: bool
    ) -> list[RouteOption]: ...


@runtime_checkable
class StreetLevelProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    async def near(
        self, lat: float, lon: float, radius_m: int, limit: int
    ) -> list[StreetImage]: ...

    async def sequence(self, sequence_id: str, limit: int) -> list[StreetImage]: ...


def format_distance(meters: float) -> str:
    if meters < 950:
        return f"{round(meters / 10) * 10:.0f} m"
    if meters < 100000:
        return f"{meters / 1000:.1f} km".replace(".", ",")
    return f"{meters / 1000:.0f} km"


def format_duration(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    if minutes < 1:
        return "unter 1 Minute"
    if minutes < 60:
        return f"{minutes} Minuten"
    hours, rest = divmod(minutes, 60)
    if rest == 0:
        return f"{hours} Stunden" if hours > 1 else "1 Stunde"
    return f"{hours} h {rest} min"
