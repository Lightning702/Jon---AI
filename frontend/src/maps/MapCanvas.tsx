import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { getMapsStyleUrl, MapsTheme } from "../lib/maps";

export interface MapMarker {
  id: string;
  lat: number;
  lon: number;
  icon?: string;
  tone?: "start" | "ziel" | "poi" | "standort" | "freund";
  active?: boolean;
  stale?: boolean;
}

export interface MapRouteLine {
  id: string;
  geometry: [number, number][];
  active?: boolean;
}

export interface MapCanvasProps {
  theme: MapsTheme;
  center: { lat: number; lon: number };
  zoom: number;
  pitch?: number;
  bearing?: number;
  markers?: MapMarker[];
  routes?: MapRouteLine[];
  layers?: Record<string, boolean>;
  terrain?: boolean;
  projection?: "mercator" | "globe" | "auto";
  interactive?: boolean;
  className?: string;
  onReady?: (map: maplibregl.Map) => void;
  onMove?: (state: {
    lat: number;
    lon: number;
    zoom: number;
    bearing: number;
    pitch: number;
  }) => void;
  onMapClick?: (lat: number, lon: number) => void;
  onMarkerClick?: (id: string) => void;
}

const LAYER_IDS: Record<string, string[]> = {
  satellit: ["jon-satellit"],
  gelaende: ["jon-hillshade"],
  gebaeude3d: ["jon-3d-gebaeude"],
  verkehr: ["jon-verkehr"],
  oepnv: ["jon-oepnv"],
  fahrrad: ["jon-fahrrad"],
  fusswege: ["jon-fusswege"],
};

const ROUTE_SOURCE = "jon-route";
const ROUTE_CASING = "jon-route-casing";
const ROUTE_MAIN = "jon-route-main";
const ROUTE_ALT = "jon-route-alt";
const ROUTE_GLOW = "jon-route-glow";

function toFeatureCollection(routes: MapRouteLine[]) {
  return {
    type: "FeatureCollection" as const,
    features: routes
      .filter((route) => route.geometry.length > 1)
      .map((route) => ({
        type: "Feature" as const,
        properties: { id: route.id, active: route.active ? 1 : 0 },
        geometry: {
          type: "LineString" as const,
          coordinates: route.geometry,
        },
      })),
  };
}

function markerElement(marker: MapMarker): HTMLElement {
  const element = document.createElement("div");
  if (marker.tone === "standort") {
    element.className = "jm-pulse";
    return element;
  }
  element.className = "jm-marker";
  element.dataset.tone = marker.tone ?? "poi";
  element.dataset.active = marker.active ? "true" : "false";
  element.dataset.stale = marker.stale ? "true" : "false";
  element.textContent =
    marker.icon ??
    (marker.tone === "start" ? "🅰️" : marker.tone === "ziel" ? "🏁" : "📍");
  return element;
}

