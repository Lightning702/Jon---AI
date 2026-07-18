import { useState } from "react";
import { pairClaim, pairRequest } from "../lib/api";

export default function PairingScreen() {
  const [name, setName] = useState("Mein Handy");
  const [requestId, setRequestId] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await pairRequest(name.trim() || "Geraet");
      setRequestId(r.request_id);
    } catch {
      setError("Jon ist gerade nicht erreichbar.");
    }
    setBusy(false);
  };

  const claim = async () => {
    if (code.trim().length < 6) return;
    setBusy(true);
    setError("");
    const r = await pairClaim(requestId, code.trim());
    if (r.token) {
      localStorage.setItem("jon_device_token", r.token);
      window.location.reload();
      return;
    }
    setError(r.detail || "Falscher Code");
    setBusy(false);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050506]">
      <div className="glass rounded-2xl border border-white/15 w-[92%] max-w-sm p-6 text-center space-y-4">
        <div className="text-2xl">🔒</div>
        <div className="text-[16px] font-semibold gold-text">
          Dieses Gerät mit Jon koppeln
        </div>
        {!requestId ? (
          <>
            <p className="text-[13px] text-white/60 leading-relaxed">
              Jon lässt nur gekoppelte Geräte zu. Gib diesem Gerät einen Namen —
              am PC erscheint danach ein 6-stelliger Code.
            </p>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name dieses Geräts"
              className="w-full bg-white/5 border border-white/15 rounded-xl px-4 py-3 text-[14px] text-white outline-none focus:border-gold/50"
            />
            <button
              onClick={() => void start()}
              disabled={busy}
              className="w-full py-3 rounded-xl bg-gold/20 border border-gold/50 text-gold font-semibold text-[14px] disabled:opacity-50"
            >
              Koppeln starten
            </button>
          </>
        ) : (
          <>
            <p className="text-[13px] text-white/60 leading-relaxed">
              Am PC zeigt Jon jetzt einen 6-stelligen Code an. Tipp ihn hier
              ein:
            </p>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              inputMode="numeric"
              placeholder="000000"
              className="w-full bg-white/5 border border-white/15 rounded-xl px-4 py-3 text-[22px] tracking-[0.4em] text-center text-white outline-none focus:border-gold/50"
            />
            <button
              onClick={() => void claim()}
              disabled={busy || code.length < 6}
              className="w-full py-3 rounded-xl bg-gold/20 border border-gold/50 text-gold font-semibold text-[14px] disabled:opacity-50"
            >
              Bestätigen
            </button>
          </>
        )}
        {error && <div className="text-[12.5px] text-red-300">{error}</div>}
      </div>
    </div>
  );
}
