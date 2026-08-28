import { motion } from "framer-motion";
import { MapsPlace, formatDistance } from "../lib/maps";

interface Props {
  place: MapsPlace;
  onClose: () => void;
  onRouteTo: () => void;
  onRouteFrom: () => void;
  onStreet: () => void;
  onExplore: () => void;
  onAskJon: (question: string) => void;
}

function addressLine(place: MapsPlace): string {
  const address = place.address ?? {};
  const street = [address.road ?? address.street, address.house_number ?? address.housenumber]
    .filter(Boolean)
    .join(" ");
  const city = [address.postcode, address.city ?? address.town ?? address.village]
    .filter(Boolean)
    .join(" ");
  return [street, city].filter(Boolean).join(", ") || place.label;
}

export default function PlaceSheet({
  place,
  onClose,
  onRouteTo,
  onRouteFrom,
  onStreet,
  onExplore,
  onAskJon,
}: Props) {
  const website = String(place.extra?.webseite ?? "");
  const phone = String(place.extra?.telefon ?? "");
  const hours = String(place.extra?.oeffnungszeiten ?? "");
  const cuisine = String(place.extra?.kueche ?? "");

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
              width: 40,
              height: 40,
              borderRadius: 14,
              display: "grid",
              placeItems: "center",
              fontSize: 18,
              background: "rgb(var(--jm-gold) / 0.14)",
              border: "1px solid rgb(var(--jm-gold) / 0.32)",
              flex: "0 0 auto",
            }}
          >
            {String(place.extra?.icon ?? "") || "📍"}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 16, fontWeight: 620, lineHeight: 1.25 }}>
              {place.name}
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--jm-text-soft)",
                marginTop: 3,
                lineHeight: 1.45,
              }}
            >
              {place.category ? `${place.category} · ` : ""}
              {addressLine(place)}
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

        {(hours || phone || cuisine || place.distance_m != null) && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              marginTop: 12,
            }}
          >
            {place.distance_m != null && (
              <span className="jm-chip" style={{ cursor: "default" }}>
                📏 {formatDistance(place.distance_m)}
              </span>
            )}
            {hours && (
              <span className="jm-chip" style={{ cursor: "default" }}>
                🕒 {hours.slice(0, 34)}
              </span>
            )}
            {cuisine && (
              <span className="jm-chip" style={{ cursor: "default" }}>
                🍴 {cuisine.replace(/;/g, ", ").slice(0, 26)}
              </span>
            )}
            {phone && (
              <span className="jm-chip" style={{ cursor: "default" }}>
                ☎ {phone.slice(0, 22)}
              </span>
            )}
          </div>
        )}

        <div style={{ display: "flex", gap: 7, marginTop: 14 }}>
          <button
            className="jm-chip"
            data-tone="nav"
            data-active="true"
            style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }}
            onClick={onRouteTo}
          >
            🧭 Route hierher
          </button>
          <button
            className="jm-chip"
            style={{ justifyContent: "center", padding: "9px 12px" }}
            onClick={onRouteFrom}
            title="Von hier aus starten"
          >
            ↗ Von hier
          </button>
        </div>

        <div style={{ display: "flex", gap: 7, marginTop: 7 }}>
          <button
            className="jm-chip"
            style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }}
            onClick={onStreet}
          >
            👁️ Street Exploration
          </button>
          <button
            className="jm-chip"
            style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }}
            onClick={onExplore}
          >
            ✈️ Hinfliegen
          </button>
        </div>

        <div style={{ display: "flex", gap: 7, marginTop: 7 }}>
          <button
            className="jm-chip"
            style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }}
            onClick={() =>
              onAskJon(`Was kann ich rund um ${place.name} unternehmen?`)
            }
          >
            ✨ Jon fragen
          </button>
          {website && (
            <button
              className="jm-chip"
              style={{ justifyContent: "center", padding: "9px 12px" }}
              onClick={() => window.open(website, "_blank", "noopener")}
            >
              🔗 Webseite
            </button>
          )}
        </div>

        <div
          className="jm-mono"
          style={{ marginTop: 12, color: "var(--jm-text-faint)" }}
        >
          {place.lat.toFixed(5)}, {place.lon.toFixed(5)}
        </div>
      </div>
    </motion.div>
  );
}
