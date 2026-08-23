import { useState } from "react";
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
  from: MapsPlace | null;
  to: MapsPlace | null;
  via: MapsPlace[];
  mode: TravelMode;
  routes: MapsRoute[];
  activeIndex: number;
  busy: boolean;
  error: string;
  onMode: (mode: TravelMode) => void;
  onPick: (index: number) => void;
  onSwap: () => void;
  onClear: () => void;
  onEdit: (slot: "from" | "to") => void;
  onRemoveVia: (index: number) => void;
  onDrive: () => void;
}

export default function RoutePanel({
  from,
  to,
  via,
  mode,
  routes,
  activeIndex,
  busy,
  error,
  onMode,
  onPick,
  onSwap,
  onClear,
  onEdit,
  onRemoveVia,
  onDrive,
}: Props) {
  const [showSteps, setShowSteps] = useState(false);
  const active = routes[activeIndex];

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
          <span className="jm-title">Route</span>
          <div style={{ display: "flex", gap: 4 }}>
            <button
              className="jm-dock-btn"
              style={{ width: 26, height: 26, fontSize: 12 }}
              onClick={onSwap}
              title="Start und Ziel tauschen"
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
          <button className="jm-row" onClick={() => onEdit("from")}>
            <span className="jm-mono" style={{ color: "rgb(var(--jm-nav))" }}>
              ●
            </span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span
                style={{
                  display: "block",
                  fontSize: 13,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: from ? "var(--jm-text)" : "var(--jm-text-faint)",
                }}
              >
                {from ? from.name : "Start wählen"}
              </span>
            </span>
          </button>
          {via.map((stop, index) => (
            <button
              key={stop.id + index}
              className="jm-row"
              onClick={() => onRemoveVia(index)}
              title="Zwischenstopp entfernen"
            >
              <span className="jm-mono" style={{ color: "var(--jm-text-faint)" }}>
                ┃
              </span>
              <span
                style={{
                  flex: 1,
                  minWidth: 0,
                  fontSize: 12.5,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {stop.name}
              </span>
              <span style={{ fontSize: 11, color: "var(--jm-text-faint)" }}>✕</span>
            </button>
          ))}
          <button className="jm-row" onClick={() => onEdit("to")}>
            <span className="jm-mono" style={{ color: "rgb(var(--jm-gold))" }}>
              ◆
            </span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span
                style={{
                  display: "block",
                  fontSize: 13,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: to ? "var(--jm-text)" : "var(--jm-text-faint)",
                }}
              >
                {to ? to.name : "Ziel wählen"}
              </span>
            </span>
          </button>
        </div>

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
                    title="Die Route in Jons 3D-Welt abfahren"
                  >
                    ▶ Route erleben
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
