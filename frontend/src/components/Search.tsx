import { useEffect, useRef, useState } from "react";
import { SearchGroup, universalSearch } from "../lib/api";

const ICON: Record<string, string> = {
  chat: "💬",
  memory: "🧠",
  journal: "📔",
  knowledge: "📚",
};

export default function Search({
  onOpenConversation,
  onClose,
}: {
  onOpenConversation: (id: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [groups, setGroups] = useState<SearchGroup[]>([]);
  const [busy, setBusy] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => inputRef.current?.focus(), []);

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    if (query.trim().length < 2) {
      setGroups([]);
      setSearched(false);
      return;
    }
    timer.current = window.setTimeout(async () => {
      setBusy(true);
      try {
        setGroups(await universalSearch(query.trim()));
        setSearched(true);
      } finally {
        setBusy(false);
      }
    }, 300);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [query]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-[12vh]" onClick={onClose}>
      <div className="glass rounded-2xl border border-white/15 w-[620px] max-w-[95vw] max-h-[72vh] flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-4 h-14 border-b border-white/10 shrink-0">
          <span className="text-[16px]">🔎</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && onClose()}
            placeholder="Alles durchsuchen — Unterhaltungen, Gedächtnis, Tagebuch, Wissen …"
            className="flex-1 bg-transparent text-[14px] text-white/90 placeholder-white/30 outline-none"
          />
          {busy && <span className="text-[11px] text-white/40">sucht …</span>}
          <button onClick={onClose} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {searched && groups.length === 0 && !busy && (
            <div className="text-center text-[12.5px] text-white/30 py-8">Nichts gefunden zu „{query}“.</div>
          )}
          {groups.map((g) => (
            <div key={g.kind} className="mb-3">
              <div className="text-[10.5px] uppercase tracking-wider text-white/40 px-1 mb-1">{ICON[g.kind] ?? "•"} {g.label}</div>
              <div className="space-y-1">
                {g.items.map((it, i) => {
                  const clickable = g.kind === "chat" && it.id;
                  return (
                    <button
                      key={i}
                      onClick={() => { if (clickable) { onOpenConversation(it.id!); onClose(); } }}
                      className={`w-full text-left rounded-xl border border-white/10 bg-white/5 px-3 py-2 transition ${clickable ? "hover:bg-white/10 hover:border-gold/30 cursor-pointer" : "cursor-default"}`}
                    >
                      {it.title && <div className="text-[12.5px] font-semibold text-white/85 truncate">{it.title}</div>}
                      <div className="text-[12px] text-white/55 leading-snug line-clamp-2">{it.snippet}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
