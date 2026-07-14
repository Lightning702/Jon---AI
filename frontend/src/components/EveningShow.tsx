import { useEffect, useRef, useState } from "react";
import { ShowLine, buildShow } from "../lib/api";
import { speakAs, stopSpeaking } from "../lib/tts";

interface Props {
  provider: string;
  model: string;
  onClose: () => void;
}

export default function EveningShow({ provider, model, onClose }: Props) {
  const [lines, setLines] = useState<ShowLine[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(-1);
  const cancelRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void (async () => {
      try {
        setLines(await buildShow(provider, model));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      cancelRef.current = true;
      stopSpeaking();
    };
  }, [provider, model]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [current]);

  const play = async () => {
    if (playing || !lines.length) return;
    setPlaying(true);
    cancelRef.current = false;
    for (let i = 0; i < lines.length; i++) {
      if (cancelRef.current) break;
      setCurrent(i);
      const line = lines[i];
      await speakAs(line.text, line.speaker === "mini" ? "junior" : "papa");
    }
    setPlaying(false);
    setCurrent(-1);
  };

  const stop = () => {
    cancelRef.current = true;
    stopSpeaking();
    setPlaying(false);
    setCurrent(-1);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[94vw] max-h-[88vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎙️</span>
            <span className="text-[14px] text-white/90">Abend-Show</span>
            <span className="text-[11px] text-white/35">Jon &amp; Mini Jon über deinen Tag</span>
          </div>
          <button
            onClick={() => {
              stop();
              onClose();
            }}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
          >
            ✕
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {loading && (
            <div className="text-center text-[13px] text-gold/70 py-10">
              Jon und Mini Jon schreiben gerade das Skript für heute …
            </div>
          )}
          {error && (
            <div className="px-4 py-3 rounded-xl border border-red-400/35 bg-red-400/10 text-[12.5px] text-red-200">
              {error}
            </div>
          )}
          {lines.map((line, i) => {
            const mini = line.speaker === "mini";
            return (
              <div
                key={i}
                className={`flex ${mini ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[78%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed border transition-all ${
                    mini
                      ? "bg-gold/10 border-gold/25 text-white/90"
                      : "bg-white/5 border-white/10 text-white/85"
                  } ${current === i ? "ring-2 ring-gold/50 scale-[1.02]" : ""}`}
                >
                  <div className="text-[10px] uppercase tracking-wider mb-1 text-white/40">
                    {mini ? "Mini Jon" : "Jon"}
                  </div>
                  {line.text}
                </div>
              </div>
            );
          })}
        </div>

        {!loading && !error && (
          <div className="px-5 py-3 border-t border-white/10 flex gap-2 shrink-0">
            {!playing ? (
              <button
                onClick={() => void play()}
                className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold hover:brightness-110 transition"
              >
                ▶ Vorspielen (echte Stimmen)
              </button>
            ) : (
              <button
                onClick={stop}
                className="flex-1 py-2.5 rounded-xl border border-white/15 bg-white/5 text-white/70 font-semibold text-[13px] hover:bg-white/10 transition"
              >
                ⏹ Stopp
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
