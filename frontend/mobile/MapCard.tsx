import React, {useEffect, useId, useMemo, useRef, useState} from "react";
import {createPortal} from "react-dom";
import {AnimatePresence, motion} from "framer-motion";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {Bike, Box, Car, Crosshair, Footprints, Layers, MapPin, Maximize2, Navigation, Train, X} from "lucide-react";
import {api, haptic} from "./bridge";
import {overlayHost, spring, useBackHandler} from "./ui";

type Ort = {id?: string; name?: string; label?: string; lat: number; lon: number; category?: string; kind?: string; distance_m?: number | null; extra?: Record<string, any>};
type Route = {id: string; mode?: string; distance_m: number; duration_s: number; geometry: [number, number][]; steps?: {text: string; distance_m: number}[]; summary?: string};

const stile: Record<string, Promise<any>> = {};
const stil = (theme: string) => stile[theme] ||= api(`/api/maps/styles/${theme}`).catch(e => {delete stile[theme]; throw e;});

export const dauer = (s = 0) => {const m = Math.round(s / 60); return m < 60 ? `${Math.max(1, m)} Min` : `${Math.floor(m / 60)} Std ${m % 60 ? `${m % 60} Min` : ""}`.trim();};
export const strecke = (m = 0) => m < 950 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(m < 10_000 ? 1 : 0).replace(".", ",")} km`;
const modusIcon = (mode = "") => /fuss|foot|walk/.test(mode) ? <Footprints/> : /rad|bike|cycl/.test(mode) ? <Bike/> : /oepnv|transit|bahn|zug/.test(mode) ? <Train/> : <Car/>;

function aufbereiten(data: any) {
  const stationen: Ort[] = (data.stationen?.length ? data.stationen : data.karte?.marker?.length ? data.karte.marker : data.treffer || []).filter((o: Ort) => Number.isFinite(o?.lat) && Number.isFinite(o?.lon));
  if (!stationen.length && data.ort && Number.isFinite(data.ort.lat)) stationen.push(data.ort);
  const routen: Route[] = (data.routen || []).filter((r: Route) => r.geometry?.length > 1);
  if (!routen.length && data.karte?.route?.length > 1) routen.push({id: "route", distance_m: 0, duration_s: 0, geometry: data.karte.route});
  const mitte = data.karte?.center || data.mittelpunkt || (stationen[0] ? {lat: stationen[0].lat, lon: stationen[0].lon} : {lat: 48.2, lon: 16.37});
  const titel = data.aktion === "route" ? [stationen[0]?.name || data.start?.name || "Start", stationen[stationen.length - 1]?.name || data.ziel?.name || "Ziel"].join(" → ")
    : data.aktion === "umgebung" ? data.kategorie || data.filter || "In der Nähe" : data.ort?.name || data.anfrage || stationen[0]?.name || "Jon Maps";
  return {stationen, routen, mitte, titel, route: data.aktion === "route"};
}

function JonKarte({data, gross, routeIndex, auswahl, drei, satellit, onKarte}: {data: any; gross: boolean; routeIndex: number; auswahl: number | null; drei: boolean; satellit: boolean; onKarte?: (m: maplibregl.Map) => void}) {
  const halter = useRef<HTMLDivElement>(null);
  const karte = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker[]>([]);
  const {stationen, routen, mitte, route} = useMemo(() => aufbereiten(data), [data]);
  const [fehler, setFehler] = useState("");

  function grenzen() {
    const punkte: [number, number][] = [...stationen.map(o => [o.lon, o.lat] as [number, number]), ...(routen[routeIndex]?.geometry || [])];
    if (!punkte.length) return null;
    const b = new maplibregl.LngLatBounds(punkte[0], punkte[0]);
    punkte.forEach(p => b.extend(p));
    return b;
  }

  function zeichnen(m: maplibregl.Map) {
    const aktiv = routen[routeIndex];
    const quelle = m.getSource("jon-route") as maplibregl.GeoJSONSource | undefined;
    const alle = {type: "FeatureCollection" as const, features: routen.map((r, i) => ({type: "Feature" as const, properties: {aktiv: i === routeIndex ? 1 : 0}, geometry: {type: "LineString" as const, coordinates: i === routeIndex ? r.geometry.slice(0, 2) : r.geometry}}))};
    if (!quelle) {
      m.addSource("jon-route", {type: "geojson", data: alle, lineMetrics: true});
      m.addLayer({id: "jon-route-alt", type: "line", source: "jon-route", filter: ["==", ["get", "aktiv"], 0], layout: {"line-cap": "round", "line-join": "round"}, paint: {"line-color": "#7d8aa8", "line-width": 5, "line-opacity": .55}});
      m.addLayer({id: "jon-route-glow", type: "line", source: "jon-route", filter: ["==", ["get", "aktiv"], 1], layout: {"line-cap": "round", "line-join": "round"}, paint: {"line-color": "#5ee7ff", "line-width": 16, "line-blur": 10, "line-opacity": .45}});
      m.addLayer({id: "jon-route-main", type: "line", source: "jon-route", filter: ["==", ["get", "aktiv"], 1], layout: {"line-cap": "round", "line-join": "round"}, paint: {"line-width": 6, "line-gradient": ["interpolate", ["linear"], ["line-progress"], 0, "#5ee7ff", .5, "#3b6cff", 1, "#a35cff"]}});
    } else quelle.setData(alle);
    if (!aktiv) return;
    const n = aktiv.geometry.length;
    const beginn = performance.now();
    const laenge = gross ? 1700 : 1300;
    const schritt = (jetzt: number) => {
      const t = Math.min(1, (jetzt - beginn) / laenge);
      const e = 1 - Math.pow(1 - t, 3);
      const k = Math.max(2, Math.round(n * e));
      const src = m.getSource("jon-route") as maplibregl.GeoJSONSource | undefined;
      if (!src) return;
      src.setData({...alle, features: alle.features.map((f, i) => i === routeIndex ? {...f, geometry: {...f.geometry, coordinates: aktiv.geometry.slice(0, k)}} : f)});
      if (t < 1) requestAnimationFrame(schritt);
    };
    requestAnimationFrame(schritt);
  }

  function setzeMarker(m: maplibregl.Map) {
    marker.current.forEach(x => x.remove());
    marker.current = stationen.map((o, i) => {
      const el = document.createElement("div");
      const letzter = i === stationen.length - 1;
      el.className = `jm-pin ${route ? (i === 0 ? "start" : letzter ? "ziel" : "halt") : "poi"} ${auswahl === i ? "aktiv" : ""}`;
      const kopf = document.createElement("span");
      kopf.textContent = route ? (i === 0 ? "A" : letzter ? "B" : String(i)) : String(o.extra?.icon || "") || "●";
      kopf.style.animationDelay = `${(gross ? 250 : 120) + i * 70}ms`;
      el.appendChild(kopf);
      return new maplibregl.Marker({element: el, anchor: "bottom"}).setLngLat([o.lon, o.lat]).addTo(m);
    });
    if (!route && (data.mittelpunkt || data.aktion === "umgebung")) {
      const puls = document.createElement("div");
      puls.className = "jm-puls";
      marker.current.push(new maplibregl.Marker({element: puls}).setLngLat([mitte.lon, mitte.lat]).addTo(m));
    }
  }

  function kamera(m: maplibregl.Map, sanft = true) {
    const b = grenzen();
    const rand = gross ? {top: 130, bottom: 320, left: 50, right: 86} : 34;
    const neigen = () => m.easeTo({pitch: drei ? 55 : 0, bearing: drei ? -18 : 0, duration: 1300, easing: t => 1 - Math.pow(1 - t, 3)});
    if (b && (stationen.length > 1 || routen.length)) {
      const ziel = m.cameraForBounds(b, {padding: rand, maxZoom: 16});
      if (ziel) m.flyTo({...ziel, pitch: 0, bearing: 0, duration: sanft ? 1500 : 0, essential: true});
      m.once("moveend", neigen);
    } else {
      m.flyTo({center: [mitte.lon, mitte.lat], zoom: data.karte?.zoom || (data.aktion === "erkunden" ? 16 : 14.5), duration: sanft ? 1500 : 0, essential: true});
      m.once("moveend", neigen);
    }
  }

  useEffect(() => {
    let lebt = true;
    const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
    stil(theme).then(style => {
      if (!lebt || !halter.current) return;
      const m = new maplibregl.Map({container: halter.current, style, center: [mitte.lon, mitte.lat], zoom: Math.max(2, (data.karte?.zoom || 12) - 2.5), interactive: gross, attributionControl: gross ? {compact: true} : false, fadeDuration: 180, pitchWithRotate: true, dragRotate: gross, touchPitch: gross});
      karte.current = m;
      m.on("load", () => {
        if (!lebt) return;
        zeichnen(m);
        setzeMarker(m);
        kamera(m);
        onKarte?.(m);
      });
      m.on("error", e => {if (String(e?.error?.message || "").includes("style")) setFehler("Karte konnte nicht geladen werden.");});
      const beobachter = new ResizeObserver(() => m.resize());
      beobachter.observe(halter.current);
      m.once("remove", () => beobachter.disconnect());
    }).catch(() => setFehler("Kartenstil vom Pi nicht erreichbar."));
    return () => {lebt = false; marker.current.forEach(x => x.remove()); karte.current?.remove(); karte.current = null;};
  }, []);

  useEffect(() => {const m = karte.current; if (m?.isStyleLoaded()) {zeichnen(m); kamera(m);}}, [routeIndex]);
  useEffect(() => {const m = karte.current; if (m?.isStyleLoaded()) setzeMarker(m);}, [auswahl]);
  useEffect(() => {const m = karte.current; if (m?.isStyleLoaded()) kamera(m);}, [drei]);
  useEffect(() => {
    const m = karte.current;
    if (!m?.isStyleLoaded()) return;
    for (const id of ["jon-satellit", "satellit"]) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", satellit ? "visible" : "none");
  }, [satellit]);

  return <div className="jm-canvas">{fehler ? <div className="jm-fehler"><MapPin/>{fehler}</div> : <div ref={halter} style={{position: "absolute", inset: 0}}/>}{!gross && <span className="jm-osm">© OpenStreetMap · OpenFreeMap</span>}</div>;
}

export default function MapCard({data}: {data: any}) {
  const id = useId();
  const [gross, setGross] = useState(false), [routeIndex, setRouteIndex] = useState(0), [auswahl, setAuswahl] = useState<number | null>(null), [drei, setDrei] = useState(false), [satellit, setSatellit] = useState(false);
  const karte = useRef<maplibregl.Map | null>(null);
  const {stationen, routen, titel, route} = useMemo(() => aufbereiten(data), [data]);
  const aktiv = routen[routeIndex];
  const info = route && aktiv ? `${dauer(aktiv.duration_s)} · ${strecke(aktiv.distance_m)}${data.modus_label ? ` · ${data.modus_label}` : ""}` : stationen.length > 1 ? `${stationen.length} Orte` : data.text?.slice(0, 80) || "";
  useBackHandler(gross, () => setGross(false));
  useEffect(() => {if (gross) setDrei(true);}, [gross]);
  const oeffnen = () => {haptic("tap"); setGross(true);};
  const allesZeigen = () => {
    const m = karte.current;
    const punkte: [number, number][] = [...(routen[routeIndex]?.geometry || []), ...stationen.map(o => [o.lon, o.lat] as [number, number])];
    if (!m || !punkte.length) return;
    haptic("tick");
    setAuswahl(null);
    const b = punkte.reduce((g, p) => g.extend(p), new maplibregl.LngLatBounds(punkte[0], punkte[0]));
    const ziel = m.cameraForBounds(b, {padding: {top: 130, bottom: 320, left: 50, right: 86}, maxZoom: 16});
    if (ziel) m.flyTo({...ziel, pitch: drei ? 55 : 0, bearing: drei ? -18 : 0, duration: 1200, essential: true});
  };
  const hinfliegen = (i: number) => {
    const o = stationen[i];
    if (!o) return;
    haptic("tick");
    setAuswahl(i);
    karte.current?.flyTo({center: [o.lon, o.lat], zoom: 16, pitch: 55, bearing: -18, duration: 1600, essential: true});
  };
  return <>
    <div className="map-slot">{!gross && <motion.div layoutId={id} className="map-card" onClick={oeffnen} transition={spring}>
      <div className="map-mini"><JonKarte data={data} gross={false} routeIndex={routeIndex} auswahl={null} drei={false} satellit={false}/></div>
      <div className="map-info">
        <span className="map-icon">{route ? modusIcon(data.modus || aktiv?.mode) : <MapPin/>}</span>
        <div><strong>{titel}</strong>{info && <small>{info}</small>}</div>
        <span className="map-open"><Maximize2/></span>
      </div>
    </motion.div>}</div>
    {createPortal(<AnimatePresence>{gross && <motion.div key="voll" layoutId={id} className="map-full" transition={spring}>
      <JonKarte data={data} gross routeIndex={routeIndex} auswahl={auswahl} drei={drei} satellit={satellit} onKarte={m => {karte.current = m;}}/>
      <motion.div className="map-top" initial={{opacity: 0, y: -12}} animate={{opacity: 1, y: 0}} transition={{delay: .25}}>
        <button className="circle glass" aria-label="Karte schließen" onClick={() => {haptic("tick"); setGross(false);}}><X/></button>
        <div className="map-title glass"><strong>{titel}</strong>{info && <small>{info}</small>}</div>
      </motion.div>
      <motion.div className="map-tools" initial={{opacity: 0, x: 16}} animate={{opacity: 1, x: 0}} transition={{delay: .35}}>
        <button className={`glass ${drei ? "on" : ""}`} aria-label="3D" onClick={() => {haptic("tick"); setDrei(!drei);}}><Box/></button>
        <button className={`glass ${satellit ? "on" : ""}`} aria-label="Satellit" onClick={() => {haptic("tick"); setSatellit(!satellit);}}><Layers/></button>
        <button className="glass" aria-label="Alles zeigen" onClick={allesZeigen}><Crosshair/></button>
      </motion.div>
      <motion.div className="map-sheet glass" initial={{y: "100%"}} animate={{y: 0}} transition={{...spring, delay: .15}}>
        <div className="sheet-handle"/>
        {route && routen.length > 1 && <div className="map-routes">{routen.map((r, i) => <button key={r.id + i} className={i === routeIndex ? "on" : ""} onClick={() => {haptic("tick"); setRouteIndex(i);}}>{modusIcon(r.mode || data.modus)}<b>{dauer(r.duration_s)}</b><span>{strecke(r.distance_m)}</span></button>)}</div>}
        <div className="map-list">
          {route && aktiv?.steps?.length ? aktiv.steps.slice(0, 40).map((s, i) => <div key={i} className="map-step"><Navigation/><span>{s.text}</span><small>{s.distance_m ? strecke(s.distance_m) : ""}</small></div>)
            : stationen.map((o, i) => <button key={(o.id || "") + i} className={`map-step ${auswahl === i ? "on" : ""}`} onClick={() => hinfliegen(i)}><span className="map-num">{route ? (i === 0 ? "A" : i === stationen.length - 1 ? "B" : i) : String(o.extra?.icon || "") || i + 1}</span><span>{o.name || o.label}<small>{[o.category || o.kind, o.distance_m ? strecke(o.distance_m) : ""].filter(Boolean).join(" · ")}</small></span></button>)}
          {data.text && <p className="hint" style={{margin: "10px 4px 0"}}>{data.text}</p>}
        </div>
      </motion.div>
    </motion.div>}</AnimatePresence>, overlayHost())}
  </>;
}
