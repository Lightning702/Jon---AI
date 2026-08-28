import { useState } from "react";
import { motion } from "framer-motion";
import type { ConversationSummary } from "../lib/api";
import { useT } from "../hooks/useT";

interface Props {
  conversations: ConversationSummary[];
  activeId: string | null;
  version: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  open?: boolean;
  onClose?: () => void;
}

export default function Sidebar({
  conversations,
  activeId,
  version,
  onSelect,
  onNew,
  onDelete,
  open = false,
  onClose,
}: Props) {
  const { t } = useT();
  const [query, setQuery] = useState("");
  const filtered = query.trim()
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(query.trim().toLowerCase())
      )
    : conversations;
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`glass-strong flex flex-col border-r border-white/10 fixed inset-y-0 left-0 z-50 w-[84vw] max-w-xs transition-transform duration-300 md:static md:z-auto md:w-72 md:max-w-none md:h-full md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
      <div className="p-4 pb-2 flex items-center gap-2">
        <button
          onClick={onClose}
          className="no-drag md:hidden flex items-center justify-center w-10 h-10 shrink-0 rounded-xl border border-white/10 bg-white/5 text-white/60"
          aria-label="Menü schließen"
        >
          ✕
        </button>
        <button
          onClick={onNew}
          className="no-drag w-full py-3 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold hover:brightness-110 transition"
        >
          {t("new_chat")}
        </button>
      </div>
      <div className="px-4 pb-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("search_history")}
          className="no-drag w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-[16px] md:text-[12px] text-white/80 placeholder-white/30 outline-none focus:border-gold/40"
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
            onClick={() => {
              onSelect(c.id);
              onClose?.();
            }}
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
              className="opacity-70 md:opacity-0 md:group-hover:opacity-100 text-white/40 hover:text-red-400 px-2 py-1 transition"
            >
              &#10005;
            </button>
          </motion.div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-white/30 text-sm mt-8">
            {query.trim() ? "—" : t("no_conversations")}
          </p>
        )}
      </div>
      <div className="p-4 safe-bottom text-[11px] text-white/30 border-t border-white/10">
        {version ? `Jon Desktop v${version}` : "Jon Desktop"}
      </div>
      </aside>
    </>
  );
}
