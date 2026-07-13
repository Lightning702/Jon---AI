import { P2PRequest } from "../lib/api";

interface Props {
  request: P2PRequest;
  busy: boolean;
  error: string;
  onDecide: (action: "accept" | "reject" | "block") => void;
}

export default function FriendRequestPopup({
  request,
  busy,
  error,
  onDecide,
}: Props) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-gold/40 w-[400px] max-w-[92vw] p-6 text-center shadow-gold">
        <div className="text-[11px] uppercase tracking-widest text-gold/70 mb-4">
          Neue Freundschaftsanfrage
        </div>
        <div className="text-6xl mb-3">{request.avatar || "🙂"}</div>
        <div className="text-[18px] text-white/95 font-semibold">
          {request.name}
        </div>
        <div className="text-[13px] text-white/50 mt-1">
          möchte mit dir schreiben
        </div>
        <div className="mt-3 inline-flex items-center gap-1.5 text-[12px] text-gold/90 bg-gold/10 border border-gold/25 rounded-full px-3 py-1">
          📍 {request.location || "Herkunft unbekannt"}
        </div>
        {error && (
          <div className="mt-3 text-[12px] text-red-300 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-1.5">
            {error}
          </div>
        )}
        <div className="mt-5 space-y-2">
          <button
            onClick={() => onDecide("accept")}
            disabled={busy}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] hover:brightness-110 disabled:opacity-50 transition"
          >
            {busy ? "…" : "✓ Annehmen & direkt schreiben"}
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => onDecide("reject")}
              disabled={busy}
              className="flex-1 py-2 rounded-xl border border-white/15 text-white/60 text-[13px] hover:bg-white/10 disabled:opacity-50 transition"
            >
              Ablehnen
            </button>
            <button
              onClick={() => onDecide("block")}
              disabled={busy}
              title="Blockieren — keine weiteren Anfragen von dieser Person"
              className="px-4 py-2 rounded-xl border border-red-400/30 text-red-300/80 text-[13px] hover:bg-red-400/10 disabled:opacity-50 transition"
            >
              🚫 Blockieren
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
