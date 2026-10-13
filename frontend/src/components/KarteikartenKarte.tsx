import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, Check, Eye, GraduationCap, LoaderCircle, RotateCcw, Send, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { answerCard, Deck, nextCard, NextCard } from "../lib/api";

export interface KarteikartenDaten {
  aktion: "lernen" | "liste";
  deck?: string;
  titel?: string;
  anzahl?: number;
  faellig?: number;
  decks?: Deck[];
}

type Ergebnis = { richtig: boolean; loesung: string; feedback: string };

function Lernen({ deck, titel, anzahl }: { deck: string; titel: string; anzahl: number }) {
  const [karte, setKarte] = useState<NextCard | null>(null);
  const [eingabe, setEingabe] = useState("");
  const [ergebnis, setErgebnis] = useState<Ergebnis | null>(null);
  const [busy, setBusy] = useState(false);
  const [fehler, setFehler] = useState("");
  const [punkte, setPunkte] = useState({ richtig: 0, gesamt: 0 });

  const laden = useCallback(async () => {
    setBusy(true);
    setFehler("");
    try {
      setKarte(await nextCard(deck));
      setErgebnis(null);
      setEingabe("");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Karte nicht geladen.");
    } finally {
      setBusy(false);
    }
  }, [deck]);

  useEffect(() => {
    void laden();
  }, [laden]);

  async function pruefen(text: string) {
    if (!karte?.id) return;
    setBusy(true);
    setFehler("");
    try {
      const r = await answerCard(deck, karte.id, text);
      setErgebnis(r);
      setPunkte((p) => ({ richtig: p.richtig + (r.richtig ? 1 : 0), gesamt: p.gesamt + 1 }));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Antwort nicht geprüft.");
    } finally {
      setBusy(false);
    }
  }

  const offen = karte?.offen ?? anzahl;
  return (
    <div className="mt-3">
      <div className="mb-2 flex items-center justify-between text-[12px] text-white/50">
        <span>{titel}</span>
        <span>
          {punkte.gesamt ? `${punkte.richtig}/${punkte.gesamt} richtig · ` : ""}
          {offen} fällig
        </span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-white/10">
        <motion.div className="h-full bg-gold" animate={{ width: `${anzahl ? Math.min(100, ((anzahl - offen) / anzahl) * 100) : 0}%` }} />
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={karte?.id ?? "leer"}
          initial={{ rotateY: -70, opacity: 0 }}
          animate={{ rotateY: 0, opacity: 1 }}
          exit={{ rotateY: 70, opacity: 0 }}
          transition={{ duration: 0.32, ease: [0.2, 0.8, 0.2, 1] }}
          className="mt-3 rounded-xl border border-white/10 bg-black/35 p-4"
          style={{ transformPerspective: 900 }}
        >
          {busy && !karte ? (
            <div className="flex items-center gap-2 text-[13px] text-white/60">
              <LoaderCircle size={14} className="animate-spin" />
              Lade Karte …
            </div>
          ) : karte?.done ? (
            <div className="text-[13.5px] text-white/80">Alle Karten sind gelernt. Jon fragt dich später wieder ab.</div>
          ) : (
            <>
              <div className="text-[11px] uppercase tracking-[0.14em] text-gold/80">Frage</div>
              <div className="mt-1 whitespace-pre-wrap text-[15px] font-medium text-white [overflow-wrap:anywhere]">{karte?.frage}</div>
              {ergebnis ? (
                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-3 border-t border-white/10 pt-3">
                  <div className={`flex items-center gap-1.5 text-[12.5px] font-semibold ${ergebnis.richtig ? "text-emerald-300" : "text-amber-300"}`}>
                    {ergebnis.richtig ? <Check size={14} /> : <X size={14} />}
                    {ergebnis.richtig ? "Richtig" : eingabe ? "Noch nicht ganz" : "Lösung"}
                  </div>
                  <div className="mt-1 whitespace-pre-wrap text-[14px] text-white/85 [overflow-wrap:anywhere]">{ergebnis.loesung}</div>
                  {ergebnis.feedback ? <div className="mt-1 text-[12.5px] text-white/55">{ergebnis.feedback}</div> : null}
                </motion.div>
              ) : null}
            </>
          )}
        </motion.div>
      </AnimatePresence>
      {!karte?.done && karte?.id ? (
        ergebnis ? (
          <button onClick={() => void laden()} className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-lg bg-gold py-2 text-[13px] font-semibold text-black transition hover:brightness-110">
            <RotateCcw size={14} />
            Nächste Karte
          </button>
        ) : (
          <form
            className="mt-2.5 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (eingabe.trim()) void pruefen(eingabe.trim());
            }}
          >
            <input
              value={eingabe}
              onChange={(e) => setEingabe(e.target.value)}
              placeholder="Deine Antwort …"
              className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-[13.5px] text-white outline-none placeholder:text-white/35 focus:border-gold/50"
            />
            <button type="submit" disabled={busy || !eingabe.trim()} className="flex items-center justify-center rounded-lg bg-gold px-3 text-black transition hover:brightness-110 disabled:opacity-40" aria-label="Prüfen">
              {busy ? <LoaderCircle size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
            <button type="button" disabled={busy} onClick={() => void pruefen("")} className="flex items-center gap-1 rounded-lg bg-white/8 px-3 text-[12.5px] text-white/75 transition hover:bg-white/15" aria-label="Aufdecken">
              <Eye size={14} />
              Aufdecken
            </button>
          </form>
        )
      ) : null}
      {fehler ? <div className="mt-2 text-[12.5px] text-red-300">{fehler}</div> : null}
    </div>
  );
}

export default function KarteikartenKarte({ data }: { data: KarteikartenDaten }) {
  const [gewaehlt, setGewaehlt] = useState<{ deck: string; titel: string; anzahl: number } | null>(
    data.aktion === "lernen" && data.deck ? { deck: data.deck, titel: data.titel || "Karteikarten", anzahl: data.anzahl || 0 } : null
  );
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      className="w-full max-w-[480px] overflow-hidden rounded-2xl border border-gold/25 bg-gradient-to-br from-[#1b2340]/80 to-black/40 p-4"
    >
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-gold/15 text-gold">
          <GraduationCap size={20} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-white">{gewaehlt ? gewaehlt.titel : "Deine Kartenstapel"}</div>
          <div className="text-[12.5px] text-white/55">{gewaehlt ? `${gewaehlt.anzahl} Karten · Wiederholung nach Lernplan` : `${data.decks?.length ?? 0} Stapel`}</div>
        </div>
      </div>
      {gewaehlt ? (
        <Lernen deck={gewaehlt.deck} titel={gewaehlt.titel} anzahl={gewaehlt.anzahl} />
      ) : (
        <div className="mt-3 space-y-1.5">
          {(data.decks ?? []).length === 0 ? <div className="text-[13px] text-white/60">Noch keine Stapel. Sag Jon einfach, was du lernen willst.</div> : null}
          {(data.decks ?? []).map((d) => (
            <button
              key={d.id}
              onClick={() => setGewaehlt({ deck: d.id, titel: d.titel, anzahl: d.anzahl })}
              className="flex w-full items-center gap-2.5 rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-left transition hover:border-gold/40"
            >
              <BookOpen size={15} className="flex-none text-gold" />
              <span className="min-w-0 flex-1 truncate text-[13.5px] text-white">{d.titel}</span>
              <span className="text-[11.5px] text-white/50">{d.faellig ? `${d.faellig} fällig` : `${d.anzahl} Karten`}</span>
            </button>
          ))}
        </div>
      )}
    </motion.div>
  );
}
