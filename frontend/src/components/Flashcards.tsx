import { useEffect, useState } from "react";
import {
  Deck,
  NextCard,
  answerCard,
  deleteDeck,
  generateDeck,
  getDecks,
  nextCard,
} from "../lib/api";

export default function Flashcards({ onClose }: { onClose: () => void }) {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState<Deck | null>(null);
  const [card, setCard] = useState<NextCard | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<{ richtig: boolean; loesung: string; feedback: string } | null>(null);

  const load = () => void getDecks().then(setDecks);
  useEffect(load, []);

  const create = async () => {
    if (!topic.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await generateDeck(topic.trim());
      setTopic("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const open = async (deck: Deck) => {
    setActive(deck);
    setResult(null);
    setAnswer("");
    setCard(await nextCard(deck.id));
  };

  const submit = async () => {
    if (!active || !card?.id || busy) return;
    setBusy(true);
    try {
      setResult(await answerCard(active.id, card.id, answer));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const cont = async () => {
    if (!active) return;
    setResult(null);
    setAnswer("");
    setCard(await nextCard(active.id));
    load();
  };

  const remove = async (id: string) => {
    await deleteDeck(id);
    load();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[94vw] h-[600px] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎴</span>
            <span className="text-[14px] text-white/90">Lern-Karteikarten</span>
            {active && <button onClick={() => { setActive(null); setCard(null); load(); }} className="text-[11px] text-gold/70 hover:text-gold">← Decks</button>}
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>

        {!active ? (
          <div className="p-4 overflow-y-auto">
            <div className="flex gap-2">
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void create()}
                placeholder="Thema oder Text einfügen … (z. B. Photosynthese)"
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
              />
              <button
                onClick={() => void create()}
                disabled={busy || !topic.trim()}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
              >
                {busy ? "…" : "Karten machen"}
              </button>
            </div>
            {error && <div className="mt-3 px-3 py-2 rounded-xl border border-red-400/30 bg-red-400/10 text-[12.5px] text-red-200">{error}</div>}
            <div className="mt-4 space-y-2">
              {decks.length === 0 && <div className="text-center text-[12.5px] text-white/30 py-8">Noch keine Decks. Gib ein Thema ein und Jon macht Karten daraus.</div>}
              {decks.map((d) => (
                <div key={d.id} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                  <button onClick={() => void open(d)} className="flex-1 text-left">
                    <div className="text-[13.5px] font-semibold text-white/90">{d.titel}</div>
                    <div className="text-[11.5px] text-white/40">{d.anzahl} Karten{d.faellig > 0 && <span className="text-gold/70"> · {d.faellig} fällig</span>}</div>
                  </button>
                  <button onClick={() => void open(d)} className="px-3 py-1.5 rounded-lg border border-gold/30 bg-gold/10 text-gold/90 text-[12px] font-semibold hover:bg-gold/20 transition">Üben</button>
                  <button onClick={() => void remove(d.id)} className="text-white/30 hover:text-red-300 text-[13px]">✕</button>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col p-5 min-h-0">
            {card?.done ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <div className="text-4xl mb-3">🎉</div>
                <div className="text-[15px] text-white/85">Alles wiederholt! Für jetzt bist du durch.</div>
                <button onClick={() => { setActive(null); setCard(null); load(); }} className="mt-5 px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-white/70 text-[12.5px] hover:bg-white/10">Zurück zu den Decks</button>
              </div>
            ) : card ? (
              <>
                <div className="text-[11px] uppercase tracking-wider text-white/40 mb-2">{active.titel}{card.offen ? ` · ${card.offen} offen` : ""}</div>
                <div className="flex-1 flex flex-col items-center justify-center text-center">
                  <div className="text-[17px] text-white/90 leading-relaxed max-w-md mb-5">{card.frage}</div>
                  {!result ? (
                    <>
                      <input
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && void submit()}
                        autoFocus
                        placeholder="Deine Antwort …"
                        className="w-full max-w-sm bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 text-center placeholder-white/25 outline-none focus:border-gold/40"
                      />
                      <button onClick={() => void submit()} disabled={busy} className="mt-3 px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold disabled:opacity-40 hover:brightness-110 transition">
                        {busy ? "Prüfe …" : "Prüfen"}
                      </button>
                      <button onClick={() => void submit()} className="mt-2 text-[11.5px] text-white/40 hover:text-white/70">Weiß ich nicht — Lösung zeigen</button>
                    </>
                  ) : (
                    <div className="w-full max-w-md">
                      <div className={`px-4 py-3 rounded-xl border ${result.richtig ? "border-emerald-400/40 bg-emerald-400/10" : "border-amber-400/40 bg-amber-400/10"}`}>
                        <div className={`text-[13.5px] font-semibold ${result.richtig ? "text-emerald-300" : "text-amber-300"}`}>
                          {result.richtig ? "Richtig! ✓" : "Nicht ganz"}
                        </div>
                        <div className="text-[13px] text-white/85 mt-1">Lösung: {result.loesung}</div>
                        {result.feedback && <div className="text-[12px] text-white/55 mt-1">{result.feedback}</div>}
                      </div>
                      <button onClick={() => void cont()} className="mt-4 px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold hover:brightness-110 transition">Nächste Karte ▶</button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-white/40 text-[13px]">Lade …</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
