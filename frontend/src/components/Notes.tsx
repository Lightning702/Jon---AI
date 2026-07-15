import { useEffect, useState } from "react";
import { Note, addNote, deleteNote, getNotes, updateNote } from "../lib/api";

const COLORS: Record<string, string> = {
  gold: "border-gold/40 bg-gold/10",
  blau: "border-sky-400/40 bg-sky-400/10",
  gruen: "border-emerald-400/40 bg-emerald-400/10",
  rosa: "border-pink-400/40 bg-pink-400/10",
  lila: "border-violet-400/40 bg-violet-400/10",
};
const SWATCH: Record<string, string> = {
  gold: "#d4af37",
  blau: "#38bdf8",
  gruen: "#34d399",
  rosa: "#f472b6",
  lila: "#a78bfa",
};

export default function Notes({ onClose }: { onClose: () => void }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");
  const [color, setColor] = useState("gold");

  const load = () => void getNotes().then(setNotes);
  useEffect(load, []);

  const add = async () => {
    if (!text.trim()) return;
    await addNote(text.trim(), color);
    setText("");
    load();
  };

  const patch = async (id: string, p: Partial<Note>) => {
    await updateNote(id, p);
    load();
  };

  const remove = async (id: string) => {
    await deleteNote(id);
    load();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[600px] max-w-[95vw] h-[620px] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">📌</span>
            <span className="text-[14px] text-white/90">Haftnotizen</span>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>

        <div className="p-4 border-b border-white/10 shrink-0">
          <div className="flex gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void add()}
              placeholder="Neue Notiz …"
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
            />
            <button onClick={() => void add()} disabled={!text.trim()} className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold disabled:opacity-40 hover:brightness-110 transition">Anheften</button>
          </div>
          <div className="flex gap-1.5 mt-2">
            {Object.keys(SWATCH).map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-6 h-6 rounded-full border-2 transition ${color === c ? "border-white/80 scale-110" : "border-white/20"}`}
                style={{ background: SWATCH[c] }}
              />
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {notes.length === 0 && <div className="text-center text-[12.5px] text-white/30 py-8">Noch keine Notizen. Schreib deine erste.</div>}
          <div className="grid grid-cols-2 gap-2.5">
            {notes.map((n) => (
              <div key={n.id} className={`rounded-xl border px-3 py-2.5 ${COLORS[n.color] ?? COLORS.gold} ${n.done ? "opacity-45" : ""}`}>
                <div className="flex items-start gap-1.5">
                  <button onClick={() => void patch(n.id, { done: !n.done })} className="mt-0.5 text-[13px] shrink-0">{n.done ? "☑" : "☐"}</button>
                  <div className={`flex-1 text-[13px] text-white/90 leading-snug whitespace-pre-wrap break-words ${n.done ? "line-through" : ""}`}>{n.text}</div>
                </div>
                <div className="flex items-center gap-1.5 mt-2 justify-end">
                  <button onClick={() => void patch(n.id, { pinned: !n.pinned })} title="Anheften" className={`text-[12px] ${n.pinned ? "text-gold" : "text-white/30 hover:text-white/60"}`}>📌</button>
                  <button onClick={() => void remove(n.id)} className="text-white/30 hover:text-red-300 text-[12px]">✕</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
