import { useEffect, useRef, useState } from "react";
import { Recipe as RecipeData, RecipeIdea, recipeMake, recipeSuggest } from "../lib/api";
import { speak, stopSpeaking } from "../lib/tts";

export default function Recipe({ onClose }: { onClose: () => void }) {
  const [input, setInput] = useState("");
  const [ideas, setIdeas] = useState<RecipeIdea[]>([]);
  const [recipe, setRecipe] = useState<RecipeData | null>(null);
  const [step, setStep] = useState(-1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => () => { stopSpeaking(); if (timerRef.current) window.clearInterval(timerRef.current); }, []);

  const suggest = async () => {
    if (!input.trim() || busy) return;
    setBusy(true);
    setError("");
    setIdeas([]);
    setRecipe(null);
    try {
      setIdeas(await recipeSuggest(input.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const cook = async (dish: string) => {
    setBusy(true);
    setError("");
    try {
      const r = await recipeMake(dish);
      setRecipe(r);
      setStep(-1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const goTo = (i: number) => {
    if (!recipe || i < 0 || i >= recipe.schritte.length) return;
    setStep(i);
    stopSpeaking();
    void speak(`Schritt ${i + 1}. ${recipe.schritte[i]}`);
  };

  const startTimer = (secs: number) => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    setTimer(secs);
    timerRef.current = window.setInterval(() => {
      setTimer((t) => {
        if (t === null) return null;
        if (t <= 1) {
          if (timerRef.current) window.clearInterval(timerRef.current);
          void speak("Timer abgelaufen!");
          return null;
        }
        return t - 1;
      });
    }, 1000);
  };

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[600px] max-w-[95vw] h-[640px] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🍳</span>
            <span className="text-[14px] text-white/90">Kochassistent</span>
            <span className="text-[11px] text-white/35">Jon liest dir vor — Hände frei</span>
          </div>
          <button onClick={() => { stopSpeaking(); onClose(); }} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>

        {!recipe ? (
          <div className="p-4 overflow-y-auto">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void suggest()}
                placeholder="Was hast du da? z. B. Eier, Nudeln, Tomaten …"
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
              />
              <button
                onClick={() => void suggest()}
                disabled={busy || !input.trim()}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
              >
                {busy && !ideas.length ? "…" : "Vorschläge"}
              </button>
            </div>
            {error && <div className="mt-3 px-3 py-2 rounded-xl border border-red-400/30 bg-red-400/10 text-[12.5px] text-red-200">{error}</div>}
            <div className="mt-4 space-y-2">
              {ideas.map((idea) => (
                <button
                  key={idea.name}
                  onClick={() => void cook(idea.name)}
                  disabled={busy}
                  className="w-full text-left rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-gold/30 px-4 py-3 transition disabled:opacity-50"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-semibold text-white/90 flex-1">{idea.name}</span>
                    <span className="text-[11px] text-gold/70">{idea.dauer}</span>
                    <span className="text-[11px] text-white/40">{idea.schwierigkeit}</span>
                  </div>
                  <div className="text-[12px] text-white/50 mt-0.5">{idea.beschreibung}</div>
                </button>
              ))}
              {busy && ideas.length > 0 && <div className="text-center text-[12px] text-gold/70 py-2">Jon schreibt das Rezept …</div>}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            <div className="px-5 pt-4 pb-2 shrink-0">
              <div className="text-[16px] font-semibold gold-text">{recipe.name}</div>
              <div className="text-[11.5px] text-white/40">{recipe.portionen} Portionen</div>
            </div>
            {step < 0 ? (
              <div className="flex-1 overflow-y-auto px-5 pb-3">
                <div className="text-[11px] uppercase tracking-wider text-white/40 mb-1.5">Zutaten</div>
                <ul className="space-y-1 mb-4">
                  {recipe.zutaten.map((z, i) => (
                    <li key={i} className="text-[13px] text-white/80 flex gap-2"><span className="text-gold/60">•</span>{z}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
                <div className="text-[11px] uppercase tracking-wider text-gold/60 mb-3">Schritt {step + 1} von {recipe.schritte.length}</div>
                <div className="text-[18px] text-white/90 leading-relaxed max-w-md">{recipe.schritte[step]}</div>
                <div className="flex gap-2 mt-5">
                  <button onClick={() => startTimer(60)} className="text-[11.5px] px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10">⏱ 1 min</button>
                  <button onClick={() => startTimer(300)} className="text-[11.5px] px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10">⏱ 5 min</button>
                  <button onClick={() => startTimer(600)} className="text-[11.5px] px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10">⏱ 10 min</button>
                </div>
                {timer !== null && <div className="mt-3 text-[22px] font-semibold text-gold">{fmt(timer)}</div>}
              </div>
            )}
            <div className="px-5 py-3 border-t border-white/10 flex gap-2 shrink-0">
              <button
                onClick={() => (step < 0 ? goTo(0) : goTo(step - 1))}
                disabled={step <= 0 && step >= 0}
                className="px-4 py-2.5 rounded-xl border border-white/10 bg-white/5 text-white/70 text-[13px] font-semibold hover:bg-white/10 disabled:opacity-30 transition"
              >
                {step < 0 ? "Los geht’s ▶" : "◀ Zurück"}
              </button>
              {step >= 0 && (
                <button
                  onClick={() => goTo(step + 1)}
                  disabled={step >= recipe.schritte.length - 1}
                  className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
                >
                  {step >= recipe.schritte.length - 1 ? "Fertig 🎉" : "Weiter ▶ (vorlesen)"}
                </button>
              )}
              <button onClick={() => { stopSpeaking(); setRecipe(null); }} className="px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 text-white/50 text-[12.5px] hover:bg-white/10 transition">Neu</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
