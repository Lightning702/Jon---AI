import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type maplibregl from "maplibre-gl";
import "./glass.css";
import MapCanvas, { MapMarker, MapRouteLine } from "./MapCanvas";
import SearchPanel from "./SearchPanel";
import ControlDock from "./ControlDock";
import LayerSheet from "./LayerSheet";
import RoutePanel from "./RoutePanel";
import PlaceSheet from "./PlaceSheet";
import FriendSheet from "./FriendSheet";
import StreetView from "./StreetView";
import WorldExplorer, { ExplorerMode } from "./WorldExplorer";
import {
  FriendLocation,
  FriendsResult,
  MapsConfig,
  MapsPlace,
  MapsRoute,
  MapsTheme,
  TravelMode,
  getFriends,
  getMapsConfig,
  locateDevice,
  locateViaJon,
  nearbyPlaces,
  planRoute,
  reversePlace,
  searchPlaces,
  setFriendSharing,
  setHome as storeHome,
  shareLocationNow,
} from "../lib/maps";

export interface JonMapsIntent {
  center?: { lat: number; lon: number };
  zoom?: number;
  markers?: MapsPlace[];
  route?: [number, number][];
  street?: boolean;
  explorer?: ExplorerMode;
  from?: MapsPlace;
  to?: MapsPlace;
  mode?: TravelMode;
  routes?: MapsRoute[];
}

interface Props {
  onClose?: () => void;
  onAskJon?: (question: string) => void;
  intent?: JonMapsIntent;
  embedded?: boolean;
}

const THEME_KEY = "jon_maps_theme";

function readTheme(): MapsTheme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

