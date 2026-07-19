import { useEffect, useState } from "react";
import {
  ClipboardEntry,
  clearClipboardHistory,
  deleteClipboardEntry,
  getClipboardHistory,
  restoreClipboardEntry,
} from "../lib/api";

interface SmartAction {
  label: string;
  run: () => void;
}

function detectActions(
  text: string,
  onAsk?: (text: string) => void
): SmartAction[] {
  const t = text.trim();
  const actions: SmartAction[] = [];
  const urlMatch = t.match(/\bhttps?:\/\/\S+/i) || t.match(/\bwww\.\S+\.\S+/i);
  const email = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(t);
  const phone = /^[+0][\d\s/()-]{6,}$/.test(t);
  const iban = t.replace(/\s/g, "").match(/^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/i);
  const address = /\b\d{4,5}\s+[A-Za-zÄÖÜäöüß]/.test(t) && /\d/.test(t);
  const strongCode = /=>|\bfunction\b|\bconst\b|\bimport\b|\bdef\b|\{\s*\n/.test(t);
  const weakCode =
    /[{};]/.test(t) && (t.includes("\n") || t.length > 40);
  const looksCode = strongCode || weakCode;

  if (urlMatch) {
    const url = urlMatch[0].startsWith("http")
      ? urlMatch[0]
      : "https://" + urlMatch[0];
    actions.push({ label: "🌐 Öffnen", run: () => window.open(url, "_blank") });
  }
  if (email) {
    actions.push({
      label: "✉️ Mail schreiben",
      run: () => window.open("mailto:" + t, "_blank"),
    });
  }
  if (phone) {
    const digits = t.replace(/[^\d+]/g, "");
    actions.push({
      label: "📞 Anrufen",
      run: () => window.open("tel:" + digits, "_blank"),
    });
    actions.push({
      label: "💬 WhatsApp",
      run: () =>
        window.open("https://wa.me/" + digits.replace(/\D/g, ""), "_blank"),
    });
  }
  if (iban && onAsk) {
    actions.push({
      label: "🧠 Merken",
      run: () => onAsk("Merk dir diese IBAN dauerhaft: " + t),
    });
  }
  if (address && !urlMatch) {
    actions.push({
      label: "🗺️ In Maps öffnen",
      run: () =>
        window.open(
          "https://www.google.com/maps/search/?api=1&query=" +
            encodeURIComponent(t),
          "_blank"
        ),
    });
  }
  if (looksCode && onAsk) {
    actions.push({
      label: "💡 Erklären",
      run: () => onAsk("Erkläre mir diesen Code kurz und verständlich:\n\n" + t),
    });
  }
  if (!looksCode && !iban && onAsk && t.length > 0 && t.length < 2000) {
    actions.push({ label: "🤖 An Jon", run: () => onAsk(t) });
  }
  return actions;
}

export default function ClipboardPanel({
  onClose,
  onAsk,
}: {
  onClose: () => void;
  onAsk?: (text: string) => void;
}) {
  const [entries, setEntries] = useState<ClipboardEntry[]>([]);
  const [query, setQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const refresh = async (q = query) => {
    setEntries(await getClipboardHistory(q));
  };

  useEffect(() => {
    void refresh("");
  }, []);

  const restore = async (id: string) => {
    const ok = await restoreClipboardEntry(id);
    if (ok) {
      setCopiedId(id);
      window.setTimeout(() => setCopiedId(null), 1500);
    }
  };

  const remove = async (id: string) => {
    await deleteClipboardEntry(id);
    await refresh();
  };

  const clearAll = async () => {
    await clearClipboardHistory();
    await refresh();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[92vw] max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-white/90 font-semibold">📋 Clipboard-Historie</div>
            <div className="text-[11px] text-white/40">
              Die letzten 50 kopierten Einträge — nur lokal gespeichert.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="px-5 py-3 flex items-center gap-2">
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              void refresh(e.target.value);
            }}
            placeholder="Suchen …"
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
          />
          <button
            onClick={clearAll}
            className="text-[11px] px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-white/50 hover:text-red-300 hover:border-red-400/40 transition-colors"
          >
            Alles löschen
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 pb-4 space-y-2">
          {entries.length === 0 && (
            <div className="text-white/35 text-[13px] text-center py-8">
              Noch keine Einträge. Kopiere etwas — Jon merkt es sich.
            </div>
          )}
          {entries.map((e) => (
            <div
              key={e.id}
              className="group rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 hover:border-gold/30 transition-colors"
            >
              <div className="text-[12px] text-white/80 whitespace-pre-wrap break-words max-h-20 overflow-hidden">
                {e.text.length > 300 ? e.text.slice(0, 300) + "…" : e.text}
              </div>
              <div className="flex flex-wrap items-center gap-1.5 mt-2">
                {detectActions(e.text, onAsk).map((a) => (
                  <button
                    key={a.label}
                    onClick={() => {
                      a.run();
                      if (a.label === "💡 Erklären" || a.label === "🤖 An Jon" || a.label === "🧠 Merken")
                        onClose();
                    }}
                    className="text-[11px] px-2 py-1 rounded-lg border border-gold/30 bg-gold/10 text-gold/90 hover:bg-gold/20 transition-colors"
                  >
                    {a.label}
                  </button>
                ))}
              </div>
              <div className="flex items-center justify-between mt-1.5">
                <span className="text-[10px] text-white/30">
                  {new Date(e.created_at).toLocaleString("de-DE")}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => restore(e.id)}
                    className="text-[11px] text-gold/80 hover:text-gold transition-colors"
                  >
                    {copiedId === e.id ? "✓ Kopiert" : "Wieder kopieren"}
                  </button>
                  <button
                    onClick={() => remove(e.id)}
                    className="text-[11px] text-white/30 hover:text-red-300 transition-colors"
                  >
                    Löschen
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
