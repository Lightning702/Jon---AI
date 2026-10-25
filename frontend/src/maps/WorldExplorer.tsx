import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import type maplibregl from "maplibre-gl";
import { Camera, Car, Footprints, MapPin, Plane, Search, X } from "lucide-react";
import { PlaneLayer } from "./PlaneLayer";
import { FARBEN, Fortbewegung, MODELLE, ModellArt, modellById, modellFuer } from "./Modelle";
import { HEUTE, Zeitreise, epochenName } from "./Zeitreise";
import { searchPlaces } from "../lib/maps";

export type ExplorerMode = Fortbewegung;

interface Props {
  map: maplibregl.Map | null;
  start: { lat: number; lon: number };
  route?: [number, number][];
  modus?: Fortbewegung;
  jahr?: number;
  onClose: () => void;
  onPosition?: (lat: number, lon: number) => void;
}

const TO_RAD = Math.PI / 180;
const TO_DEG = 180 / Math.PI;
const MAX_HEIGHT = 15000;
const AUGE = 1.68;

const FLUG: Record<string, { basis: number; bereich: number; boost: number }> = {
  doppeldecker: { basis: 18, bereich: 30, boost: 44 },
  propeller: { basis: 26, bereich: 44, boost: 68 },
  jet: { basis: 55, bereich: 250, boost: 430 },
};

const AUTO: Record<string, { vmax: number; beschl: number }> = {
  oldtimer: { vmax: 19, beschl: 1.4 },
  rundheck: { vmax: 33, beschl: 2.4 },
  limousine: { vmax: 58, beschl: 4.4 },
  suv: { vmax: 52, beschl: 3.9 },
  sport: { vmax: 86, beschl: 8.2 },
};

const SCHNELLJAHRE = [1800, 1900, 1950, 1990, 2014];

function segmentLength(a: [number, number], b: [number, number]): number {
  const dLat = (b[1] - a[1]) * 111320;
  const dLon = (b[0] - a[0]) * 111320 * Math.cos(a[1] * TO_RAD);
  return Math.hypot(dLat, dLon);
}

function bearingOf(a: [number, number], b: [number, number]): number {
  const y = Math.sin((b[0] - a[0]) * TO_RAD) * Math.cos(b[1] * TO_RAD);
  const x =
    Math.cos(a[1] * TO_RAD) * Math.sin(b[1] * TO_RAD) -
    Math.sin(a[1] * TO_RAD) * Math.cos(b[1] * TO_RAD) * Math.cos((b[0] - a[0]) * TO_RAD);
  return (Math.atan2(y, x) * TO_DEG + 360) % 360;
}

function shortestTurn(from: number, to: number): number {
  return ((to - from + 540) % 360) - 180;
}

function versetzt(lat: number, lon: number, nord: number, ost: number): { lat: number; lon: number } {
  const neuLat = Math.max(-85, Math.min(85, lat + nord / 111320));
  const skala = 111320 * Math.max(0.12, Math.cos(neuLat * TO_RAD));
  return { lat: neuLat, lon: ((lon + ost / skala + 540) % 360) - 180 };
}

type Ring = [number, number][];
type Hindernis = { ringe: Ring[]; west: number; ost: number; sued: number; nord: number };

function imRing(lon: number, lat: number, ring: Ring): boolean {
  let drin = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi || 1e-12) + xi) drin = !drin;
  }
  return drin;
}

class Hindernisse {
  private liste: Hindernis[] = [];
  private mitte = { lat: 999, lon: 999 };

  aktualisieren(map: maplibregl.Map, lat: number, lon: number, zeit: Zeitreise, zwingend = false): void {
    if (!zwingend && Math.abs(lat - this.mitte.lat) * 111320 < 40 && Math.abs(lon - this.mitte.lon) * 111320 * Math.cos(lat * TO_RAD) < 40) return;
    this.mitte = { lat, lon };
    const schicht = map.getLayer("jon-3d-gebaeude") as unknown as { source?: string } | undefined;
    if (!schicht?.source) {
      this.liste = [];
      return;
    }
    const rLat = 140 / 111320;
    const rLon = rLat / Math.max(0.15, Math.cos(lat * TO_RAD));
    const neu: Hindernis[] = [];
    let features: ReturnType<maplibregl.Map["querySourceFeatures"]> = [];
    try {
      features = map.querySourceFeatures(schicht.source, { sourceLayer: "building" });
    } catch {
      features = [];
    }
    for (const f of features) {
      const hoehe = Number(f.properties?.render_height ?? f.properties?.height ?? 0);
      if (hoehe < 2.2 || !zeit.sichtbar(f.id as number | string | undefined, hoehe)) continue;
      const g = f.geometry;
      const polygone = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
      for (const poly of polygone) {
        const aussen = poly[0] as Ring;
        if (!aussen?.length) continue;
        let west = 180, ost = -180, sued = 90, nord = -90;
        for (const [x, y] of aussen) {
          if (x < west) west = x;
          if (x > ost) ost = x;
          if (y < sued) sued = y;
          if (y > nord) nord = y;
        }
        if (ost < lon - rLon || west > lon + rLon || nord < lat - rLat || sued > lat + rLat) continue;
        neu.push({ ringe: poly as Ring[], west, ost, sued, nord });
      }
    }
    this.liste = neu;
  }

