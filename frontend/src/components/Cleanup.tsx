import { useState } from "react";
import { CleanupPreview, cleanupApply, cleanupPreview } from "../lib/api";

const FOLDERS = [
  { id: "downloads", label: "Downloads" },
  { id: "desktop", label: "Desktop" },
  { id: "dokumente", label: "Dokumente" },
  { id: "bilder", label: "Bilder" },
];

export default function Cleanup({ onClose }: { onClose: () => void }) {
  const [folder, setFolder] = useState("downloads");
  const [by, setBy] = useState<"typ" | "datum">("typ");
  const [preview, setPreview] = useState<CleanupPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  const scan = async () => {
    setBusy(true);
    setError("");
    setDone("");
    setPreview(null);
    try {
      setPreview(await cleanupPreview(folder, by));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const apply = async () => {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      const res = await cleanupApply(preview.plan);
      setDone(`${res.moved} Dateien einsortiert${res.failed ? `, ${res.failed} übersprungen` : ""}. ✓`);
      setPreview(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[94vw] max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🧹</span>
            <span className="text-[14px] text-white/90">Ordner aufräumen</span>
            <span className="text-[11px] text-white/35">mit Vorschau — nichts ohne dein OK</span>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>

        <div className="p-4 overflow-y-auto">
          <div className="flex gap-1.5 mb-2">
            {FOLDERS.map((f) => (
              <button
                key={f.id}
                onClick={() => { setFolder(f.id); setPreview(null); setDone(""); }}
                className={`flex-1 py-2 rounded-xl border text-[12.5px] font-semibold transition ${
                  folder === f.id ? "border-gold/45 bg-gold/15 text-gold" : "border-white/10 bg-white/5 text-white/55 hover:bg-white/10"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex gap-1.5 mb-3">
            {(["typ", "datum"] as const).map((b) => (
              <button
                key={b}
                onClick={() => { setBy(b); setPreview(null); }}
                className={`flex-1 py-1.5 rounded-lg border text-[12px] transition ${
                  by === b ? "border-gold/40 bg-gold/10 text-gold/90" : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                }`}
              >
                {b === "typ" ? "Nach Dateityp" : "Nach Monat"}
              </button>
            ))}
          </div>

          <button
            onClick={() => void scan()}
            disabled={busy}
            className="w-full py-2.5 rounded-xl border border-white/10 bg-white/5 text-white/75 text-[13px] font-semibold hover:bg-white/10 disabled:opacity-40 transition"
          >
            {busy && !preview ? "Schaue nach …" : "Vorschau anzeigen"}
          </button>

          {error && <div className="mt-3 px-3 py-2 rounded-xl border border-red-400/30 bg-red-400/10 text-[12.5px] text-red-200">{error}</div>}
          {done && <div className="mt-3 px-3 py-2 rounded-xl border border-emerald-400/30 bg-emerald-400/10 text-[12.5px] text-emerald-200">{done}</div>}

          {preview && (
            <div className="mt-4">
              <div className="text-[12.5px] text-white/70 mb-2">
                Jon würde <b className="text-gold/90">{preview.count}</b> Dateien so einsortieren:
              </div>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {preview.summary.map((s) => (
                  <span key={s.ordner} className="text-[11.5px] px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70">
                    📁 {s.ordner} <span className="text-gold/80">{s.dateien}</span>
                  </span>
                ))}
              </div>
              <div className="max-h-40 overflow-y-auto rounded-xl border border-white/10 bg-black/20 p-2 space-y-1">
                {preview.sample.map((m, i) => (
                  <div key={i} className="text-[11.5px] text-white/55 flex items-center gap-1.5">
                    <span className="truncate flex-1">{m.name}</span>
                    <span className="text-white/30">→</span>
                    <span className="text-gold/70 shrink-0">{m.target}</span>
                  </div>
                ))}
                {preview.count > preview.sample.length && (
                  <div className="text-[11px] text-white/30 text-center pt-1">… und {preview.count - preview.sample.length} weitere</div>
                )}
              </div>
              <button
                onClick={() => void apply()}
                disabled={busy}
                className="w-full mt-3 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold disabled:opacity-50 hover:brightness-110 transition"
              >
                {busy ? "Räume auf …" : `Ja, ${preview.count} Dateien einsortieren`}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