export default function JonMaps({
  onClose,
  onAskJon,
  intent,
  embedded = false,
}: Props) {
  const [theme, setTheme] = useState<MapsTheme>(readTheme);
  const [config, setConfig] = useState<MapsConfig | null>(null);
  const [view, setView] = useState({
    lat: 51.1657,
    lon: 10.4515,
    zoom: 5.2,
    bearing: 0,
    pitch: 0,
  });
  const [results, setResults] = useState<MapsPlace[]>([]);
  const [searching, setSearching] = useState(false);
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState<MapsPlace | null>(null);
  const [home, setHome] = useState<{ lat: number; lon: number } | null>(null);
  const [routeOpen, setRouteOpen] = useState(false);
  const [routeFrom, setRouteFrom] = useState<MapsPlace | null>(null);
  const [routeTo, setRouteTo] = useState<MapsPlace | null>(null);
  const [routeVia, setRouteVia] = useState<MapsPlace[]>([]);
  const [routeMode, setRouteMode] = useState<TravelMode>("auto");
  const [routes, setRoutes] = useState<MapsRoute[]>([]);
  const [routeIndex, setRouteIndex] = useState(0);
  const [routeBusy, setRouteBusy] = useState(false);
  const [routeError, setRouteError] = useState("");
  const [routeSlot, setRouteSlot] = useState<"from" | "to" | null>(null);
  const [layersOpen, setLayersOpen] = useState(false);
  const [layers, setLayers] = useState<Record<string, boolean>>({
    gebaeude3d: false,
    satellit: false,
    gelaende: false,
    verkehr: false,
    oepnv: false,
    fahrrad: false,
    fusswege: false,
  });
  const [terrain, setTerrain] = useState(false);
  const [projection, setProjection] = useState<"auto" | "globe" | "mercator">(
    "auto"
  );
  const [street, setStreet] = useState<{ lat: number; lon: number } | null>(null);
  const [explorer, setExplorer] = useState<ExplorerMode | null>(null);
  const [explorerStart, setExplorerStart] = useState({ lat: 0, lon: 0 });
  const [toast, setToast] = useState("");
  const [homeName, setHomeName] = useState("");
  const [friends, setFriends] = useState<FriendsResult | null>(null);
  const [activeFriend, setActiveFriend] = useState<FriendLocation | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const pendingStart = useRef<{ lat: number; lon: number; zoom: number } | null>(
    null
  );
  const viewRef = useRef(view);
  viewRef.current = view;
  const flyToRef = useRef<
    ((lat: number, lon: number, zoom?: number) => void) | null
  >(null);
  const locatedRef = useRef(false);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    getMapsConfig()
      .then((data) => {
        if (cancelled) return;
        setConfig(data);
        const start = data.standort ?? data.start;
        setHome({ lat: start.lat, lon: start.lon });
        setHomeName(data.standort?.name ?? "");
        if (data.standort?.quelle !== "geraet") void locate(false);
        if (!intent?.center && !locatedRef.current) {
          const zoom = data.standort ? 12.5 : data.start.zoom;
          setView((current) => ({
            ...current,
            lat: start.lat,
            lon: start.lon,
            zoom,
          }));
          const map = mapRef.current;
          if (map) {
            map.jumpTo({ center: [start.lon, start.lat], zoom });
          } else {
            pendingStart.current = { lat: start.lat, lon: start.lon, zoom };
          }
        }
      })
      .catch(() => setToast("Jon Maps konnte die Konfiguration nicht laden."));
    return () => {
      cancelled = true;
    };
  }, []);

  const pinHome = useCallback(async () => {
    const map = mapRef.current;
    if (!map) return;
    const middle = map.getCenter();
    try {
      const saved = await storeHome(middle.lat, middle.lng, "karte");
      setHome({ lat: middle.lat, lon: middle.lng });
      setHomeName(saved.name);
      setToast(
        saved.name
          ? `Standort gesetzt: ${saved.name}`
          : "Standort auf die Kartenmitte gesetzt."
      );
    } catch {
      setToast("Standort konnte nicht gespeichert werden.");
    }
  }, []);

  const applyHome = useCallback(
    (lat: number, lon: number, name: string) => {
      locatedRef.current = true;
      setHome({ lat, lon });
      setHomeName(name);
      const map = mapRef.current;
      if (map) {
        pendingStart.current = null;
        flyToRef.current?.(lat, lon, 15);
      } else {
        pendingStart.current = { lat, lon, zoom: 15 };
      }
    },
    []
  );

  const locate = useCallback(
    async (interactive: boolean) => {
      try {
        const fix = await locateViaJon();
        applyHome(fix.lat, fix.lon, fix.name);
        if (interactive) {
          const accuracy = fix.genauigkeit_m
            ? ` (±${Math.round(fix.genauigkeit_m)} m)`
            : "";
          setToast(
            fix.name
              ? `Standort: ${fix.name}${accuracy}`
              : `Standort vom Gerät übernommen${accuracy}.`
          );
        }
        return true;
      } catch {
        try {
          const position = await locateDevice();
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          const saved = await storeHome(lat, lon, "geraet");
          applyHome(lat, lon, saved.name);
          if (interactive) {
            setToast(
              saved.name
                ? `Standort: ${saved.name}`
                : "Standort vom Gerät übernommen."
            );
          }
          return true;
        } catch {
          if (interactive) {
            setToast(
              "Ortung ging nicht. Schalte in Windows unter Datenschutz den " +
                "Standortdienst ein, oder setze ihn unter Ebenen auf die Kartenmitte."
            );
          }
          return false;
        }
      }
    },
    [applyHome]
  );

  const flyTo = useCallback(
    (lat: number, lon: number, zoom?: number, pitch?: number) => {
      const map = mapRef.current;
      if (!map) {
        setView((current) => ({ ...current, lat, lon, zoom: zoom ?? current.zoom }));
        return;
      }
      map.flyTo({
        center: [lon, lat],
        zoom: zoom ?? Math.max(map.getZoom(), 14),
        pitch: pitch ?? map.getPitch(),
        duration: 1500,
        essential: true,
        curve: 1.42,
      });
    },
    []
  );

  useEffect(() => {
    flyToRef.current = flyTo;
  }, [flyTo]);

  const refreshFriends = useCallback(async () => {
    try {
      setFriends(await getFriends());
    } catch {
      return;
    }
  }, []);

  useEffect(() => {
    void refreshFriends();
    const timer = window.setInterval(() => void refreshFriends(), 20000);
    return () => window.clearInterval(timer);
  }, [refreshFriends]);

  const changeSharing = useCallback(
    async (patch: { aktiv?: boolean; alle?: boolean; peers?: string[] }) => {
      try {
        await setFriendSharing(patch);
        if (patch.aktiv === true) {
          setToast("Deine Freunde sehen jetzt deinen Standort.");
        } else if (patch.aktiv === false) {
          setToast("Standortfreigabe aus. Niemand sieht dich mehr.");
        }
      } catch {
        setToast("Die Freigabe ließ sich nicht ändern.");
      }
      await refreshFriends();
    },
    [refreshFriends]
  );

  const pushLocation = useCallback(async () => {
    try {
      const result = await shareLocationNow();
      setToast(
        result.gesendet > 0
          ? `Standort an ${result.gesendet} Freund${result.gesendet === 1 ? "" : "e"} gesendet.`
          : (result.grund ?? "Es war niemand erreichbar.")
      );
    } catch {
      setToast("Senden hat nicht geklappt.");
    }
    await refreshFriends();
  }, [refreshFriends]);

  useEffect(() => {
    if (!intent) return;
    if (intent.markers?.length) setResults(intent.markers);
    if (intent.from) setRouteFrom(intent.from);
    if (intent.to) setRouteTo(intent.to);
    if (intent.mode) setRouteMode(intent.mode);
    if (intent.routes?.length) {
      setRoutes(intent.routes);
      setRouteIndex(0);
      setRouteOpen(true);
    }
    if (intent.center) {
      flyTo(intent.center.lat, intent.center.lon, intent.zoom);
    }
    if (intent.street && intent.center) {
      setStreet({ lat: intent.center.lat, lon: intent.center.lon });
    }
    if (intent.explorer && intent.center) {
      setExplorerStart({ lat: intent.center.lat, lon: intent.center.lon });
      setExplorer(intent.explorer);
    }
  }, [intent, flyTo]);

  const choosePlace = useCallback(
    (place: MapsPlace) => {
      if (routeOpen) {
        if (routeSlot === "from") setRouteFrom(place);
        else if (routeSlot === "to") setRouteTo(place);
        else if (!routeTo) setRouteTo(place);
        else setRouteFrom(place);
        setRouteSlot(null);
      } else {
        setSelected(place);
      }
    },
    [routeOpen, routeSlot, routeTo]
  );

  const runSearch = useCallback(
    async (query: string) => {
      setSearching(true);
      setCategory("");
      try {
        const near = { lat: viewRef.current.lat, lon: viewRef.current.lon };
        const found = await searchPlaces(query, near, 10);
        setResults(found);
        if (found.length > 0) {
          choosePlace(found[0]);
          flyTo(found[0].lat, found[0].lon, found[0].bbox ? 12 : 15);
        } else {
          setToast(`Zu „${query}“ habe ich nichts gefunden.`);
        }
      } catch {
        setToast("Die Suche ist gerade nicht erreichbar.");
      } finally {
        setSearching(false);
      }
    },
    [flyTo, choosePlace]
  );

  const runCategory = useCallback(
    async (key: string) => {
      if (category === key) {
        setCategory("");
        setResults([]);
        return;
      }
      setSearching(true);
      setCategory(key);
      try {
        const found = await nearbyPlaces(
          key,
          viewRef.current.lat,
          viewRef.current.lon,
          viewRef.current.zoom > 13 ? 1600 : 4500,
          30
        );
        setResults(found);
        if (found.length === 0) setToast("Hier in der Nähe finde ich dazu nichts.");
      } catch {
        setToast("Die Umgebungssuche ist gerade nicht erreichbar.");
      } finally {
        setSearching(false);
      }
    },
    [category]
  );

  useEffect(() => {
    if (!routeFrom || !routeTo) {
      setRoutes([]);
      return;
    }
    let cancelled = false;
    setRouteBusy(true);
    setRouteError("");
    const points = [
      { lat: routeFrom.lat, lon: routeFrom.lon },
      ...routeVia.map((stop) => ({ lat: stop.lat, lon: stop.lon })),
      { lat: routeTo.lat, lon: routeTo.lon },
    ];
    planRoute(points, routeMode, true)
      .then((found) => {
        if (cancelled) return;
        setRoutes(found);
        setRouteIndex(0);
        if (found.length === 0) {
          setRouteError("Für diese Strecke finde ich keine Route.");
          return;
        }
        const map = mapRef.current;
        const geometry = found[0].geometry;
        if (map && geometry.length > 1) {
          const lons = geometry.map((point) => point[0]);
          const lats = geometry.map((point) => point[1]);
          map.fitBounds(
            [
              [Math.min(...lons), Math.min(...lats)],
              [Math.max(...lons), Math.max(...lats)],
            ],
            { padding: { top: 150, bottom: 120, left: 420, right: 140 }, duration: 1400 }
          );
        }
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setRoutes([]);
        try {
          const parsed = JSON.parse(error.message);
          setRouteError(String(parsed.detail ?? error.message).slice(0, 200));
        } catch {
          setRouteError(error.message.slice(0, 200));
        }
      })
      .finally(() => {
        if (!cancelled) setRouteBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [routeFrom, routeTo, routeVia, routeMode]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 4200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const markers = useMemo<MapMarker[]>(() => {
    const list: MapMarker[] = results.map((place) => ({
      id: place.id + place.lat,
      lat: place.lat,
      lon: place.lon,
      icon: String(place.extra?.icon ?? "") || "📍",
      tone: "poi",
      active: selected?.id === place.id,
    }));
    if (routeFrom) {
      list.push({
        id: "route-from",
        lat: routeFrom.lat,
        lon: routeFrom.lon,
        icon: "🅰",
        tone: "start",
      });
    }
    routeVia.forEach((stop, index) => {
      list.push({
        id: `route-via-${index}`,
        lat: stop.lat,
        lon: stop.lon,
        icon: String(index + 1),
        tone: "poi",
      });
    });
    if (routeTo) {
      list.push({
        id: "route-to",
        lat: routeTo.lat,
        lon: routeTo.lon,
        icon: "🏁",
        tone: "ziel",
      });
    }
    if (home) {
      list.push({ id: "home", lat: home.lat, lon: home.lon, tone: "standort" });
    }
    (friends?.freunde ?? []).forEach((friend) => {
      list.push({
        id: `freund-${friend.id}`,
        lat: friend.lat,
        lon: friend.lon,
        icon: friend.avatar || "🙂",
        tone: "freund",
        stale: !friend.frisch,
        active: activeFriend?.id === friend.id,
      });
    });
    return list;
  }, [results, selected, routeFrom, routeTo, routeVia, home, friends, activeFriend]);

  const routeLines = useMemo<MapRouteLine[]>(
    () =>
      routes.map((route, index) => ({
        id: route.id,
        geometry: route.geometry,
        active: index === routeIndex,
      })),
    [routes, routeIndex]
  );

  const activeGeometry = routes[routeIndex]?.geometry;

  const handleMapClick = useCallback(
    async (lat: number, lon: number) => {
      if (routeSlot) {
        try {
          const place = await reversePlace(lat, lon);
          if (routeSlot === "from") setRouteFrom(place);
          else setRouteTo(place);
        } catch {
          setToast("Diesen Punkt konnte Jon nicht auflösen.");
        }
        setRouteSlot(null);
        return;
      }
      try {
        const place = await reversePlace(lat, lon);
        setSelected(place);
      } catch {
        setToast("Zu diesem Punkt gibt es keine Daten.");
      }
    },
    [routeSlot]
  );

  const handleMarkerClick = useCallback(
    (id: string) => {
      if (id.startsWith("freund-")) {
        const peerId = id.slice("freund-".length);
        const friend = (friends?.freunde ?? []).find(
          (entry) => entry.id === peerId
        );
        if (friend) {
          setActiveFriend(friend);
          setSelected(null);
          flyTo(friend.lat, friend.lon, Math.max(viewRef.current.zoom, 15));
        }
        return;
      }
      const found = results.find((place) => place.id + place.lat === id);
      if (found) {
        setActiveFriend(null);
        setSelected(found);
        flyTo(found.lat, found.lon, Math.max(viewRef.current.zoom, 15));
      }
    },
    [results, flyTo, friends]
  );

  const is3d = view.pitch > 12;
  const isGlobe = projection === "globe" || (projection === "auto" && view.zoom < 5.4);

  const toggle3d = () => {
    const map = mapRef.current;
    if (!map) return;
    const next = is3d ? 0 : 62;
    map.easeTo({
      pitch: next,
      zoom: is3d ? map.getZoom() : Math.max(map.getZoom(), 15.5),
      duration: 900,
    });
    if (!is3d) {
      setLayers((current) => ({ ...current, gebaeude3d: true }));
    }
  };

  const isEarth = layers.satellit && layers.gebaeude3d && terrain;

  const toggleEarth = () => {
    const map = mapRef.current;
    if (isEarth) {
      setLayers((current) => ({ ...current, satellit: false }));
      setTerrain(false);
      map?.easeTo({ pitch: 0, duration: 900 });
      return;
    }
    setLayers((current) => ({ ...current, satellit: true, gebaeude3d: true }));
    setTerrain(true);
    setProjection("auto");
    map?.easeTo({
      pitch: 66,
      zoom: Math.max(map.getZoom(), 15),
      duration: 1400,
    });
    setToast("Erde-Ansicht: Satellit, echtes Gelände und 3D-Gebäude.");
  };

  const toggleGlobe = () => {
    const map = mapRef.current;
    if (isGlobe) {
      setProjection("mercator");
      map?.easeTo({ zoom: Math.max(map.getZoom(), 11), duration: 1400 });
      return;
    }
    setProjection("globe");
    map?.easeTo({ zoom: Math.min(map.getZoom(), 3.4), pitch: 0, duration: 1400 });
  };

  const openStreet = (lat?: number, lon?: number) => {
    setStreet({
      lat: lat ?? selected?.lat ?? view.lat,
      lon: lon ?? selected?.lon ?? view.lon,
    });
  };

  const openExplorer = (mode: ExplorerMode, lat?: number, lon?: number) => {
    setExplorerStart({
      lat: lat ?? selected?.lat ?? view.lat,
      lon: lon ?? selected?.lon ?? view.lon,
    });
    setLayers((current) => ({ ...current, gebaeude3d: true }));
    setTerrain(true);
    setProjection("mercator");
    setExplorer(mode);
  };

  const overlayHidden = Boolean(explorer) || Boolean(street);

  return (
    <div className="jm-root" data-jm-theme={theme}>
      <MapCanvas
        theme={theme}
        center={{ lat: view.lat, lon: view.lon }}
        zoom={view.zoom}
        markers={overlayHidden ? [] : markers}
        routes={routeLines}
        layers={layers}
        terrain={terrain}
        projection={projection}
        onReady={(map) => {
          mapRef.current = map;
          const target = pendingStart.current;
          if (target) {
            pendingStart.current = null;
            map.jumpTo({ center: [target.lon, target.lat], zoom: target.zoom });
          }
        }}
        onMove={setView}
        onMapClick={handleMapClick}
        onMarkerClick={handleMarkerClick}
      />

      <AnimatePresence>
        {!overlayHidden && (
          <motion.div
            key="chrome"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, filter: "blur(12px)" }}
            transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="jm-layer" style={{ top: 18, left: 18 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div
                    className="jm-glass jm-glass--chrome"
                    style={{
                      padding: "9px 15px 9px 10px",
                      borderRadius: 999,
                    }}
                  >
                    <div className="jm-specular" />
                    <div className="jm-brand">
                      <span className="jm-brand-mark">🗺️</span>
                      Jon Maps
                    </div>
                  </div>
                  {!embedded && onClose && (
                    <button
                      className="jm-glass jm-glass--chrome jm-dock-btn jm-press"
                      style={{ width: 38, height: 38, borderRadius: 999 }}
                      onClick={onClose}
                      title="Jon Maps schließen"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <SearchPanel
                  config={config}
                  results={results}
                  busy={searching}
                  activeCategory={category}
                  onSearch={runSearch}
                  onCategory={runCategory}
                  onPick={(place) => {
                    choosePlace(place);
                    flyTo(place.lat, place.lon, place.bbox ? 12 : 16);
                  }}
                  onClear={() => {
                    setResults([]);
                    setSelected(null);
                    setCategory("");
                  }}
                  onOpenRoute={() => {
                    setRouteOpen(true);
                    if (!routeFrom && home) {
                      void reversePlace(home.lat, home.lon)
                        .then(setRouteFrom)
                        .catch(() => undefined);
                    }
                  }}
                />
              </div>
            </div>

            <div className="jm-layer" style={{ top: 18, right: 18 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <AnimatePresence>
                  {layersOpen && (
                    <LayerSheet
                      config={config}
                      layers={layers}
                      terrain={terrain}
                      theme={theme}
                      onToggle={(key) =>
                        setLayers((current) => ({
                          ...current,
                          [key]: !current[key],
                        }))
                      }
                      onTerrain={() => setTerrain((value) => !value)}
                      onTheme={setTheme}
                      homeName={homeName}
                      onPinHome={() => void pinHome()}
                      onLocate={() => void locate(true)}
                      friends={friends}
                      onSharing={(patch) => void changeSharing(patch)}
                      onShareNow={() => void pushLocation()}
                      onClose={() => setLayersOpen(false)}
                    />
                  )}
                </AnimatePresence>
                <button
                  className="jm-glass jm-glass--chrome jm-dock-btn jm-press"
                  style={{ width: 40, height: 40, borderRadius: 999 }}
                  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  title={theme === "dark" ? "Hellen Modus einschalten" : "Dunklen Modus einschalten"}
                >
                  {theme === "dark" ? "☀️" : "🌙"}
                </button>
              </div>
            </div>

            <div
              className="jm-layer"
              style={{ top: "50%", right: 18, transform: "translateY(-50%)" }}
            >
              <ControlDock
                bearing={view.bearing}
                pitch={view.pitch}
                is3d={is3d}
                isGlobe={isGlobe}
                isEarth={isEarth}
                layersOpen={layersOpen}
                onZoom={(delta) =>
                  mapRef.current?.easeTo({
                    zoom: mapRef.current.getZoom() + delta,
                    duration: 420,
                  })
                }
                onResetNorth={() =>
                  mapRef.current?.easeTo({ bearing: 0, duration: 700 })
                }
                onToggle3d={toggle3d}
                onToggleGlobe={toggleGlobe}
                onToggleEarth={toggleEarth}
                onLayers={() => setLayersOpen((value) => !value)}
                onLocate={() => void locate(true)}
                onExplore={() => openExplorer("mensch")}
                onStreet={() => openStreet()}
              />
            </div>

            <div
              className="jm-layer"
              style={{
                bottom: 18,
                left: 18,
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              <AnimatePresence>
                {routeOpen && (
                  <RoutePanel
                    key="route"
                    from={routeFrom}
                    to={routeTo}
                    via={routeVia}
                    mode={routeMode}
                    routes={routes}
                    activeIndex={routeIndex}
                    busy={routeBusy}
                    error={routeError}
                    onMode={setRouteMode}
                    onPick={setRouteIndex}
                    onSwap={() => {
                      setRouteFrom(routeTo);
                      setRouteTo(routeFrom);
                    }}
                    onClear={() => {
                      setRouteOpen(false);
                      setRoutes([]);
                      setRouteFrom(null);
                      setRouteTo(null);
                      setRouteVia([]);
                    }}
                    onEdit={(slot) => {
                      setRouteSlot(slot);
                      setToast(
                        slot === "from"
                          ? "Suche einen Ort oder klick auf die Karte, um den Start zu setzen."
                          : "Suche einen Ort oder klick auf die Karte, um das Ziel zu setzen."
                      );
                    }}
                    onRemoveVia={(index) =>
                      setRouteVia((current) =>
                        current.filter((_, position) => position !== index)
                      )
                    }
                    onDrive={() => {
                      const start = routes[routeIndex]?.geometry?.[0];
                      openExplorer(
                        routeMode === "fuss" ? "mensch" : "auto",
                        start ? start[1] : undefined,
                        start ? start[0] : undefined
                      );
                    }}
                  />
                )}
                {activeFriend && !routeOpen && (
                  <FriendSheet
                    key={`freund-${activeFriend.id}`}
                    friend={activeFriend}
                    distance={
                      home
                        ? Math.round(
                            Math.hypot(
                              (activeFriend.lat - home.lat) * 111320,
                              (activeFriend.lon - home.lon) *
                                111320 *
                                Math.cos((home.lat * Math.PI) / 180)
                            )
                          )
                        : null
                    }
                    onClose={() => setActiveFriend(null)}
                    onRouteTo={() => {
                      setRouteTo({
                        id: `freund:${activeFriend.id}`,
                        name: activeFriend.name,
                        label: "Standort deines Freundes",
                        lat: activeFriend.lat,
                        lon: activeFriend.lon,
                        kind: "freund",
                        category: "",
                        address: {},
                        bbox: null,
                        distance_m: null,
                        source: "jon-freunde",
                        extra: { icon: activeFriend.avatar },
                      });
                      setRouteOpen(true);
                      setActiveFriend(null);
                      if (!routeFrom && home) {
                        void reversePlace(home.lat, home.lon)
                          .then(setRouteFrom)
                          .catch(() => undefined);
                      }
                    }}
                    onStreet={() => {
                      openStreet(activeFriend.lat, activeFriend.lon);
                      setActiveFriend(null);
                    }}
                    onChat={(id) => {
                      setActiveFriend(null);
                      onAskJon?.(`/freunde ${id}`);
                    }}
                  />
                )}
                {selected && !activeFriend && !routeOpen && (
                  <PlaceSheet
                    key={selected.id + selected.lat}
                    place={selected}
                    onClose={() => setSelected(null)}
                    onRouteTo={() => {
                      setRouteTo(selected);
                      setRouteOpen(true);
                      if (!routeFrom && home) {
                        void reversePlace(home.lat, home.lon)
                          .then(setRouteFrom)
                          .catch(() => undefined);
                      }
                    }}
                    onRouteFrom={() => {
                      setRouteFrom(selected);
                      setRouteOpen(true);
                    }}
                    onStreet={() => openStreet(selected.lat, selected.lon)}
                    onExplore={() =>
                      openExplorer("mensch", selected.lat, selected.lon)
                    }
                    onAskJon={(question) => onAskJon?.(question)}
                  />
                )}
              </AnimatePresence>

              <div
                className="jm-glass jm-glass--thin"
                style={{
                  padding: "6px 12px",
                  borderRadius: 999,
                  fontSize: 10,
                  color: "var(--jm-text-faint)",
                  alignSelf: "flex-start",
                }}
              >
                {config?.attribution ?? "© OpenStreetMap-Mitwirkende"}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {street && (
          <StreetView
            key="street"
            lat={street.lat}
            lon={street.lon}
            onClose={() => setStreet(null)}
            onWalkMode={(lat, lon) => {
              setStreet(null);
              openExplorer("mensch", lat, lon);
              setToast(
                "Keine Straßenfotos an dieser Stelle — du stehst jetzt in Jons " +
                  "3D-Ansicht auf der Straße. W A S D laufen, Maus ziehen schaut um."
              );
            }}
            onPositionChange={(lat, lon) => {
              mapRef.current?.jumpTo({ center: [lon, lat] });
            }}
          />
        )}
      </AnimatePresence>

      {explorer && (
        <WorldExplorer
          map={mapRef.current}
          mode={explorer}
          start={explorerStart}
          route={activeGeometry}
          onModeChange={setExplorer}
          onClose={() => {
            setExplorer(null);
            setProjection("auto");
          }}
        />
      )}

      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast}
            className="jm-glass jm-glass--chrome"
            style={{
              position: "absolute",
              bottom: 24,
              left: "50%",
              transform: "translateX(-50%)",
              padding: "11px 20px",
              borderRadius: 999,
              fontSize: 12.5,
              zIndex: 40,
            }}
            initial={{ opacity: 0, y: 18, filter: "blur(10px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: 12, filter: "blur(8px)" }}
            transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="jm-specular" />
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
