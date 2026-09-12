import { useState } from "react";
import { motion } from "framer-motion";
import { JonDatei, dateiInhaltUrl, dateiOeffnen } from "../lib/api";

const SYMBOLE: Record<string, string> = {
  dokument: "📄",
  tabelle: "📊",
  praesentation: "📽️",
  bild: "🖼️",
  video: "🎬",
  audio: "🎵",
  "3d": "🧊",
  archiv: "🗜️",
  datei: "📁",
};

const FARBEN: Record<string, string> = {
  dokument: "text-[#e8c45a]",
  tabelle: "text-[#7fd07f]",
  praesentation: "text-[#e08a5a]",
  bild: "text-[#7fb4e8]",
  video: "text-[#c98ae0]",
  audio: "text-[#5fd0c0]",
  "3d": "text-[#e0a05f]",
};

function endung(name: string): string {
  const teil = name.split(".").pop();
  return teil && teil !== name ? teil.toUpperCase() : "Datei";
}

export default function DateiCard({ dateien }: { dateien: JonDatei[] }) {
  const [meldung, setMeldung] = useState("");
  const [busy, setBusy] = useState("");

  if (!dateien?.length) return null;

  const oeffnen = async (datei: JonDatei, ordner: boolean) => {
    setBusy(datei.path + (ordner ? "-o" : ""));
    setMeldung("");
    const ergebnis = await dateiOeffnen(datei.path, ordner);
    setBusy("");
    if (ergebnis?.error) setMeldung(ergebnis.error);
  };

  return (
    <div className="space-y-2 mt-2">
      {dateien.map((datei) => {
        const symbol = SYMBOLE[datei.kind] ?? SYMBOLE.datei;
        const farbe = FARBEN[datei.kind] ?? "text-white/80";
        return (
          <motion.div
            key={datei.path}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
            className="rounded-xl border border-gold/25 bg-black/30 px-3 py-2.5 max-w-md"
          >
            <div className="flex items-start gap-3">
              <span className={`text-[22px] leading-none ${farbe}`}>{symbol}</span>
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate" title={datei.name}>
                  {datei.name}
                </div>
                <div className="text-[11px] text-white/45">
                  {endung(datei.name)} · {datei.sizeText}
                  {!datei.exists && " · nicht mehr da"}
                </div>
                <div
                  className="text-[10.5px] text-white/30 truncate mt-0.5"
                  title={datei.folder}
                >
                  {datei.folder}
                </div>
              </div>
            </div>
            {datei.exists && (
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                <button
                  onClick={() => void oeffnen(datei, false)}
                  disabled={busy === datei.path}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-gold/80 text-black font-semibold disabled:opacity-50"
                >
                  {busy === datei.path ? "öffnet …" : "Öffnen"}
                </button>
                <a
                  href={dateiInhaltUrl(datei.path)}
                  download={datei.name}
                  className="text-[11px] px-2.5 py-1 rounded-lg border border-white/15 text-white/70 hover:bg-white/5"
                >
                  Herunterladen
                </a>
                <button
                  onClick={() => void oeffnen(datei, true)}
                  disabled={busy === datei.path + "-o"}
                  className="text-[11px] px-2.5 py-1 rounded-lg border border-gold/30 text-gold/85 hover:bg-gold/10 disabled:opacity-50"
                >
                  {busy === datei.path + "-o" ? "öffnet …" : "Im Ordner öffnen"}
                </button>
              </div>
            )}
          </motion.div>
        );
      })}
      {meldung && <div className="text-[11px] text-red-300/85">{meldung}</div>}
    </div>
  );
}
