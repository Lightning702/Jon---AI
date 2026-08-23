import { motion } from "framer-motion";
import { FriendsResult, MapsConfig, MapsTheme, formatAge } from "../lib/maps";

interface Props {
  config: MapsConfig | null;
  layers: Record<string, boolean>;
  terrain: boolean;
  theme: MapsTheme;
  onToggle: (key: string) => void;
  onTerrain: () => void;
  onTheme: (theme: MapsTheme) => void;
  homeName: string;
  onPinHome: () => void;
  onLocate: () => void;
  friends: FriendsResult | null;
  onSharing: (patch: {
    aktiv?: boolean;
    alle?: boolean;
    peers?: string[];
  }) => void;
  onShareNow: () => void;
  onClose: () => void;
}

const ENTRIES: { id: string; icon: string; label: string; hint: string }[] = [
  {
    id: "satellit",
    icon: "🛰️",
    label: "Satellit",
    hint: "Echte Luftbilder über der Karte",
  },
  {
    id: "gebaeude3d",
    icon: "🏙️",
    label: "3D-Gebäude",
    hint: "Häuser mit echter Höhe aus OpenStreetMap",
  },
  {
    id: "gelaende",
    icon: "⛰️",
    label: "Gelände-Schattierung",
    hint: "Berge und Täler plastisch",
  },
  {
    id: "verkehr",
    icon: "🚦",
    label: "Verkehr",
    hint: "Braucht einen Verkehrsanbieter in der .env",
  },
  {
    id: "oepnv",
    icon: "🚇",
    label: "Öffentliche Verkehrsmittel",
    hint: "Linien, Haltestellen, Bahnnetz",
  },
  {
    id: "fahrrad",
    icon: "🚲",
    label: "Fahrradnetz",
    hint: "Radwege und Radrouten",
  },
  {
    id: "fusswege",
    icon: "🥾",
    label: "Fußwege",
    hint: "Pfade, Treppen und Fußgängerzonen",
  },
];

