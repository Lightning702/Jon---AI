import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import type maplibregl from "maplibre-gl";

export type ExplorerMode = "mensch" | "auto" | "flugzeug";

export interface ExplorerProfile {
  id: ExplorerMode;
  icon: string;
  label: string;
  eye: number;
  speed: number;
  boost: number;
  turn: number;
  hint: string;
}

export const EXPLORER_PROFILES: ExplorerProfile[] = [
  {
    id: "mensch",
    icon: "🚶",
    label: "Mensch",
    eye: 1.7,
    speed: 1.5,
    boost: 4.4,
    turn: 62,
    hint: "Augenhöhe 1,70 m · Shift zum Laufen",
  },
  {
    id: "auto",
    icon: "🚗",
    label: "Auto",
    eye: 1.45,
    speed: 14,
    boost: 33,
    turn: 48,
    hint: "Fahrzeugperspektive · Shift für Landstraßentempo",
  },
  {
    id: "flugzeug",
    icon: "✈️",
    label: "Flugzeug",
    eye: 650,
    speed: 90,
    boost: 260,
    turn: 34,
    hint: "R steigen · F sinken · Shift für Reisegeschwindigkeit",
  },
];

interface Props {
  map: maplibregl.Map | null;
  mode: ExplorerMode;
  start: { lat: number; lon: number };
  route?: [number, number][];
  onModeChange: (mode: ExplorerMode) => void;
  onClose: () => void;
  onPosition?: (lat: number, lon: number) => void;
}

const TO_RAD = Math.PI / 180;

function segmentLength(a: [number, number], b: [number, number]): number {
  const dLat = (b[1] - a[1]) * 111320;
  const dLon = (b[0] - a[0]) * 111320 * Math.cos(a[1] * TO_RAD);
  return Math.sqrt(dLat * dLat + dLon * dLon);
}

function bearingOf(a: [number, number], b: [number, number]): number {
  const y = Math.sin((b[0] - a[0]) * TO_RAD) * Math.cos(b[1] * TO_RAD);
  const x =
    Math.cos(a[1] * TO_RAD) * Math.sin(b[1] * TO_RAD) -
    Math.sin(a[1] * TO_RAD) *
      Math.cos(b[1] * TO_RAD) *
      Math.cos((b[0] - a[0]) * TO_RAD);
  return (Math.atan2(y, x) / TO_RAD + 360) % 360;
}

