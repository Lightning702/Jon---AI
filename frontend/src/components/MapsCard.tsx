import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import MapCanvas, { MapMarker } from "../maps/MapCanvas";
import "../maps/glass.css";
import {
  MODE_ICONS,
  MapsCardData,
  MapsTheme,
  formatDistance,
  formatDuration,
} from "../lib/maps";

interface Props {
  data: MapsCardData;
  onOpen: (data: MapsCardData) => void;
}

function readTheme(): MapsTheme {
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

export default function MapsCard({ data, onOpen }: Props) {
  const [theme, setTheme] = useState<MapsTheme>(readTheme);
  const [routeIndex, setRouteIndex] = useState(0);

  const center = data.karte?.center ?? { lat: 51.1657, lon: 10.4515 };
  const routes = data.routen ?? [];
  const active = routes[routeIndex];

  const markers = useMemo<MapMarker[]>(() => {
    const list: MapMarker[] = (data.karte?.marker ?? []).map((place, index) => ({
      id: `${place.id}-${index}`,
      lat: place.lat,
      lon: place.lon,
      icon:
        data.aktion === "route"
          ? index === 0
            ? "🅰"
            : "🏁"
          : String(place.extra?.icon ?? "") || "📍",
      tone:
        data.aktion === "route" ? (index === 0 ? "start" : "ziel") : "poi",
    }));
    return list;
  }, [data]);

  const routeLines = useMemo(
    () =>
      routes.map((route, index) => ({
        id: route.id,
        geometry: route.geometry,
        active: index === routeIndex,
      })),
    [routes, routeIndex]
  );

  const zoom =
    data.aktion === "route"
      ? 6
      : data.aktion === "erkunden"
        ? 16
        : (data.karte?.zoom ?? 13);

  const title =
    data.aktion === "route"
      ? `${data.start?.name ?? "Start"} → ${data.ziel?.name ?? "Ziel"}`
      : data.aktion === "umgebung"
        ? `${data.kategorie || "In der Nähe"}`
        : data.aktion === "erkunden"
          ? (data.ort?.name ?? "Erkunden")
          : (data.anfrage ?? "Karte");

  return (
    <motion.div
      className="jm-root"
      data-jm-theme={theme}
      style={{
        width: "100%",
        height: "auto",
        borderRadius: 20,
        overflow: "hidden",
        marginTop: 4,
      }}
      initial={{ opacity: 0, y: 12, filter: "blur(10px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.44, ease: [0.22, 1, 0.36, 1] }}
    >
      <div
        className="jm-glass"
        style={{ borderRadius: 20, padding: 0, overflow: "hidden" }}
      >
        <div className="jm-specular" />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 9,
            padding: "11px 14px",
          }}
        >
          <span className="jm-brand-mark" style={{ width: 22, height: 22, fontSize: 11 }}>
            🗺️
          </span>
          <span style={{ fontSize: 12.5, fontWeight: 600, flex: 1, minWidth: 0 }}>
            Jon Maps
            <span
              style={{
                color: "var(--jm-text-faint)",
                fontWeight: 400,
                marginLeft: 8,
                fontSize: 11.5,
              }}
            >
              {title}
            </span>
          </span>
          <button
            className="jm-dock-btn"
            style={{ width: 26, height: 26, fontSize: 12 }}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            title="Hell / Dunkel"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          <button
            className="jm-chip"
            data-active="true"
            style={{ padding: "5px 11px" }}
            onClick={() => onOpen(data)}
          >
            Groß öffnen
          </button>
        </div>

        <div className="jm-card-map" style={{ borderRadius: 0 }}>
          <MapCanvas
            theme={theme}
            center={center}
            zoom={zoom}
            markers={markers}
            routes={routeLines}
            layers={{ gebaeude3d: data.aktion === "erkunden" }}
            projection="mercator"
          />
        </div>

        <div style={{ padding: "11px 14px 13px" }}>
          {data.aktion === "route" && active && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {routes.map((route, index) => (
                <button
                  key={route.id}
                  className="jm-chip"
                  data-tone="nav"
                  data-active={index === routeIndex}
                  onClick={() => setRouteIndex(index)}
                >
                  <span>{MODE_ICONS[route.mode] ?? "🧭"}</span>
                  {formatDuration(route.duration_s)}
                  <span style={{ opacity: 0.65 }}>
                    {formatDistance(route.distance_m)}
                  </span>
                </button>
              ))}
              {typeof active.extra?.umstiege === "number" && (
                <span className="jm-chip" style={{ cursor: "default" }}>
                  🔁 {active.extra.umstiege} Umstiege
                </span>
              )}
            </div>
          )}

          {(data.aktion === "suche" || data.aktion === "umgebung") && (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {(data.treffer ?? []).slice(0, 4).map((place, index) => (
                <div
                  key={place.id + index}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 9,
                    padding: "5px 2px",
                    fontSize: 12,
                  }}
                >
                  <span style={{ width: 18, textAlign: "center" }}>
                    {String(place.extra?.icon ?? "") || "📍"}
                  </span>
                  <span
                    style={{
                      flex: 1,
                      minWidth: 0,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {place.name}
                    <span
                      style={{ color: "var(--jm-text-faint)", marginLeft: 7 }}
                    >
                      {place.category}
                    </span>
                  </span>
                  {place.distance_m != null && (
                    <span
                      className="jm-mono"
                      style={{ color: "var(--jm-text-faint)" }}
                    >
                      {formatDistance(place.distance_m)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {data.aktion === "erkunden" && (
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              <span className="jm-chip" style={{ cursor: "default" }}>
                {data.street?.modus === "fotos"
                  ? `👁️ ${data.street.bilder.length} Straßenfotos`
                  : "🕹️ 3D-Erkundung"}
              </span>
              <button className="jm-chip" onClick={() => onOpen(data)}>
                🚶 Loslaufen
              </button>
            </div>
          )}

          {data.text && (
            <div
              style={{
                marginTop: 9,
                fontSize: 11.5,
                lineHeight: 1.5,
                color: "var(--jm-text-soft)",
              }}
            >
              {data.text}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
