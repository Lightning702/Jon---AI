import { motion } from "framer-motion";
import { BatteryCharging, BellRing, Compass, Eye, Home, Laptop, LoaderCircle, LocateFixed, Smartphone, Tablet, Watch, X } from "lucide-react";
import { useState } from "react";
import { GeraetOrt, geraetKlingeln, geraetOrten } from "../lib/api";
import { formatDistance } from "../lib/maps";

interface Props {
  ort: GeraetOrt;
  distance: number | null;
  onClose: () => void;
  onRouteTo: () => void;
  onStreet: () => void;
  onAktualisiert: () => void;
  onMeldung: (text: string) => void;
}

const SYMBOLE = { handy: Smartphone, tablet: Tablet, uhr: Watch, pc: Laptop };

function alterText(sekunden: number): string {
  if (sekunden < 90) return "gerade eben";
  if (sekunden < 3600) return `vor ${Math.floor(sekunden / 60)} Min.`;
  if (sekunden < 86400) return `vor ${Math.floor(sekunden / 3600)} Std.`;
  return `vor ${Math.floor(sekunden / 86400)} Tagen`;
}

export default function GeraetSheet({ ort, distance, onClose, onRouteTo, onStreet, onAktualisiert, onMeldung }: Props) {
  const [busy, setBusy] = useState("");
  const Symbol = SYMBOLE[ort.typ as keyof typeof SYMBOLE] ?? Smartphone;

  async function ausfuehren(art: "orten" | "klingeln") {
    setBusy(art);
    try {
      if (art === "orten") {
        await geraetOrten(ort.id);
        onAktualisiert();
        onMeldung(`${ort.besitzer || ort.name} wurde gerade geortet.`);
      } else {
        await geraetKlingeln(ort.id);
        onMeldung(`${ort.name} klingelt.`);
      }
    } catch (e) {
      onMeldung(e instanceof Error ? e.message : "Das hat nicht geklappt.");
    } finally {
      setBusy("");
    }
  }

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
              background: "rgb(var(--jm-gold) / 0.16)",
              border: `1px solid rgb(var(--jm-gold) / ${ort.frisch ? 0.7 : 0.25})`,
              color: "rgb(var(--jm-gold))",
              flex: "0 0 auto",
            }}
          >
            <Symbol size={20} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 16, fontWeight: 620 }}>{ort.besitzer || ort.name}</div>
            <div style={{ fontSize: 12, color: "var(--jm-text-soft)", marginTop: 3 }}>
              {ort.name}
              {ort.fern && ort.jon ? ` · über ${ort.jon}` : ""}
            </div>
          </div>
          <button className="jm-dock-btn" style={{ width: 26, height: 26, flex: "0 0 auto" }} onClick={onClose} aria-label="Schließen">
            <X size={13} />
          </button>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
          <span className="jm-chip" style={{ cursor: "default" }}>
            {ort.zuhause ? <Home size={13} /> : <LocateFixed size={13} />}
            {ort.zuhause ? "Zuhause" : alterText(ort.alter_s)}
          </span>
          {typeof ort.akku === "number" && ort.akku >= 0 ? (
            <span className="jm-chip" style={{ cursor: "default" }}>
              {ort.laedt ? <BatteryCharging size={13} /> : null}
              {ort.akku} %
            </span>
          ) : null}
          {ort.genau ? (
            <span className="jm-chip" style={{ cursor: "default" }}>
              ± {Math.round(ort.genau)} m
            </span>
          ) : null}
          {distance != null ? (
            <span className="jm-chip" style={{ cursor: "default" }}>
              {formatDistance(distance)} entfernt
            </span>
          ) : null}
          <span className="jm-chip" style={{ cursor: "default", color: ort.online ? "rgb(62 213 152)" : undefined }}>
            {ort.online ? "online" : "offline"}
          </span>
        </div>

        {!ort.frisch ? (
          <div style={{ marginTop: 10, fontSize: 11.5, lineHeight: 1.5, color: "var(--jm-text-faint)" }}>
            Das ist der zuletzt gemeldete Standort. Mit „Jetzt orten“ fragt Jon das Gerät neu.
          </div>
        ) : null}

        <div style={{ display: "flex", gap: 7, marginTop: 14 }}>
          <button className="jm-chip jm-press" data-tone="nav" data-active="true" style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }} onClick={onRouteTo}>
            <Compass size={14} /> Route hin
          </button>
          <button className="jm-chip jm-press" style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }} onClick={onStreet}>
            <Eye size={14} /> Umsehen
          </button>
        </div>
        {!ort.fern ? (
          <div style={{ display: "flex", gap: 7, marginTop: 7 }}>
            <button className="jm-chip jm-press" disabled={!!busy} style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }} onClick={() => void ausfuehren("orten")}>
              {busy === "orten" ? <LoaderCircle size={14} className="animate-spin" /> : <LocateFixed size={14} />} Jetzt orten
            </button>
            {ort.typ !== "pc" ? (
              <button className="jm-chip jm-press" disabled={!!busy} style={{ flex: 1, justifyContent: "center", padding: "9px 12px" }} onClick={() => void ausfuehren("klingeln")}>
                {busy === "klingeln" ? <LoaderCircle size={14} className="animate-spin" /> : <BellRing size={14} />} Klingeln
              </button>
            ) : null}
          </div>
        ) : null}

        <div className="jm-mono" style={{ marginTop: 12, color: "var(--jm-text-faint)" }}>
          {ort.lat.toFixed(5)}, {ort.lon.toFixed(5)}
        </div>
      </div>
    </motion.div>
  );
}
