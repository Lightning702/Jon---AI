import { useEffect, useRef, useState } from "react";
import {
  JournalEntry,
  addJournal,
  askJournal,
  deleteJournal,
  getJournal,
  transcribeAudio,
} from "../lib/api";

const MOOD = { gut: "🙂", neutral: "😐", schlecht: "🙁" } as const;

export default function Journal({ onClose }: { onClose: () => void }) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const load = () => void getJournal().then(setEntries);
  useEffect(load, []);

  const startRec = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setBusy(true);
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const said = await transcribeAudio(blob);
          setText((t) => (t ? t + " " : "") + said);
        } catch {
          setError("Ich konnte die Aufnahme nicht verstehen.");
        } finally {
          setBusy(false);
        }
      };
      rec.start();
      recRef.current = rec;
      setRecording(true);
    } catch {
      setError("Kein Mikrofon-Zugriff. Erlaube das Mikrofon und versuch es nochmal.");
    }
  };

  const stopRec = () => {
    recRef.current?.stop();
    setRecording(false);
  };

  const save = async () => {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await addJournal(text.trim());
      setText("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const ask = async () => {
    if (!query.trim() || asking) return;
    setAsking(true);
    setAnswer("");
    try {
      setAnswer(await askJournal(query.trim()));
    } catch (e) {
      setAnswer(e instanceof Error ? e.message : String(e));
    } finally {
      setAsking(false);
    }
  };

  const remove = async (id: string) => {
    await deleteJournal(id);
    load();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[640px] max-w-[95vw] h-[680px] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">📔</span>
            <span className="text-[14px] text-white/90">Sprach-Tagebuch</span>
            <span className="text-[11px] text-white/35">sprich frei, Jon ordnet es</span>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>

        <div className="p-4 border-b border-white/10 shrink-0 space-y-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Erzähl von deinem Tag … (tippen oder sprechen)"
            className="w-full h-20 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40 resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={recording ? stopRec : startRec}
              disabled={busy}
              className={`px-3.5 py-2 rounded-xl text-[12.5px] font-semibold transition ${
                recording
                  ? "bg-red-500/80 text-white animate-pulse"
                  : "border border-white/10 bg-white/5 text-white/70 hover:bg-white/10"
              }`}
            >
              {recording ? "⏹ Stopp" : "🎙️ Sprechen"}
            </button>
            <button
              onClick={() => void save()}
              disabled={busy || !text.trim()}
              className="flex-1 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
            >
              {busy ? "…" : "Eintrag speichern"}
            </button>
          </div>
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void ask()}
              placeholder="Frag dein Tagebuch: „Was war letzte Woche los?“"
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12.5px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
            />
            <button
              onClick={() => void ask()}
              disabled={asking || !query.trim()}
              className="px-3.5 py-2 rounded-xl border border-gold/30 bg-gold/10 text-gold/90 text-[12.5px] font-semibold hover:bg-gold/20 disabled:opacity-40 transition"
            >
              {asking ? "…" : "Fragen"}
            </button>
          </div>
          {error && <div className="text-[12px] text-red-300">{error}</div>}
          {answer && (
            <div className="px-3 py-2 rounded-xl border border-gold/20 bg-gold/5 text-[12.5px] text-white/85 leading-relaxed whitespace-pre-wrap">
              {answer}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {entries.length === 0 && (
            <div className="text-center text-[12.5px] text-white/30 py-8">
              Noch keine Einträge. Sprich oder schreib deinen ersten.
            </div>
          )}
          {entries.map((e) => (
            <div key={e.id} className="rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5">
              <div className="flex items-center gap-2">
                <span>{MOOD[e.mood as keyof typeof MOOD] ?? "📝"}</span>
                <span className="text-[13px] font-semibold text-white/90 flex-1">{e.title}</span>
                <span className="text-[11px] text-white/35">{e.date} · {e.time}</span>
                <button onClick={() => void remove(e.id)} className="text-white/30 hover:text-red-300 text-[13px]">✕</button>
              </div>
              <div className="text-[12.5px] text-white/60 mt-1 leading-relaxed">{e.text}</div>
              {e.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {e.tags.map((t) => (
                    <span key={t} className="text-[10.5px] px-1.5 py-0.5 rounded-md bg-white/5 text-white/45">#{t}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
