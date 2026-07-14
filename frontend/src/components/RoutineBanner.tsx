import { useEffect, useState } from "react";
import {
  RoutineSuggestion,
  acceptRoutine,
  dismissRoutine,
  getRoutineSuggestions,
} from "../lib/api";

export default function RoutineBanner() {
  const [suggestion, setSuggestion] = useState<RoutineSuggestion | null>(null);
  const [done, setDone] = useState("");

  const load = async () => {
    const list = await getRoutineSuggestions();
    setSuggestion(list[0] ?? null);
  };

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 120000);
    return () => window.clearInterval(timer);
  }, []);

  if (done) {
    return (
      <div className="mx-auto max-w-2xl mb-3 px-4 py-2.5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 text-[12.5px] text-emerald-200">
        {done}
      </div>
    );
  }

  if (!suggestion) return null;

  const accept = async () => {
    await acceptRoutine(suggestion.id);
    setDone(
      `Erledigt — ich öffne ${suggestion.app} künftig ${suggestion.slot} automatisch um ${suggestion.time}. Ändern kannst du das unter Automationen.`
    );
    setSuggestion(null);
  };

  const dismiss = async () => {
    await dismissRoutine(suggestion.id);
    setSuggestion(null);
  };

  return (
    <div className="mx-auto max-w-2xl mb-3 px-4 py-3 rounded-xl border border-gold/25 bg-gold/10 flex items-center gap-3">
      <span className="text-lg shrink-0">🔁</span>
      <div className="flex-1 text-[12.5px] text-white/85 leading-snug">
        {suggestion.text}
      </div>
      <div className="flex gap-1.5 shrink-0">
        <button
          onClick={() => void accept()}
          className="px-3 py-1.5 rounded-lg bg-gold/20 border border-gold/40 text-gold text-[12px] font-semibold hover:bg-gold/30 transition"
        >
          Ja, übernehmen
        </button>
        <button
          onClick={() => void dismiss()}
          className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 text-white/50 text-[12px] hover:bg-white/10 transition"
        >
          Nein
        </button>
      </div>
    </div>
  );
}
