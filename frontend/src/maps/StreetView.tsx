import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import Panorama from "./Panorama";
import {
  StreetImage,
  StreetResult,
  reversePlace,
  streetImages,
} from "../lib/maps";

interface Props {
  lat: number;
  lon: number;
  onClose: () => void;
  onWalkMode: (lat: number, lon: number) => void;
  onPositionChange?: (lat: number, lon: number) => void;
}

const TO_RAD = Math.PI / 180;

function distanceM(a: StreetImage, lat: number, lon: number): number {
  const dLat = (a.lat - lat) * 111320;
  const dLon = (a.lon - lon) * 111320 * Math.cos(lat * TO_RAD);
  return Math.sqrt(dLat * dLat + dLon * dLon);
}

function bearingTo(
  fromLat: number,
  fromLon: number,
  toLat: number,
  toLon: number
): number {
  const y = Math.sin((toLon - fromLon) * TO_RAD) * Math.cos(toLat * TO_RAD);
  const x =
    Math.cos(fromLat * TO_RAD) * Math.sin(toLat * TO_RAD) -
    Math.sin(fromLat * TO_RAD) *
      Math.cos(toLat * TO_RAD) *
      Math.cos((toLon - fromLon) * TO_RAD);
  return (Math.atan2(y, x) / TO_RAD + 360) % 360;
}

function angleGap(a: number, b: number): number {
  return Math.abs(((a - b + 540) % 360) - 180);
}

function streetAxis(current: StreetImage, pool: StreetImage[]): number {
  const sequence = pool
    .filter((image) => image.sequence && image.sequence === current.sequence)
    .sort((a, b) => a.index - b.index);
  const position = sequence.findIndex((image) => image.id === current.id);
  if (position >= 0) {
    const ahead = sequence[position + 1];
    const behind = sequence[position - 1];
    if (ahead) return bearingTo(current.lat, current.lon, ahead.lat, ahead.lon);
    if (behind) {
      return (bearingTo(current.lat, current.lon, behind.lat, behind.lon) + 180) % 360;
    }
  }
  const nearest = pool
    .filter((image) => image.id !== current.id)
    .map((image) => ({
      image,
      distance: distanceM(image, current.lat, current.lon),
    }))
    .filter((entry) => entry.distance > 1.5)
    .sort((a, b) => a.distance - b.distance)[0];
  if (nearest) {
    return bearingTo(
      current.lat,
      current.lon,
      nearest.image.lat,
      nearest.image.lon
    );
  }
  return current.bearing;
}