export default function LayerSheet({
  config,
  layers,
  terrain,
  theme,
  onToggle,
  onTerrain,
  onTheme,
  homeName,
  onPinHome,
  onLocate,
  friends,
  onSharing,
  onShareNow,
  onClose,
}: Props) {
  const available = config?.ebenen ?? {};
  return (
    <motion.div
      className="jm-glass"
      style={{
        width: 306,
        maxHeight: "calc(100vh - 130px)",
        display: "flex",
        flexDirection: "column",
        padding: 0,
        borderRadius: 26,
      }}
      initial={{ opacity: 0, x: 26, scale: 0.96, filter: "blur(14px)" }}
      animate={{ opacity: 1, x: 0, scale: 1, filter: "blur(0px)" }}
      exit={{ opacity: 0, x: 20, scale: 0.97, filter: "blur(12px)" }}
      transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-specular" />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 16px 10px",
          flex: "0 0 auto",
        }}
      >
        <span className="jm-title">Ebenen</span>
        <button
          className="jm-dock-btn"
          style={{ width: 26, height: 26, fontSize: 12 }}
          onClick={onClose}
        >
          ✕
        </button>
      </div>
      <div
        className="jm-scroll"
        style={{
          flex: "1 1 auto",
          minHeight: 0,
          overflowY: "auto",
          padding: "0 16px 16px",
        }}
      >

      <div
        style={{
          display: "flex",
          gap: 6,
          padding: 4,
          borderRadius: 14,
          background: "var(--jm-field)",
          marginBottom: 12,
        }}
      >
        {(["dark", "light"] as MapsTheme[]).map((item) => (
          <button
            key={item}
            className="jm-chip"
            data-active={theme === item}
            style={{ flex: 1, justifyContent: "center", border: "none" }}
            onClick={() => onTheme(item)}
          >
            {item === "dark" ? "🌙 Dunkel" : "☀️ Hell"}
          </button>
        ))}
      </div>

      <div
        style={{ height: 1, background: "var(--jm-hairline)", margin: "12px 0" }}
      />

      <div style={{ padding: "0 4px 10px" }}>
        <span className="jm-title">Mein Standort</span>
        <div
          style={{
            fontSize: 12,
            color: "var(--jm-text-soft)",
            marginTop: 6,
            lineHeight: 1.5,
          }}
        >
          {homeName || "Noch nicht gesetzt — Jon schätzt ihn über die IP."}
        </div>
        <div style={{ display: "flex", gap: 6, marginTop: 9 }}>
          <button
            className="jm-chip jm-press"
            style={{ flex: 1, justifyContent: "center" }}
            onClick={onLocate}
            title="Standort vom Gerät holen"
          >
            ◎ Orten
          </button>
          <button
            className="jm-chip jm-press"
            style={{ flex: 1, justifyContent: "center" }}
            onClick={onPinHome}
            title="Kartenmitte als deinen Standort speichern"
          >
            📍 Kartenmitte
          </button>
        </div>
      </div>

      <div
        style={{ height: 1, background: "var(--jm-hairline)", margin: "0 0 12px" }}
      />

      <div style={{ padding: "0 4px 12px" }}>
        <span className="jm-title">Freunde auf der Karte</span>
        <div
          style={{
            fontSize: 11.5,
            color: "var(--jm-text-faint)",
            marginTop: 6,
            lineHeight: 1.5,
          }}
        >
          Du siehst Freunde nur, wenn sie ihren Standort fuer dich freigeben —
          und sie sehen dich nur, wenn du es hier einschaltest.
        </div>

        <button
          className="jm-row"
          data-active={Boolean(friends?.teilen.aktiv)}
          onClick={() => onSharing({ aktiv: !friends?.teilen.aktiv })}
          style={{ marginTop: 10 }}
        >
          <span style={{ fontSize: 15, width: 22, textAlign: "center" }}>
            📡
          </span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <span style={{ display: "block", fontSize: 13, fontWeight: 550 }}>
              Meinen Standort teilen
            </span>
            <span
              style={{
                display: "block",
                fontSize: 11,
                color: "var(--jm-text-faint)",
              }}
            >
              {friends?.teilen.aktiv
                ? friends.zuletzt_gesendet
                  ? `zuletzt gesendet ${formatAge(
                      Date.now() / 1000 - friends.zuletzt_gesendet
                    )}`
                  : "wird gleich gesendet"
                : "aus — niemand sieht dich"}
            </span>
          </span>
          <span
            style={{
              width: 34,
              height: 19,
              borderRadius: 999,
              background: friends?.teilen.aktiv
                ? "rgb(var(--jm-nav) / 0.85)"
                : "var(--jm-field-hover)",
              position: "relative",
              transition: "background 0.3s var(--jm-ease)",
              flex: "0 0 auto",
            }}
          >
            <span
              style={{
                position: "absolute",
                top: 2,
                left: friends?.teilen.aktiv ? 17 : 2,
                width: 15,
                height: 15,
                borderRadius: "50%",
                background: "#fff",
                boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
                transition: "left 0.32s cubic-bezier(0.34,1.56,0.64,1)",
              }}
            />
          </span>
        </button>

        {friends?.teilen.aktiv && (
          <>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <button
                className="jm-chip jm-press"
                data-tone="nav"
                data-active={friends.teilen.alle}
                style={{ flex: 1, justifyContent: "center" }}
                onClick={() => onSharing({ alle: true })}
              >
                Alle Freunde
              </button>
              <button
                className="jm-chip jm-press"
                data-tone="nav"
                data-active={!friends.teilen.alle}
                style={{ flex: 1, justifyContent: "center" }}
                onClick={() => onSharing({ alle: false })}
              >
                Nur ausgewaehlte
              </button>
            </div>

            {!friends.teilen.alle && (
              <div style={{ marginTop: 6 }}>
                {friends.kontakte.length === 0 && (
                  <div
                    style={{
                      fontSize: 11.5,
                      color: "var(--jm-text-faint)",
                      padding: "8px 4px",
                    }}
                  >
                    Du hast noch keine Freunde in Jon.
                  </div>
                )}
                {friends.kontakte.map((contact) => {
                  const on = friends.teilen.peers.includes(contact.id);
                  return (
                    <button
                      key={contact.id}
                      className="jm-row"
                      data-active={on}
                      onClick={() =>
                        onSharing({
                          peers: on
                            ? friends.teilen.peers.filter(
                                (id) => id !== contact.id
                              )
                            : [...friends.teilen.peers, contact.id],
                        })
                      }
                    >
                      <span
                        style={{ fontSize: 15, width: 22, textAlign: "center" }}
                      >
                        {contact.avatar || "🙂"}
                      </span>
                      <span style={{ flex: 1, fontSize: 12.5 }}>
                        {contact.name}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          color: on
                            ? "rgb(var(--jm-nav))"
                            : "var(--jm-text-faint)",
                        }}
                      >
                        {on ? "sieht dich" : "sieht dich nicht"}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            <button
              className="jm-chip jm-press"
              style={{ width: "100%", justifyContent: "center", marginTop: 8 }}
              onClick={onShareNow}
            >
              📡 Jetzt senden
            </button>
          </>
        )}

        {(friends?.freunde.length ?? 0) > 0 && (
          <div style={{ marginTop: 10 }}>
            {friends?.freunde.map((friend) => (
              <div
                key={friend.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 9,
                  padding: "6px 4px",
                  fontSize: 12,
                }}
              >
                <span style={{ width: 20, textAlign: "center" }}>
                  {friend.avatar || "🙂"}
                </span>
                <span style={{ flex: 1, minWidth: 0 }}>{friend.name}</span>
                <span
                  style={{
                    fontSize: 10.5,
                    color: friend.frisch
                      ? "rgb(var(--jm-nav))"
                      : "var(--jm-text-faint)",
                  }}
                >
                  {formatAge(friend.alter_s)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div
        style={{ height: 1, background: "var(--jm-hairline)", margin: "0 0 12px" }}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {ENTRIES.map((entry) => {
          const usable = available[entry.id] !== false;
          const on = Boolean(layers[entry.id]);
          return (
            <button
              key={entry.id}
              className="jm-row"
              data-active={on}
              disabled={!usable}
              onClick={() => usable && onToggle(entry.id)}
              style={{ opacity: usable ? 1 : 0.4 }}
              title={usable ? entry.hint : `${entry.hint} — nicht verfügbar`}
            >
              <span style={{ fontSize: 15, width: 22, textAlign: "center" }}>
                {entry.icon}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", fontSize: 13, fontWeight: 550 }}>
                  {entry.label}
                </span>
                <span
                  style={{
                    display: "block",
                    fontSize: 11,
                    color: "var(--jm-text-faint)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {entry.hint}
                </span>
              </span>
              <span
                style={{
                  width: 34,
                  height: 19,
                  borderRadius: 999,
                  background: on
                    ? "rgb(var(--jm-gold) / 0.8)"
                    : "var(--jm-field-hover)",
                  position: "relative",
                  transition: "background 0.3s var(--jm-ease)",
                  flex: "0 0 auto",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    top: 2,
                    left: on ? 17 : 2,
                    width: 15,
                    height: 15,
                    borderRadius: "50%",
                    background: "#fff",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
                    transition: "left 0.32s cubic-bezier(0.34,1.56,0.64,1)",
                  }}
                />
              </span>
            </button>
          );
        })}
      </div>

      <button
        className="jm-row"
        data-active={terrain}
        onClick={onTerrain}
        disabled={available.gelaende === false}
        style={{ opacity: available.gelaende === false ? 0.4 : 1 }}
      >
        <span style={{ fontSize: 15, width: 22, textAlign: "center" }}>🏔️</span>
        <span style={{ flex: 1 }}>
          <span style={{ display: "block", fontSize: 13, fontWeight: 550 }}>
            Echtes 3D-Gelände
          </span>
          <span style={{ display: "block", fontSize: 11, color: "var(--jm-text-faint)" }}>
            Höhendaten verformen die Karte wirklich
          </span>
        </span>
        <span
          style={{
            width: 34,
            height: 19,
            borderRadius: 999,
            background: terrain
              ? "rgb(var(--jm-gold) / 0.8)"
              : "var(--jm-field-hover)",
            position: "relative",
            transition: "background 0.3s var(--jm-ease)",
            flex: "0 0 auto",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 2,
              left: terrain ? 17 : 2,
              width: 15,
              height: 15,
              borderRadius: "50%",
              background: "#fff",
              boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
              transition: "left 0.32s cubic-bezier(0.34,1.56,0.64,1)",
            }}
          />
        </span>
      </button>
      </div>
    </motion.div>
  );
}
