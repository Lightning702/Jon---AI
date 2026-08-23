import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MapsConfig, MapsPlace, formatDistance } from "../lib/maps";

interface Props {
  config: MapsConfig | null;
  results: MapsPlace[];
  busy: boolean;
  activeCategory: string;
  onSearch: (query: string) => void;
  onCategory: (category: string) => void;
  onPick: (place: MapsPlace) => void;
  onClear: () => void;
  onOpenRoute: () => void;
}

const QUICK = [
  "restaurant",
  "cafe",
  "hotel",
  "supermarkt",
  "tankstelle",
  "bahnhof",
  "apotheke",
  "sehenswuerdigkeit",
  "parken",
];

export default function SearchPanel({
  config,
  results,
  busy,
  activeCategory,
  onSearch,
  onCategory,
  onPick,
  onClear,
  onOpenRoute,
}: Props) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "f") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const quickChips = (config?.kategorien ?? []).filter((item) =>
    QUICK.includes(item.id)
  );

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim()) onSearch(query.trim());
  };

  const open = focused && (results.length > 0 || busy);

  return (
    <div style={{ width: "min(560px, calc(100vw - 40px))" }}>
      <motion.div
        className="jm-glass jm-glass--chrome"
        layout
        style={{ width: "min(392px, 100%)", borderRadius: 26 }}
        initial={{ opacity: 0, y: -14, filter: "blur(12px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="jm-specular" />
        <form
          onSubmit={submit}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 11,
            padding: "14px 16px",
          }}
        >
          <span style={{ fontSize: 16, opacity: 0.8 }}>🔍</span>
          <input
            ref={inputRef}
            className="jm-field"
            value={query}
            placeholder="Wo möchtest du hin?"
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => window.setTimeout(() => setFocused(false), 160)}
          />
          {query && (
            <button
              type="button"
              className="jm-dock-btn"
              style={{ width: 28, height: 28, fontSize: 13 }}
              onClick={() => {
                setQuery("");
                onClear();
              }}
              title="Suche leeren"
            >
              ✕
            </button>
          )}
          <button
            type="button"
            className="jm-dock-btn"
            style={{ width: 32, height: 32, fontSize: 15 }}
            onClick={onOpenRoute}
            title="Route planen"
          >
            🧭
          </button>
        </form>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              key="results"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
              style={{ overflow: "hidden" }}
            >
              <div
                style={{
                  height: 1,
                  background: "var(--jm-hairline)",
                  margin: "0 14px",
                }}
              />
              <div
                className="jm-scroll"
                style={{ maxHeight: 320, padding: 8 }}
              >
                {busy && results.length === 0 && (
                  <div
                    style={{
                      padding: "16px 12px",
                      fontSize: 12.5,
                      color: "var(--jm-text-faint)",
                    }}
                  >
                    Jon sucht …
                  </div>
                )}
                {results.map((place) => (
                  <button
                    key={place.id + place.lat}
                    className="jm-row"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      setFocused(false);
                      onPick(place);
                    }}
                  >
                    <span style={{ fontSize: 15, width: 22, textAlign: "center" }}>
                      {String(place.extra?.icon ?? "") || "📍"}
                    </span>
                    <span style={{ minWidth: 0, flex: 1 }}>
                      <span
                        style={{
                          display: "block",
                          fontSize: 13.5,
                          fontWeight: 550,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {place.name}
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
                        {place.category ? `${place.category} · ` : ""}
                        {place.label}
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
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <motion.div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 7,
          marginTop: 11,
        }}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
      >
        {quickChips.map((item) => (
          <button
            key={item.id}
            className="jm-chip jm-glass jm-glass--thin jm-press"
            data-active={activeCategory === item.id}
            style={{ borderRadius: 999, flex: "0 0 auto" }}
            onClick={() => onCategory(item.id)}
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </motion.div>
    </div>
  );
}
