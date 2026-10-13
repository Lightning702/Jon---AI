import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, X } from "lucide-react";
import { useState } from "react";
import { createPortal } from "react-dom";
import { dateiInhaltUrl } from "../lib/api";

export interface WebBild {
  pfad: string;
  titel?: string;
  quelle?: string;
  seite?: string;
  lizenz?: string;
  autor?: string;
  beschreibung?: string;
}

export interface WebBildDaten {
  titel?: string;
  bilder: WebBild[];
}

function name(bild: WebBild): string {
  return (bild.titel || "").replace(/\.(jpe?g|png|webp|gif|tiff?)$/i, "").replace(/_/g, " ");
}

function herkunft(bild: WebBild): string {
  return [bild.quelle, bild.lizenz, bild.autor ? bild.autor.split(/\n/)[0].slice(0, 60) : ""].filter(Boolean).join(" · ");
}

export default function WebBildKarte({ data }: { data: WebBildDaten }) {
  const [gross, setGross] = useState<WebBild | null>(null);
  const bilder = (data.bilder ?? []).filter((b) => b.pfad);
  if (!bilder.length) return null;
  const einzeln = bilder.length === 1;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 360, damping: 30 }}
      className="w-full max-w-[560px]"
    >
      {data.titel ? <div className="mb-1.5 text-[12px] text-white/55">{data.titel}</div> : null}
      <div className={einzeln ? "" : "grid grid-cols-2 gap-2"}>
        {bilder.map((bild, index) => (
          <figure
            key={bild.pfad}
            className={"group overflow-hidden rounded-2xl border border-white/10 bg-black/40 " + (!einzeln && bilder.length === 3 && index === 0 ? "col-span-2" : "")}
          >
            <button onClick={() => setGross(bild)} className="block w-full" aria-label="Bild vergrößern">
              <img
                src={dateiInhaltUrl(bild.pfad)}
                alt={name(bild)}
                loading="lazy"
                className={"w-full object-cover transition duration-500 group-hover:scale-[1.02] " + (einzeln ? "max-h-[360px]" : "h-[170px]")}
              />
            </button>
            <figcaption className="flex items-center gap-2 px-3 py-2 text-[11px] text-white/50">
              <span className="min-w-0 flex-1 truncate" title={`${name(bild)} — ${herkunft(bild)}`}>
                <span className="text-white/75">{name(bild)}</span>
                {herkunft(bild) ? ` · ${herkunft(bild)}` : ""}
              </span>
              {bild.seite ? (
                <a href={bild.seite} target="_blank" rel="noreferrer" className="flex-none text-white/45 transition hover:text-gold" aria-label="Quelle öffnen">
                  <ExternalLink size={13} />
                </a>
              ) : null}
            </figcaption>
          </figure>
        ))}
      </div>
      {createPortal(
        <AnimatePresence>
          {gross ? (
            <motion.div
              key="gross"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setGross(null)}
              className="fixed inset-0 z-[400] flex flex-col items-center justify-center gap-3 bg-black/85 p-6 backdrop-blur-sm"
            >
              <button className="absolute right-5 top-5 rounded-full bg-white/10 p-2 text-white/80 hover:bg-white/20" aria-label="Schließen">
                <X size={18} />
              </button>
              <motion.img
                initial={{ scale: 0.94 }}
                animate={{ scale: 1 }}
                src={dateiInhaltUrl(gross.pfad)}
                alt={name(gross)}
                className="max-h-[82vh] max-w-[92vw] rounded-xl object-contain shadow-2xl"
              />
              <div className="max-w-[80vw] text-center text-[12.5px] text-white/70">
                {name(gross)}
                {herkunft(gross) ? <span className="text-white/45"> · {herkunft(gross)}</span> : null}
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>,
        document.body
      )}
    </motion.div>
  );
}
