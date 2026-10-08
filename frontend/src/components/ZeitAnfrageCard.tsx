import Symbol from "./Symbol";
import { motion } from "framer-motion";
import { useState } from "react";
import { handyZeitanfrageBeantworten } from "../lib/api";

export interface ZeitAnfrageDaten {
  geraet: string;
  meldung: string;
  name: string;
  app: string;
  minuten: number;
  text?: string;
}

export default function ZeitAnfrageCard({ data }: { data: ZeitAnfrageDaten }) {
  const [minuten, setMinuten] = useState(Math.max(5, Math.min(120, Number(data.minuten) || 30)));
  const [stand, setStand] = useState<"offen" | "laeuft" | "ja" | "nein">("offen");
  const [fehler, setFehler] = useState("");
  const [hinweis, setHinweis] = useState("");

  async function antworten(erlaubt: boolean) {
    setStand("laeuft");
    setFehler("");
    try {
      const antwort = await handyZeitanfrageBeantworten(data.geraet, data.meldung, erlaubt, minuten);
      setStand(erlaubt ? "ja" : "nein");
      if (antwort.zugestellt === false) setHinweis("Das Handy ist gerade offline – es erfährt die Antwort beim nächsten Verbinden.");
    } catch (e) {
      setStand("offen");
      setFehler(e instanceof Error ? e.message : "Das hat nicht geklappt.");
    }
  }

  const fertig = stand === "ja" || stand === "nein";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      className="max-w-md overflow-hidden rounded-2xl border border-gold/25 bg-gradient-to-br from-[#1b2340]/80 to-black/40 p-4"
    >
      <div className="flex items-start gap-3">
        <motion.span
          className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-gold/15 text-[20px]"
          animate={fertig ? { scale: [1, 1.18, 1] } : { rotate: [0, -8, 8, 0] }}
          transition={fertig ? { duration: 0.45 } : { duration: 1.6, repeat: Infinity, repeatDelay: 1.2 }}
        >
          <Symbol zeichen={stand === "ja" ? "✅" : stand === "nein" ? "🙅" : "⏳"} />
        </motion.span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-white">
            {data.name} möchte mehr {data.app || "Bildschirmzeit"}
          </div>
          {data.text ? (
            <div className="mt-1 text-[13px] italic text-white/70">„{data.text}“</div>
          ) : null}
          {fertig ? (
            <div className={`mt-2 text-[13px] ${stand === "ja" ? "text-emerald-300" : "text-white/60"}`}>
              {stand === "ja" ? `Erlaubt: ${minuten} Minuten mehr.` : "Abgelehnt."}
              {hinweis ? <div className="mt-1 text-white/45">{hinweis}</div> : null}
            </div>
          ) : (
            <>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {[15, 30, 60, 90].map((m) => (
                  <button
                    key={m}
                    onClick={() => setMinuten(m)}
                    disabled={stand === "laeuft"}
                    className={`rounded-full px-3 py-1 text-[12.5px] font-medium transition ${
                      minuten === m ? "bg-gold text-black" : "bg-white/8 text-white/75 hover:bg-white/15"
                    }`}
                  >
                    {m} Min.
                  </button>
                ))}
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => void antworten(true)}
                  disabled={stand === "laeuft"}
                  className="flex-1 rounded-xl bg-emerald-500/90 px-3 py-2 text-[13px] font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-60"
                >
                  {stand === "laeuft" ? "Sende …" : `Erlauben · ${minuten} Min.`}
                </button>
                <button
                  onClick={() => void antworten(false)}
                  disabled={stand === "laeuft"}
                  className="rounded-xl bg-white/10 px-3 py-2 text-[13px] font-medium text-white/80 transition hover:bg-white/15 disabled:opacity-60"
                >
                  Ablehnen
                </button>
              </div>
            </>
          )}
          {fehler ? <div className="mt-2 text-[12.5px] text-red-300">{fehler}</div> : null}
        </div>
      </div>
    </motion.div>
  );
}
