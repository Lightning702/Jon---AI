import { useState } from "react";
import { StudioWork, saveStudioWork, studioFileUrl } from "../lib/api";

interface Props {
  data: StudioWork;
  onOpen?: () => void;
}

export default function BildCard({ data, onOpen }: Props) {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const url = studioFileUrl(data);
  const video = data.art === "video";

  const speichern = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const r = await saveStudioWork(data.id);
      setStatus(`Gespeichert: ${r.gespeichert}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 overflow-hidden max-w-[520px]">
      {video ? (
        <video src={url} controls loop className="w-full max-h-[420px] bg-black" />
      ) : (
        <img
          src={url}
          alt={data.prompt}
          className="w-full max-h-[420px] object-contain bg-black"
        />
      )}
      <div className="p-2.5">
        <div className="text-[12px] text-white/60 leading-snug">{data.prompt}</div>
        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
          <button
            onClick={() => void speichern()}
            disabled={busy}
            className="px-2.5 py-1 rounded-lg border border-gold/30 bg-gold/10 text-[11.5px] text-gold/90 hover:bg-gold/20 transition disabled:opacity-40"
          >
            {busy ? "…" : "⬇ Herunterladen"}
          </button>
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-[11.5px] text-white/60 hover:text-white/90 transition"
          >
            Groß ansehen
          </a>
          {onOpen && (
            <button
              onClick={onOpen}
              className="px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-[11.5px] text-white/60 hover:text-white/90 transition"
            >
              Im Studio öffnen
            </button>
          )}
          <span className="text-[10.5px] text-white/30 ml-auto">
            {data.anbieter_label} · {data.dauer_s}s
          </span>
        </div>
        {status && (
          <div className="text-[11px] text-white/45 mt-1.5 break-all">{status}</div>
        )}
      </div>
    </div>
  );
}
