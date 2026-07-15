import { useEffect, useState } from "react";
import { explainScreen } from "../lib/api";
import { speak, stopSpeaking } from "../lib/tts";

export default function ScreenExplain({ onClose }: { onClose: () => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const run = async () => {
    setLoading(true);
    setError("");
    setText("");
    try {
      const explanation = await explainScreen();
      setText(explanation);
      void speak(explanation);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void run();
    return () => stopSpeaking();
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[94vw] max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🔍</span>
            <span className="text-[14px] text-white/90">Jon erklärt den Bildschirm</span>
          </div>
          <button onClick={() => { stopSpeaking(); onClose(); }} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
        </div>
        <div className="p-5 overflow-y-auto">
          {loading && <div className="text-center text-[13px] text-gold/70 py-8">Jon schaut sich deinen Bildschirm an …</div>}
          {error && <div className="px-4 py-3 rounded-xl border border-red-400/30 bg-red-400/10 text-[12.5px] text-red-200 leading-relaxed">{error}</div>}
          {text && <div className="text-[13.5px] text-white/85 leading-relaxed whitespace-pre-wrap">{text}</div>}
        </div>
        {!loading && (
          <div className="px-5 py-3 border-t border-white/10 flex gap-2 shrink-0">
            <button onClick={() => void run()} className="flex-1 py-2.5 rounded-xl border border-white/10 bg-white/5 text-white/70 text-[13px] font-semibold hover:bg-white/10 transition">Nochmal anschauen</button>
            {text && <button onClick={() => void speak(text)} className="px-4 py-2.5 rounded-xl border border-gold/30 bg-gold/10 text-gold/90 text-[13px] font-semibold hover:bg-gold/20 transition">🔊 Vorlesen</button>}
          </div>
        )}
      </div>
    </div>
  );
}
