from __future__ import annotations

import copy
from typing import Any

from app.core.config import get_settings

from .http import get_json

THEMES = ("dark", "light")

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "background": "#050507",
        "land": "#0a0a0e",
        "land_alt": "#101016",
        "green": "#0d1613",
        "green_soft": "#111a16",
        "sand": "#14120d",
        "water": "#05131f",
        "water_line": "#0b2135",
        "building": "#13131a",
        "building_top": "#1c1c25",
        "building_side": "#111119",
        "road_minor": "#1a1a22",
        "road_mid": "#26262f",
        "road_major": "#37333a",
        "road_motorway": "#4a4130",
        "road_casing": "#0a0a0e",
        "path": "#2b2a24",
        "rail": "#24242d",
        "boundary": "#33333f",
        "text": "#e9e9f0",
        "text_soft": "#a9a9b8",
        "halo": "#040406",
        "accent": "#d4af37",
        "accent_soft": "#f5d67b",
        "nav": "#4c8dff",
        "sky_high": "#050508",
        "sky_low": "#0f1a26",
        "hillshade_shadow": "#000000",
        "hillshade_highlight": "#2a2a33",
    },
    "light": {
        "background": "#f7f6f2",
        "land": "#f2f1ec",
        "land_alt": "#eae8e1",
        "green": "#e2ebdd",
        "green_soft": "#e9f0e4",
        "sand": "#f2ecdc",
        "water": "#cfe1f0",
        "water_line": "#b6cfe4",
        "building": "#e7e4dc",
        "building_top": "#eeece5",
        "building_side": "#dedbd2",
        "road_minor": "#ffffff",
        "road_mid": "#fdfcf8",
        "road_major": "#fbf4e4",
        "road_motorway": "#f6e6bd",
        "road_casing": "#dedbd2",
        "path": "#dfd6bd",
        "rail": "#d6d3cb",
        "boundary": "#cfccc3",
        "text": "#26262c",
        "text_soft": "#5c5c66",
        "halo": "#fdfdfb",
        "accent": "#9a7b1f",
        "accent_soft": "#d4af37",
        "nav": "#2f6fe0",
        "sky_high": "#bcd6ef",
        "sky_low": "#e7f0f8",
        "hillshade_shadow": "#8b8778",
        "hillshade_highlight": "#ffffff",
    },
}

_WATER = ("water", "ocean", "sea", "lake", "river", "waterway", "bathymetry")
_GREEN = ("park", "wood", "forest", "grass", "green", "golf", "pitch", "garden")
_LAND = ("landuse", "landcover", "residential", "industrial", "sand", "glacier")
_ROAD_MOTORWAY = ("motorway", "trunk")
_ROAD_MAJOR = ("primary", "secondary")
_ROAD_MID = ("tertiary", "street", "road", "link")
_PATH = ("path", "footway", "pedestrian", "track", "steps", "cycle")
_RAIL = ("rail", "transit", "subway", "tram", "train")
_BOUNDARY = ("boundary", "admin", "border")
_BUILDING = ("building",)


def _tokens(layer: dict[str, Any]) -> str:
    return " ".join(
        str(layer.get(key, ""))
        for key in ("id", "source-layer", "source")
    ).lower()


def _set(paint: dict[str, Any], key: str, value: Any) -> None:
    if key in paint:
        paint[key] = value


