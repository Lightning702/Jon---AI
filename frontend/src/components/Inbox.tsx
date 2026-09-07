import { useCallback, useEffect, useState } from "react";
import {
  InboxAction,
  InboxAnalysis,
  InboxFeed,
  InboxItem,
  analyzeInboxItem,
  getInbox,
  markInboxSeen,
  runInboxAction,
} from "../lib/api";

const ICON: Record<string, string> = {
  email: "✉️",
  termin: "📅",
  aufgabe: "✅",
  projekt: "📁",
  system: "⚙️",
};

const TYPE_LABEL: Record<string, string> = {
  termin: "Termin",
  terminaenderung: "Terminänderung",
  absage: "Absage",
  aufgabe: "Aufgabe",
  deadline: "Deadline",
  erinnerung: "Erinnerung",
  info: "Information",
  bestellung: "Bestellung",
  lieferung: "Lieferung",
  projektupdate: "Projektupdate",
  anfrage: "Anfrage",
  antwort_noetig: "Antwort nötig",
};

function when(value: string): string {
  if (!value) return "";
  const stamp = Date.parse(value);
  if (Number.isNaN(stamp)) return value;
  const date = new Date(stamp);
  const diff = Date.now() - stamp;
  if (diff >= 0 && diff < 3600000) return `vor ${Math.max(1, Math.round(diff / 60000))} Min.`;
  if (diff >= 0 && diff < 86400000) return `vor ${Math.round(diff / 3600000)} Std.`;
  return date.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Inbox({
  onClose,
  onAsk,
  onOpenProject,
}: {
  onClose: () => void;
  onAsk?: (text: string) => void;
  onOpenProject?: (root: string) => void;
}) {
  const [feed, setFeed] = useState<InboxFeed | null>(null);
  const [category, setCategory] = useState("alle");
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, InboxAnalysis>>({});
  const [confirm, setConfirm] = useState<{ id: string; action: InboxAction } | null>(
    null
  );
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const data = await getInbox();
      setFeed(data);
      const known: Record<string, InboxAnalysis> = {};
      for (const item of data.eintraege) {
        if (item.analyse) known[item.id] = item.analyse;
      }
      setAnalysis((current) => ({ ...known, ...current }));
    } catch {
      setError("Die Inbox ist gerade nicht erreichbar.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const analyze = async (item: InboxItem, force = false) => {
    setAnalyzing(item.id);
    setNote("");
    setError("");
    try {
      const result = await analyzeInboxItem(item.id, {
        text: item.kategorie === "email" ? "" : `${item.titel}\n${item.text}`,
        betreff: item.betreff ?? item.titel,
        von: item.von ?? item.untertitel,
        force,
      });
      setAnalysis((current) => ({ ...current, [item.id]: result }));
    } catch (exception) {
      setError((exception as Error).message.slice(0, 240));
    } finally {
      setAnalyzing(null);
    }
  };

  const apply = async (action: InboxAction) => {
    setConfirm(null);
    setNote("");
    try {
      await runInboxAction(action.typ, action.payload);
      setNote(`${action.label} — erledigt.`);
      await load();
    } catch (exception) {
      setError((exception as Error).message.slice(0, 240));
    }
  };

  const items = (feed?.eintraege ?? []).filter((item) => {
    if (category === "alle") return true;
    if (category === "wichtig") return item.wichtig;
    return item.kategorie === category;
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-[8vh]"
      onClick={onClose}
    >
      <div
        className="glass rounded-2xl border border-white/15 w-[720px] max-w-[95vw] max-h-[82vh] flex flex-col overflow-hidden"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-4 h-14 border-b border-white/10 shrink-0">
          <span className="text-[16px]">📥</span>
          <div className="flex-1 min-w-0">
            <div className="text-[14px] font-semibold text-white/90">
              Intelligente Inbox
            </div>
            <div className="text-[11px] text-white/40 truncate">
              {feed
                ? `${feed.zaehler.alle ?? 0} Einträge · ${feed.zaehler.wichtig ?? 0} wichtig`
                : "lädt …"}
            </div>
          </div>
          <button
            onClick={() => void load()}
            disabled={busy}
            className="text-[11.5px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 disabled:opacity-40"
          >
            {busy ? "…" : "↻"}
          </button>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
          >
            ✕
          </button>
        </div>

        <div className="flex gap-1 px-3 py-2 border-b border-white/10 overflow-x-auto shrink-0">
          {(feed?.kategorien ?? []).map((entry) => (
            <button
              key={entry.id}
              onClick={() => setCategory(entry.id)}
              className={`text-[11.5px] px-2.5 py-1 rounded-lg whitespace-nowrap border transition ${
                category === entry.id
                  ? "bg-gold/15 border-gold/30 text-gold"
                  : "bg-white/5 border-white/10 text-white/60 hover:bg-white/10"
              }`}
            >
              {entry.label}
              {feed?.zaehler[entry.id] ? ` ${feed.zaehler[entry.id]}` : ""}
            </button>
          ))}
        </div>

        {(error || feed?.mail_fehler) && (
          <div className="px-4 py-2 text-[11.5px] text-amber-300/85 border-b border-white/10">
            {error || feed?.mail_fehler}
          </div>
        )}
        {note && (
          <div className="px-4 py-2 text-[11.5px] text-emerald-300/85 border-b border-white/10">
            {note}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {items.length === 0 && !busy && (
            <div className="text-center text-[12.5px] text-white/30 py-10">
              Hier ist gerade nichts, worum du dich kümmern müsstest.
            </div>
          )}
          {items.map((item) => {
            const open = openId === item.id;
            const found = analysis[item.id];
            return (
              <div
                key={item.id}
                className={`rounded-xl border transition ${
                  item.wichtig
                    ? "border-gold/25 bg-gold/[0.06]"
                    : "border-white/10 bg-white/5"
                }`}
              >
                <button
                  onClick={() => {
                    setOpenId(open ? null : item.id);
                    if (!open && !item.gesehen) void markInboxSeen(item.id);
                  }}
                  className="w-full text-left px-3 py-2.5 flex items-start gap-2.5"
                >
                  <span className="text-[15px] leading-5">
                    {ICON[item.kategorie] ?? "•"}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="text-[12.5px] font-semibold text-white/85 truncate">
                        {item.titel || "(ohne Betreff)"}
                      </span>
                      {found && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/60 whitespace-nowrap">
                          {TYPE_LABEL[found.typ] ?? found.typ}
                        </span>
                      )}
                    </span>
                    <span className="block text-[11.5px] text-white/50 truncate">
                      {item.untertitel}
                    </span>
                    {(found?.zusammenfassung || item.text) && (
                      <span className="block text-[11.5px] text-white/60 leading-snug line-clamp-2 mt-0.5">
                        {found?.zusammenfassung || item.text}
                      </span>
                    )}
                  </span>
                  <span className="text-[10.5px] text-white/35 whitespace-nowrap">
                    {when(item.zeit)}
                  </span>
                </button>

                {open && (
                  <div className="px-3 pb-3 pt-0 space-y-2 border-t border-white/10 mt-1">
                    {found && (
                      <div className="text-[11.5px] text-white/60 leading-snug pt-2 space-y-0.5">
                        {found.zusammenfassung && <div>{found.zusammenfassung}</div>}
                        {(found.datum || found.zeit) && (
                          <div className="text-white/45">
                            🗓️ {found.datum} {found.zeit}
                          </div>
                        )}
                        {found.deadline && (
                          <div className="text-white/45">⏳ Deadline {found.deadline}</div>
                        )}
                        {found.personen.length > 0 && (
                          <div className="text-white/45">
                            👥 {found.personen.join(", ")}
                          </div>
                        )}
                        {found.projekt && (
                          <div className="text-white/45">📁 {found.projekt}</div>
                        )}
                      </div>
                    )}

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {item.kategorie === "email" && (
                        <button
                          onClick={() => void analyze(item, Boolean(found))}
                          disabled={analyzing === item.id}
                          className="text-[11.5px] px-2.5 py-1 rounded-lg bg-gold/80 text-black font-medium disabled:opacity-40"
                        >
                          {analyzing === item.id
                            ? "Jon liest …"
                            : found
                              ? "Neu auswerten"
                              : "Von Jon auswerten lassen"}
                        </button>
                      )}
                      {item.kategorie === "projekt" && item.root && (
                        <button
                          onClick={() => {
                            onOpenProject?.(item.root!);
                            onClose();
                          }}
                          className="text-[11.5px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10"
                        >
                          In Jon Code öffnen
                        </button>
                      )}
                      {onAsk && (
                        <button
                          onClick={() => {
                            onAsk(
                              `Fasse mir das zusammen und sag mir, was ich tun sollte: ${item.titel} — ${found?.zusammenfassung || item.text || item.untertitel}`
                            );
                            onClose();
                          }}
                          className="text-[11.5px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10"
                        >
                          Jon fragen
                        </button>
                      )}
                    </div>

                    {found && found.aktionen.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {found.aktionen.map((action, index) => (
                          <button
                            key={index}
                            onClick={() => setConfirm({ id: item.id, action })}
                            className="text-[11.5px] px-2.5 py-1 rounded-lg bg-sky-500/15 border border-sky-400/30 text-sky-200 hover:bg-sky-500/25"
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>
                    )}

                    {confirm?.id === item.id && (
                      <div className="rounded-lg border border-gold/30 bg-black/40 p-2.5 space-y-2">
                        <div className="text-[12px] text-white/80">
                          {confirm.action.label}?
                        </div>
                        <div className="text-[11px] text-white/45 leading-snug">
                          {Object.entries(confirm.action.payload)
                            .filter(([, value]) => value !== "" && value != null)
                            .map(([key, value]) => `${key}: ${String(value)}`)
                            .join(" · ") || "Ohne weitere Angaben"}
                        </div>
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => void apply(confirm.action)}
                            className="text-[11.5px] px-2.5 py-1 rounded-lg bg-gold/80 text-black font-medium"
                          >
                            Bestätigen
                          </button>
                          <button
                            onClick={() => setConfirm(null)}
                            className="text-[11.5px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70"
                          >
                            Abbrechen
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
