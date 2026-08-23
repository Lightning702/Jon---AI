import { motion } from "framer-motion";
import { FriendLocation, formatAge, formatDistance } from "../lib/maps";

interface Props {
  friend: FriendLocation;
  distance: number | null;
  onClose: () => void;
  onRouteTo: () => void;
  onStreet: () => void;
  onChat: (id: string) => void;
}

export default function FriendSheet({
  friend,
  distance,
  onClose,
  onRouteTo,
  onStreet,
  onChat,
}: Props) {
  return (
    <motion.div
      className="jm-glass"
      style={{ width: 372, maxWidth: "calc(100vw - 40px)", borderRadius: 26 }}
      initial={{ opacity: 0, y: 26, scale: 0.96, filter: "blur(16px)" }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
      exit={{ opacity: 0, y: 18, scale: 0.97, filter: "blur(12px)" }}
      transition={{ duration: 0.44, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-specular" />
      <div style={{ padding: "16px 17px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              display: "grid",
              placeItems: "center",
              fontSize: 21,
              background: "rgb(var(--jm-nav) / 0.16)",
              border: `1px solid rgb(var(--jm-nav) / ${friend.frisch ? 0.6 : 0.25})`,
              flex: "0 0 auto",
            }}
          >
            {friend.avatar || "🙂"}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 16, fontWeight: 620 }}>{friend.name}</div>
            <div
              style={{
                fontSize: 12,
                color: friend.frisch
                  ? "var(--jm-text-soft)"
                  : "var(--jm-text-faint)",
                marginTop: 3,
              }}
            >
              {formatAge(friend.alter_s)}
              {friend.genauigkeit_m
                ? ` · ±${Math.round(friend.genauigkeit_m)} m`
                : ""}
              {friend.online ? " · online" : ""}
            </div>
          </div>
          <button
            className="jm-dock-btn"
            style={{ width: 26, height: 26, fontSize: 12, flex: "0 0 auto" }}
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {!friend.frisch && (
          <div
            style={{
              marginTop: 12,
              fontSize: 11.5,
              lineHeight: 1.5,
              color: "var(--jm-text-faint)",
            }}
          >
            Das ist der letzte Standort, den du bekommen hast — nicht unbedingt
            der aktuelle.
          </div>
        )}

        {distance != null && (
          <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
            <span className="jm-chip" style={{ cursor: "default" }}>
              📏 {formatDistance(distance)} entfernt
            </span>
          </div>
        )}

        <div style={{ display: "flex", gap: 7, marginTop: 14 }}>
          <button
            className="jm-chip jm-press"
            data-tone="nav"
            data-active="true"
            style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }}
            onClick={onRouteTo}
          >
            🧭 Route hin
          </button>
          <button
            className="jm-chip jm-press"
            style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }}
            onClick={onStreet}
          >
            👁️ Umsehen
          </button>
        </div>

        <button
          className="jm-chip jm-press"
          style={{
            width: "100%",
            justifyContent: "center",
            marginTop: 7,
            padding: "9px 12px",
          }}
          onClick={() => onChat(friend.id)}
        >
          💬 Nachricht schreiben
        </button>

        <div
          className="jm-mono"
          style={{ marginTop: 12, color: "var(--jm-text-faint)" }}
        >
          {friend.lat.toFixed(5)}, {friend.lon.toFixed(5)}
        </div>
      </div>
    </motion.div>
  );
}