def _recolor(layer: dict[str, Any], palette: dict[str, str]) -> dict[str, Any]:
    kind = str(layer.get("type", ""))
    marks = _tokens(layer)
    paint = dict(layer.get("paint") or {})
    if kind == "background":
        paint["background-color"] = palette["background"]
        paint.pop("background-pattern", None)
        layer["paint"] = paint
        return layer
    if kind == "symbol":
        _set(paint, "text-color", palette["text"])
        _set(paint, "text-halo-color", palette["halo"])
        if "text-halo-width" in paint:
            paint["text-halo-width"] = 1.4
        if "icon-color" in paint:
            paint["icon-color"] = palette["accent"]
        if "text-color" not in paint:
            paint["text-color"] = palette["text"]
            paint["text-halo-color"] = palette["halo"]
            paint["text-halo-width"] = 1.4
        layer["paint"] = paint
        return layer
    if kind == "hillshade":
        paint["hillshade-shadow-color"] = palette["hillshade_shadow"]
        paint["hillshade-highlight-color"] = palette["hillshade_highlight"]
        paint["hillshade-exaggeration"] = 0.35
        layer["paint"] = paint
        return layer
    if kind == "raster":
        if palette is PALETTES["dark"]:
            paint["raster-saturation"] = -0.7
            paint["raster-brightness-max"] = 0.32
            paint["raster-contrast"] = 0.1
            paint["raster-opacity"] = 0.55
        else:
            paint["raster-saturation"] = -0.25
            paint["raster-opacity"] = 0.6
        layer["paint"] = paint
        return layer

    color = None
    if any(token in marks for token in _BUILDING):
        color = palette["building"]
    elif any(token in marks for token in _WATER):
        color = palette["water"] if kind == "fill" else palette["water_line"]
    elif any(token in marks for token in _GREEN):
        color = palette["green"]
    elif any(token in marks for token in _BOUNDARY):
        color = palette["boundary"]
    elif any(token in marks for token in _RAIL):
        color = palette["rail"]
    elif any(token in marks for token in _PATH):
        color = palette["path"]
    elif any(token in marks for token in _ROAD_MOTORWAY):
        color = palette["road_motorway"]
    elif any(token in marks for token in _ROAD_MAJOR):
        color = palette["road_major"]
    elif any(token in marks for token in _ROAD_MID):
        color = palette["road_mid"]
    elif "aeroway" in marks:
        color = palette["land_alt"]
    elif any(token in marks for token in _LAND):
        color = palette["land_alt"]
    elif "transportation" in marks or "highway" in marks:
        color = palette["road_minor"]
    else:
        color = palette["land"]

    if ("casing" in marks or "outline" in marks) and kind in ("line", "fill"):
        casing = palette["road_casing"]
        if kind == "line":
            _set(paint, "line-color", casing)
        else:
            _set(paint, "fill-outline-color", casing)
            _set(paint, "fill-color", color)
        layer["paint"] = paint
        return layer

    if kind == "fill":
        paint["fill-color"] = color
        paint.pop("fill-pattern", None)
        if "fill-outline-color" in paint:
            paint["fill-outline-color"] = palette["road_casing"]
    elif kind == "line":
        paint["line-color"] = color
    elif kind == "fill-extrusion":
        paint["fill-extrusion-color"] = palette["building_top"]
    layer["paint"] = paint
    return layer


def _vector_source(style: dict[str, Any]) -> str:
    for name, source in (style.get("sources") or {}).items():
        if str(source.get("type")) == "vector":
            return str(name)
    return ""


def _overlay_sources(settings: Any) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    if settings.maps_tiles_satellite:
        sources["jon-satellit"] = {
            "type": "raster",
            "tiles": [settings.maps_tiles_satellite],
            "tileSize": 256,
            "maxzoom": 19,
            "attribution": "Esri, Maxar, Earthstar Geographics",
        }
    if settings.maps_terrain_tiles:
        sources["jon-gelaende"] = {
            "type": "raster-dem",
            "tiles": [settings.maps_terrain_tiles],
            "tileSize": 256,
            "maxzoom": 14,
            "encoding": "terrarium",
            "attribution": "Terrain: Mapzen / AWS Open Data",
        }
    if settings.maps_transit_tiles:
        sources["jon-oepnv"] = {
            "type": "raster",
            "tiles": [settings.maps_transit_tiles],
            "tileSize": 256,
            "maxzoom": 18,
            "attribution": "ÖPNV-Karte, OpenStreetMap-Mitwirkende",
        }
    if settings.maps_bike_tiles:
        sources["jon-fahrrad"] = {
            "type": "raster",
            "tiles": [settings.maps_bike_tiles],
            "tileSize": 256,
            "maxzoom": 18,
            "attribution": "CyclOSM, OpenStreetMap-Mitwirkende",
        }
    if settings.maps_traffic_tiles:
        sources["jon-verkehr"] = {
            "type": "raster",
            "tiles": [settings.maps_traffic_tiles],
            "tileSize": 256,
            "maxzoom": 18,
        }
    return sources


