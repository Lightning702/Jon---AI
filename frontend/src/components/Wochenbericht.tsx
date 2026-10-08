import Symbol from "./Symbol";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { HandyBericht, handyBericht } from "../lib/api";

function dauer(minuten: number): string {
  const stunden = Math.floor(minuten / 60);
  const rest = minuten % 60;
  if (stunden && rest) return `${stunden} h ${rest} min`;
  return stunden ? `${stunden} h` : `${rest} min`;
}

function datum(iso: string): string {
  const [, monat, tag] = iso.split("-").map(Number);
  return `${tag}.${monat}.`;
}

const FARBEN = ["#5ee0b0", "#6ec8ff", "#a996ff", "#ffb86b", "#ff86b6", "#e8d27c"];

export default function Wochenbericht({ geraet, bis, rahmen = true }: { geraet: string; bis?: string; rahmen?: boolean }) {
  const [bericht, setBericht] = useState<HandyBericht | null>(null);
  const [fehler, setFehler] = useState("");

  useEffect(() => {
    let aktiv = true;
    setFehler("");
    handyBericht(geraet, bis)
      .then((b) => aktiv && setBericht(b))
      .catch((e) => aktiv && setFehler(e instanceof Error ? e.message : "Bericht nicht verfügbar."));
    return () => {
      aktiv = false;
    };
  }, [geraet, bis]);

  const aussen = rahmen ? "max-w-md rounded-2xl border border-gold/25 bg-gradient-to-br from-[#161d33]/80 to-black/40 p-4" : "";
  if (fehler) return <div className={`${aussen} text-[12px] text-red-300`}>{fehler}</div>;
  if (!bericht) return <div className={`${aussen} text-[12px] text-white/40`}>Wochenbericht wird geladen …</div>;

  const hoechstes = Math.max(60, ...bericht.tage.map((t) => t.minuten));
  const aenderung = bericht.vorwoche ? Math.round(((bericht.gesamt - bericht.vorwoche) * 100) / bericht.vorwoche) : null;
  const appMax = Math.max(1, ...bericht.apps.map((a) => a.minuten));

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 360, damping: 32 }}
      className={aussen}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="font-semibold text-white"><Symbol zeichen="📊" /> {bericht.name}</div>
        <div className="text-[11px] text-white/45">
          {datum(bericht.von)} – {datum(bericht.bis)}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-end gap-x-5 gap-y-1">
        <div>
          <div className="text-[22px] font-semibold leading-none text-white">{dauer(bericht.gesamt)}</div>
          <div className="mt-1 text-[11px] text-white/45">Bildschirmzeit gesamt</div>
        </div>
        <div>
          <div className="text-[15px] font-medium leading-none text-white/85">Ø {dauer(bericht.schnitt)}</div>
          <div className="mt-1 text-[11px] text-white/45">pro Tag</div>
        </div>
        {aenderung !== null && (
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
              aenderung > 0 ? "bg-amber-500/15 text-amber-200" : "bg-emerald-500/15 text-emerald-200"
            }`}
          >
            {aenderung > 0 ? "▲" : aenderung < 0 ? "▼" : "■"} {Math.abs(aenderung)} % zur Vorwoche
          </span>
        )}
      </div>

      <div className="mt-4 flex h-28 items-end gap-2">
        {bericht.tage.map((tag, i) => (
          <div key={tag.tag} className="flex h-full flex-1 flex-col items-center justify-end gap-1" title={`${tag.wochentag} ${datum(tag.tag)}: ${dauer(tag.minuten)}`}>
            <div className="text-[9.5px] text-white/40">{tag.minuten ? Math.round(tag.minuten / 6) / 10 + " h" : ""}</div>
            <motion.div
              className={`w-full rounded-md ${i === bericht.tage.length - 1 ? "bg-gold/80" : tag.erfasst ? "bg-sky-400/60" : "bg-white/10"}`}
              initial={{ height: 0 }}
              animate={{ height: `${Math.max(tag.erfasst ? 4 : 2, (tag.minuten / hoechstes) * 100)}%` }}
              transition={{ type: "spring", stiffness: 140, damping: 18, delay: 0.05 * i }}
            />
            <div className="text-[10px] text-white/55">{tag.wochentag}</div>
          </div>
        ))}
      </div>

      {bericht.apps.length > 0 && (
        <div className="mt-4 space-y-1.5">
          {bericht.apps.map((app, i) => (
            <div key={app.id} className="flex items-center gap-2 text-[11.5px]">
              <span className="w-24 truncate text-white/75">{app.name}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: FARBEN[i % FARBEN.length] }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(app.minuten / appMax) * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.2 + 0.06 * i, ease: [0.2, 0.8, 0.2, 1] }}
                />
              </div>
              <span className="w-16 text-right text-white/45">{dauer(app.minuten)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-white/60">
        {bericht.schritte > 0 && <span><Symbol zeichen="👣" /> {bericht.schritte.toLocaleString("de-AT")} Schritte</span>}
        {bericht.anfragen > 0 && (
          <span>
            <Symbol zeichen="⏳" /> {bericht.anfragen} Extra-Zeit-Anfrage{bericht.anfragen === 1 ? "" : "n"} · {bericht.erlaubt} erlaubt
          </span>
        )}
        {bericht.sos > 0 && <span className="text-red-300"><Symbol zeichen="🆘" /> {bericht.sos}× SOS</span>}
        {!bericht.gesamt && !bericht.schritte && <span>Für diese Woche gibt es noch keine Daten.</span>}
      </div>
    </motion.div>
  );
}
