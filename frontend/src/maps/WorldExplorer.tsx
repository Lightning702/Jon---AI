import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import type maplibregl from "maplibre-gl";
import { PlaneLayer } from "./PlaneLayer";

export type ExplorerMode = "flugzeug";

interface Props {
  map: maplibregl.Map | null;
  start: { lat: number; lon: number };
  route?: [number, number][];
  onClose: () => void;
  onPosition?: (lat: number, lon: number) => void;
}

const TO_RAD = Math.PI / 180;
const TO_DEG = 180 / Math.PI;
const BASE_SPEED = 55;
const RANGE_SPEED = 250;
const BOOST_SPEED = 430;
const MIN_HEIGHT = 22;
const MAX_HEIGHT = 15000;

function segmentLength(a: [number, number], b: [number, number]): number {
  const dLat = (b[1] - a[1]) * 111320;
  const dLon = (b[0] - a[0]) * 111320 * Math.cos(a[1] * TO_RAD);
  return Math.hypot(dLat, dLon);
}

function bearingOf(a: [number, number], b: [number, number]): number {
  const y = Math.sin((b[0] - a[0]) * TO_RAD) * Math.cos(b[1] * TO_RAD);
  const x =
    Math.cos(a[1] * TO_RAD) * Math.sin(b[1] * TO_RAD) -
    Math.sin(a[1] * TO_RAD) *
      Math.cos(b[1] * TO_RAD) *
      Math.cos((b[0] - a[0]) * TO_RAD);
  return (Math.atan2(y, x) * TO_DEG + 360) % 360;
}

function shortestTurn(from: number, to: number): number {
  return ((to - from + 540) % 360) - 180;
}

