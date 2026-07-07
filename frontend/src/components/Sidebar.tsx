import { useState } from "react";
import { motion } from "framer-motion";
import type { ConversationSummary } from "../lib/api";

interface Props {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  const [query, setQuery] = useState("");
  const filtered = query.trim()
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(query.trim().toLowerCase())
      )
    : conversations;
  return (
    <aside className="glass-strong w-72 flex flex-col h-full border-r border-white/10">
      <div className="p-4 pb-2">
        <button
          onClick={onNew}
          className="no-drag w-full py-3 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold hover:brightness-110 transition"
        >
          + Neue Unterhaltung
        </button>
      </div>
      <div className="px-4 pb-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Verlauf durchsuchen …"
          className="no-drag w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-[12px] text-white/80 placeholder-white/30 outline-none focus:border-gold/40"
        />
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {filtered.map((c) => (
          <motion.div
            key={c.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className={`group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition ${
              activeId === c.id
                ? "bg-gold/15 border border-gold/30"
                : "hover:bg-white/5 border border-transparent"
            }`}
            onClick={() => onSelect(c.id)}
          >
            <div className="min-w-0">
              <p className="text-sm truncate">{c.title}</p>
              <p className="text-[11px] text-white/40 truncate">
                {c.provider} · {c.model}
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
              className="opacity-0 group-hover:opacity-100 text-white/40 hover:text-red-400 px-1 transition"
            >
              &#10005;
            </button>
          </motion.div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-white/30 text-sm mt-8">
            {query.trim() ? "Keine Treffer" : "Noch keine Unterhaltungen"}
          </p>
        )}
      </div>
      <div className="p-4 text-[11px] text-white/30 border-t border-white/10">
        Jon Desktop v1.0.0
      </div>
    </aside>
  );
}