export default function MapCanvas({
  theme,
  center,
  zoom,
  pitch = 0,
  bearing = 0,
  markers = [],
  routes = [],
  layers = {},
  terrain = false,
  projection = "auto",
  interactive = true,
  className,
  onReady,
  onMove,
  onMapClick,
  onMarkerClick,
}: MapCanvasProps) {
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRefs = useRef<Map<string, maplibregl.Marker>>(new Map());
  const readyRef = useRef(false);
  const projectionRef = useRef<"mercator" | "globe" | "">("");
  const announcedRef = useRef(false);
  const themeRef = useRef(theme);
  const stateRef = useRef({ routes, layers, terrain, projection, theme });
  stateRef.current = { routes, layers, terrain, projection, theme };
  const handlers = useRef({ onMove, onMapClick, onMarkerClick, onReady });
  handlers.current = { onMove, onMapClick, onMarkerClick, onReady };

  const applyRoutes = (map: maplibregl.Map, lines: MapRouteLine[]) => {
    const data = toFeatureCollection(lines);
    const existing = map.getSource(ROUTE_SOURCE) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (existing) {
      existing.setData(data);
      return;
    }
    map.addSource(ROUTE_SOURCE, { type: "geojson", data, lineMetrics: true });
    map.addLayer({
      id: ROUTE_GLOW,
      type: "line",
      source: ROUTE_SOURCE,
      filter: ["==", ["get", "active"], 1],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#5c98ff",
        "line-opacity": 0.28,
        "line-blur": 8,
        "line-width": ["interpolate", ["linear"], ["zoom"], 5, 10, 16, 26],
      },
    });
    map.addLayer({
      id: ROUTE_ALT,
      type: "line",
      source: ROUTE_SOURCE,
      filter: ["==", ["get", "active"], 0],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#9aa2b1",
        "line-opacity": 0.55,
        "line-dasharray": [2, 1.6],
        "line-width": ["interpolate", ["linear"], ["zoom"], 5, 2.2, 16, 5],
      },
    });
    map.addLayer({
      id: ROUTE_CASING,
      type: "line",
      source: ROUTE_SOURCE,
      filter: ["==", ["get", "active"], 1],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#04101f",
        "line-opacity": 0.85,
        "line-width": ["interpolate", ["linear"], ["zoom"], 5, 6.5, 16, 15],
      },
    });
    map.addLayer({
      id: ROUTE_MAIN,
      type: "line",
      source: ROUTE_SOURCE,
      filter: ["==", ["get", "active"], 1],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#5c98ff",
        "line-width": ["interpolate", ["linear"], ["zoom"], 5, 3.6, 16, 9.5],
        "line-gradient": [
          "interpolate",
          ["linear"],
          ["line-progress"],
          0,
          "#7fb2ff",
          0.5,
          "#5c98ff",
          1,
          "#d4af37",
        ],
      },
    });
  };

  const buildingRamp = (
    low: string,
    mid: string,
    high: string
  ): maplibregl.ExpressionSpecification =>
    [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", "render_height"], ["get", "height"], 6],
      0,
      low,
      40,
      mid,
      140,
      high,
    ] as unknown as maplibregl.ExpressionSpecification;

  const applyLayers = (map: maplibregl.Map, flags: Record<string, boolean>) => {
    Object.entries(LAYER_IDS).forEach(([key, ids]) => {
      const on = Boolean(flags[key]);
      ids.forEach((id) => {
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
        }
      });
    });
    if (!map.getLayer("jon-3d-gebaeude")) return;
    const meta = (map.getStyle().metadata ?? {}) as Record<string, unknown>;
    const palette = (meta["jon:palette"] ?? {}) as Record<string, string>;
    const overImagery = Boolean(flags.satellit);
    map.setPaintProperty(
      "jon-3d-gebaeude",
      "fill-extrusion-color",
      overImagery
        ? buildingRamp("#b9b4a8", "#cfcabd", "#e6e2d6")
        : buildingRamp(
            palette.building_side ?? "#111119",
            palette.building ?? "#13131a",
            palette.building_top ?? "#1c1c25"
          )
    );
    map.setPaintProperty(
      "jon-3d-gebaeude",
      "fill-extrusion-opacity",
      overImagery ? 1 : 0.92
    );
    try {
      map.setLight(
        overImagery
          ? {
              anchor: "viewport",
              color: "#ffffff",
              intensity: 0.42,
              position: [1.2, 210, 28],
            }
          : {
              anchor: "viewport",
              color: palette.accent_soft ?? "#ffffff",
              intensity: 0.22,
              position: [1.4, 200, 32],
            }
      );
    } catch {
      return;
    }
  };

  const applyTerrain = (map: maplibregl.Map, on: boolean) => {
    if (!map.getSource("jon-gelaende")) return;
    if (on) {
      map.setTerrain({ source: "jon-gelaende", exaggeration: 1.25 });
    } else {
      map.setTerrain(null);
    }
  };

  const applyProjection = (
    map: maplibregl.Map,
    mode: "mercator" | "globe" | "auto"
  ) => {
    const wanted =
      mode === "auto" ? (map.getZoom() < 5.4 ? "globe" : "mercator") : mode;
    if (projectionRef.current === wanted) return;
    projectionRef.current = wanted;
    map.setProjection({ type: wanted });
  };

  const applyAll = (map: maplibregl.Map) => {
    const current = stateRef.current;
    try {
      applyRoutes(map, current.routes);
      applyLayers(map, current.layers);
      applyTerrain(map, current.terrain);
      applyProjection(map, current.projection);
    } catch {
      return;
    }
  };

  useEffect(() => {
    if (!holder.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: holder.current,
      style: getMapsStyleUrl(theme),
      center: [center.lon, center.lat],
      zoom,
      pitch,
      bearing,
      maxPitch: 85,
      attributionControl: false,
      interactive,
      dragRotate: interactive,
      pitchWithRotate: interactive,
      fadeDuration: 240,
    });
    mapRef.current = map;
    themeRef.current = theme;
    const announce = () => {
      if (announcedRef.current) return;
      announcedRef.current = true;
      handlers.current.onReady?.(map);
    };
    const settle = () => {
      if (readyRef.current) return;
      if (!map.style || !map.getStyle()) return;
      readyRef.current = true;
      projectionRef.current = "";
      applyAll(map);
      announce();
    };
    map.on("style.load", () => {
      readyRef.current = true;
      projectionRef.current = "";
      applyAll(map);
      announce();
    });
    map.on("load", () => {
      settle();
      announce();
    });
    map.on("idle", settle);
    map.on("error", (event) => {
      const message = String(event?.error?.message ?? "");
      if (message.includes("sprite") || message.includes("Failed to fetch")) {
        settle();
      }
    });
    map.on("move", () => {
      const middle = map.getCenter();
      handlers.current.onMove?.({
        lat: middle.lat,
        lon: middle.lng,
        zoom: map.getZoom(),
        bearing: map.getBearing(),
        pitch: map.getPitch(),
      });
      if (readyRef.current && stateRef.current.projection === "auto") {
        try {
          applyProjection(map, "auto");
        } catch {
          return;
        }
      }
    });
    map.on("click", (event) => {
      handlers.current.onMapClick?.(event.lngLat.lat, event.lngLat.lng);
    });
    const container = holder.current;
    const observer = new ResizeObserver(() => {
      try {
        map.resize();
      } catch {
        return;
      }
    });
    if (container) observer.observe(container);
    return () => {
      observer.disconnect();
      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current.clear();
      readyRef.current = false;
      announcedRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || themeRef.current === theme) return;
    themeRef.current = theme;
    readyRef.current = false;
    map.setStyle(getMapsStyleUrl(theme), { diff: false });
  }, [theme]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    try {
      applyRoutes(map, routes);
    } catch {
      return;
    }
  }, [routes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    try {
      applyLayers(map, layers);
    } catch {
      return;
    }
  }, [layers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    try {
      applyTerrain(map, terrain);
    } catch {
      return;
    }
  }, [terrain]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    try {
      applyProjection(map, projection);
    } catch {
      return;
    }
  }, [projection]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const seen = new Set<string>();
    markers.forEach((marker) => {
      seen.add(marker.id);
      const existing = markerRefs.current.get(marker.id);
      if (existing) {
        existing.setLngLat([marker.lon, marker.lat]);
        const element = existing.getElement();
        if (element.classList.contains("jm-marker")) {
          element.dataset.active = marker.active ? "true" : "false";
          element.dataset.tone = marker.tone ?? "poi";
          element.dataset.stale = marker.stale ? "true" : "false";
          const next = marker.icon ?? element.textContent ?? "📍";
          if (element.textContent !== next) element.textContent = next;
        }
        return;
      }
      const element = markerElement(marker);
      element.addEventListener("click", (event) => {
        event.stopPropagation();
        handlers.current.onMarkerClick?.(marker.id);
      });
      const instance = new maplibregl.Marker({ element, anchor: "center" })
        .setLngLat([marker.lon, marker.lat])
        .addTo(map);
      markerRefs.current.set(marker.id, instance);
    });
    markerRefs.current.forEach((instance, id) => {
      if (!seen.has(id)) {
        instance.remove();
        markerRefs.current.delete(id);
      }
    });
  }, [markers]);

  return <div ref={holder} className={className ?? "jm-map"} />;
}