  trifft(lat: number, lon: number, rand = 0): boolean {
    const dLat = rand / 111320;
    const dLon = dLat / Math.max(0.15, Math.cos(lat * TO_RAD));
    for (const h of this.liste) {
      if (lon < h.west - dLon || lon > h.ost + dLon || lat < h.sued - dLat || lat > h.nord + dLat) continue;
      const proben: [number, number][] = rand ? [[lon, lat], [lon + dLon, lat], [lon - dLon, lat], [lon, lat + dLat], [lon, lat - dLat]] : [[lon, lat]];
      for (const [x, y] of proben) {
        if (imRing(x, y, h.ringe[0]) && !h.ringe.slice(1).some((loch) => imRing(x, y, loch))) return true;
      }
    }
    return false;
  }
}

export default function WorldExplorer({ map, start, route, modus = "flugzeug", jahr: startJahr, onClose, onPosition }: Props) {
  const [art, setArt] = useState<Fortbewegung>(modus);
  const [jahr, setJahr] = useState<number>(startJahr ?? HEUTE);
  const [jahrText, setJahrText] = useState(String(startJahr ?? HEUTE));
  const [modellWahl, setModellWahl] = useState<Record<Fortbewegung, string | null>>({ fuss: null, auto: null, flugzeug: null });
  const [farbe, setFarbe] = useState(1);
  const [nah, setNah] = useState(art === "fuss");
  const [followRoute, setFollowRoute] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [suche, setSuche] = useState("");
  const [sucheLaeuft, setSucheLaeuft] = useState(false);
  const [meldung, setMeldung] = useState("");
  const [zeitInfo, setZeitInfo] = useState({ bekannte: 0, ausgeblendet: 0, luftbild: "" });
  const [hud, setHud] = useState({ speed: 0, altitude: 0, ground: 0, heading: 0, pitch: 0, roll: 0, throttle: 0.55, climb: 0, lat: start.lat, lon: start.lon });

  const modell: ModellArt = useMemo(() => {
    const gewaehlt = modellWahl[art];
    return (gewaehlt && modellById(gewaehlt)) || modellFuer(art, jahr);
  }, [art, jahr, modellWahl]);

  const stateRef = useRef({
    lat: start.lat,
    lon: start.lon,
    altitude: 900,
    heading: 0,
    pitch: 0,
    roll: 0,
    speed: 0,
    throttle: 0.55,
    stickPitch: 0,
    stickRoll: 0,
    travelled: 0,
    blick: -8,
    schritt: 0,
    lenkung: 0,
    sprung: 0,
    vz: 0,
    zoomFaktor: 1,
  });
  const keys = useRef<Set<string>>(new Set());
  const dragRef = useRef<{ x: number; y: number; heading: number; blick: number } | null>(null);
  const routeRef = useRef(route);
  routeRef.current = route;
  const followRef = useRef(followRoute);
  followRef.current = followRoute;
  const artRef = useRef(art);
  artRef.current = art;
  const nahRef = useRef(nah);
  nahRef.current = nah;
  const modellRef = useRef(modell);
  modellRef.current = modell;
  const farbeRef = useRef(FARBEN[farbe].wert);
  farbeRef.current = FARBEN[farbe].wert;
  const layerRef = useRef<PlaneLayer | null>(null);
  const zeitRef = useRef<Zeitreise | null>(null);
  const wechselRef = useRef<Fortbewegung | null>(null);

  useEffect(() => {
    const current = stateRef.current;
    current.lat = start.lat;
    current.lon = start.lon;
    current.travelled = 0;
    const line = routeRef.current;
    if (line && line.length > 1) current.heading = bearingOf(line[0], line[1]);
  }, [start.lat, start.lon]);

  useEffect(() => {
    zeitRef.current?.setJahr(jahr);
  }, [jahr]);

  useEffect(() => {
    if (!modell.animiert) layerRef.current?.setModell(modell.bauen(farbeRef.current, 0));
  }, [modell, farbe]);

  useEffect(() => {
    wechselRef.current = art;
    setNah(art === "fuss");
  }, [art]);

  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      const ziel = event.target as HTMLElement | null;
      if (ziel && (ziel.tagName === "INPUT" || ziel.tagName === "TEXTAREA")) return;
      const key = event.key.toLowerCase();
      if (key === "escape") {
        onClose();
        return;
      }
      if (key === "c") {
        setNah((value) => !value);
        return;
      }
      if (key === "1") setArt("fuss");
      if (key === "2") setArt("auto");
      if (key === "3") setArt("flugzeug");
      keys.current.add(key);
      if (["w", "a", "s", "d", "q", "e", "r", "f", "arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(key)) event.preventDefault();
    };
    const up = (event: KeyboardEvent) => {
      keys.current.delete(event.key.toLowerCase());
    };
    const blur = () => keys.current.clear();
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", blur);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", blur);
    };
  }, [onClose]);

  useEffect(() => {
    if (!map) return;
    const center = map.getCenter();
    const restore = { center: [center.lng, center.lat] as [number, number], zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing() };
    const alteMaxZoom = map.getMaxZoom();
    const alteMaxPitch = map.getMaxPitch();
    const altesGelaende = map.getTerrain();
    try {
      map.setMaxZoom(24);
      map.setMaxPitch(100);
    } catch {
      try {
        map.setMaxPitch(85);
      } catch {
        map.getMaxPitch();
      }
    }
    if (altesGelaende) {
      try {
        map.setTerrain({ ...altesGelaende, exaggeration: 1 });
      } catch {
        map.getTerrain();
      }
    }
    const grenzePitch = map.getMaxPitch();
    const altesLicht = map.getLight();
    const alterHimmel = map.getSky();
    const satellitSichtbar = map.getLayer("jon-satellit") ? map.getLayoutProperty("jon-satellit", "visibility") : undefined;
    const tageslicht = () => {
      try {
        const licht = map.getLight();
        if (!licht || licht.color !== "#fff6e8" || licht.intensity !== 0.5) map.setLight({ anchor: "map", color: "#fff6e8", intensity: 0.5, position: [1.25, 215, 38] });
        if (map.getLayer("jon-satellit") && map.getLayoutProperty("jon-satellit", "visibility") !== "visible") map.setLayoutProperty("jon-satellit", "visibility", "visible");
      } catch {
        map.getLight();
      }
    };
    map.on("styledata", tageslicht);
    try {
      map.setLight({ anchor: "map", color: "#fff6e8", intensity: 0.5, position: [1.25, 215, 38] });
      map.setSky({
        "sky-color": "#6fa8dc",
        "horizon-color": "#d6e6f2",
        "fog-color": "#e3ebf2",
        "sky-horizon-blend": 0.55,
        "horizon-fog-blend": 0.7,
        "fog-ground-blend": 0.25,
        "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 10, 1, 12, 0],
      } as maplibregl.SkySpecification);
      if (map.getLayer("jon-satellit")) map.setLayoutProperty("jon-satellit", "visibility", "visible");
    } catch {
      map.getLight();
    }
    const layer = new PlaneLayer(modellRef.current.bauen(farbeRef.current, 0), "jon-weltmodell");
    layerRef.current = layer;
    let mounted = false;
    try {
      if (!map.getLayer(layer.id)) {
        map.addLayer(layer);
        mounted = true;
      }
    } catch {
      mounted = false;
    }
    const zeit = new Zeitreise(map);
    zeitRef.current = zeit;
    zeit.onAenderung = () => setZeitInfo({ bekannte: zeit.bekannte, ausgeblendet: zeit.ausgeblendet, luftbild: zeit.luftbildJahr });
    zeit.setJahr(startJahr ?? HEUTE);
    const hindernisse = new Hindernisse();

    const ground = (lon = stateRef.current.lon, lat = stateRef.current.lat) => {
      try {
        return map.queryTerrainElevation([lon, lat]) ?? 0;
      } catch {
        return 0;
      }
    };

    const state = stateRef.current;
    if (artRef.current === "flugzeug") state.altitude = Math.max(state.altitude, ground() + 620);
    else state.altitude = ground();

    let frame = 0;
    let last = performance.now();
    let hudTick = 0;
    let ladeTick = 0;
    let animTick = 0;

    const bewegen = (nord: number, ost: number, rand: number): boolean => {
      const current = stateRef.current;
      const ziel = versetzt(current.lat, current.lon, nord, ost);
      if (!hindernisse.trifft(ziel.lat, ziel.lon, rand)) {
        current.lat = ziel.lat;
        current.lon = ziel.lon;
        return true;
      }
      const nurNord = versetzt(current.lat, current.lon, nord, 0);
      if (Math.abs(nord) > 1e-4 && !hindernisse.trifft(nurNord.lat, nurNord.lon, rand)) {
        current.lat = nurNord.lat;
        current.lon = nurNord.lon;
        return false;
      }
      const nurOst = versetzt(current.lat, current.lon, 0, ost);
      if (Math.abs(ost) > 1e-4 && !hindernisse.trifft(nurOst.lat, nurOst.lon, rand)) {
        current.lat = nurOst.lat;
        current.lon = nurOst.lon;
      }
      return false;
    };

    const gehen = (dt: number) => {
      const current = stateRef.current;
      const held = keys.current;
      const vor = (held.has("w") || held.has("arrowup") ? 1 : 0) - (held.has("s") || held.has("arrowdown") ? 1 : 0);
      const seit = (held.has("d") ? 1 : 0) - (held.has("a") ? 1 : 0);
      const drehen = (held.has("e") || held.has("arrowright") ? 1 : 0) - (held.has("q") || held.has("arrowleft") ? 1 : 0);
      current.heading = (current.heading + drehen * 95 * dt + 360) % 360;
      const ziel = vor || seit ? (held.has("shift") ? 5.6 : 1.7) : 0;
      current.speed += (ziel - current.speed) * Math.min(1, dt * 6);
      const laenge = Math.hypot(vor, seit) || 1;
      const h = current.heading * TO_RAD;
      const weg = current.speed * dt;
      const nord = ((Math.cos(h) * vor - Math.sin(h) * seit) / laenge) * weg;
      const ost = ((Math.sin(h) * vor + Math.cos(h) * seit) / laenge) * weg;
      if (weg > 0) bewegen(nord, ost, 0.35);
      current.schritt += (weg / 0.75) * Math.PI;
      const boden = ground();
      if (held.has(" ") && current.sprung <= 0.001 && current.vz <= 0) current.vz = 3.6;
      current.vz -= 9.81 * dt;
      current.sprung = Math.max(0, current.sprung + current.vz * dt);
      if (current.sprung === 0) current.vz = Math.max(0, current.vz);
      current.altitude = boden + current.sprung;
      current.pitch = 0;
      current.roll = 0;
    };

    const fahren = (dt: number) => {
      const current = stateRef.current;
      const held = keys.current;
      const daten = AUTO[modellRef.current.id] ?? AUTO.limousine;
      const gas = held.has("w") || held.has("arrowup") ? 1 : 0;
      const bremse = held.has("s") || held.has("arrowdown") ? 1 : 0;
      const lenk = (held.has("d") || held.has("arrowright") ? 1 : 0) - (held.has("a") || held.has("arrowleft") ? 1 : 0);
      const handbremse = held.has(" ");
      if (gas) current.speed += daten.beschl * (1 - Math.max(0, current.speed) / daten.vmax) * dt * (held.has("shift") ? 1.35 : 1);
      if (bremse) current.speed -= (current.speed > 0.5 ? 9 : 3) * dt;
      if (handbremse) current.speed -= Math.sign(current.speed) * Math.min(Math.abs(current.speed), 11 * dt);
      if (!gas && !bremse) current.speed -= Math.sign(current.speed) * Math.min(Math.abs(current.speed), (0.4 + Math.abs(current.speed) * 0.035) * dt);
      current.speed = Math.max(-7, Math.min(daten.vmax * 1.08, current.speed));
      const maxLenk = 34 / (1 + Math.abs(current.speed) / 16);
      current.lenkung += (lenk * maxLenk - current.lenkung) * Math.min(1, dt * 5);
      const radstand = 2.7;
      const drehrate = (current.speed / radstand) * Math.tan(current.lenkung * TO_RAD);
      current.heading = (current.heading + drehrate * TO_DEG * dt + 360) % 360;
      const h = current.heading * TO_RAD;
      const weg = current.speed * dt;
      if (Math.abs(weg) > 0) {
        const frei = bewegen(Math.cos(h) * weg, Math.sin(h) * weg, 0.9);
        if (!frei) current.speed *= Math.abs(current.speed) > 6 ? -0.25 : 0.5;
      }
      const vorn = versetzt(current.lat, current.lon, Math.cos(h) * 1.6, Math.sin(h) * 1.6);
      const hinten = versetzt(current.lat, current.lon, -Math.cos(h) * 1.6, -Math.sin(h) * 1.6);
      const hv = ground(vorn.lon, vorn.lat);
      const hh = ground(hinten.lon, hinten.lat);
      current.altitude = (hv + hh) / 2;
      current.pitch += (Math.atan2(hv - hh, 3.2) * TO_DEG - current.pitch) * Math.min(1, dt * 8);
      current.roll += (-current.lenkung * Math.min(1, Math.abs(current.speed) / 25) * 0.12 - current.roll) * Math.min(1, dt * 5);
      current.schritt += (weg / 0.34) * 1;
    };

    const fly = (dt: number) => {
      const current = stateRef.current;
      const held = keys.current;
      const daten = FLUG[modellRef.current.id] ?? FLUG.jet;
      const boosting = held.has("shift");
      const gas = (held.has("w") || held.has("arrowup") ? 1 : 0) - (held.has("s") || held.has("arrowdown") ? 1 : 0);
      const rollKeys = (held.has("d") || held.has("arrowright") ? 1 : 0) - (held.has("a") || held.has("arrowleft") ? 1 : 0);
      const noseKeys = (held.has("r") || held.has(" ") ? 1 : 0) - (held.has("f") ? 1 : 0);
      current.throttle = Math.max(0, Math.min(1, current.throttle + gas * dt * 0.6));
      const target = daten.basis + current.throttle * (boosting ? daten.boost : daten.bereich);
      current.speed += (target - current.speed) * Math.min(1, dt * 0.6);
      const rollInput = Math.max(-1, Math.min(1, rollKeys + current.stickRoll));
      const noseInput = Math.max(-1, Math.min(1, noseKeys + current.stickPitch));
      if (Math.abs(rollInput) > 0.02) current.roll = Math.max(-72, Math.min(72, current.roll + rollInput * 96 * dt));
      else current.roll -= current.roll * Math.min(1, dt * 1.7);
      if (Math.abs(noseInput) > 0.02) current.pitch = Math.max(-38, Math.min(42, current.pitch + noseInput * 34 * dt));
      else current.pitch -= current.pitch * Math.min(1, dt * 0.8);

      const line = routeRef.current;
      if (followRef.current && line && line.length > 1) {
        current.travelled += current.speed * dt;
        let walked = 0;
        let placed = false;
        for (let index = 0; index < line.length - 1; index += 1) {
          const from = line[index];
          const to = line[index + 1];
          const length = segmentLength(from, to);
          if (walked + length >= current.travelled) {
            const ratio = length === 0 ? 0 : (current.travelled - walked) / length;
            current.lon = from[0] + (to[0] - from[0]) * ratio;
            current.lat = from[1] + (to[1] - from[1]) * ratio;
            const turn = shortestTurn(current.heading, bearingOf(from, to));
            current.heading = (current.heading + turn * Math.min(1, dt * 2.4) + 360) % 360;
            current.roll = Math.max(-45, Math.min(45, turn * 1.6));
            placed = true;
            break;
          }
          walked += length;
        }
        if (!placed) {
          const end = line[line.length - 1];
          current.lon = end[0];
          current.lat = end[1];
          current.roll -= current.roll * Math.min(1, dt * 2);
        }
        const floor = ground() + 520;
        current.altitude += (floor - current.altitude) * Math.min(1, dt * 0.5);
        return;
      }

      const rate = (9.81 / Math.max(15, current.speed)) * Math.tan(current.roll * TO_RAD) * (daten.basis > 40 ? 2.6 : 1.4);
      current.heading = (current.heading + rate * TO_DEG * dt + 360) % 360;
      const forward = current.speed * Math.cos(current.pitch * TO_RAD) * dt;
      const ziel = versetzt(current.lat, current.lon, Math.cos(current.heading * TO_RAD) * forward, Math.sin(current.heading * TO_RAD) * forward);
      current.lat = ziel.lat;
      current.lon = ziel.lon;
      current.altitude += current.speed * Math.sin(current.pitch * TO_RAD) * dt;
      const floor = ground() + 18;
      if (current.altitude < floor) {
        current.altitude = floor;
        if (current.pitch < 0) current.pitch = 0;
      }
      if (current.altitude > MAX_HEIGHT) {
        current.altitude = MAX_HEIGHT;
        if (current.pitch > 0) current.pitch = 0;
      }
      current.schritt += dt;
    };

    const kamera = (lon: number, lat: number, alt: number, bearing: number, pitch: number, roll: number) => {
      const options = map.calculateCameraOptionsFromCameraLngLatAltRotation([lon, lat], alt, bearing, Math.max(0, Math.min(grenzePitch, pitch)), roll);
      map.jumpTo(options);
    };

    const verfolgen = (abstand: number, hoehe: number, blickHoehe: number, extraPitch: number, roll: number) => {
      const current = stateRef.current;
      const h = current.heading * TO_RAD;
      const cam = versetzt(current.lat, current.lon, -Math.cos(h) * abstand, -Math.sin(h) * abstand);
      const camAlt = Math.max(ground(cam.lon, cam.lat) + 1.2, current.altitude + hoehe - Math.sin(current.pitch * TO_RAD) * abstand * (artRef.current === "flugzeug" ? 1 : 0.3));
      const drop = Math.atan2(camAlt - (current.altitude + blickHoehe), abstand) * TO_DEG;
      kamera(cam.lon, cam.lat, camAlt, current.heading, 90 - drop + extraPitch, roll);
    };

    const place = () => {
      const current = stateRef.current;
      const modus = artRef.current;
      const m = modellRef.current;
      const sichtbar = !(nahRef.current && modus !== "auto") && !(modus === "auto" && nahRef.current);
      layer.set({ lon: current.lon, lat: current.lat, altitude: current.altitude, heading: current.heading, pitch: modus === "fuss" ? 0 : current.pitch, roll: modus === "fuss" ? 0 : current.roll, visible: sichtbar, scale: 1 });
      const z = current.zoomFaktor;
      if (modus === "fuss") {
        if (nahRef.current) {
          kamera(current.lon, current.lat, current.altitude + AUGE, current.heading, 90 + current.blick, 0);
        } else {
          verfolgen(4.2 * z, 2.1 * z, 1.4, current.blick * 0.5 + 6, 0);
        }
        return;
      }
      if (modus === "auto") {
        if (nahRef.current) {
          const h = current.heading * TO_RAD;
          const sitz = versetzt(current.lat, current.lon, Math.cos(h) * 0.05 - Math.sin(h) * -0.36 * 0, Math.sin(h) * 0.05);
          const links = versetzt(sitz.lat, sitz.lon, Math.sin(h) * 0.36, -Math.cos(h) * 0.36);
          kamera(links.lon, links.lat, current.altitude + (m.id === "oldtimer" ? 1.62 : m.id === "sport" ? 0.98 : m.id === "suv" ? 1.5 : 1.2), current.heading, 87 + current.pitch + current.blick * 0.4, current.roll * 0.4);
        } else {
          verfolgen((7.2 + Math.abs(current.speed) * 0.07) * z, 2.5 * z, 1.0, 2, 0);
        }
        return;
      }
      if (nahRef.current) {
        kamera(current.lon, current.lat, current.altitude + (m.id === "jet" ? 3.2 : 1.4), current.heading, Math.max(12, 85 + current.pitch * 0.75), current.roll * 0.85);
        return;
      }
      const abstand = (m.laenge * 2.3 + current.speed * 0.3) * z;
      const hoehe = m.laenge * 0.6 + current.speed * 0.05;
      const h = current.heading * TO_RAD;
      const cam = versetzt(current.lat, current.lon, -Math.cos(h) * abstand, -Math.sin(h) * abstand);
      const camAlt = current.altitude + hoehe - Math.sin(current.pitch * TO_RAD) * abstand;
      const drop = Math.atan2(camAlt - current.altitude, abstand) * TO_DEG;
      kamera(cam.lon, cam.lat, camAlt, current.heading, Math.max(8, Math.min(85, 90 - drop + current.pitch * 0.3)), current.roll * 0.5);
    };

    const wechseln = (neu: Fortbewegung) => {
      const current = stateRef.current;
      const boden = ground();
      if (neu === "flugzeug") {
        current.altitude = Math.max(current.altitude, boden + 300);
        current.speed = (FLUG[modellRef.current.id] ?? FLUG.jet).basis * 1.5;
        current.pitch = 4;
      } else {
        current.altitude = boden;
        current.speed = 0;
        current.pitch = 0;
        current.roll = 0;
        hindernisse.aktualisieren(map, current.lat, current.lon, zeit, true);
        if (hindernisse.trifft(current.lat, current.lon, 0.5)) {
          for (let r = 4; r < 120; r += 4) {
            const frei = [0, 90, 180, 270].map((w) => versetzt(current.lat, current.lon, Math.cos(w * TO_RAD) * r, Math.sin(w * TO_RAD) * r)).find((p) => !hindernisse.trifft(p.lat, p.lon, 0.5));
            if (frei) {
              current.lat = frei.lat;
              current.lon = frei.lon;
              break;
            }
          }
        }
      }
    };

    wechseln(artRef.current);

    const step = (now: number) => {
      frame = requestAnimationFrame(step);
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      try {
        if (wechselRef.current) {
          const neu = wechselRef.current;
          wechselRef.current = null;
          wechseln(neu);
          layer.setModell(modellRef.current.bauen(farbeRef.current, 0));
        }
        const modus = artRef.current;
        if (modus !== "flugzeug") hindernisse.aktualisieren(map, stateRef.current.lat, stateRef.current.lon, zeit);
        if (modus === "fuss") gehen(dt);
        else if (modus === "auto") fahren(dt);
        else fly(dt);
        animTick += dt;
        if (modellRef.current.animiert && animTick > 1 / 30) {
          animTick = 0;
          layer.setModell(modellRef.current.bauen(farbeRef.current, stateRef.current.schritt));
        }
        place();
      } catch {
        return;
      }
      ladeTick += dt;
      if (ladeTick > 1.5) {
        ladeTick = 0;
        if (artRef.current !== "flugzeug" || stateRef.current.altitude - ground() < 2500) void zeit.nachladen(stateRef.current.lat, stateRef.current.lon);
      }
      hudTick += dt;
      if (hudTick > 0.1) {
        hudTick = 0;
        const current = stateRef.current;
        const below = ground();
        setHud({
          speed: current.speed,
          altitude: current.altitude,
          ground: Math.max(0, current.altitude - below),
          heading: current.heading,
          pitch: current.pitch,
          roll: current.roll,
          throttle: current.throttle,
          climb: artRef.current === "flugzeug" ? current.speed * Math.sin(current.pitch * TO_RAD) : 0,
          lat: current.lat,
          lon: current.lon,
        });
        onPosition?.(current.lat, current.lon);
      }
    };

    void zeit.nachladen(state.lat, state.lon);
    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
      zeit.entfernen();
      zeitRef.current = null;
      layerRef.current = null;
      if (mounted) {
        try {
          map.removeLayer(layer.id);
        } catch {
          layer.set({ lon: 0, lat: 0, altitude: 0, heading: 0, pitch: 0, roll: 0, visible: false, scale: 1 });
        }
      }
      map.off("styledata", tageslicht);
      try {
        if (altesLicht) map.setLight(altesLicht);
        map.setSky(alterHimmel ?? {});
        if (map.getLayer("jon-satellit")) map.setLayoutProperty("jon-satellit", "visibility", satellitSichtbar ?? "none");
      } catch {
        map.getLight();
      }
      try {
        if (altesGelaende) map.setTerrain(altesGelaende);
        map.setMaxPitch(alteMaxPitch);
        map.setMaxZoom(alteMaxZoom);
      } catch {
        map.getMaxZoom();
      }
      map.easeTo({ center: restore.center, zoom: Math.min(restore.zoom, alteMaxZoom), pitch: Math.min(restore.pitch, alteMaxPitch), bearing: restore.bearing, roll: 0, duration: 900 });
    };
  }, [map, onPosition]);

  const onPointerDown = (event: React.PointerEvent) => {
    dragRef.current = { x: event.clientX, y: event.clientY, heading: stateRef.current.heading, blick: stateRef.current.blick };
    setDragging(true);
    (event.target as HTMLElement).setPointerCapture?.(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent) => {
    const origin = dragRef.current;
    if (!origin) return;
    const width = window.innerWidth || 1200;
    const height = window.innerHeight || 800;
    if (artRef.current === "flugzeug") {
      stateRef.current.stickRoll = Math.max(-1, Math.min(1, ((event.clientX - origin.x) / width) * 5));
      stateRef.current.stickPitch = Math.max(-1, Math.min(1, ((origin.y - event.clientY) / height) * 5));
      return;
    }
    const s = stateRef.current;
    if (artRef.current === "fuss") s.heading = (origin.heading + ((event.clientX - origin.x) / width) * 220 + 360) % 360;
    s.blick = Math.max(-65, Math.min(28, origin.blick + ((origin.y - event.clientY) / height) * 120));
  };

  const onPointerUp = () => {
    dragRef.current = null;
    stateRef.current.stickRoll = 0;
    stateRef.current.stickPitch = 0;
    setDragging(false);
  };

  const onWheel = (event: React.WheelEvent) => {
    const s = stateRef.current;
    s.zoomFaktor = Math.max(0.5, Math.min(4, s.zoomFaktor * (event.deltaY > 0 ? 1.1 : 0.9)));
  };

  const springen = async () => {
    const text = suche.trim();
    if (!text || sucheLaeuft) return;
    setSucheLaeuft(true);
    setMeldung("");
    try {
      const treffer = await searchPlaces(text, { lat: stateRef.current.lat, lon: stateRef.current.lon }, 1);
      if (!treffer.length) {
        setMeldung(`„${text}“ nicht gefunden`);
        return;
      }
      const ziel = treffer[0];
      stateRef.current.lat = ziel.lat;
      stateRef.current.lon = ziel.lon;
      stateRef.current.travelled = 0;
      wechselRef.current = artRef.current;
      setMeldung(`Du bist jetzt in ${ziel.name}`);
      setSuche("");
    } catch (e) {
      setMeldung(e instanceof Error ? e.message : String(e));
    } finally {
      setSucheLaeuft(false);
    }
  };

  const jahrSetzen = (wert: number) => {
    const neu = Math.max(-500, Math.min(HEUTE, Math.round(wert)));
    setJahr(neu);
    setJahrText(String(neu));
  };

  const kmh = Math.round(Math.abs(hud.speed) * 3.6);
  const modelle = MODELLE.filter((m) => m.art === art);
  const steuerung =
    art === "fuss"
      ? "W A S D gehen · Shift rennen · Leertaste springen · Q / E oder Maus ziehen drehen · C Ich-Sicht · 1 2 3 Fortbewegung"
      : art === "auto"
        ? "W Gas · S Bremse und Rückwärts · A / D lenken · Leertaste Handbremse · Shift Turbo · C Fahrersicht · Mausrad Abstand"
        : "W / S Schub · A / D rollen · R / F Nase · Shift Nachbrenner · C Cockpit · Maus ziehen wie ein Steuerknüppel";

  return (
    <>
      <div
        className="jm-fps"
        data-dragging={dragging}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onWheel={onWheel}
      />
      <div className="jm-vignette" data-on="true" />
      {art === "flugzeug" && (
        <div className="jm-horizon" style={{ transform: `rotate(${-hud.roll}deg)` }}>
          <span />
        </div>
      )}

      <motion.div
        className="jm-layer jm-welt-oben"
        style={{ top: 16, left: "50%", x: "-50%" }}
        initial={{ opacity: 0, y: -18, filter: "blur(10px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="jm-glass jm-glass--chrome jm-welt-leiste">
          <div className="jm-specular" />
          <div className="jm-welt-gruppe">
            <button className="jm-chip" data-active={art === "fuss"} onClick={() => setArt("fuss")} title="Spazieren gehen (1)">
              <Footprints size={14} /> Zu Fuß
            </button>
            <button className="jm-chip" data-active={art === "auto"} onClick={() => setArt("auto")} title="Auto fahren (2)">
              <Car size={14} /> Auto
            </button>
            <button className="jm-chip" data-active={art === "flugzeug"} onClick={() => setArt("flugzeug")} title="Fliegen (3)">
              <Plane size={14} /> Flugzeug
            </button>
          </div>
          <div className="jm-welt-trenner" />
          <div className="jm-welt-gruppe">
            {modelle.map((m) => (
              <button
                key={m.id}
                className="jm-chip"
                data-active={modell.id === m.id}
                data-epoche={jahr >= m.von && jahr <= m.bis ? "passt" : "fremd"}
                onClick={() => setModellWahl((w) => ({ ...w, [art]: m.id }))}
                title={m.von > 0 && m.bis < 9999 ? `${m.name} (${m.von}–${m.bis})` : m.von > 0 ? `${m.name} (ab ${m.von})` : m.name}
              >
                {m.name}
              </button>
            ))}
            <div className="jm-welt-farben" role="radiogroup" aria-label="Farbe">
              {FARBEN.map((f, i) => (
                <button
                  key={f.name}
                  role="radio"
                  aria-checked={farbe === i}
                  title={f.name}
                  data-active={farbe === i}
                  onClick={() => setFarbe(i)}
                  style={{ background: `rgb(${f.wert.map((v) => Math.round(v * 255)).join(",")})` }}
                />
              ))}
            </div>
          </div>
          <div className="jm-welt-trenner" />
          <div className="jm-welt-gruppe">
            <button className="jm-chip" data-active={nah} onClick={() => setNah((v) => !v)} title="Kamera wechseln (C)">
              <Camera size={14} /> {art === "fuss" ? (nah ? "Ich-Sicht" : "Von hinten") : art === "auto" ? (nah ? "Fahrersicht" : "Verfolger") : nah ? "Cockpit" : "Verfolger"}
            </button>
            {art === "flugzeug" && route && route.length > 1 && (
              <button className="jm-chip" data-tone="nav" data-active={followRoute} onClick={() => setFollowRoute((value) => !value)} title="Der berechneten Route folgen">
                <MapPin size={14} /> Route abfliegen
              </button>
            )}
            <form
              className="jm-welt-suche"
              onSubmit={(e) => {
                e.preventDefault();
                void springen();
              }}
            >
              <Search size={13} />
              <input value={suche} onChange={(e) => setSuche(e.target.value)} placeholder="Irgendwohin auf der Welt …" aria-label="Ort, zu dem du springen willst" />
            </form>
            <button className="jm-chip" onClick={onClose} title="Zurück zur Karte (Esc)">
              <X size={14} /> Beenden
            </button>
          </div>
        </div>
        {meldung && <div className="jm-welt-meldung">{meldung}</div>}
      </motion.div>

      <motion.div
        className="jm-layer jm-welt-zeit"
        style={{ left: 16, top: "50%", y: "-50%" }}
        initial={{ opacity: 0, x: -18 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="jm-glass jm-glass--chrome jm-welt-zeitkarte">
          <div className="jm-specular" />
          <div className="jm-welt-zeitkopf">
            <span>Jahr</span>
            <input
              type="number"
              value={jahrText}
              min={-500}
              max={HEUTE}
              onChange={(e) => setJahrText(e.target.value)}
              onBlur={() => jahrSetzen(Number(jahrText) || HEUTE)}
              onKeyDown={(e) => {
                if (e.key === "Enter") jahrSetzen(Number(jahrText) || HEUTE);
              }}
              aria-label="Jahr eingeben"
            />
          </div>
          <input type="range" min={1700} max={HEUTE} step={1} value={Math.max(1700, jahr)} onChange={(e) => jahrSetzen(Number(e.target.value))} aria-label="Jahr wählen" />
          <div className="jm-welt-schnell">
            {SCHNELLJAHRE.map((j) => (
              <button key={j} className="jm-chip" data-active={jahr === j} onClick={() => jahrSetzen(j)}>
                {j}
              </button>
            ))}
            <button className="jm-chip" data-active={jahr === HEUTE} onClick={() => jahrSetzen(HEUTE)}>
              Heute
            </button>
          </div>
          <div className="jm-welt-epoche">{epochenName(jahr)}</div>
          <div className="jm-welt-info">
            {jahr >= HEUTE
              ? `Alle Gebäude von heute in ihren echten Farben. ${zeitInfo.bekannte} davon kennen ihr Baujahr.`
              : `${zeitInfo.ausgeblendet} neuere Gebäude ausgeblendet · ${zeitInfo.bekannte} mit bekanntem Baujahr · abgerissene Bauten aus OpenHistoricalMap${zeitInfo.luftbild ? ` · Luftbild ${zeitInfo.luftbild}` : ""}`}
          </div>
        </div>
      </motion.div>

      <motion.div
        className="jm-layer"
        style={{ bottom: 24, left: "50%", x: "-50%" }}
        initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.4, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="jm-glass jm-glass--chrome jm-hud">
          <div className="jm-specular" />
          <span>
            Tempo <b>{kmh} km/h</b>
          </span>
          {art === "flugzeug" ? (
            <>
              <span>
                Höhe <b>{Math.round(hud.altitude)} m</b>
              </span>
              <span>
                Boden <b>{Math.round(hud.ground)} m</b>
              </span>
              <span>
                Steigen <b>{hud.climb >= 0 ? "+" : ""}{Math.round(hud.climb)} m/s</b>
              </span>
              <span>
                Lage <b>{Math.round(hud.roll)}° / {Math.round(hud.pitch)}°</b>
              </span>
            </>
          ) : (
            <span>
              Höhe <b>{Math.round(hud.altitude)} m ü. M.</b>
            </span>
          )}
          <span>
            Kurs <b>{Math.round(hud.heading)}°</b>
          </span>
          <span>
            {modell.name} · <b>{jahr}</b>
          </span>
          <span className="jm-mono">
            {hud.lat.toFixed(4)}, {hud.lon.toFixed(4)}
          </span>
        </div>
        {art === "flugzeug" && (
          <div className="jm-throttle">
            <span style={{ width: `${Math.round(hud.throttle * 100)}%` }} />
          </div>
        )}
        <div style={{ marginTop: 8, textAlign: "center", fontSize: 11, color: "var(--jm-text-faint)" }}>{steuerung}</div>
      </motion.div>
    </>
  );
}