export default function WorldExplorer({
  map,
  start,
  route,
  onClose,
  onPosition,
}: Props) {
  const [hud, setHud] = useState({
    speed: 0,
    altitude: 900,
    ground: 0,
    heading: 0,
    pitch: 0,
    roll: 0,
    throttle: 0.55,
    climb: 0,
    lat: start.lat,
    lon: start.lon,
  });
  const [followRoute, setFollowRoute] = useState(false);
  const [cockpit, setCockpit] = useState(false);
  const [dragging, setDragging] = useState(false);

  const stateRef = useRef({
    lat: start.lat,
    lon: start.lon,
    altitude: 900,
    heading: 0,
    pitch: 0,
    roll: 0,
    speed: 150,
    throttle: 0.55,
    stickPitch: 0,
    stickRoll: 0,
    travelled: 0,
  });
  const keys = useRef<Set<string>>(new Set());
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const routeRef = useRef<[number, number][] | undefined>(route);
  routeRef.current = route;
  const followRef = useRef(followRoute);
  followRef.current = followRoute;
  const cockpitRef = useRef(cockpit);
  cockpitRef.current = cockpit;
  const restoreRef = useRef<{
    center: [number, number];
    zoom: number;
    pitch: number;
    bearing: number;
  } | null>(null);

  useEffect(() => {
    const current = stateRef.current;
    current.lat = start.lat;
    current.lon = start.lon;
    current.travelled = 0;
    const line = routeRef.current;
    if (line && line.length > 1) current.heading = bearingOf(line[0], line[1]);
  }, [start.lat, start.lon]);

  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if (key === "escape") {
        onClose();
        return;
      }
      if (key === "c") {
        setCockpit((value) => !value);
        return;
      }
      keys.current.add(key);
      if (
        [
          "w",
          "a",
          "s",
          "d",
          "r",
          "f",
          "arrowup",
          "arrowdown",
          "arrowleft",
          "arrowright",
          " ",
        ].includes(key)
      ) {
        event.preventDefault();
      }
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
    restoreRef.current = {
      center: [center.lng, center.lat],
      zoom: map.getZoom(),
      pitch: map.getPitch(),
      bearing: map.getBearing(),
    };
    const layer = new PlaneLayer();
    let mounted = false;
    try {
      if (!map.getLayer(layer.id)) {
        map.addLayer(layer);
        mounted = true;
      }
    } catch {
      mounted = false;
    }

    const ground = () => {
      const current = stateRef.current;
      try {
        return map.queryTerrainElevation([current.lon, current.lat]) ?? 0;
      } catch {
        return 0;
      }
    };

    const state = stateRef.current;
    state.altitude = Math.max(state.altitude, ground() + 620);

    let frame = 0;
    let last = performance.now();
    let hudTick = 0;

    const fly = (dt: number) => {
      const current = stateRef.current;
      const held = keys.current;
      const boosting = held.has("shift");
      const gas =
        (held.has("w") || held.has("arrowup") ? 1 : 0) -
        (held.has("s") || held.has("arrowdown") ? 1 : 0);
      const rollKeys =
        (held.has("d") || held.has("arrowright") ? 1 : 0) -
        (held.has("a") || held.has("arrowleft") ? 1 : 0);
      const noseKeys =
        (held.has("r") || held.has(" ") ? 1 : 0) - (held.has("f") ? 1 : 0);

      current.throttle = Math.max(
        0,
        Math.min(1, current.throttle + gas * dt * 0.6)
      );
      const target =
        BASE_SPEED +
        current.throttle * (boosting ? BOOST_SPEED : RANGE_SPEED);
      current.speed += (target - current.speed) * Math.min(1, dt * 0.6);

      const rollInput = Math.max(-1, Math.min(1, rollKeys + current.stickRoll));
      const noseInput = Math.max(-1, Math.min(1, noseKeys + current.stickPitch));

      if (Math.abs(rollInput) > 0.02) {
        current.roll = Math.max(
          -72,
          Math.min(72, current.roll + rollInput * 96 * dt)
        );
      } else {
        current.roll -= current.roll * Math.min(1, dt * 1.7);
      }
      if (Math.abs(noseInput) > 0.02) {
        current.pitch = Math.max(
          -38,
          Math.min(42, current.pitch + noseInput * 34 * dt)
        );
      } else {
        current.pitch -= current.pitch * Math.min(1, dt * 0.8);
      }

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
            const wanted = bearingOf(from, to);
            const turn = shortestTurn(current.heading, wanted);
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

      const rate =
        (9.81 / Math.max(50, current.speed)) *
        Math.tan(current.roll * TO_RAD) *
        2.6;
      current.heading = (current.heading + rate * TO_DEG * dt + 360) % 360;

      const forward = current.speed * Math.cos(current.pitch * TO_RAD) * dt;
      const headingRad = current.heading * TO_RAD;
      current.lat = Math.max(
        -85,
        Math.min(85, current.lat + (Math.cos(headingRad) * forward) / 111320)
      );
      const scale = 111320 * Math.max(0.12, Math.cos(current.lat * TO_RAD));
      current.lon =
        ((current.lon + (Math.sin(headingRad) * forward) / scale + 540) % 360) - 180;

      current.altitude += current.speed * Math.sin(current.pitch * TO_RAD) * dt;
      const floor = ground() + MIN_HEIGHT;
      if (current.altitude < floor) {
        current.altitude = floor;
        if (current.pitch < 0) current.pitch = 0;
      }
      if (current.altitude > MAX_HEIGHT) {
        current.altitude = MAX_HEIGHT;
        if (current.pitch > 0) current.pitch = 0;
      }
    };

    const place = () => {
      const current = stateRef.current;
      layer.set({
        lon: current.lon,
        lat: current.lat,
        altitude: current.altitude,
        heading: current.heading,
        pitch: current.pitch,
        roll: current.roll,
        visible: !cockpitRef.current,
        scale: 1,
      });
      const headingRad = current.heading * TO_RAD;
      if (cockpitRef.current) {
        const options = map.calculateCameraOptionsFromCameraLngLatAltRotation(
          [current.lon, current.lat],
          current.altitude + 3.2,
          current.heading,
          Math.max(12, Math.min(85, 85 + current.pitch * 0.75)),
          current.roll * 0.85
        );
        map.jumpTo(options);
        return;
      }
      const distance = 74 + current.speed * 0.3;
      const height = 20 + current.speed * 0.05;
      const scale = 111320 * Math.max(0.12, Math.cos(current.lat * TO_RAD));
      const camLat = current.lat - (Math.cos(headingRad) * distance) / 111320;
      const camLon = current.lon - (Math.sin(headingRad) * distance) / scale;
      const camAlt =
        current.altitude + height - Math.sin(current.pitch * TO_RAD) * distance;
      const drop = Math.atan2(camAlt - current.altitude, distance) * TO_DEG;
      const options = map.calculateCameraOptionsFromCameraLngLatAltRotation(
        [camLon, camLat],
        camAlt,
        current.heading,
        Math.max(8, Math.min(85, 90 - drop + current.pitch * 0.3)),
        current.roll * 0.5
      );
      map.jumpTo(options);
    };

    const step = (now: number) => {
      frame = requestAnimationFrame(step);
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      try {
        fly(dt);
        place();
      } catch {
        return;
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
          climb: current.speed * Math.sin(current.pitch * TO_RAD),
          lat: current.lat,
          lon: current.lon,
        });
        onPosition?.(current.lat, current.lon);
      }
    };

    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
      if (mounted) {
        try {
          map.removeLayer(layer.id);
        } catch {
          layer.set({
            lon: 0,
            lat: 0,
            altitude: 0,
            heading: 0,
            pitch: 0,
            roll: 0,
            visible: false,
            scale: 1,
          });
        }
      }
      const restore = restoreRef.current;
      if (restore) {
        map.easeTo({
          center: restore.center,
          zoom: restore.zoom,
          pitch: restore.pitch,
          bearing: restore.bearing,
          roll: 0,
          duration: 900,
        });
      }
    };
  }, [map, onPosition]);

  const onPointerDown = (event: React.PointerEvent) => {
    dragRef.current = { x: event.clientX, y: event.clientY };
    setDragging(true);
    (event.target as HTMLElement).setPointerCapture?.(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent) => {
    const origin = dragRef.current;
    if (!origin) return;
    const width = window.innerWidth || 1200;
    const height = window.innerHeight || 800;
    stateRef.current.stickRoll = Math.max(
      -1,
      Math.min(1, ((event.clientX - origin.x) / width) * 5)
    );
    stateRef.current.stickPitch = Math.max(
      -1,
      Math.min(1, ((origin.y - event.clientY) / height) * 5)
    );
  };

  const onPointerUp = () => {
    dragRef.current = null;
    stateRef.current.stickRoll = 0;
    stateRef.current.stickPitch = 0;
    setDragging(false);
  };

  const knots = Math.round(hud.speed * 3.6);
  const throttleWidth = `${Math.round(hud.throttle * 100)}%`;

  return (
    <>
      <div
        className="jm-fps"
        data-dragging={dragging}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      />
      <div className="jm-vignette" data-on="true" />
      <div className="jm-horizon" style={{ transform: `rotate(${-hud.roll}deg)` }}>
        <span />
      </div>

      <motion.div
        className="jm-layer"
        style={{ top: 20, left: "50%", x: "-50%" }}
        initial={{ opacity: 0, y: -18, filter: "blur(10px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <div
          className="jm-glass jm-glass--chrome"
          style={{ padding: 6, display: "flex", gap: 5, borderRadius: 22 }}
        >
          <div className="jm-specular" />
          <span
            className="jm-chip"
            data-active="true"
            style={{ cursor: "default" }}
          >
            ✈️ Flugzeug
          </span>
          <button
            className="jm-chip"
            data-active={cockpit}
            onClick={() => setCockpit((value) => !value)}
            title="Zwischen Cockpit und Verfolgerkamera wechseln (C)"
          >
            {cockpit ? "🎥 Cockpit" : "🎥 Verfolger"}
          </button>
          {route && route.length > 1 && (
            <button
              className="jm-chip"
              data-tone="nav"
              data-active={followRoute}
              onClick={() => setFollowRoute((value) => !value)}
              title="Der berechneten Route folgen"
            >
              🛣️ Route abfliegen
            </button>
          )}
          <div
            style={{ width: 1, background: "var(--jm-hairline)", margin: "4px 6px" }}
          />
          <button className="jm-chip" onClick={onClose}>
            ✕ Landen
          </button>
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
            Tempo <b>{knots} km/h</b>
          </span>
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
            Kurs <b>{Math.round(hud.heading)}°</b>
          </span>
          <span>
            Lage <b>{Math.round(hud.roll)}° / {Math.round(hud.pitch)}°</b>
          </span>
          <span className="jm-mono">
            {hud.lat.toFixed(4)}, {hud.lon.toFixed(4)}
          </span>
        </div>
        <div className="jm-throttle">
          <span style={{ width: throttleWidth }} />
        </div>
        <div
          style={{
            marginTop: 8,
            textAlign: "center",
            fontSize: 11,
            color: "var(--jm-text-faint)",
          }}
        >
          W / S Schub · A / D rollen · R / F Nase · Shift Nachbrenner · C Kamera ·
          Maus ziehen steuert wie ein Steuerknüppel
        </div>
      </motion.div>
    </>
  );
}
