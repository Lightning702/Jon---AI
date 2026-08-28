import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  MODE_ICONS,
  MODE_LABELS,
  MapsPlace,
  MapsRoute,
  TravelMode,
  formatDistance,
  formatDuration,
} from "../lib/maps";

interface Props {
  stops: (MapsPlace | null)[];
  mode: TravelMode;
  routes: MapsRoute[];
  activeIndex: number;
  busy: boolean;
  error: string;
  onMode: (mode: TravelMode) => void;
  onPick: (index: number) => void;
  onReverse: () => void;
  onClear: () => void;
  onEdit: (index: number) => void;
  onRemove: (index: number) => void;
  onAdd: () => void;
  onShift: (index: number, delta: number) => void;
  onDrive: () => void;
}

const MAX_STOPS = 12;

function stopMark(index: number, total: number): string {
  if (index === 0) return "●";
  if (index === total - 1) return "◆";
  return String(index);
}

function stopHint(index: number, total: number): string {
  if (index === 0) return "Start wählen";
  if (index === total - 1) return "Ziel wählen";
  return `Station ${index} wählen`;
}

export default function RoutePanel({
  stops,
  mode,
  routes,
  activeIndex,
  busy,
  error,
  onMode,
  onPick,
  onReverse,
  onClear,
  onEdit,
  onRemove,
  onAdd,
  onShift,
  onDrive,
}: Props) {
  const [showSteps, setShowSteps] = useState(false);
  const active = routes[activeIndex];

  const legs = useMemo(() => {
    const filled = stops.filter((stop): stop is MapsPlace => Boolean(stop));
    const raw = (active?.legs ?? []) as Record<string, unknown>[];
    if (raw.length !== filled.length - 1) return [];
    return raw.map((leg, index) => ({
      von: filled[index].name,
      nach: filled[index + 1].name,
      distanz: Number(leg.distanz_m ?? 0),
      dauer: Number(leg.dauer_s ?? 0),
    }));
  }, [active, stops]);

  return (
    <motion.div
      className="jm-glass"
      style={{ width: 372, maxWidth: "calc(100vw - 40px)", borderRadius: 26 }}
      initial={{ opacity: 0, y: 24, scale: 0.97, filter: "blur(14px)" }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
      exit={{ opacity: 0, y: 18, scale: 0.98, filter: "blur(12px)" }}
      transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-specular" />
      <div style={{ padding: "15px 16px 12px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
          }}
        >
          <span className="jm-title">
            {stops.length > 2 ? `Trip · ${stops.length} Stationen` : "Route"}
          </span>
          <div style={{ display: "flex", gap: 4 }}>
            <button
              className="jm-dock-btn"
              style={{ width: 26, height: 26, fontSize: 12 }}
              onClick={onReverse}
              title="Reihenfolge umdrehen"
            >
              ⇅
            </button>
            <button
              className="jm-dock-btn"
              style={{ width: 26, height: 26, fontSize: 12 }}
              onClick={onClear}
              title="Route schließen"
            >
              ✕
            </button>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {stops.map((stop, index) => (
            <div
              key={`${stop?.id ?? "leer"}-${index}`}
              style={{ display: "flex", alignItems: "center", gap: 4 }}
            >
              <button
                className="jm-row"
                style={{ flex: 1, minWidth: 0 }}
                onClick={() => onEdit(index)}
                title={stop ? stop.label : stopHint(index, stops.length)}
              >
                <span
                  className="jm-mono"
                  style={{
                    color:
                      index === 0
                        ? "rgb(var(--jm-nav))"
                        : index === stops.length - 1
                          ? "rgb(var(--jm-gold))"
                          : "var(--jm-text-faint)",
                    width: 14,
                    textAlign: "center",
                  }}
                >
                  {stopMark(index, stops.length)}
                </span>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span
                    style={{
                      display: "block",
                      fontSize: 13,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      color: stop ? "var(--jm-text)" : "var(--jm-text-faint)",
                    }}
                  >
                    {stop ? stop.name : stopHint(index, stops.length)}
                  </span>
                </span>
              </button>
              <button
                className="jm-dock-btn"
                style={{ width: 22, height: 22, fontSize: 10 }}
                onClick={() => onShift(index, -1)}
                disabled={index === 0}
                title="Nach oben"
              >
                ↑
              </button>
              <button
                className="jm-dock-btn"
                style={{ width: 22, height: 22, fontSize: 10 }}
                onClick={() => onShift(index, 1)}
                disabled={index === stops.length - 1}
                title="Nach unten"
              >
                ↓
              </button>
              <button
                className="jm-dock-btn"
                style={{ width: 22, height: 22, fontSize: 10 }}
                onClick={() => onRemove(index)}
                disabled={stops.length <= 2}
                title="Station entfernen"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {stops.length < MAX_STOPS && (
          <button
            className="jm-chip"
            style={{ marginTop: 8, width: "100%", justifyContent: "center" }}
            onClick={onAdd}
            title="Noch ein Ziel an den Trip hängen"
          >
            ＋ Station hinzufügen
          </button>
        )}

        <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
          {(Object.keys(MODE_LABELS) as TravelMode[]).map((item) => (
            <button
              key={item}
              className="jm-chip"
              data-tone="nav"
              data-active={mode === item}
              style={{ flex: 1, justifyContent: "center" }}
              onClick={() => onMode(item)}
              title={MODE_LABELS[item]}
            >
              {MODE_ICONS[item]}
            </button>
          ))}
        </div>
      </div>

      {(busy || error || routes.length > 0) && (
        <>
          <div style={{ height: 1, background: "var(--jm-hairline)" }} />
          <div style={{ padding: "12px 16px 16px" }}>
            {busy && (
              <div style={{ fontSize: 12.5, color: "var(--jm-text-faint)" }}>
                Jon berechnet die Route …
              </div>
            )}
            {!busy && error && (
              <div style={{ fontSize: 12.5, color: "rgb(var(--jm-gold))" }}>
                {error}
              </div>
            )}
            {!busy &&
              routes.map((route, index) => (
                <button
                  key={route.id}
                  className="jm-row"
                  data-active={index === activeIndex}
                  onClick={() => onPick(index)}
                  style={{ marginBottom: 4 }}
                >
                  <span style={{ fontSize: 15, width: 22, textAlign: "center" }}>
                    {index === 0 ? "⚡" : "↩"}
                  </span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span
                      style={{
                        display: "block",
                        fontSize: 14,
                        fontWeight: 600,
                      }}
                    >
                      {formatDuration(route.duration_s)}
                      <span
                        style={{
                          fontWeight: 400,
                          color: "var(--jm-text-faint)",
                          marginLeft: 8,
                          fontSize: 12,
                        }}
                      >
                        {formatDistance(route.distance_m)}
                      </span>
                    </span>
                    <span
                      style={{
                        display: "block",
                        fontSize: 11.5,
                        color: "var(--jm-text-faint)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {route.summary}
                      {typeof route.extra?.umstiege === "number"
                        ? ` · ${route.extra.umstiege} Umstiege`
                        : ""}
                    </span>
                  </span>
                </button>
              ))}

            {!busy && legs.length > 1 && (
              <div
                className="jm-scroll jm-fade-mask"
                style={{ maxHeight: 148, marginTop: 8 }}
              >
                {legs.map((leg, index) => (
                  <div
                    key={`${leg.von}-${index}`}
                    style={{
                      display: "flex",
                      gap: 10,
                      alignItems: "baseline",
                      padding: "6px 4px",
                      fontSize: 11.5,
                      borderBottom: "1px solid var(--jm-hairline)",
                    }}
                  >
                    <span
                      className="jm-mono"
                      style={{ color: "var(--jm-text-faint)", minWidth: 16 }}
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
                    <span
                      className="jm-mono"
                      style={{ color: "var(--jm-text-soft)" }}
                    >
                      {formatDuration(leg.dauer)}
                    </span>
                    <span
                      className="jm-mono"
                      style={{ color: "var(--jm-text-faint)" }}
                    >
                      {formatDistance(leg.distanz)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {active && (
              <>
                <div style={{ display: "flex", gap: 7, marginTop: 10 }}>
                  <button
                    className="jm-chip"
                    style={{ flex: 1, justifyContent: "center" }}
                    onClick={() => setShowSteps((value) => !value)}
                  >
                    {showSteps ? "Schritte ausblenden" : `${active.steps.length} Schritte`}
                  </button>
                  <button
                    className="jm-chip"
                    data-active="true"
                    style={{ flex: 1, justifyContent: "center" }}
                    onClick={onDrive}
                    title="Die Route in Jons Flugansicht abfliegen"
                  >
                    ✈️ Route abfliegen
                  </button>
                </div>
                <AnimatePresence initial={false}>
                  {showSteps && (
                    <motion.div
                      key="steps"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
                      style={{ overflow: "hidden" }}
                    >
                      <div
                        className="jm-scroll jm-fade-mask"
                        style={{ maxHeight: 220, marginTop: 10 }}
                      >
                        {active.steps.map((step, index) => (
                          <div
                            key={index}
                            style={{
                              display: "flex",
                              gap: 10,
                              padding: "7px 4px",
                              fontSize: 12,
                              borderBottom: "1px solid var(--jm-hairline)",
                            }}
                          >
                            <span
                              className="jm-mono"
                              style={{
                                color: "var(--jm-text-faint)",
                                minWidth: 52,
                              }}
                            >
                              {formatDistance(step.distance_m)}
                            </span>
                            <span style={{ flex: 1 }}>{step.text}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}
          </div>
        </>
      )}
    </motion.div>
  );
}
