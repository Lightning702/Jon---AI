import { useCallback, useMemo, useState } from "react";
import { motion } from "framer-motion";
import MapCanvas, { MapMarker } from "../maps/MapCanvas";
import "../maps/glass.css";
import {
  MODE_ICONS,
  MapsCardData,
  MapsPlace,
  MapsRoute,
  MapsTheme,
  TripLeg,
  formatDistance,
  formatDuration,
  planRoute,
} from "../lib/maps";

function chainTitle(names: string[]): string {
  if (names.length <= 3) return names.join(" → ");
  return `${names[0]} → +${names.length - 2} → ${names[names.length - 1]}`;
}

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
  const [ziel, setZiel] = useState<MapsPlace | null>(null);
  const [eigeneRouten, setEigeneRouten] = useState<MapsRoute[] | null>(null);
  const [routeBusy, setRouteBusy] = useState(false);
  const [routeError, setRouteError] = useState("");

  const basis = useMemo(
    () => data.stationen ?? data.karte?.marker ?? [],
    [data.stationen, data.karte]
  );

  const stations = useMemo(
    () => (ziel && basis.length > 1 ? [...basis.slice(0, -1), ziel] : basis),
    [basis, ziel]
  );

  const routes = eigeneRouten ?? data.routen ?? [];
  const active = routes[routeIndex];

  const legs = useMemo<TripLeg[]>(() => {
    if (!eigeneRouten) return data.abschnitte ?? [];
    const roh = active?.legs ?? [];
    if (roh.length !== stations.length - 1) return [];
    return roh.map((leg, index) => ({
      von: stations[index].name,
      nach: stations[index + 1].name,
      distanz_m: Number(leg.distanz_m ?? 0),
      dauer_s: Number(leg.dauer_s ?? 0),
      zusammenfassung: String(leg.zusammenfassung ?? ""),
    }));
  }, [eigeneRouten, active, stations, data.abschnitte]);

  const alternativen = useMemo<MapsPlace[]>(() => {
    const liste = [...(data.ziel_optionen ?? [])];
    const original = data.ziel;
    if (ziel && original && !liste.some((place) => place.id === original.id)) {
      liste.unshift(original);
    }
    const aktiv = ziel?.id ?? original?.id;
    return liste.filter((place) => place.id !== aktiv);
  }, [data.ziel_optionen, data.ziel, ziel]);

  const markers = useMemo<MapMarker[]>(() => {
    const list: MapMarker[] = stations.map((place, index) => {
      const last = index === stations.length - 1;
      if (data.aktion !== "route") {
        return {
          id: `${place.id}-${index}`,
          lat: place.lat,
          lon: place.lon,
          icon: String(place.extra?.icon ?? "") || "📍",
          tone: "poi" as const,
        };
      }
      return {
        id: `${place.id}-${index}`,
        lat: place.lat,
        lon: place.lon,
        icon: index === 0 ? "🅰" : last ? "🏁" : String(index),
        tone: index === 0 ? "start" : last ? "ziel" : "poi",
      };
    });
    alternativen.forEach((place, index) => {
      list.push({
        id: `option-${place.id}-${index}`,
        lat: place.lat,
        lon: place.lon,
        icon: String(place.extra?.icon ?? "") || "📍",
        tone: "poi",
      });
    });
    return list;
  }, [stations, alternativen, data.aktion]);

  const routeLines = useMemo(
    () =>
      routes.map((route, index) => ({
        id: route.id,
        geometry: route.geometry,
        active: index === routeIndex,
      })),
    [routes, routeIndex]
  );

  const center = useMemo(() => {
    if (data.aktion === "route" && stations.length > 1) {
      const lats = stations.map((place) => place.lat);
      const lons = stations.map((place) => place.lon);
      return {
        lat: (Math.min(...lats) + Math.max(...lats)) / 2,
        lon: (Math.min(...lons) + Math.max(...lons)) / 2,
      };
    }
    return data.karte?.center ?? { lat: 51.1657, lon: 10.4515 };
  }, [data.aktion, data.karte, stations]);

  const zoom = useMemo(() => {
    if (data.aktion === "erkunden") return 16;
    if (data.aktion !== "route") return data.karte?.zoom ?? 13;
    if (stations.length < 2) return 6;
    const lats = stations.map((place) => place.lat);
    const lons = stations.map((place) => place.lon);
    const middle = (Math.min(...lats) + Math.max(...lats)) / 2;
    const span = Math.max(
      Math.max(...lats) - Math.min(...lats),
      (Math.max(...lons) - Math.min(...lons)) *
        Math.cos((middle * Math.PI) / 180),
      0.02
    );
    return Math.max(2, Math.min(13, Math.log2(360 / span) - 1.35));
  }, [data, stations]);

  const title =
    data.aktion === "route"
      ? chainTitle(
          stations.length > 1
            ? stations.map((place) => place.name)
            : [data.start?.name ?? "Start", data.ziel?.name ?? "Ziel"]
        )
      : data.aktion === "umgebung"
        ? `${data.kategorie || "In der Nähe"}`
        : data.aktion === "erkunden"
          ? (data.ort?.name ?? "Erkunden")
          : (data.anfrage ?? "Karte");

  const text = useMemo(() => {
    if (!ziel || !active) return data.text;
    const kette = stations.map((place) => place.name).join(" → ");
    return (
      `${data.modus_label ?? "Route"}: ${kette} — ` +
      `${formatDuration(active.duration_s)} · ${formatDistance(active.distance_m)}.`
    );
  }, [ziel, active, stations, data.text, data.modus_label]);

  const ansicht = useMemo<MapsCardData>(() => {
    if (!ziel) return data;
    return {
      ...data,
      ziel,
      stationen: stations,
      zwischenstopps: stations.slice(1, -1),
      abschnitte: legs,
      routen: routes,
      ziel_optionen: alternativen,
      karte: {
        ...data.karte,
        center,
        marker: stations,
        route: routes[routeIndex]?.geometry ?? [],
      },
      text,
    };
  }, [
    data,
    ziel,
    stations,
    legs,
    routes,
    routeIndex,
    alternativen,
    center,
    text,
  ]);

  const waehleZiel = useCallback(
    async (place: MapsPlace) => {
      const kette = [...basis.slice(0, -1), place];
      if (kette.length < 2) return;
      setRouteBusy(true);
      setRouteError("");
      try {
        const gefunden = await planRoute(
          kette.map((stop) => ({ lat: stop.lat, lon: stop.lon })),
          data.modus ?? "auto",
          kette.length === 2
        );
        if (gefunden.length === 0) {
          setRouteError(`Zu ${place.name} finde ich keine Route.`);
          return;
        }
        setZiel(place);
        setEigeneRouten(gefunden);
        setRouteIndex(0);
      } catch {
        setRouteError("Die Route ließ sich gerade nicht berechnen.");
      } finally {
        setRouteBusy(false);
      }
    },
    [basis, data.modus]
  );

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
            onClick={() => onOpen(ansicht)}
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
              {stations.length > 2 && (
                <span className="jm-chip" style={{ cursor: "default" }}>
                  📍 {stations.length} Stationen
                </span>
              )}
            </div>
          )}

          {data.aktion === "route" && legs.length > 1 && (
            <div style={{ marginTop: 9, display: "flex", flexDirection: "column" }}>
              {legs.map((leg, index) => (
                <div
                  key={`${leg.von}-${index}`}
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: 9,
                    padding: "4px 2px",
                    fontSize: 11.5,
                    borderBottom: "1px solid var(--jm-hairline)",
                  }}
                >
                  <span
                    className="jm-mono"
                    style={{ color: "var(--jm-text-faint)", width: 14 }}
                  >
                    {index + 1}
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
                    {leg.von} → {leg.nach}
                  </span>
                  <span className="jm-mono" style={{ color: "var(--jm-text-soft)" }}>
                    {formatDuration(leg.dauer_s)}
                  </span>
                  <span
                    className="jm-mono"
                    style={{ color: "var(--jm-text-faint)" }}
                  >
                    {formatDistance(leg.distanz_m)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {data.aktion === "route" && alternativen.length > 0 && (
            <div
              style={{
                marginTop: 9,
                display: "flex",
                flexWrap: "wrap",
                gap: 7,
                alignItems: "center",
              }}
            >
              <span style={{ fontSize: 11.5, color: "var(--jm-text-faint)" }}>
                {routeBusy ? "Route wird berechnet …" : "Stattdessen hierher"}
              </span>
              {alternativen.slice(0, 4).map((place, index) => (
                <button
                  key={`${place.id}-${index}`}
                  className="jm-chip"
                  disabled={routeBusy}
                  title={`Route nach ${place.name}${
                    place.label ? ` · ${place.label}` : ""
                  }`}
                  onClick={() => void waehleZiel(place)}
                >
                  <span>{String(place.extra?.icon ?? "") || "📍"}</span>
                  {place.name}
                  {place.distance_m != null && (
                    <span style={{ opacity: 0.65 }}>
                      {formatDistance(place.distance_m)}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {routeError && (
            <div
              style={{
                marginTop: 8,
                fontSize: 11.5,
                color: "var(--jm-warn, #ff9a9a)",
              }}
            >
              {routeError}
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
                  : "✈️ 3D-Erkundung"}
              </span>
              <button className="jm-chip" onClick={() => onOpen(data)}>
                ✈️ Abheben
              </button>
            </div>
          )}

          {text && (
            <div
              style={{
                marginTop: 9,
                fontSize: 11.5,
                lineHeight: 1.5,
                whiteSpace: "pre-line",
                color: "var(--jm-text-soft)",
              }}
            >
              {legs.length > 1 ? text.split("\n")[0] : text}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
