import { useEffect, useRef, useState } from "react";
import {
  HumanizeScore,
  humanizeText,
  scoreText,
} from "../lib/api";

const STYLES = [
  { id: "neutral", label: "Neutral" },
  { id: "locker", label: "Locker" },
  { id: "schule", label: "Schule / Uni" },
  { id: "beruflich", label: "Beruflich" },
];

const STRENGTHS = [
  { value: 1, label: "Sanft" },
  { value: 2, label: "Mittel" },
  { value: 3, label: "Stark" },
];

interface Props {
  provider: string;
  model: string;
  onClose: () => void;
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 66
      ? "bg-red-400"
      : score >= 33
        ? "bg-amber-400"
        : "bg-emerald-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-[11px] text-white/50 w-32 text-right">
        {score}% · {label}
      </span>
    </div>
  );
}

export default function Humanizer({ provider, model, onClose }: Props) {
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [style, setStyle] = useState("neutral");
  const [strength, setStrength] = useState(2);
  const [before, setBefore] = useState<HumanizeScore | null>(null);
  const [after, setAfter] = useState<HumanizeScore | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    if (input.trim().length < 40) {
      setBefore(null);
      return;
    }
    timerRef.current = window.setTimeout(() => {
      void scoreText(input).then(setBefore).catch(() => setBefore(null));
    }, 500);
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [input]);

  const run = async () => {
    if (busy || input.trim().length < 20) return;
    setBusy(true);
    setError("");
    setOutput("");
    setAfter(null);
    try {
      const result = await humanizeText(input, style, strength, provider, model);
      setOutput(result.text);
      setBefore(result.before);
      setAfter(result.after);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const copy = () => {
    void navigator.clipboard.writeText(output);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[960px] max-w-[95vw] h-[680px] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-xl">✍️</span>
            <span className="text-[14px] text-white/90">Humanisierer</span>
            <span className="text-[11px] text-white/35">
              schreibt Texte natürlicher — Inhalt bleibt gleich
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
          >
            ✕
          </button>
        </div>

        <div className="px-5 py-3 border-b border-white/10 flex flex-wrap items-center gap-3">
          <div className="flex gap-1">
            {STYLES.map((s) => (
              <button
                key={s.id}
                onClick={() => setStyle(s.id)}
                className={`text-[11px] px-2.5 py-1 rounded-lg border transition ${
                  style === s.id
                    ? "border-gold/40 bg-gold/15 text-gold"
                    : "border-white/10 text-white/40 hover:bg-white/5"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <div className="flex gap-1">
            {STRENGTHS.map((s) => (
              <button
                key={s.value}
                onClick={() => setStrength(s.value)}
                className={`text-[11px] px-2.5 py-1 rounded-lg border transition ${
                  strength === s.value
                    ? "border-gold/40 bg-gold/15 text-gold"
                    : "border-white/10 text-white/40 hover:bg-white/5"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => void run()}
            disabled={busy || input.trim().length < 20}
            className="ml-auto px-4 py-1.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
          >
            {busy ? "Schreibt um …" : "Umschreiben"}
          </button>
        </div>

        <div className="flex-1 grid grid-cols-2 min-h-0 divide-x divide-white/10">
          <div className="flex flex-col min-h-0">
            <div className="px-4 pt-3 pb-2 space-y-2">
              <div className="text-[11px] uppercase tracking-wide text-white/40">
                Dein Text
              </div>
              {before && <ScoreBar score={before.score} label={before.label} />}
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Text hier einfügen …"
              className="flex-1 mx-4 mb-4 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40 resize-none"
            />
          </div>

          <div className="flex flex-col min-h-0">
            <div className="px-4 pt-3 pb-2 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-[11px] uppercase tracking-wide text-white/40">
                  Umgeschrieben
                </div>
                {output && (
                  <button
                    onClick={copy}
                    className="text-[11px] px-2 py-0.5 rounded-lg border border-white/10 text-white/50 hover:text-gold hover:border-gold/40 transition"
                  >
                    {copied ? "✓ kopiert" : "Kopieren"}
                  </button>
                )}
              </div>
              {after && <ScoreBar score={after.score} label={after.label} />}
            </div>
            <div className="flex-1 mx-4 mb-4 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 overflow-y-auto">
              {error && (
                <div className="text-[12px] text-red-300">{error}</div>
              )}
              {!error && !output && !busy && (
                <div className="text-[12px] text-white/25">
                  Der umgeschriebene Text erscheint hier.
                </div>
              )}
              {busy && (
                <div className="text-[12px] text-gold/70">
                  Jon schreibt den Text um …
                </div>
              )}
              {output && (
                <div className="whitespace-pre-wrap text-[13px] text-white/90 leading-relaxed">
                  {output}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="px-5 py-2 border-t border-white/10 text-[11px] text-white/30">
          Die Prozentzahl ist eine grobe eigene Schätzung (Satzlängen-Verteilung und
          typische Floskeln), kein echter KI-Detektor — echte Detektoren rechnen anders
          und liegen oft daneben.
        </div>
      </div>
    </div>
  );
}
