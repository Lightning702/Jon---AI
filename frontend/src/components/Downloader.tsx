import { useEffect, useRef, useState } from "react";
import {
  DownloadInfo,
  analyzeDownload,
  downloadFileUrl,
  downloadProgressUrl,
  startDownload,
} from "../lib/api";

const QUALITIES = [
  { id: "best", label: "Beste" },
  { id: "1080", label: "1080p" },
  { id: "720", label: "720p" },
  { id: "480", label: "480p" },
];

interface Progress {
  status: string;
  percent: number;
  speed: number;
  eta: number | null;
  error: string | null;
  name: string | null;
}

function fmtDuration(total: number): string {
  if (!total) return "";
  const s = Math.round(total);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return (h ? `${h}:${String(m).padStart(2, "0")}` : `${m}`) + `:${String(r).padStart(2, "0")}`;
}

function fmtSpeed(bps: number): string {
  if (!bps) return "";
  if (bps > 1048576) return `${(bps / 1048576).toFixed(1)} MB/s`;
  return `${Math.round(bps / 1024)} KB/s`;
}

function fmtEta(sec: number | null): string {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `noch ${m ? `${m} min ` : ""}${s} s`;
}

export default function Downloader({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [info, setInfo] = useState<DownloadInfo | null>(null);
  const [format, setFormat] = useState<"mp4" | "mp3">("mp4");
  const [quality, setQuality] = useState("best");
  const [analyzing, setAnalyzing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [doneName, setDoneName] = useState("");
  const [error, setError] = useState("");
  const sourceRef = useRef<EventSource | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    return () => sourceRef.current?.close();
  }, []);

  const analyze = async (value?: string) => {
    const link = (value ?? url).trim();
    if (!link || analyzing || busy) return;
    setError("");
    setInfo(null);
    setProgress(null);
    setDoneName("");
    setAnalyzing(true);
    try {
      const data = await analyzeDownload(link);
      setInfo(data);
      setFormat(data.audio_only || data.music ? "mp3" : "mp4");
      setQuality("best");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
    }
  };

  const run = async () => {
    if (!info || busy) return;
    setBusy(true);
    setError("");
    setDoneName("");
    setProgress({ status: "starting", percent: 0, speed: 0, eta: null, error: null, name: null });
    try {
      const job = await startDownload(info.url, format, quality, info.music ? info.title : "");
      const source = new EventSource(downloadProgressUrl(job));
      sourceRef.current = source;
      source.onmessage = (event) => {
        const d: Progress = JSON.parse(event.data);
        setProgress(d);
        if (d.status === "done") {
          source.close();
          setBusy(false);
          setDoneName(d.name ?? "Datei");
          window.location.href = downloadFileUrl(job);
        }
        if (d.status === "error") {
          source.close();
          setBusy(false);
          setProgress(null);
          setError(d.error ?? "Download fehlgeschlagen.");
        }
      };
      source.onerror = () => {
        source.close();
        setBusy(false);
        setProgress(null);
        setError("Verbindung zum Backend verloren.");
      };
    } catch (e) {
      setBusy(false);
      setProgress(null);
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const reset = () => {
    sourceRef.current?.close();
    setUrl("");
    setInfo(null);
    setProgress(null);
    setDoneName("");
    setError("");
    setBusy(false);
    inputRef.current?.focus();
  };

  const pct = progress ? Math.max(2, progress.percent) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[620px] max-w-[95vw] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">⬇️</span>
            <span className="text-[14px] text-white/90">Downloader</span>
            <span className="text-[11px] text-white/35">
              YouTube · TikTok · Instagram · X · Spotify · Amazon Music
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
          >
            ✕
          </button>
        </div>

        <div className="p-5 overflow-y-auto">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void analyze();
              }}
              onPaste={(e) => {
                const pasted = e.clipboardData.getData("text");
                window.setTimeout(() => void analyze(pasted), 60);
              }}
              placeholder="Link hier einfügen …"
              spellCheck={false}
              className="flex-1 min-w-0 bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40 transition"
            />
            <button
              onClick={() => void analyze()}
              disabled={analyzing || busy || !url.trim()}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
            >
              {analyzing ? "Prüft …" : "Prüfen"}
            </button>
          </div>

          {error && (
            <div className="mt-4 px-4 py-3 rounded-xl border border-red-400/35 bg-red-400/10 text-[12.5px] text-red-200 leading-relaxed">
              {error}
            </div>
          )}

          {analyzing && (
            <div className="mt-5 space-y-2 animate-pulse">
              <div className="h-36 rounded-xl bg-white/5" />
              <div className="h-4 w-2/3 rounded bg-white/5" />
              <div className="h-3 w-1/3 rounded bg-white/5" />
            </div>
          )}

          {info && !analyzing && (
            <div className="mt-5">
              {info.thumbnail && (
                <div className="relative rounded-xl overflow-hidden border border-white/10">
                  <img
                    src={info.thumbnail}
                    alt=""
                    className="w-full aspect-video object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
                  {info.duration > 0 && (
                    <span className="absolute right-2.5 bottom-2.5 px-2 py-0.5 rounded-lg bg-black/60 border border-white/15 text-[11px] font-semibold">
                      {fmtDuration(info.duration)}
                    </span>
                  )}
                </div>
              )}
              <div className="mt-3 text-[14px] font-semibold text-white/90 leading-snug line-clamp-2">
                {info.title}
              </div>
              <div className="text-[11.5px] text-white/40 mt-0.5">
                {[info.uploader, info.extractor].filter(Boolean).join(" · ")}
              </div>
              {info.music && (
                <div className="mt-2 px-3 py-2 rounded-xl border border-gold/25 bg-gold/10 text-[11.5px] text-gold/80 leading-relaxed">
                  🎵 {info.extractor}-Link erkannt. {info.extractor} ist kopiergeschützt —
                  ich lade die passende Aufnahme von YouTube: „{info.matched}"
                </div>
              )}

              <div className="mt-4 text-[10.5px] uppercase tracking-widest text-white/35">
                Format
              </div>
              <div className="mt-1.5 flex gap-1.5">
                <button
                  onClick={() => !busy && !info.audio_only && !info.music && setFormat("mp4")}
                  disabled={info.audio_only || info.music}
                  className={`flex-1 py-2 rounded-xl border text-[12.5px] font-semibold transition disabled:opacity-30 ${
                    format === "mp4"
                      ? "border-gold/45 bg-gold/15 text-gold"
                      : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                  }`}
                >
                  MP4 · Video
                </button>
                <button
                  onClick={() => !busy && setFormat("mp3")}
                  className={`flex-1 py-2 rounded-xl border text-[12.5px] font-semibold transition ${
                    format === "mp3"
                      ? "border-gold/45 bg-gold/15 text-gold"
                      : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                  }`}
                >
                  MP3 · Nur Ton (320 kbps)
                </button>
              </div>

              {format === "mp4" && (
                <>
                  <div className="mt-3 text-[10.5px] uppercase tracking-widest text-white/35">
                    Qualität
                  </div>
                  <div className="mt-1.5 flex gap-1.5">
                    {QUALITIES.map((q) => {
                      const off =
                        q.id !== "best" &&
                        info.max_height > 0 &&
                        Number(q.id) > info.max_height;
                      return (
                        <button
                          key={q.id}
                          onClick={() => !busy && !off && setQuality(q.id)}
                          disabled={off}
                          className={`flex-1 py-2 rounded-xl border text-[12.5px] font-semibold transition disabled:opacity-30 ${
                            quality === q.id && !off
                              ? "border-gold/45 bg-gold/15 text-gold"
                              : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                          }`}
                        >
                          {q.label}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}

              {!doneName && (
                <button
                  onClick={() => void run()}
                  disabled={busy}
                  className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13.5px] shadow-gold disabled:opacity-50 hover:brightness-110 transition"
                >
                  {busy
                    ? "Lädt …"
                    : format === "mp3"
                      ? "MP3 herunterladen"
                      : "Video herunterladen"}
                </button>
              )}

              {progress && (
                <div className="mt-4">
                  <div className="h-2.5 rounded-full bg-white/10 border border-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        doneName
                          ? "bg-emerald-400"
                          : "bg-gradient-to-r from-gold-dark via-gold to-gold-light"
                      }`}
                      style={{ width: `${doneName ? 100 : pct}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-1.5 text-[11.5px] text-white/45">
                    <span className="text-white/80 font-semibold">
                      {Math.floor(doneName ? 100 : progress.percent)}%
                    </span>
                    <span>{fmtSpeed(progress.speed)}</span>
                    <span>
                      {progress.status === "downloading" ? fmtEta(progress.eta) : ""}
                    </span>
                  </div>
                  <div
                    className={`mt-2 text-center text-[12.5px] ${
                      doneName ? "text-emerald-300" : "text-white/60"
                    }`}
                  >
                    {doneName
                      ? `Fertig — ${doneName} wird gespeichert ✓`
                      : progress.status === "processing"
                        ? format === "mp3"
                          ? "Wandle in MP3 um …"
                          : "Füge Video zusammen …"
                        : progress.status === "downloading"
                          ? "Lade herunter …"
                          : "Starte …"}
                  </div>
                </div>
              )}

              {doneName && (
                <button
                  onClick={reset}
                  className="w-full mt-3 py-2.5 rounded-xl border border-white/10 bg-white/5 text-[12.5px] text-white/60 hover:bg-white/10 transition"
                >
                  Anderen Link laden
                </button>
              )}
            </div>
          )}
        </div>

        <div className="px-5 py-2 border-t border-white/10 text-[10.5px] text-white/30 shrink-0">
          Läuft komplett lokal. Bitte nur Inhalte laden, die du laden darfst.
        </div>
      </div>
    </div>
  );
}