export default function WorldExplorer({
  map,
  mode,
  start,
  route,
  onModeChange,
  onClose,
  onPosition,
}: Props) {
  const profile = useMemo(
    () => EXPLORER_PROFILES.find((item) => item.id === mode) ?? EXPLORER_PROFILES[0],
    [mode]
  );
  const [hud, setHud] = useState({
    speed: 0,
    altitude: profile.eye,
    heading: 0,
    lat: start.lat,
    lon: start.lon,
  });
  const [followRoute, setFollowRoute] = useState(false);
  const [dragging, setDragging] = useState(false);

  const stateRef = useRef({
    lat: start.lat,
    lon: start.lon,
    yaw: 0,
    pitch: 82,
    altitude: profile.eye,
    speed: 0,
    routeDistance: 0,
  });
  const keys = useRef<Set<string>>(new Set());
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const profileRef = useRef(profile);
  profileRef.current = profile;
  const routeRef = useRef<[number, number][] | undefined>(route);
  routeRef.current = route;
  const followRef = useRef(followRoute);
  followRef.current = followRoute;
  const restoreRef = useRef<{
    center: [number, number];
    zoom: number;
    pitch: number;
    bearing: number;
  } | null>(null);

  useEffect(() => {
    stateRef.current.lat = start.lat;
    stateRef.current.lon = start.lon;
    stateRef.current.routeDistance = 0;
  }, [start.lat, start.lon]);

  useEffect(() => {
    stateRef.current.altitude = profile.eye;
  }, [profile.id, profile.eye]);

  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      keys.current.add(event.key.toLowerCase());
      if (
        ["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(
          event.key.toLowerCase()
        )
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
    let frame = 0;
    let last = performance.now();
    let hudTick = 0;

    const step = (now: number) => {
      try {
        advanceFrame(now);
      } catch {
        last = now;
      }
      frame = requestAnimationFrame(step);
    };

    const advanceFrame = (now: number) => {
      const dt = Math.min(0.12, (now - last) / 1000);
      last = now;
      const held = keys.current;
      const current = stateRef.current;
      const active = profileRef.current;
      const boosting = held.has("shift");
      const maxSpeed = boosting ? active.boost : active.speed;

      const forward =
        (held.has("w") || held.has("arrowup") ? 1 : 0) -
        (held.has("s") || held.has("arrowdown") ? 1 : 0);
      const turn =
        (held.has("d") || held.has("arrowright") ? 1 : 0) -
        (held.has("a") || held.has("arrowleft") ? 1 : 0);
      const strafe = (held.has("e") ? 1 : 0) - (held.has("q") ? 1 : 0);
      const climb =
        (held.has("r") || held.has(" ") ? 1 : 0) - (held.has("f") ? 1 : 0);

      const line = routeRef.current;
      if (followRef.current && line && line.length > 1) {
        const target = forward >= 0 ? maxSpeed : -maxSpeed;
        current.speed += (target - current.speed) * Math.min(1, dt * 2.4);
        current.routeDistance = Math.max(
          0,
          current.routeDistance + current.speed * dt
        );
        let walked = 0;
        let placed = false;
        for (let index = 0; index < line.length - 1; index += 1) {
          const from = line[index];
          const to = line[index + 1];
          const length = segmentLength(from, to);
          if (walked + length >= current.routeDistance) {
            const ratio = length === 0 ? 0 : (current.routeDistance - walked) / length;
            current.lon = from[0] + (to[0] - from[0]) * ratio;
            current.lat = from[1] + (to[1] - from[1]) * ratio;
            current.yaw = bearingOf(from, to);
            placed = true;
            break;
          }
          walked += length;
        }
        if (!placed) {
          const end = line[line.length - 1];
          current.lon = end[0];
          current.lat = end[1];
          current.speed = 0;
        }
      } else {
        current.yaw = (current.yaw + turn * active.turn * dt + 360) % 360;
        const target = forward * maxSpeed;
        current.speed += (target - current.speed) * Math.min(1, dt * 2.2);
        if (Math.abs(current.speed) < 0.02) current.speed = 0;
        const distance = current.speed * dt;
        const side = strafe * maxSpeed * 0.5 * dt;
        const yawRad = current.yaw * TO_RAD;
        const sideRad = yawRad + Math.PI / 2;
        const dLat =
          (Math.cos(yawRad) * distance + Math.cos(sideRad) * side) / 111320;
        const dLon =
          (Math.sin(yawRad) * distance + Math.sin(sideRad) * side) /
          (111320 * Math.max(0.15, Math.cos(current.lat * TO_RAD)));
        current.lat = Math.max(-85, Math.min(85, current.lat + dLat));
        current.lon = ((current.lon + dLon + 540) % 360) - 180;
      }

      const ground = map.queryTerrainElevation([current.lon, current.lat]) ?? 0;
      if (active.id === "flugzeug") {
        const rate = boosting ? 240 : 90;
        current.altitude = Math.max(
          ground + 40,
          Math.min(120000, current.altitude + climb * rate * dt)
        );
      } else {
        current.altitude = ground + active.eye;
      }

      const options = map.calculateCameraOptionsFromCameraLngLatAltRotation(
        [current.lon, current.lat],
        current.altitude,
        current.yaw,
        current.pitch
      );
      map.jumpTo({
        center: options.center,
        zoom: options.zoom,
        bearing: options.bearing,
        pitch: options.pitch,
      });

      hudTick += dt;
      if (hudTick > 0.12) {
        hudTick = 0;
        setHud({
          speed: Math.abs(current.speed),
          altitude: current.altitude - (active.id === "flugzeug" ? 0 : ground),
          heading: current.yaw,
          lat: current.lat,
          lon: current.lon,
        });
        onPosition?.(current.lat, current.lon);
      }
    };

    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
      const restore = restoreRef.current;
      if (restore) {
        map.easeTo({
          center: restore.center,
          zoom: restore.zoom,
          pitch: restore.pitch,
          bearing: restore.bearing,
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
    const dx = event.clientX - origin.x;
    const dy = event.clientY - origin.y;
    dragRef.current = { x: event.clientX, y: event.clientY };
    const current = stateRef.current;
    current.yaw = (current.yaw + dx * 0.22 + 360) % 360;
    current.pitch = Math.max(20, Math.min(85, current.pitch - dy * 0.16));
  };

  const onPointerUp = () => {
    dragRef.current = null;
    setDragging(false);
  };

  const speedLabel =
    profile.id === "mensch"
      ? `${hud.speed.toFixed(1)} m/s`
      : `${Math.round(hud.speed * 3.6)} km/h`;

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
      <div className="jm-crosshair" />

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
          {EXPLORER_PROFILES.map((item) => (
            <button
              key={item.id}
              className="jm-chip"
              data-active={item.id === mode}
              onClick={() => onModeChange(item.id)}
              title={item.hint}
            >
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
          <div style={{ width: 1, background: "var(--jm-hairline)", margin: "4px 6px" }} />
          {route && route.length > 1 && (
            <button
              className="jm-chip"
              data-tone="nav"
              data-active={followRoute}
              onClick={() => setFollowRoute((value) => !value)}
              title="Der berechneten Route folgen"
            >
              🛣️ Route abfahren
            </button>
          )}
          <button className="jm-chip" onClick={onClose}>
            ✕ Verlassen
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
            {profile.icon} <b>{profile.label}</b>
          </span>
          <span>
            Tempo <b>{speedLabel}</b>
          </span>
          <span>
            {profile.id === "flugzeug" ? "Höhe" : "Augenhöhe"}{" "}
            <b>{Math.round(hud.altitude)} m</b>
          </span>
          <span>
            Kurs <b>{Math.round(hud.heading)}°</b>
          </span>
          <span className="jm-mono">
            {hud.lat.toFixed(5)}, {hud.lon.toFixed(5)}
          </span>
        </div>
        <div
          style={{
            marginTop: 8,
            textAlign: "center",
            fontSize: 11,
            color: "var(--jm-text-faint)",
          }}
        >
          W A S D bewegen · Maus ziehen zum Umsehen · {profile.hint}
        </div>
      </motion.div>
    </>
  );
}