export default function StreetView({
  lat,
  lon,
  onClose,
  onWalkMode,
  onPositionChange,
}: Props) {
  const [result, setResult] = useState<StreetResult | null>(null);
  const [pool, setPool] = useState<StreetImage[]>([]);
  const [current, setCurrent] = useState<StreetImage | null>(null);
  const [yaw, setYaw] = useState(0);
  const [pitch, setPitch] = useState(0);
  const [fov, setFov] = useState(78);
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const positionRef = useRef(onPositionChange);
  positionRef.current = onPositionChange;

  const viewBearing = useMemo(() => {
    const base = current?.bearing ?? 0;
    return (base + (yaw / TO_RAD) + 360) % 360;
  }, [current, yaw]);

  const load = useCallback(
    async (targetLat: number, targetLon: number, keepYaw: boolean) => {
      setLoading(true);
      try {
        let data = await streetImages(targetLat, targetLon, 220, 40);
        if (data.bilder.length === 0) {
          data = await streetImages(targetLat, targetLon, 1800, 60);
        }
        setResult(data);
        setPool(data.bilder);
        const first = data.bilder[0] ?? null;
        setCurrent(first);
        if (!keepYaw) {
          setYaw(0);
          setPitch(0);
        }
        if (first) positionRef.current?.(first.lat, first.lon);
      } catch {
        setResult({
          modus: "render",
          anbieter: "jon-render",
          bilder: [],
          hinweis: "Straßenfotos sind gerade nicht erreichbar.",
        });
        setPool([]);
        setCurrent(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    void load(lat, lon, false);
  }, [lat, lon, load]);

  useEffect(() => {
    if (loading || !result || result.modus === "fotos") return;
    const timer = window.setTimeout(() => onWalkMode(lat, lon), 900);
    return () => window.clearTimeout(timer);
  }, [loading, result, lat, lon, onWalkMode]);

  useEffect(() => {
    let cancelled = false;
    const point = current ?? { lat, lon };
    reversePlace(point.lat, point.lon)
      .then((place) => {
        if (!cancelled) setAddress(place.name || place.label);
      })
      .catch(() => {
        if (!cancelled) setAddress("");
      });
    return () => {
      cancelled = true;
    };
  }, [current, lat, lon]);

  const advance = useCallback(
    (next: StreetImage, from: StreetImage) => {
      setCurrent(next);
      setYaw((value) => value + (from.bearing - next.bearing) * TO_RAD);
      positionRef.current?.(next.lat, next.lon);
      setPool((current) => {
        const known = new Set(current.map((image) => image.id));
        if (current.filter((image) => image.sequence === next.sequence).length > 4) {
          return current;
        }
        void streetImages(next.lat, next.lon, 220, 40)
          .then((data) => {
            const extra = data.bilder.filter((image) => !known.has(image.id));
            if (extra.length) setPool((now) => [...now, ...extra]);
          })
          .catch(() => undefined);
        return current;
      });
    },
    []
  );

  const step = useCallback(
    (backwards: boolean) => {
      if (!current) return;
      const direction = backwards ? -1 : 1;
      const sequence = pool
        .filter((image) => image.sequence && image.sequence === current.sequence)
        .sort((a, b) => a.index - b.index);
      const position = sequence.findIndex((image) => image.id === current.id);
      const neighbour = position >= 0 ? sequence[position + direction] : undefined;
      if (neighbour) {
        advance(neighbour, current);
        return;
      }
      const axis = streetAxis(current, pool);
      const heading = (axis + (backwards ? 180 : 0) + 360) % 360;
      const candidate = pool
        .filter((image) => image.id !== current.id)
        .map((image) => ({
          image,
          distance: distanceM(image, current.lat, current.lon),
          gap: angleGap(
            bearingTo(current.lat, current.lon, image.lat, image.lon),
            heading
          ),
        }))
        .filter(
          (entry) => entry.distance > 1.5 && entry.distance < 90 && entry.gap < 70
        )
        .sort(
          (a, b) => a.distance + a.gap * 0.4 - (b.distance + b.gap * 0.4)
        )[0];
      if (candidate) {
        advance(candidate.image, current);
        return;
      }
      const ahead = 0.00028;
      const targetLat = current.lat + Math.cos(heading * TO_RAD) * ahead;
      const targetLon =
        current.lon +
        (Math.sin(heading * TO_RAD) * ahead) /
          Math.max(0.2, Math.cos(current.lat * TO_RAD));
      void load(targetLat, targetLon, true);
    },
    [current, pool, load, advance]
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key === "ArrowUp" || event.key.toLowerCase() === "w") {
        event.preventDefault();
        step(false);
      } else if (event.key === "ArrowDown" || event.key.toLowerCase() === "s") {
        event.preventDefault();
        step(true);
      } else if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
        setYaw((value) => value - 0.22);
      } else if (event.key === "ArrowRight" || event.key.toLowerCase() === "d") {
        setYaw((value) => value + 0.22);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step, onClose]);

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
    const speed = (fov / 78) * 0.0042;
    setYaw((value) => value - dx * speed);
    setPitch((value) =>
      Math.max(-1.15, Math.min(1.15, value - dy * speed * 0.85))
    );
  };

  const onPointerUp = () => {
    dragRef.current = null;
    setDragging(false);
  };

  const onWheel = (event: React.WheelEvent) => {
    setFov((value) => Math.max(28, Math.min(105, value + event.deltaY * 0.05)));
  };

  const photos = result?.modus === "fotos" && current;

  return (
    <motion.div
      className="jm-layer"
      style={{ inset: 0, zIndex: 30 }}
      initial={{ opacity: 0, scale: 1.03, filter: "blur(14px)" }}
      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
      exit={{ opacity: 0, scale: 1.02, filter: "blur(10px)" }}
      transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
    >
      <div
        className="jm-fps"
        data-dragging={dragging}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onWheel={onWheel}
        style={{ pointerEvents: photos ? "auto" : "none" }}
      >
        {photos && current && (
          <Panorama
            url={current.url}
            spherical={current.spherical}
            yaw={yaw}
            pitch={pitch}
            fov={fov}
          />
        )}
      </div>

      <div className="jm-crosshair" />

      <div
        className="jm-layer"
        style={{ top: 20, left: 20, right: 20, display: "flex", gap: 12 }}
      >
        <div
          className="jm-glass jm-glass--chrome"
          style={{
            padding: "12px 18px",
            display: "flex",
            alignItems: "center",
            gap: 14,
            flex: 1,
            borderRadius: 22,
          }}
        >
          <div className="jm-specular" />
          <span style={{ fontSize: 17 }}>🧭</span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {address || "Street Exploration"}
            </div>
            <div style={{ fontSize: 11.5, color: "var(--jm-text-faint)" }}>
              {photos && current
                ? `${result?.anbieter} · ${current.captured_at || "Straßenfoto"} · Blick ${Math.round(viewBearing)}°`
                : loading
                  ? "Straßenfotos werden gesucht …"
                  : (result?.hinweis ?? "")}
            </div>
          </div>
          <button
            className="jm-chip"
            data-tone="nav"
            data-active="true"
            onClick={() => onWalkMode(current?.lat ?? lat, current?.lon ?? lon)}
          >
            ✈️ Von oben erkunden
          </button>
          <button className="jm-chip" onClick={onClose}>
            ✕ Zurück zur Karte
          </button>
        </div>
      </div>

      {photos && (
        <div
          className="jm-layer"
          style={{
            bottom: 26,
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: 10,
            alignItems: "center",
          }}
        >
          <div
            className="jm-glass jm-glass--chrome"
            style={{ padding: 6, display: "flex", gap: 4, borderRadius: 20 }}
          >
            <div className="jm-specular" />
            <button
              className="jm-dock-btn"
              title="Nach links schauen (A)"
              onClick={() => setYaw((value) => value - 0.35)}
            >
              ←
            </button>
            <button
              className="jm-dock-btn"
              title="Vorwärts gehen (W)"
              onClick={() => step(false)}
            >
              ↑
            </button>
            <button
              className="jm-dock-btn"
              title="Zurück gehen (S)"
              onClick={() => step(true)}
            >
              ↓
            </button>
            <button
              className="jm-dock-btn"
              title="Nach rechts schauen (D)"
              onClick={() => setYaw((value) => value + 0.35)}
            >
              →
            </button>
            <div className="jm-dock-sep" style={{ width: 1, height: 30, margin: "6px 4px" }} />
            <button
              className="jm-dock-btn"
              title="Umdrehen"
              onClick={() => setYaw((value) => value + Math.PI)}
            >
              ⟲
            </button>
          </div>
          <div className="jm-glass jm-glass--thin jm-hud">
            <span>
              <b>{pool.length}</b> Fotos in der Nähe
            </span>
            <span>Ziehen zum Umsehen · Scrollen zum Zoomen</span>
          </div>
        </div>
      )}

      {!photos && !loading && (
        <div
          className="jm-layer"
          style={{ bottom: 96, left: "50%", transform: "translateX(-50%)" }}
        >
          <div
            className="jm-glass jm-glass--chrome"
            style={{
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              gap: 12,
              borderRadius: 20,
            }}
          >
            <div className="jm-specular" />
            <span style={{ fontSize: 18 }}>🧍</span>
            <span
              style={{ fontSize: 12, color: "var(--jm-text-soft)", maxWidth: 330 }}
            >
              Hier gibt es keine Straßenfotos — dafür hebt Jon mit dir ab und zeigt
              dir die Gegend aus dem Cockpit.
            </span>
            <button
              className="jm-chip jm-press"
              data-tone="nav"
              data-active="true"
              onClick={() => onWalkMode(current?.lat ?? lat, current?.lon ?? lon)}
            >
              ✈️ Abheben
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