def _overlay_layers(
    palette: dict[str, str], vector_source: str, sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    if "jon-satellit" in sources:
        layers.append(
            {
                "id": "jon-satellit",
                "type": "raster",
                "source": "jon-satellit",
                "layout": {"visibility": "none"},
                "paint": {"raster-opacity": 1.0, "raster-fade-duration": 260},
            }
        )
    if "jon-gelaende" in sources:
        layers.append(
            {
                "id": "jon-hillshade",
                "type": "hillshade",
                "source": "jon-gelaende",
                "layout": {"visibility": "none"},
                "paint": {
                    "hillshade-shadow-color": palette["hillshade_shadow"],
                    "hillshade-highlight-color": palette["hillshade_highlight"],
                    "hillshade-exaggeration": 0.32,
                },
            }
        )
    if vector_source:
        layers.append(
            {
                "id": "jon-fusswege",
                "type": "line",
                "source": vector_source,
                "source-layer": "transportation",
                "minzoom": 13,
                "filter": [
                    "in",
                    ["get", "class"],
                    ["literal", ["path", "footway", "pedestrian", "steps", "track"]],
                ],
                "layout": {
                    "visibility": "none",
                    "line-cap": "round",
                    "line-join": "round",
                },
                "paint": {
                    "line-color": palette["accent_soft"],
                    "line-opacity": 0.7,
                    "line-width": ["interpolate", ["linear"], ["zoom"], 13, 0.6, 18, 2.4],
                    "line-dasharray": [1.4, 1.6],
                },
            }
        )
        layers.append(
            {
                "id": "jon-3d-gebaeude",
                "type": "fill-extrusion",
                "source": vector_source,
                "source-layer": "building",
                "minzoom": 13.5,
                "layout": {"visibility": "none"},
                "paint": {
                    "fill-extrusion-color": [
                        "interpolate",
                        ["linear"],
                        ["coalesce", ["get", "render_height"], ["get", "height"], 6],
                        0,
                        palette["building_side"],
                        40,
                        palette["building"],
                        140,
                        palette["building_top"],
                    ],
                    "fill-extrusion-height": [
                        "interpolate",
                        ["linear"],
                        ["zoom"],
                        13.5,
                        0,
                        16,
                        ["coalesce", ["get", "render_height"], ["get", "height"], 6],
                    ],
                    "fill-extrusion-base": [
                        "coalesce",
                        ["get", "render_min_height"],
                        ["get", "min_height"],
                        0,
                    ],
                    "fill-extrusion-opacity": 0.92,
                    "fill-extrusion-vertical-gradient": True,
                },
            }
        )
    for key, label in (
        ("jon-verkehr", "jon-verkehr"),
        ("jon-oepnv", "jon-oepnv"),
        ("jon-fahrrad", "jon-fahrrad"),
    ):
        if key in sources:
            layers.append(
                {
                    "id": label,
                    "type": "raster",
                    "source": key,
                    "layout": {"visibility": "none"},
                    "paint": {"raster-opacity": 0.85, "raster-fade-duration": 200},
                }
            )
    return layers


def _fallback_style(theme: str, palette: dict[str, str]) -> dict[str, Any]:
    return {
        "version": 8,
        "name": f"Jon Maps {theme}",
        "sources": {
            "jon-osm": {
                "type": "raster",
                "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                "tileSize": 256,
                "maxzoom": 19,
                "attribution": "OpenStreetMap-Mitwirkende",
            }
        },
        "layers": [
            {
                "id": "background",
                "type": "background",
                "paint": {"background-color": palette["background"]},
            },
            {
                "id": "jon-osm",
                "type": "raster",
                "source": "jon-osm",
                "paint": {
                    "raster-saturation": -0.75 if theme == "dark" else -0.15,
                    "raster-brightness-max": 0.55 if theme == "dark" else 1.0,
                    "raster-contrast": 0.1,
                },
            },
        ],
    }


async def build_style(theme: str) -> dict[str, Any]:
    settings = get_settings()
    palette = PALETTES.get(theme, PALETTES["dark"])
    style: dict[str, Any] | None = None
    upstream = (
        settings.maps_style_dark if theme == "dark" else settings.maps_style_light
    ).strip()
    if upstream:
        try:
            raw = await get_json(upstream, ttl=86400.0)
            if isinstance(raw, dict) and raw.get("layers"):
                style = copy.deepcopy(raw)
        except Exception:
            style = None
    if style is None:
        style = _fallback_style(theme, palette)
    else:
        style["layers"] = [
            _recolor(dict(layer), palette) for layer in style.get("layers") or []
        ]
    style["name"] = f"Jon Maps · {theme}"
    style.setdefault("sources", {})
    vector_source = _vector_source(style)
    overlays = _overlay_sources(settings)
    style["sources"].update(overlays)
    style["layers"].extend(_overlay_layers(palette, vector_source, overlays))
    style["sky"] = {
        "sky-color": palette["sky_high"],
        "horizon-color": palette["sky_low"],
        "fog-color": palette["sky_low"],
        "sky-horizon-blend": 0.6,
        "horizon-fog-blend": 0.7,
        "fog-ground-blend": 0.4,
        "atmosphere-blend": [
            "interpolate",
            ["linear"],
            ["zoom"],
            0,
            1,
            6,
            0.6,
            12,
            0,
        ],
    }
    style["light"] = {
        "anchor": "viewport",
        "color": palette["accent_soft"] if theme == "dark" else "#ffffff",
        "intensity": 0.22 if theme == "dark" else 0.4,
        "position": [1.4, 200.0, 32.0],
    }
    style["metadata"] = {
        "jon:theme": theme,
        "jon:palette": palette,
        "jon:vectorSource": vector_source,
        "jon:overlays": sorted(overlays.keys()),
    }
    return style


def palette_for(theme: str) -> dict[str, str]:
    return PALETTES.get(theme, PALETTES["dark"])
